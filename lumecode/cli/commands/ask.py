"""
Ask Command
AI-powered Q&A about your codebase.
"""

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from typing import List, Optional

from lumecode.cli.core.llm import get_provider_with_fallback
from lumecode.cli.core.llm import list_available_providers

# Backward-compatibility shim for tests that patch get_provider at module level
# The tests expect lumecode.cli.commands.ask.get_provider to exist
from lumecode.cli.core.llm import get_provider  # noqa: F401
from lumecode.cli.core.prompts import PromptTemplates, PromptContext
from lumecode.cli.core.context import GitContext
from lumecode.cli.core.ui import StreamingDisplay


console = Console()


@click.command(name="ask", help="Ask AI questions about your code")
@click.argument("question", nargs=-1, required=True)
@click.option("--files", "-f", multiple=True, help="Include specific files in context")
@click.option("--git/--no-git", default=True, help="Include git context (diff, status, commits)")
@click.option(
    "--provider", "-p", default="groq", help="LLM provider to use (groq, openrouter, mock)"
)
@click.option("--stream/--no-stream", default=True, help="Stream the response")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "markdown", "json"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Output format. Use json for machine-readable output",
)
def ask(
    question: tuple,
    files: tuple,
    git: bool,
    provider: str,
    stream: bool,
    verbose: bool,
    output_format: str,
):
    """
    Ask AI a question about your code.

    Examples:

        lumecode ask "How does authentication work?"

        lumecode ask "What does main.py do?" --files main.py

        lumecode ask "Explain the latest changes" --git

        lumecode ask "What are the key functions?" --files src/*.py --no-stream
    """
    try:
        # Support legacy alias: `ask query <question>`
        if question and question[0].lower() == "query":
            question = question[1:]

        # Join tokens into a single question string
        question = " ".join(question).strip()
        if not question:
            raise click.UsageError("Question cannot be empty")
        # Show what we're doing
        if verbose:
            console.print(f"[dim]Using provider: {provider}[/dim]")
            console.print(f"[dim]Question: {question}[/dim]")

        # Build context
        ctx = PromptContext()

        # Get file context if specified
        file_context = None
        if files:
            if verbose:
                console.print(f"[dim]Including {len(files)} file(s)[/dim]")
            file_context = ctx.build_file_context(list(files))

        # Get git context if enabled
        git_context = None
        if git and ctx.git.is_git_repo():
            if verbose:
                console.print("[dim]Including git context[/dim]")
            # Limit diff size to avoid 413 errors (5K chars = ~1.25K tokens)
            git_context = ctx.build_git_context(
                include_diff=True, include_status=True, include_commits=3, max_diff_size=5000
            )

        # Build prompt
        prompt = PromptTemplates.ask_about_code(
            question=question, file_context=file_context, git_context=git_context
        )

        # Get system prompt
        system_prompt = PromptTemplates.system_prompt("ask")

        # Check prompt size and warn if too large
        prompt_chars = len(prompt) + len(system_prompt)
        # Rough estimate: 1 token ≈ 4 chars
        estimated_tokens = prompt_chars // 4

        if verbose:
            console.print(
                f"[dim]Prompt length: {prompt_chars:,} chars (~{estimated_tokens:,} tokens)[/dim]\n"
            )

        # Warn if context is very large (Groq has ~6K token limit for input)
        if estimated_tokens > 5000:
            console.print(
                f"[yellow]Warning: Large context (~{estimated_tokens:,} tokens). "
                "Consider using --no-git or specifying fewer files.[/yellow]\n"
            )

        # Warn on unknown provider name (we will still fallback gracefully)
        known_providers = {"groq", "openrouter", "mock"}
        warnings: list[str] = []
        if provider.lower() not in known_providers:
            available = list_available_providers()
            msg = (
                f"Unknown provider '{provider}'. Falling back automatically. "
                f"Available: {', '.join(available)}"
            )
            # Only print warning in non-JSON modes to keep output machine-readable
            if output_format.lower() != "json":
                console.print(f"[yellow]{msg}[/yellow]")
            else:
                warnings.append(msg)

        # Get LLM provider
        llm = get_provider_with_fallback(provider, verbose=verbose)

        # Show question in panel unless JSON output is requested
        if output_format.lower() != "json":
            console.print(
                Panel(
                    f"[bold cyan]Q:[/bold cyan] {question}", title="Question", border_style="cyan"
                )
            )

        # Get response
        if stream:
            # Stream response with improved UI (unless JSON output)
            chunks = llm.stream_complete(
                prompt, max_tokens=1000, temperature=0.7, system_prompt=system_prompt
            )

            if output_format.lower() == "json":
                # Collect chunks silently for JSON output
                collected = []
                for c in chunks:
                    collected.append(c)
                response_text = "".join(collected)
            else:
                console.print()  # Add spacing
                streamer = StreamingDisplay(console)
                response_text = streamer.stream_markdown(
                    chunks,
                    title=(
                        "💡 Answer" if output_format.lower() == "text" else "💡 Answer (Markdown)"
                    ),
                )

        else:
            # Get full response
            with console.status("[bold green]Thinking...", spinner="dots"):
                response_text = llm.complete(
                    prompt, max_tokens=1000, temperature=0.7, system_prompt=system_prompt
                )

            # Display response unless JSON output is requested
            if output_format.lower() != "json":
                if output_format.lower() == "markdown":
                    rendered = Markdown(response_text)
                else:
                    # Treat text as plain markdown rendering for consistency
                    rendered = Markdown(response_text)
                console.print(Panel(rendered, title="Answer", border_style="green"))

        # Output and/or extra info
        if output_format.lower() == "json":
            import json

            info = llm.get_model_info()
            payload = {
                "question": question,
                "answer": response_text,
                "provider": getattr(info, "provider", None),
                "model": getattr(info, "model", None),
                "stream": bool(stream),
                "git": bool(git),
                "files": list(files) if files else [],
                "warnings": warnings,
            }
            # Emit pure JSON to stdout
            click.echo(json.dumps(payload))
        else:
            # Show provider info if verbose
            if verbose:
                info = llm.get_model_info()
                rate_limit = llm.check_rate_limit()
                console.print(f"\n[dim]Provider: {info.provider}[/dim]")
                console.print(f"[dim]Model: {info.model}[/dim]")
                if rate_limit.requests_remaining:
                    console.print(
                        f"[dim]Requests remaining: {rate_limit.requests_remaining}/{rate_limit.requests_limit}[/dim]"
                    )

    except click.UsageError:
        # Re-raise Click errors (they're already formatted nicely)
        raise
    except Exception as e:
        error_msg = str(e)

        # Special handling for HTTP 413 Payload Too Large
        if "413" in error_msg or "Payload Too Large" in error_msg:
            console.print("[bold red]Error: Request too large for provider[/bold red]")
            console.print("\n[yellow]The context is too large. Try:[/yellow]")
            console.print("  • Use [cyan]--no-git[/cyan] to exclude git changes")
            console.print("  • Specify fewer files with [cyan]--files[/cyan]")
            console.print("  • Ask a more specific question")
            console.print("  • Try OpenRouter provider: [cyan]--provider openrouter[/cyan]")
            if verbose:
                console.print(f"\n[dim]Details: {error_msg}[/dim]")
        else:
            console.print(f"[bold red]Error:[/bold red] {error_msg}")
            if verbose:
                import traceback

                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


# Shorthand command for quick questions
def quick(question: str):
    """
    Quick question (no context, fast response).

    Example:
        lumecode ask quick "What is a closure?"
    """
    try:
        llm = get_provider_with_fallback("groq")
        system_prompt = PromptTemplates.system_prompt("ask")

        console.print(f"[bold cyan]Q:[/bold cyan] {question}\n")

        # Use streaming display for better formatting
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(
            question, max_tokens=500, temperature=0.7, system_prompt=system_prompt
        )

        response_text = streamer.stream_markdown(chunks, title="💡 Quick Answer")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        raise click.Abort()
