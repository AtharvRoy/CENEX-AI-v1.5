#!/usr/bin/env python3
"""
🔱 CENEX AI - Backtesting Engine
Test trading strategies on historical data

Strategies:
1. Momentum - Buy strong performers
2. Mean Reversion - Buy oversold, sell overbought
3. Breakout - Buy price breakouts above resistance
4. Trend Following - Follow moving average crossovers
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class Strategy:
    """Base strategy class"""
    
    def __init__(self, name):
        self.name = name
        self.trades = []
        self.positions = []
    
    def generate_signals(self, data):
        """Generate buy/sell signals - override in subclasses"""
        raise NotImplementedError
    
    def backtest(self, data, initial_capital=100000):
        """Run backtest on historical data"""
        signals = self.generate_signals(data)
        
        capital = initial_capital
        position = 0
        entry_price = 0
        
        for i in range(len(data)):
            price = data['Close'].iloc[i]
            signal = signals.iloc[i]
            
            # Buy signal
            if signal == 1 and position == 0:
                shares = capital // price
                if shares > 0:
                    position = shares
                    entry_price = price
                    capital -= shares * price
                    self.trades.append({
                        'type': 'BUY',
                        'date': data.index[i],
                        'price': price,
                        'shares': shares
                    })
            
            # Sell signal
            elif signal == -1 and position > 0:
                capital += position * price
                pnl = (price - entry_price) * position
                self.trades.append({
                    'type': 'SELL',
                    'date': data.index[i],
                    'price': price,
                    'shares': position,
                    'pnl': pnl
                })
                position = 0
                entry_price = 0
        
        # Close any open position
        if position > 0:
            final_price = data['Close'].iloc[-1]
            capital += position * final_price
            pnl = (final_price - entry_price) * position
            self.trades.append({
                'type': 'SELL',
                'date': data.index[-1],
                'price': final_price,
                'shares': position,
                'pnl': pnl
            })
        
        return capital


class MomentumStrategy(Strategy):
    """Buy when price momentum is strong"""
    
    def __init__(self, period=20):
        super().__init__(f"Momentum ({period}d)")
        self.period = period
    
    def generate_signals(self, data):
        """Generate signals based on momentum"""
        close = data['Close']
        momentum = close.pct_change(self.period)
        
        signals = pd.Series(0, index=data.index)
        signals[momentum > 0.05] = 1  # Buy if >5% gain
        signals[momentum < -0.03] = -1  # Sell if <-3% loss
        
        return signals


class MeanReversionStrategy(Strategy):
    """Buy oversold, sell overbought"""
    
    def __init__(self, period=20, std_dev=2):
        super().__init__(f"Mean Reversion ({period}d, {std_dev}σ)")
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data):
        """Generate signals based on Bollinger Bands"""
        close = data['Close']
        sma = close.rolling(window=self.period).mean()
        std = close.rolling(window=self.period).std()
        
        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)
        
        signals = pd.Series(0, index=data.index)
        signals[close < lower_band] = 1  # Buy when below lower band
        signals[close > upper_band] = -1  # Sell when above upper band
        
        return signals


class BreakoutStrategy(Strategy):
    """Buy price breakouts above resistance"""
    
    def __init__(self, period=20):
        super().__init__(f"Breakout ({period}d)")
        self.period = period
    
    def generate_signals(self, data):
        """Generate signals based on breakouts"""
        close = data['Close']
        high = data['High'].rolling(window=self.period).max()
        low = data['Low'].rolling(window=self.period).min()
        
        signals = pd.Series(0, index=data.index)
        signals[close > high.shift(1)] = 1  # Buy on breakout above resistance
        signals[close < low.shift(1)] = -1  # Sell on breakdown below support
        
        return signals


class TrendFollowingStrategy(Strategy):
    """Follow moving average crossovers"""
    
    def __init__(self, short_period=20, long_period=50):
        super().__init__(f"Trend Following ({short_period}/{long_period} MA)")
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, data):
        """Generate signals based on MA crossovers"""
        close = data['Close']
        short_ma = close.rolling(window=self.short_period).mean()
        long_ma = close.rolling(window=self.long_period).mean()
        
        signals = pd.Series(0, index=data.index)
        
        # Golden cross - buy
        signals[(short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))] = 1
        
        # Death cross - sell
        signals[(short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))] = -1
        
        return signals


class Backtester:
    """Main backtesting engine"""
    
    def __init__(self, symbol, start_date, end_date):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.data = None
        self.strategies = [
            MomentumStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy()
        ]
    
    def fetch_data(self):
        """Fetch historical data"""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(self.symbol)
            self.data = stock.history(start=self.start_date, end=self.end_date)
            
            if self.data.empty:
                console.print(f"[red]❌ No data found for {self.symbol}[/red]")
                return False
            
            return True
        
        except Exception as e:
            console.print(f"[red]❌ Error fetching data: {e}[/red]")
            return False
    
    def calculate_metrics(self, initial_capital, final_capital, trades):
        """Calculate performance metrics"""
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Calculate returns for each trade
        returns = []
        for trade in trades:
            if trade['type'] == 'SELL' and 'pnl' in trade:
                returns.append(trade['pnl'])
        
        if not returns:
            return {
                'total_return': total_return,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'num_trades': 0
            }
        
        returns = np.array(returns)
        
        # Sharpe ratio (simplified)
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Win rate
        wins = len([r for r in returns if r > 0])
        win_rate = (wins / len(returns)) * 100 if returns else 0
        
        # Max drawdown (simplified)
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) * 100 if len(drawdown) > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len([t for t in trades if t['type'] == 'BUY'])
        }
    
    def run(self, initial_capital=100000):
        """Run backtest for all strategies"""
        if not self.fetch_data():
            return
        
        console.print(f"\n[cyan]📊 Backtesting {self.symbol}[/cyan]")
        console.print(f"[dim]Period: {self.start_date} to {self.end_date}[/dim]")
        console.print(f"[dim]Data points: {len(self.data)} days[/dim]")
        console.print(f"[dim]Initial capital: ₹{initial_capital:,.0f}[/dim]\n")
        
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for strategy in self.strategies:
                task = progress.add_task(f"Testing {strategy.name}...", total=None)
                
                final_capital = strategy.backtest(self.data, initial_capital)
                metrics = self.calculate_metrics(initial_capital, final_capital, strategy.trades)
                
                results.append({
                    'strategy': strategy.name,
                    'final_capital': final_capital,
                    **metrics
                })
                
                progress.remove_task(task)
        
        # Display results
        self.display_results(results, initial_capital)
        
        return results
    
    def display_results(self, results, initial_capital):
        """Display backtest results in a table"""
        table = Table(
            title="🏆 Backtest Results",
            box=box.DOUBLE,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Strategy", style="bold white", width=25)
        table.add_column("Final Capital", justify="right", style="yellow")
        table.add_column("Return", justify="right", width=12)
        table.add_column("Sharpe", justify="right", width=10)
        table.add_column("Max DD", justify="right", width=10)
        table.add_column("Win Rate", justify="right", width=10)
        table.add_column("Trades", justify="right", width=8)
        
        # Sort by return
        results = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        for i, result in enumerate(results):
            return_color = "green" if result['total_return'] > 0 else "red"
            
            # Mark best strategy
            rank = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else ""
            
            table.add_row(
                f"{rank} {result['strategy']}",
                f"₹{result['final_capital']:,.0f}",
                f"[{return_color}]{result['total_return']:+.2f}%[/{return_color}]",
                f"{result['sharpe_ratio']:.2f}",
                f"{result['max_drawdown']:.1f}%",
                f"{result['win_rate']:.1f}%",
                str(result['num_trades'])
            )
        
        console.print(table)
        
        # Show best strategy
        best = results[0]
        if best['total_return'] > 0:
            console.print(f"\n[green]✅ Best Strategy: {best['strategy']} ({best['total_return']:+.2f}% return)[/green]")
        else:
            console.print(f"\n[yellow]⚠️  Best Strategy: {best['strategy']} ({best['total_return']:+.2f}% return)[/yellow]")
            console.print("[dim]All strategies lost money in this period[/dim]")


def main():
    """CLI entry point"""
    console.print(Panel(
        "[bold cyan]🔱 CENEX AI - Backtesting Engine[/bold cyan]\n"
        "Test trading strategies on historical data",
        box=box.DOUBLE,
        border_style="cyan"
    ))
    
    # Get inputs
    symbol = input("\n💹 Stock symbol (default: RELIANCE.NS): ").strip() or "RELIANCE.NS"
    
    # Default to 1 year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    initial_capital = 100000
    capital_input = input(f"💰 Initial capital (default: ₹{initial_capital:,}): ").strip()
    if capital_input:
        try:
            initial_capital = float(capital_input)
        except:
            pass
    
    # Run backtest
    backtester = Backtester(symbol, start_date, end_date)
    backtester.run(initial_capital)
    
    console.print("\n[dim]Backtest complete![/dim]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise
