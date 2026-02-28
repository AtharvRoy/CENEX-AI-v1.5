#!/usr/bin/env python3
"""
🔱 CENEX AI - Terminal User Interface
Full interactive terminal experience - like OpenClaw but for trading

Run: python cenex_tui.py
"""

import os
import sys
from datetime import datetime, timedelta
from time import sleep

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    from rich.text import Text
    from rich.columns import Columns
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install rich yfinance pandas numpy")
    sys.exit(1)

console = Console()

# Color scheme
COLORS = {
    'primary': 'cyan',
    'success': 'green',
    'danger': 'red',
    'warning': 'yellow',
    'info': 'blue',
    'muted': 'bright_black'
}

class CenexAI:
    """Main application class"""
    
    def __init__(self):
        self.watchlist = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']
        self.signals = []
        self.portfolio = []
        
    def show_banner(self):
        """Display startup banner"""
        banner = Text()
        banner.append("🔱 ", style="bold cyan")
        banner.append("CENEX AI", style="bold white")
        banner.append(" - Institutional Trading Intelligence\n", style="cyan")
        banner.append("Built by CNX Studios | Phase 1 MVP", style="dim")
        
        console.print(Panel(
            banner,
            box=box.DOUBLE,
            border_style="cyan",
            padding=(1, 2)
        ))
        
    def main_menu(self):
        """Show main menu"""
        console.clear()
        self.show_banner()
        
        menu_items = [
            "[1] 📊 Live Dashboard",
            "[2] 🔍 Scan Market",
            "[3] 📈 View Signals",
            "[4] 💼 Portfolio",
            "[5] ⚙️  Settings",
            "[6] 🚪 Exit"
        ]
        
        console.print("\n")
        for item in menu_items:
            console.print(f"  {item}", style="bright_white")
        
        console.print("\n")
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "5", "6"], default="1")
        
        return choice
    
    def live_dashboard(self):
        """Show live dashboard with market data"""
        console.clear()
        console.print(Panel("[bold cyan]📊 Live Dashboard[/bold cyan]", box=box.ROUNDED))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading market data...", total=None)
            
            try:
                import yfinance as yf
                import pandas as pd
                
                # Fetch data for watchlist
                data = {}
                for symbol in self.watchlist:
                    stock = yf.Ticker(symbol)
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        data[symbol] = {
                            'price': hist['Close'].iloc[-1],
                            'change': ((hist['Close'].iloc[-1] / hist['Open'].iloc[-1]) - 1) * 100,
                            'volume': hist['Volume'].iloc[-1]
                        }
                
                progress.stop()
                console.clear()
                self.show_banner()
                
                # Create dashboard layout
                table = Table(
                    title="🎯 Watchlist",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan"
                )
                
                table.add_column("Symbol", style="bold white", width=15)
                table.add_column("Price", justify="right", style="yellow")
                table.add_column("Change", justify="right", width=12)
                table.add_column("Volume", justify="right", style="dim")
                table.add_column("Status", justify="center", width=10)
                
                for symbol, info in data.items():
                    change_color = "green" if info['change'] > 0 else "red"
                    change_text = f"{info['change']:+.2f}%"
                    
                    # Simple status indicator
                    if abs(info['change']) > 2:
                        status = "🔥 HOT"
                        status_style = "bold red"
                    elif abs(info['change']) > 1:
                        status = "📈 Active"
                        status_style = "yellow"
                    else:
                        status = "💤 Calm"
                        status_style = "dim"
                    
                    table.add_row(
                        symbol.replace('.NS', ''),
                        f"₹{info['price']:.2f}",
                        Text(change_text, style=change_color),
                        f"{info['volume']:,.0f}",
                        Text(status, style=status_style)
                    )
                
                console.print("\n")
                console.print(table)
                
                # Quick stats
                console.print("\n")
                stats = Columns([
                    Panel(f"[bold green]{len(data)}[/bold green]\nTracking", border_style="green"),
                    Panel(f"[bold yellow]{len(self.signals)}[/bold yellow]\nActive Signals", border_style="yellow"),
                    Panel(f"[bold cyan]₹0[/bold cyan]\nP&L Today", border_style="cyan"),
                ], equal=True, expand=True)
                console.print(stats)
                
            except Exception as e:
                progress.stop()
                console.print(f"\n[red]❌ Error: {e}[/red]")
                console.print("[dim]Tip: pip install yfinance pandas[/dim]")
        
        console.print("\n")
        Prompt.ask("Press Enter to continue", default="")
    
    def scan_market(self):
        """Scan market and generate signals"""
        console.clear()
        console.print(Panel("[bold cyan]🔍 Market Scanner[/bold cyan]", box=box.ROUNDED))
        
        symbol = Prompt.ask("\n💹 Enter stock symbol", default="RELIANCE.NS")
        
        console.print(f"\n[cyan]Analyzing {symbol}...[/cyan]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Simulate analysis stages
            stages = [
                "Fetching market data",
                "Calculating indicators",
                "Running Quant Agent",
                "Running Sentiment Agent",
                "Running Regime Agent",
                "Running Risk Agent",
                "Ensemble decision",
                "Quality filtering"
            ]
            
            for stage in stages:
                task = progress.add_task(f"[cyan]{stage}...", total=None)
                sleep(0.5)  # Simulate processing
                progress.remove_task(task)
            
            progress.stop()
        
        try:
            import yfinance as yf
            import numpy as np
            
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo")
            
            if hist.empty:
                console.print(f"[red]❌ No data found for {symbol}[/red]")
                Prompt.ask("\nPress Enter to continue", default="")
                return
            
            # Quick analysis
            close = hist['Close']
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]
            
            # Signal logic
            if rsi_val < 35:
                signal = "BUY"
                signal_color = "green"
                confidence = 78
            elif rsi_val > 65:
                signal = "SELL"
                signal_color = "red"
                confidence = 75
            else:
                signal = "HOLD"
                signal_color = "yellow"
                confidence = 55
            
            current_price = close.iloc[-1]
            target = current_price * 1.05
            stoploss = current_price * 0.97
            
            # Display result
            console.print("\n")
            result = Table(box=box.DOUBLE, border_style=signal_color, show_header=False)
            result.add_column("Field", style="bold white")
            result.add_column("Value", style=signal_color)
            
            result.add_row("🎯 Signal", f"[bold {signal_color}]{signal}[/bold {signal_color}]")
            result.add_row("📊 Confidence", f"{confidence}%")
            result.add_row("💰 Entry Price", f"₹{current_price:.2f}")
            result.add_row("🎯 Target", f"₹{target:.2f} (+{((target/current_price)-1)*100:.1f}%)")
            result.add_row("🛑 Stop Loss", f"₹{stoploss:.2f} ({((stoploss/current_price)-1)*100:.1f}%)")
            result.add_row("📈 RSI", f"{rsi_val:.2f}")
            
            console.print(result)
            
            # Save signal
            if signal != "HOLD":
                if Confirm.ask("\n💾 Save this signal?", default=True):
                    self.signals.append({
                        'symbol': symbol,
                        'signal': signal,
                        'confidence': confidence,
                        'entry': current_price,
                        'target': target,
                        'stoploss': stoploss,
                        'timestamp': datetime.now()
                    })
                    console.print("[green]✅ Signal saved![/green]")
        
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")
        
        console.print("\n")
        Prompt.ask("Press Enter to continue", default="")
    
    def view_signals(self):
        """View saved signals"""
        console.clear()
        console.print(Panel("[bold cyan]📈 Active Signals[/bold cyan]", box=box.ROUNDED))
        
        if not self.signals:
            console.print("\n[yellow]No active signals. Run a market scan first![/yellow]")
            Prompt.ask("\nPress Enter to continue", default="")
            return
        
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("#", style="dim", width=4)
        table.add_column("Symbol", style="bold white")
        table.add_column("Signal", justify="center")
        table.add_column("Confidence", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("Target", justify="right")
        table.add_column("Time", style="dim")
        
        for i, sig in enumerate(self.signals, 1):
            signal_style = "green" if sig['signal'] == "BUY" else "red"
            table.add_row(
                str(i),
                sig['symbol'].replace('.NS', ''),
                Text(sig['signal'], style=f"bold {signal_style}"),
                f"{sig['confidence']}%",
                f"₹{sig['entry']:.2f}",
                f"₹{sig['target']:.2f}",
                sig['timestamp'].strftime("%H:%M")
            )
        
        console.print("\n")
        console.print(table)
        console.print("\n")
        Prompt.ask("Press Enter to continue", default="")
    
    def portfolio_view(self):
        """Show portfolio"""
        console.clear()
        console.print(Panel("[bold cyan]💼 Portfolio[/bold cyan]", box=box.ROUNDED))
        
        console.print("\n[yellow]Portfolio tracking coming soon![/yellow]")
        console.print("[dim]This will show your positions, P&L, and performance metrics.[/dim]")
        
        # Mock data for demo
        demo_table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        demo_table.add_column("Symbol")
        demo_table.add_column("Qty", justify="right")
        demo_table.add_column("Avg Price", justify="right")
        demo_table.add_column("LTP", justify="right")
        demo_table.add_column("P&L", justify="right")
        
        console.print("\n[dim]Demo positions:[/dim]")
        demo_table.add_row("RELIANCE", "10", "₹1400", "₹1450", Text("₹+500", style="green"))
        demo_table.add_row("TCS", "5", "₹3200", "₹3150", Text("₹-250", style="red"))
        
        console.print(demo_table)
        
        console.print("\n")
        Prompt.ask("Press Enter to continue", default="")
    
    def settings(self):
        """Settings menu"""
        console.clear()
        console.print(Panel("[bold cyan]⚙️  Settings[/bold cyan]", box=box.ROUNDED))
        
        console.print("\n[bold white]Watchlist:[/bold white]")
        for i, symbol in enumerate(self.watchlist, 1):
            console.print(f"  {i}. {symbol}")
        
        console.print("\n[dim]Settings management coming soon![/dim]")
        console.print("\n")
        Prompt.ask("Press Enter to continue", default="")
    
    def run(self):
        """Main application loop"""
        while True:
            choice = self.main_menu()
            
            if choice == "1":
                self.live_dashboard()
            elif choice == "2":
                self.scan_market()
            elif choice == "3":
                self.view_signals()
            elif choice == "4":
                self.portfolio_view()
            elif choice == "5":
                self.settings()
            elif choice == "6":
                console.clear()
                console.print("\n[cyan]👋 Thanks for using Cenex AI![/cyan]")
                console.print("[dim]Built by CNX Studios[/dim]\n")
                break

def main():
    """Entry point"""
    try:
        app = CenexAI()
        app.run()
    except KeyboardInterrupt:
        console.clear()
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error: {e}[/red]\n")
        raise

if __name__ == "__main__":
    main()
