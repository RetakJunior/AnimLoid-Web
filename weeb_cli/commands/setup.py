from rich.console import Console
from rich.panel import Panel
from ..services.dependency_manager import dependency_manager
from ..i18n import i18n

console = Console()

def start_setup_wizard(force=False):
    console.print(Panel(f"[bold cyan]{i18n.t('setup.wizard_title')}[/bold cyan]", expand=False))
    
    tools = ["yt-dlp", "ffmpeg", "aria2", "mpv"]
    
    for tool in tools:
        console.print(f"\n[bold]{tool.upper()}[/bold]")
        console.print(i18n.t('setup.check', tool=tool))
        
        path = dependency_manager.check_dependency(tool)
        if path and not force:
            console.print(f"[green]{i18n.t('setup.found', path=path)}[/green]")
            continue
            
        console.print(f"[yellow]{i18n.t('setup.not_found', tool=tool)}[/yellow]")
        dependency_manager.install_dependency(tool)
    
    console.print(f"\n[bold green]{i18n.t('setup.complete')}[/bold green]")
    console.print(f"[dim]{i18n.t('setup.location', path=dependency_manager.bin_dir)}[/dim]")
