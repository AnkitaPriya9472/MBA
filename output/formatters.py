"""Rich terminal formatters for simulation output.

Story 19: RichFormatter for beautiful console output.
"""

from typing import Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from models.agent_types import RoundResponse
from models.world_state import RoundResolution
from output.results import SimulationResult


class RichFormatter:
    """Formatter for rich console output."""
    
    def __init__(self):
        """Initialize the formatter with a console."""
        self.console = Console()
    
    def print_round_summary(
        self, 
        round_n: int, 
        responses: dict[str, RoundResponse],
        resolution: RoundResolution | None = None
    ) -> None:
        """Print a formatted summary of a simulation round.
        
        Args:
            round_n: Round number
            responses: Agent responses for this round
            resolution: Optional resolution data
        """
        # Create table
        table = Table(title=f"Round {round_n} Summary", show_header=True, header_style="bold magenta")
        
        table.add_column("Agent", style="cyan", width=20)
        table.add_column("Action", style="green", width=25)
        table.add_column("Confidence", justify="right", style="yellow", width=10)
        table.add_column("Assessment", style="white", width=60)
        table.add_column("Fear/Greed", justify="right", style="blue", width=10)
        
        for agent_id, response in responses.items():
            # Truncate assessment to 80 chars
            assessment = response.assessment[:77] + "..." if len(response.assessment) > 80 else response.assessment
            
            # Format confidence with bold for high confidence
            confidence_str = f"{response.confidence:.2f}"
            if response.confidence > 0.7:
                confidence_str = f"[bold]{confidence_str}[/bold]"
            
            # Get fear-greed if available (would need to pass agent state)
            fear_greed = "N/A"
            
            table.add_row(
                agent_id,
                response.primary_action,
                confidence_str,
                assessment,
                fear_greed
            )
        
        self.console.print(table)
        self.console.print()
    
    def print_final_summary(self, result: SimulationResult) -> None:
        """Print final simulation summary across all rounds.
        
        Args:
            result: The simulation result object
        """
        # Header
        self.console.print(Panel.fit(
            f"[bold cyan]{result.scenario.name}[/bold cyan]\n"
            f"Rounds Completed: {result.rounds_completed}\n"
            f"Model: {result.metadata.get('model_used', 'N/A')}\n"
            f"Duration: {result.metadata.get('duration_seconds', 0):.1f}s",
            title="Simulation Complete",
            border_style="green"
        ))
        self.console.print()
        
        # Final agent states table
        table = Table(title="Final Agent States", show_header=True, header_style="bold magenta")
        
        table.add_column("Agent", style="cyan", width=20)
        table.add_column("Role", style="green", width=15)
        table.add_column("Financial Health", justify="right", style="yellow", width=15)
        table.add_column("Fear/Greed", justify="right", style="blue", width=12)
        table.add_column("Capture Score", justify="right", style="red", width=12)
        
        for agent_id, profile in result.world_state.agent_profiles.items():
            state = result.world_state.agent_states[agent_id]
            
            # Format values
            health = f"{state.financial_health:.2f}"
            sentiment = f"{state.fear_greed_index:.1f}/10"
            capture = f"{state.capture_score:.2f}"
            
            # Highlight concerning values
            if state.financial_health < 0.5:
                health = f"[bold red]{health}[/bold red]"
            if state.capture_score > 0.7:
                capture = f"[bold red]{capture}[/bold red]"
            
            table.add_row(
                profile.name,
                profile.agent_type.value,
                health,
                sentiment,
                capture
            )
        
        self.console.print(table)
        self.console.print()
        
        # Events summary
        events = result.get_events()
        if events:
            self.console.print("[bold]Events Fired:[/bold]")
            for event in events:
                event_text = Text()
                event_text.append(f"Round {event.round}: ", style="cyan")
                event_text.append(f"{event.event_type}", style="bold red")
                event_text.append(f" - {event.description}")
                self.console.print(f"  • {event_text}")
            self.console.print()
        
        # Metadata
        if result.metadata.get("total_fallbacks", 0) > 0:
            self.console.print(
                f"[yellow]⚠ Warning: {result.metadata['total_fallbacks']} fallback responses used[/yellow]"
            )
