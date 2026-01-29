"""Main entry point for Agentic SDLC."""

import asyncio
import sys
from datetime import datetime

import structlog
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agentic.orchestrator import run_sdlc_pipeline
from agentic.state.schemas import Phase


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                    🤖 AGENTIC SDLC                        ║
    ║         Multi-Agent Software Development System           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="bold blue"))


def print_phase_summary(phase: Phase, details: dict):
    """Print a summary for a completed phase."""
    table = Table(title=f"Phase: {phase.value.upper()}", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in details.items():
        table.add_row(key, str(value))
    
    console.print(table)


def print_final_summary(state):
    """Print the final project summary."""
    console.print("\n")
    console.print(Panel("📊 PROJECT SUMMARY", style="bold green"))
    
    # Project info
    table = Table(show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Project Name", state.project_name)
    table.add_row("Project ID", str(state.project_id))
    table.add_row("Final Phase", state.current_phase.value)
    
    if state.completed_at:
        duration = (state.completed_at - state.started_at).seconds
        table.add_row("Duration", f"{duration} seconds")
    
    console.print(table)
    
    # Artifacts summary
    console.print("\n📦 Artifacts Created:")
    artifacts_table = Table(show_header=True)
    artifacts_table.add_column("Type", style="cyan")
    artifacts_table.add_column("Count", style="green")
    
    artifacts_table.add_row("Epics", str(len(state.epics)))
    artifacts_table.add_row(
        "Stories",
        str(sum(len(e.stories) for e in state.epics))
    )
    artifacts_table.add_row("Code Files", str(len(state.code_artifacts)))
    artifacts_table.add_row("Test Cases", str(len(state.test_cases)))
    artifacts_table.add_row("Security Findings", str(len(state.security_findings)))
    artifacts_table.add_row("Architecture Decisions", str(len(state.architecture_decisions)))
    
    console.print(artifacts_table)
    
    # Errors if any
    if state.errors:
        console.print("\n⚠️ Errors encountered:", style="yellow")
        for error in state.errors:
            console.print(f"  - {error}", style="red")


async def main(project_description: str, project_name: str = "New Project"):
    """Run the SDLC pipeline."""
    print_banner()
    
    console.print(f"\n📝 Project: [bold]{project_name}[/bold]")
    console.print(f"📄 Description: {project_description[:100]}...\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running SDLC pipeline...", total=None)
        
        try:
            final_state = await run_sdlc_pipeline(
                project_description=project_description,
                project_name=project_name,
            )
            
            progress.update(task, completed=True)
            
            print_final_summary(final_state)
            
            if final_state.current_phase == Phase.COMPLETED:
                console.print("\n✅ Pipeline completed successfully!", style="bold green")
            else:
                console.print(
                    f"\n⚠️ Pipeline ended at phase: {final_state.current_phase.value}",
                    style="yellow"
                )
            
            return final_state
            
        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"\n❌ Pipeline failed: {str(e)}", style="bold red")
            raise


def cli():
    """Command line interface entry point."""
    if len(sys.argv) < 2:
        console.print("Usage: python -m agentic.main '<project_description>' [project_name]")
        console.print("\nExample:")
        console.print("  python -m agentic.main 'Build a REST API for user management' 'UserAPI'")
        sys.exit(1)
    
    project_description = sys.argv[1]
    project_name = sys.argv[2] if len(sys.argv) > 2 else "New Project"
    
    asyncio.run(main(project_description, project_name))


if __name__ == "__main__":
    cli()
