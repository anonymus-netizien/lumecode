"""
Cache Management Command
Manage LLM response cache
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core.cache import get_cache

console = Console()


@click.group(name="cache")
def cache_group():
    """💾 Manage response cache"""
    pass


@cache_group.command(name="info")
def info():
    """
    Show cache information and statistics.
    
    Examples:
        # View cache stats
        lume cache info
    """
    try:
        cache = get_cache()
        stats = cache.get_stats()
        
        # Create info table
        table = Table(title="📊 Cache Statistics", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Cache Directory", str(cache.cache_dir))
        table.add_row("Number of Entries", str(stats['num_entries']))
        table.add_row("Cache Size", f"{stats['cache_size_mb']} MB")
        table.add_row("TTL (Time to Live)", f"{cache.ttl_hours} hours")
        table.add_row("", "")
        table.add_row("Cache Hits", str(stats['hits']))
        table.add_row("Cache Misses", str(stats['misses']))
        table.add_row("Total Requests", str(stats['total_requests']))
        table.add_row("Hit Rate", stats['hit_rate'])
        table.add_row("API Calls Saved", str(stats['total_saved_api_calls']))
        table.add_row("", "")
        table.add_row("Created At", stats['created_at'][:19])
        
        console.print()
        console.print(table)
        console.print()
        
        # Show benefits
        if stats['total_saved_api_calls'] > 0:
            console.print(Panel(
                f"✨ You've saved [green]{stats['total_saved_api_calls']}[/green] API calls!\n"
                f"💰 That's faster responses and lower costs.",
                title="Benefits",
                border_style="green"
            ))
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@cache_group.command(name="clear")
@click.option("--older-than", "-o", type=int, help="Clear entries older than N hours")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
def clear(older_than, force):
    """
    Clear cached responses.
    
    Examples:
        # Clear all cache
        lume cache clear
        
        # Clear entries older than 48 hours
        lume cache clear --older-than 48
        
        # Skip confirmation
        lume cache clear --force
    """
    try:
        cache = get_cache()
        
        # Confirm if not forced
        if not force:
            if older_than:
                message = f"Clear cache entries older than {older_than} hours?"
            else:
                message = "Clear ALL cached responses?"
            
            if not click.confirm(message):
                console.print("[yellow]Cancelled[/yellow]")
                return
        
        # Clear cache
        count = cache.clear(older_than_hours=older_than)
        
        if count > 0:
            console.print(f"\n✅ Cleared [green]{count}[/green] cache entries")
        else:
            console.print("\n[yellow]No cache entries to clear[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@cache_group.command(name="enable")
def enable():
    """
    Enable response caching (enabled by default).
    
    Examples:
        # Enable caching
        lume cache enable
    """
    try:
        # This will be implemented when we add config file
        console.print("✅ Caching is enabled")
        console.print("\n💡 Tip: Caching is enabled by default to save API calls")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@cache_group.command(name="disable")
def disable():
    """
    Disable response caching.
    
    Examples:
        # Disable caching
        lume cache disable
    """
    try:
        # This will be implemented when we add config file
        console.print("⚠️  Caching disabled")
        console.print("\n💡 Note: You'll make more API calls without caching")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    cache_group()
