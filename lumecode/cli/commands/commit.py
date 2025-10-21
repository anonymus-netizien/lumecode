"""
Commit Command
AI-powered commit message generation.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
import subprocess
from typing import Optional, List

from lumecode.cli.core.context import GitContext
from lumecode.cli.core.prompts import PromptTemplates
from lumecode.cli.core.llm import get_provider_with_fallback


console = Console()


@click.group(name="commit")
def commit_group():
    """Generate AI-powered commit messages"""
    pass


@commit_group.command()
@click.option("--staged/--unstaged", default=True, help="Generate from staged or unstaged changes")
@click.option(
    "--auto/--interactive",
    "auto_commit",
    default=False,
    help="Auto-commit or show interactive preview",
)
@click.option("--provider", "-p", default="groq", help="LLM provider to use")
@click.option("--conventional/--simple", default=True, help="Use conventional commits format")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def generate(staged: bool, auto_commit: bool, provider: str, conventional: bool, verbose: bool):
    """Generate commit message from changes"""

    try:
        # Initialize git context
        git = GitContext()

        # Check if git repo
        if not git.is_git_repo():
            console.print("[red]Error:[/red] Not a git repository", style="bold")
            return

        # Get changes
        if verbose:
            console.print(f"Analyzing {'staged' if staged else 'unstaged'} changes...")

        if staged:
            # Get staged diff
            diff = git.get_current_diff(staged=True)
            files = git.get_diff_files(staged=True)
        else:
            # Get unstaged diff
            diff = git.get_current_diff(staged=False)
            files = git.get_diff_files(staged=False)

        # Check if there are changes
        if not diff or not diff.strip():
            console.print(
                f"[yellow]No {'staged' if staged else 'unstaged'} changes to commit[/yellow]"
            )
            return

        if verbose:
            console.print(f"Found changes in {len(files)} file(s)")
            for file_diff in files:
                console.print(
                    f"  • {file_diff.file_path} (+{file_diff.additions}, -{file_diff.deletions})"
                )

        # Show diff preview
        console.print()
        console.print(
            Panel(
                f"[cyan]Changes to commit:[/cyan]\n{len(files)} file(s) modified",
                title="📝 Git Diff",
                border_style="cyan",
            )
        )

        # Build prompt
        file_paths = [f.file_path for f in files]
        prompt = PromptTemplates.generate_commit_message(
            diff=diff, staged_files=file_paths, conventional=conventional
        )

        system_prompt = PromptTemplates.system_prompt("commit")

        if verbose:
            console.print(f"\nPrompt length: {len(prompt)} chars")
            console.print(f"Using provider: {provider}\n")

        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)

        # Detect if fallback occurred and notify user
        actual_provider = getattr(llm, "provider_name", provider)
        if verbose and actual_provider and actual_provider != provider:
            console.print(
                f"[dim yellow]⚠️  Fallback: Using {actual_provider} instead of {provider}[/dim yellow]"
            )

        # Generate commit message
        console.print(Panel("[yellow]Generating commit message...[/yellow]", border_style="yellow"))

        commit_message = ""

        # Use non-streaming for commit messages (need complete message)
        response = llm.complete(prompt=prompt, system_prompt=system_prompt)

        commit_message = response.strip()

        # Display generated commit message
        console.print()
        console.print(
            Panel(
                Markdown(f"```\n{commit_message}\n```"),
                title="✨ Generated Commit Message",
                border_style="green",
            )
        )

        if verbose:
            console.print(f"\nProvider: {actual_provider}")
            console.print(f"Model: {llm.model}")

        # Interactive mode - ask user
        if not auto_commit:
            console.print()

            # Ask if user wants to use this message
            use_message = Confirm.ask("Use this commit message?", default=True)

            if not use_message:
                # Ask if they want to edit
                edit_message = Confirm.ask("Edit the message?", default=True)

                if edit_message:
                    # Let user edit
                    commit_message = Prompt.ask("Enter commit message", default=commit_message)
                else:
                    console.print("[yellow]Commit cancelled[/yellow]")
                    return

            # Ask if they want to commit
            should_commit = Confirm.ask("Commit now?", default=True)

            if not should_commit:
                console.print("\n[cyan]Commit message (copy and use manually):[/cyan]")
                console.print(f"\n{commit_message}\n")
                return

        # Commit changes
        if verbose:
            console.print("\nCommitting changes...")

        try:
            # Run git commit
            result = subprocess.run(
                ["git", "commit", "-m", commit_message], capture_output=True, text=True, check=True
            )

            console.print(
                Panel(
                    f"[green]✅ Successfully committed![/green]\n\n{result.stdout}",
                    title="Commit Complete",
                    border_style="green",
                )
            )

        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error committing:[/red] {e.stderr}", style="bold")
            console.print("\n[cyan]Generated message (use manually):[/cyan]")
            console.print(f"\n{commit_message}\n")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())


@commit_group.command()
@click.option("--count", "-n", default=5, help="Number of recent commits to analyze")
@click.option("--provider", "-p", default="groq", help="LLM provider to use")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def history(count: int, provider: str, verbose: bool):
    """Show and analyze recent commits"""

    try:
        # Initialize git context
        git = GitContext()

        # Check if git repo
        if not git.is_git_repo():
            console.print("[red]Error:[/red] Not a git repository", style="bold")
            return

        # Get recent commits
        commits = git.get_recent_commits(count=count)

        if not commits:
            console.print("[yellow]No commits found[/yellow]")
            return

        # Display commits
        console.print(
            Panel(
                f"[cyan]Showing {len(commits)} recent commit(s)[/cyan]",
                title="📜 Commit History",
                border_style="cyan",
            )
        )

        for i, commit in enumerate(commits, 1):
            # Format date
            date_str = commit.date.strftime("%Y-%m-%d %H:%M")

            # Display commit
            commit_info = f"[bold]{commit.hash[:8]}[/bold] - {commit.message}\n"
            commit_info += f"[dim]by {commit.author} on {date_str}[/dim]"

            console.print(Panel(commit_info, title=f"Commit {i}", border_style="blue"))

        # Offer to analyze
        if not verbose:
            return

        console.print("\n[cyan]Commit quality analysis available with --provider option[/cyan]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())


@commit_group.command()
@click.argument("message", required=True)
@click.option("--provider", "-p", default="groq", help="LLM provider to use")
@click.option(
    "--conventional/--simple", default=True, help="Convert to conventional commits format"
)
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def improve(message: str, provider: str, conventional: bool, verbose: bool):
    """Improve an existing commit message"""

    try:
        if verbose:
            console.print(f"Using provider: {provider}")

        # Build prompt
        prompt = f"Improve this commit message"
        if conventional:
            prompt += " and convert it to Conventional Commits format (feat:, fix:, etc.)"
        prompt += ":\n\n"
        prompt += f"Original: {message}\n\n"
        prompt += "Generate ONLY the improved commit message, no explanations."

        system_prompt = PromptTemplates.system_prompt("commit")

        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)

        # Detect if fallback occurred and notify user
        actual_provider = getattr(llm, "provider_name", provider)
        if verbose and actual_provider and actual_provider != provider:
            console.print(
                f"[dim yellow]⚠️  Fallback: Using {actual_provider} instead of {provider}[/dim yellow]"
            )

        # Generate improved message
        console.print(Panel("[yellow]Improving commit message...[/yellow]", border_style="yellow"))

        response = llm.complete(prompt=prompt, system_prompt=system_prompt)

        improved_message = response.strip()

        # Display both messages
        comparison = f"**Original:**\n{message}\n\n**Improved:**\n{improved_message}"

        console.print()
        console.print(
            Panel(Markdown(comparison), title="✨ Commit Message Improvement", border_style="green")
        )

        if verbose:
            console.print(f"\nProvider: {actual_provider}")
            console.print(f"Model: {llm.model}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())


if __name__ == "__main__":
    commit_group()
