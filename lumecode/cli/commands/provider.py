"""
Provider Management Commands
Configure, list, and test AI providers
"""

import click
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from lumecode.cli.core.llm import get_provider_with_fallback, ProviderType
from lumecode.cli.core.config import get_config, set_config


console = Console()


@click.group(name='provider')
def provider_group():
    """Manage AI providers and API keys"""
    pass


@provider_group.command(name='list')
def list_providers():
    """
    List all available AI providers and their status.
    
    Examples:
        lumecode provider list
    """
    table = Table(title="Available AI Providers", show_header=True)
    table.add_column("Provider", style="cyan", no_wrap=True)
    table.add_column("Models", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("API Key", style="dim")
    
    providers_info = [
        {
            "name": "Groq",
            "key_env": "GROQ_API_KEY",
            "models": "llama-70b, mixtral, llama-8b, gemma",
            "free": True
        },
        {
            "name": "OpenRouter",
            "key_env": "OPENROUTER_API_KEY",
            "models": "100+ models (GPT-4, Claude, etc.)",
            "free": False
        },
        {
            "name": "OpenAI",
            "key_env": "OPENAI_API_KEY",
            "models": "GPT-4, GPT-3.5-turbo",
            "free": False
        },
        {
            "name": "Anthropic",
            "key_env": "ANTHROPIC_API_KEY",
            "models": "Claude 3 (Opus, Sonnet, Haiku)",
            "free": False
        },
        {
            "name": "Mock",
            "key_env": None,
            "models": "Test provider (offline)",
            "free": True
        }
    ]
    
    for provider in providers_info:
        name = provider["name"]
        models = provider["models"]
        
        # Check if API key is set
        if provider["key_env"]:
            has_key = bool(os.getenv(provider["key_env"]))
            status = "[green]✓ Configured[/green]" if has_key else "[yellow]⚠ No API Key[/yellow]"
            key_status = "Set" if has_key else "Not set"
        else:
            status = "[green]✓ Ready[/green]"
            key_status = "N/A"
        
        # Add free tier badge
        if provider["free"]:
            status += " [dim](FREE)[/dim]"
        
        table.add_row(name, models, status, key_status)
    
    console.print(table)
    console.print("\n[dim]Tip: Set API keys using environment variables or `lumecode provider set`[/dim]")


@provider_group.command(name='set')
@click.option('--groq', help='Set Groq API key')
@click.option('--openrouter', help='Set OpenRouter API key')
@click.option('--openai', help='Set OpenAI API key')
@click.option('--anthropic', help='Set Anthropic API key')
def set_key(groq: Optional[str], openrouter: Optional[str], openai: Optional[str], anthropic: Optional[str]):
    """
    Set API keys for providers.
    
    Examples:
        lumecode provider set --groq "gsk_..."
        lumecode provider set --openai "sk-..." --anthropic "sk-ant-..."
    
    Note: Keys are stored in ~/.lumecode/config.yaml
    """
    config_updates = {}
    
    if groq:
        os.environ['GROQ_API_KEY'] = groq
        config_updates['providers.groq.api_key'] = groq
        console.print("[green]✓[/green] Groq API key set")
    
    if openrouter:
        os.environ['OPENROUTER_API_KEY'] = openrouter
        config_updates['providers.openrouter.api_key'] = openrouter
        console.print("[green]✓[/green] OpenRouter API key set")
    
    if openai:
        os.environ['OPENAI_API_KEY'] = openai
        config_updates['providers.openai.api_key'] = openai
        console.print("[green]✓[/green] OpenAI API key set")
    
    if anthropic:
        os.environ['ANTHROPIC_API_KEY'] = anthropic
        config_updates['providers.anthropic.api_key'] = anthropic
        console.print("[green]✓[/green] Anthropic API key set")
    
    if not config_updates:
        console.print("[yellow]No API keys provided. Use --groq, --openrouter, --openai, or --anthropic[/yellow]")
        return
    
    # Save to config file
    for key, value in config_updates.items():
        set_config(key, value)
    
    console.print(f"\n[dim]Keys saved to config file[/dim]")


@provider_group.command(name='test')
@click.argument('provider_name', default='groq')
@click.option('--model', '-m', help='Specific model to test')
def test_provider(provider_name: str, model: Optional[str]):
    """
    Test a provider connection and response.
    
    Examples:
        lumecode provider test groq
        lumecode provider test openrouter --model gpt-4
        lumecode provider test mock
    """
    try:
        console.print(f"[blue]Testing {provider_name}...[/blue]")
        
        # Get provider
        provider = get_provider_with_fallback(provider_name, verbose=True)
        
        # Show provider info
        info = provider.get_model_info()
        
        console.print(Panel(
            f"""[bold]Provider Info[/bold]
Provider: {info.provider}
Model: {info.model}
Max Tokens: {info.max_tokens:,}
Context Window: {info.context_window:,}
Streaming: {'Yes' if info.supports_streaming else 'No'}""",
            title=f"✓ {provider_name.title()} Connected",
            border_style="green"
        ))
        
        # Test with a simple query
        test_prompt = "Say 'Hello from LumeCode!' in exactly 5 words."
        
        console.print("\n[dim]Sending test query...[/dim]")
        
        response = provider.complete(
            test_prompt,
            max_tokens=50,
            temperature=0.7
        )
        
        console.print(Panel(
            response,
            title="Test Response",
            border_style="cyan"
        ))
        
        # Show rate limit if available
        rate_limit = provider.check_rate_limit()
        if rate_limit.requests_remaining:
            console.print(f"\n[dim]Rate Limit: {rate_limit.requests_remaining}/{rate_limit.requests_limit} requests remaining[/dim]")
        
        console.print("\n[green]✓ Provider test successful![/green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Test failed: {str(e)}[/red]")
        console.print("\n[dim]Troubleshooting:[/dim]")
        console.print("  1. Check your API key is set correctly")
        console.print("  2. Verify you have internet connection")
        console.print("  3. Check provider status at their website")


@provider_group.command(name='default')
@click.argument('provider_name')
@click.option('--model', '-m', help='Default model for this provider')
def set_default(provider_name: str, model: Optional[str]):
    """
    Set the default provider and model.
    
    Examples:
        lumecode provider default groq
        lumecode provider default openrouter --model gpt-4
    """
    try:
        # Validate provider exists
        provider = get_provider_with_fallback(provider_name)
        
        # Save to config
        set_config('default_provider', provider_name)
        
        if model:
            set_config(f'providers.{provider_name}.default_model', model)
            console.print(f"[green]✓[/green] Default provider set to {provider_name} with model {model}")
        else:
            console.print(f"[green]✓[/green] Default provider set to {provider_name}")
        
        console.print(f"\n[dim]All commands will now use {provider_name} by default[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@provider_group.command(name='info')
@click.argument('provider_name')
def show_info(provider_name: str):
    """
    Show detailed information about a provider.
    
    Examples:
        lumecode provider info groq
        lumecode provider info openrouter
    """
    provider_details = {
        "groq": {
            "name": "Groq",
            "description": "Ultra-fast inference with FREE tier",
            "website": "https://groq.com",
            "pricing": "FREE: 30 req/min, 500+ tokens/sec",
            "models": [
                "llama-3.3-70b-versatile (70B parameters)",
                "mixtral-8x7b-32768 (8x7B MoE)",
                "llama-3.1-8b-instant (8B parameters)",
                "gemma2-9b-it (9B parameters)"
            ],
            "key_env": "GROQ_API_KEY",
            "get_key": "https://console.groq.com"
        },
        "openrouter": {
            "name": "OpenRouter",
            "description": "Access to 100+ AI models through one API",
            "website": "https://openrouter.ai",
            "pricing": "Pay-per-use, prices vary by model",
            "models": [
                "GPT-4, GPT-3.5-turbo (OpenAI)",
                "Claude 3 Opus, Sonnet, Haiku (Anthropic)",
                "Llama 2/3 (Meta)",
                "Many more..."
            ],
            "key_env": "OPENROUTER_API_KEY",
            "get_key": "https://openrouter.ai/keys"
        },
        "mock": {
            "name": "Mock Provider",
            "description": "Test provider for development (offline)",
            "website": "N/A",
            "pricing": "FREE (offline)",
            "models": ["mock (test responses)"],
            "key_env": None,
            "get_key": None
        }
    }
    
    if provider_name not in provider_details:
        console.print(f"[yellow]Provider '{provider_name}' not found[/yellow]")
        console.print("\nAvailable providers: groq, openrouter, mock")
        return
    
    details = provider_details[provider_name]
    
    # Build info panel
    info_text = f"""[bold]{details['name']}[/bold]
{details['description']}

[bold cyan]Website:[/bold cyan] {details['website']}
[bold cyan]Pricing:[/bold cyan] {details['pricing']}

[bold cyan]Available Models:[/bold cyan]"""
    
    for model in details['models']:
        info_text += f"\n  • {model}"
    
    if details['key_env']:
        has_key = bool(os.getenv(details['key_env']))
        key_status = "[green]✓ Set[/green]" if has_key else "[yellow]⚠ Not set[/yellow]"
        info_text += f"\n\n[bold cyan]API Key:[/bold cyan] {key_status}"
        info_text += f"\n[dim]Environment variable: {details['key_env']}[/dim]"
        if details['get_key']:
            info_text += f"\n[dim]Get your key: {details['get_key']}[/dim]"
    
    console.print(Panel(info_text, title=f"ℹ️  Provider Info", border_style="blue"))


# Add to main CLI
def register(cli_group):
    """Register provider commands with main CLI"""
    cli_group.add_command(provider_group)
