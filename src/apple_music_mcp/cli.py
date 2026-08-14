from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from apple_music_mcp.auth import extract_tokens_from_safari, get_auth_status
from apple_music_mcp.cache import cache
from apple_music_mcp.config import config
from apple_music_mcp.server import main as run_server

app = typer.Typer(
    name="apple-music-mcp",
    help="High-Efficiency Apple Music MCP Server CLI",
    add_completion=False,
)
console = Console()


@app.command()
def serve():
    """Run the Apple Music MCP server over stdio."""
    run_server()


@app.command()
def status():
    """Show Apple Music MCP system and authentication status."""
    st = get_auth_status()
    table = Table(title="Apple Music MCP Status")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")

    table.add_row("macOS Native Bridge", "✅ Available" if st["native_macos"] else "❌ Unavailable")
    table.add_row("Apple Music Web API", "✅ Authenticated" if st["authenticated"] else "⚠️ Unauthenticated")
    table.add_row("Storefront", st["storefront"].upper())
    table.add_row("Developer Token", "✅ Present" if st["developer_token_present"] else "❌ Missing")
    table.add_row("User Token", "✅ Present" if st["user_token_present"] else "❌ Missing")
    table.add_row("Audio-Only Filtering", "✅ Enabled" if st["pure_audio_only"] else "❌ Disabled")

    console.print(table)


@app.command()
def login():
    """Extract authenticated session tokens from open Safari tab on music.apple.com."""
    console.print("[yellow]Extracting authentication tokens from Safari...[/yellow]")
    success, res = extract_tokens_from_safari()
    if success:
        console.print("[green]✅ Successfully extracted Apple Music session from Safari![/green]")
        console.print(f"Developer Token: [dim]{res['developer_token'][:20]}...[/dim]")
        console.print(f"User Token: [dim]{res['user_token'][:20]}...[/dim]")
    else:
        console.print(f"[red]❌ Extraction failed: {res.get('error')}[/red]")
        console.print("[dim]Tip: Open Safari and log into music.apple.com with Developer features enabled.[/dim]")


@app.command()
def clean_cache():
    """Clear in-memory and disk catalog caches."""
    count = cache.clear()
    console.print(f"[green]✅ Cleared {count} cached catalog entries.[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
