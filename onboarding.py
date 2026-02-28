#!/usr/bin/env python3
"""
🔱 CENEX AI - User Onboarding
Profile new users and understand their trading needs
"""

import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

class UserProfile:
    """User profile data structure"""
    
    def __init__(self):
        self.experience_level = None
        self.trading_style = None
        self.risk_tolerance = None
        self.preferred_sectors = []
        self.investment_range = None
        self.goals = []
        self.timeframe = None
    
    def to_dict(self):
        return {
            'experience_level': self.experience_level,
            'trading_style': self.trading_style,
            'risk_tolerance': self.risk_tolerance,
            'preferred_sectors': self.preferred_sectors,
            'investment_range': self.investment_range,
            'goals': self.goals,
            'timeframe': self.timeframe
        }
    
    def save(self, filepath='user_profile.json'):
        """Save profile to file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath='user_profile.json'):
        """Load profile from file"""
        if not Path(filepath).exists():
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        profile = cls()
        for key, value in data.items():
            setattr(profile, key, value)
        
        return profile


class Onboarding:
    """Onboarding flow"""
    
    def __init__(self):
        self.profile = UserProfile()
    
    def show_welcome(self):
        """Show welcome message"""
        console.clear()
        
        welcome = Panel(
            "[bold cyan]🔱 Welcome to CENEX AI[/bold cyan]\n\n"
            "Institutional-grade AI trading intelligence, personalized for you.\n\n"
            "[dim]Let's understand your trading style and preferences to\n"
            "provide the most relevant signals and recommendations.[/dim]",
            box=box.DOUBLE,
            border_style="cyan",
            padding=(1, 2)
        )
        
        console.print(welcome)
        console.print()
    
    def ask_experience(self):
        """Ask about trading experience"""
        console.print("[bold white]📚 Trading Experience[/bold white]")
        console.print()
        console.print("  [1] 🌱 Newbie - Just getting started")
        console.print("  [2] 📊 Intermediate - Some experience, learning strategies")
        console.print("  [3] 🎯 Professional - Experienced trader")
        console.print("  [4] 🏢 Institutional - Fund manager / Analyst")
        console.print()
        
        choice = Prompt.ask(
            "Your experience level",
            choices=["1", "2", "3", "4"],
            default="2"
        )
        
        levels = {
            "1": "newbie",
            "2": "intermediate",
            "3": "professional",
            "4": "institutional"
        }
        
        self.profile.experience_level = levels[choice]
        console.print(f"[green]✓[/green] Experience: {levels[choice].title()}\n")
    
    def ask_trading_style(self):
        """Ask about trading style"""
        console.print("[bold white]⏱️  Trading Style[/bold white]")
        console.print()
        console.print("  [1] ⚡ Day Trading - Intraday positions")
        console.print("  [2] 📈 Swing Trading - Days to weeks")
        console.print("  [3] 🎯 Position Trading - Weeks to months")
        console.print("  [4] 💎 Long-term Investing - Months to years")
        console.print()
        
        choice = Prompt.ask(
            "Your preferred style",
            choices=["1", "2", "3", "4"],
            default="2"
        )
        
        styles = {
            "1": "day_trading",
            "2": "swing_trading",
            "3": "position_trading",
            "4": "long_term"
        }
        
        self.profile.trading_style = styles[choice]
        console.print(f"[green]✓[/green] Style: {styles[choice].replace('_', ' ').title()}\n")
    
    def ask_risk_tolerance(self):
        """Ask about risk tolerance"""
        console.print("[bold white]⚠️  Risk Tolerance[/bold white]")
        console.print()
        console.print("  [1] 🛡️  Conservative - Prefer stable, low-risk investments")
        console.print("  [2] ⚖️  Balanced - Mix of growth and stability")
        console.print("  [3] 🚀 Aggressive - High risk, high reward")
        console.print()
        
        choice = Prompt.ask(
            "Your risk tolerance",
            choices=["1", "2", "3"],
            default="2"
        )
        
        levels = {
            "1": "conservative",
            "2": "balanced",
            "3": "aggressive"
        }
        
        self.profile.risk_tolerance = levels[choice]
        console.print(f"[green]✓[/green] Risk: {levels[choice].title()}\n")
    
    def ask_sectors(self):
        """Ask about preferred sectors"""
        console.print("[bold white]🏭 Preferred Sectors[/bold white]")
        console.print()
        console.print("  [1] 🏦 Banking & Finance")
        console.print("  [2] 💻 Technology & IT")
        console.print("  [3] 💊 Pharma & Healthcare")
        console.print("  [4] 🏭 Infrastructure & Manufacturing")
        console.print("  [5] ⚡ Energy & Utilities")
        console.print("  [6] 🛒 Consumer Goods")
        console.print("  [7] 🎯 All sectors")
        console.print()
        
        console.print("[dim]You can select multiple (comma-separated, e.g., 1,2,3)[/dim]")
        
        choice = Prompt.ask(
            "Select sectors",
            default="7"
        )
        
        sector_map = {
            "1": "banking_finance",
            "2": "technology",
            "3": "pharma_healthcare",
            "4": "infrastructure",
            "5": "energy",
            "6": "consumer_goods",
            "7": "all"
        }
        
        selected = [c.strip() for c in choice.split(',')]
        
        if "7" in selected:
            self.profile.preferred_sectors = ["all"]
        else:
            self.profile.preferred_sectors = [sector_map.get(s, "all") for s in selected if s in sector_map]
        
        console.print(f"[green]✓[/green] Sectors: {', '.join(self.profile.preferred_sectors).replace('_', ' ').title()}\n")
    
    def ask_investment_range(self):
        """Ask about investment amount"""
        console.print("[bold white]💰 Investment Range[/bold white]")
        console.print()
        console.print("  [1] ₹10,000 - ₹50,000")
        console.print("  [2] ₹50,000 - ₹2,00,000")
        console.print("  [3] ₹2,00,000 - ₹10,00,000")
        console.print("  [4] ₹10,00,000+")
        console.print()
        
        choice = Prompt.ask(
            "Typical investment per trade",
            choices=["1", "2", "3", "4"],
            default="2"
        )
        
        ranges = {
            "1": "10k-50k",
            "2": "50k-200k",
            "3": "200k-1M",
            "4": "1M+"
        }
        
        self.profile.investment_range = ranges[choice]
        console.print(f"[green]✓[/green] Range: ₹{ranges[choice]}\n")
    
    def ask_goals(self):
        """Ask about trading goals"""
        console.print("[bold white]🎯 Trading Goals[/bold white]")
        console.print()
        console.print("  [1] 💵 Generate regular income")
        console.print("  [2] 📈 Grow wealth over time")
        console.print("  [3] 🎓 Learn and improve trading skills")
        console.print("  [4] 🛡️  Preserve capital with modest gains")
        console.print()
        
        console.print("[dim]Select multiple if applicable (comma-separated)[/dim]")
        
        choice = Prompt.ask(
            "Your goals",
            default="1,2"
        )
        
        goal_map = {
            "1": "income",
            "2": "growth",
            "3": "learning",
            "4": "preservation"
        }
        
        selected = [c.strip() for c in choice.split(',')]
        self.profile.goals = [goal_map.get(s, "growth") for s in selected if s in goal_map]
        
        console.print(f"[green]✓[/green] Goals: {', '.join(self.profile.goals).title()}\n")
    
    def ask_timeframe(self):
        """Ask about expected timeframe"""
        console.print("[bold white]⏰ Expected Returns Timeframe[/bold white]")
        console.print()
        console.print("  [1] 📅 Short-term - Within 3 months")
        console.print("  [2] 📊 Medium-term - 3-12 months")
        console.print("  [3] 📈 Long-term - 1+ years")
        console.print()
        
        choice = Prompt.ask(
            "Your timeframe",
            choices=["1", "2", "3"],
            default="2"
        )
        
        frames = {
            "1": "short_term",
            "2": "medium_term",
            "3": "long_term"
        }
        
        self.profile.timeframe = frames[choice]
        console.print(f"[green]✓[/green] Timeframe: {frames[choice].replace('_', ' ').title()}\n")
    
    def show_summary(self):
        """Show profile summary"""
        console.print("\n")
        console.print(Panel(
            "[bold cyan]📋 Your Trading Profile[/bold cyan]",
            box=box.ROUNDED
        ))
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="dim")
        table.add_column("Value", style="bold white")
        
        table.add_row("Experience", self.profile.experience_level.replace('_', ' ').title())
        table.add_row("Style", self.profile.trading_style.replace('_', ' ').title())
        table.add_row("Risk", self.profile.risk_tolerance.title())
        table.add_row("Sectors", ', '.join(self.profile.preferred_sectors).replace('_', ' ').title())
        table.add_row("Investment", f"₹{self.profile.investment_range}")
        table.add_row("Goals", ', '.join(self.profile.goals).title())
        table.add_row("Timeframe", self.profile.timeframe.replace('_', ' ').title())
        
        console.print(table)
        console.print()
    
    def run(self):
        """Run the onboarding flow"""
        self.show_welcome()
        
        self.ask_experience()
        self.ask_trading_style()
        self.ask_risk_tolerance()
        self.ask_sectors()
        self.ask_investment_range()
        self.ask_goals()
        self.ask_timeframe()
        
        self.show_summary()
        
        if Confirm.ask("\n💾 Save this profile?", default=True):
            self.profile.save()
            console.print("[green]✅ Profile saved![/green]")
            console.print("[dim]Cenex AI will now personalize signals based on your preferences.[/dim]\n")
        else:
            console.print("[yellow]Profile not saved. You can run onboarding again anytime.[/yellow]\n")
        
        return self.profile


def main():
    """CLI entry point"""
    onboarding = Onboarding()
    profile = onboarding.run()
    
    console.print("\n[cyan]🔱 Onboarding complete! Welcome to Cenex AI.[/cyan]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Onboarding cancelled[/yellow]\n")
