"""
Review Command
AI-powered code reviews.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from lumecode.cli.core.context import FileContext, GitContext
from lumecode.cli.core.llm import get_provider_with_fallback
from lumecode.cli.core.prompts import PromptTemplates
from lumecode.cli.core.review import ReviewParser, Severity
from lumecode.cli.core.ui import StreamingDisplay

console = Console()


@click.group(name="review")
def review_group():
    """Review code and provide feedback"""
    pass


@review_group.command()
@click.option("--staged/--unstaged", default=True, help="Review staged or unstaged changes")
@click.option(
    "--files", "-f", multiple=True, help="Specific files to review (instead of all changes)"
)
@click.option(
    "--severity",
    type=click.Choice(["all", "critical", "major", "minor"]),
    default="all",
    help="Filter by severity level",
)
@click.option(
    "--focus",
    type=click.Choice(
        ["bugs", "security", "performance", "style", "best_practice", "maintainability"]
    ),
    multiple=True,
    help="Focus on specific areas",
)
@click.option("--export", type=click.Path(), help="Export review to markdown file")
@click.option("--provider", "-p", default="groq", help="LLM provider to use")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def changes(
    staged: bool,
    files: Tuple[str],
    severity: str,
    focus: Tuple[str],
    export: Optional[str],
    provider: str,
    verbose: bool,
):
    """Review changes in git or specific files"""

    try:
        # Initialize contexts
        git = GitContext()
        fc = FileContext()

        # Check if git repo
        if not git.is_git_repo():
            console.print("[red]Error:[/red] Not a git repository", style="bold")
            return

        # Get changes to review
        if files:
            # Review specific files
            if verbose:
                console.print(f"Reviewing {len(files)} specific file(s)")

            code_to_review = []
            for file_path in files:
                try:
                    file_info = fc.read_file(file_path)
                    code_to_review.append(
                        {
                            "file": file_path,
                            "language": file_info.language,
                            "content": file_info.content,
                        }
                    )
                except Exception as e:
                    console.print(f"[yellow]Warning:[/yellow] Could not read {file_path}: {e}")

            if not code_to_review:
                console.print("[red]Error:[/red] No files could be read", style="bold")
                return

        else:
            # Review git changes
            diff_text = git.get_current_diff(staged=staged)

            if not diff_text or not diff_text.strip():
                console.print(
                    f"[yellow]No {'staged' if staged else 'unstaged'} changes to review[/yellow]"
                )
                return

            # Get changed files
            diff_files = git.get_diff_files(staged=staged)

            if verbose:
                console.print(f"Found changes in {len(diff_files)} file(s)")
                for file_diff in diff_files:
                    console.print(
                        f"  • {file_diff.file_path} (+{file_diff.additions}, -{file_diff.deletions})"
                    )
                console.print()

            code_to_review = [
                {
                    "file": "git_diff",
                    "language": "diff",
                    "content": diff_text[:10000],  # Limit to first 10k chars
                }
            ]

        # Show review scope
        console.print()
        console.print(
            Panel(
                f"[cyan]Reviewing {'staged' if staged else 'unstaged'} changes[/cyan]\n"
                f"{len(code_to_review)} file(s) to review\n"
                f"Focus: {', '.join(focus) if focus else 'all areas'}",
                title="🔍 Code Review",
                border_style="cyan",
            )
        )

        # Build prompt
        if len(code_to_review) == 1 and code_to_review[0]["file"] == "git_diff":
            # Review git diff
            prompt = "Review the following code changes:\n\n"
            prompt += f"```diff\n{code_to_review[0]['content']}\n```\n\n"

            if focus:
                prompt += "**Focus on:**\n"
                for area in focus:
                    prompt += f"- {area.replace('_', ' ').title()}\n"
                prompt += "\n"

            prompt += "**Provide:**\n"
            prompt += "1. Summary of changes\n"
            prompt += "2. Issues found (categorized by severity)\n"
            prompt += "3. Specific suggestions for improvements\n"
            prompt += "4. Security concerns if any\n"
            prompt += "5. Best practices recommendations\n\n"
            prompt += "Be thorough but concise. Focus on actionable feedback."
        else:
            # Review specific files
            prompt = "Review the following code files:\n\n"

            for item in code_to_review:
                prompt += f"**File:** {item['file']}\n"
                prompt += f"```{item['language']}\n{item['content'][:5000]}\n```\n\n"

            if focus:
                prompt += "**Focus on:**\n"
                for area in focus:
                    prompt += f"- {area.replace('_', ' ').title()}\n"
                prompt += "\n"

            prompt += "**Review for:**\n"
            prompt += "1. Bugs and potential errors\n"
            prompt += "2. Security vulnerabilities\n"
            prompt += "3. Performance issues\n"
            prompt += "4. Code quality and best practices\n"
            prompt += "5. Maintainability concerns\n\n"
            prompt += "Provide specific, actionable feedback with severity levels."

        system_prompt = PromptTemplates.system_prompt("review")

        if verbose:
            console.print(f"Prompt length: {len(prompt)} chars")
            console.print(f"Using provider: {provider}\n")

        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)

        # Detect if fallback occurred and notify user
        actual_provider = getattr(llm, "provider_name", provider)
        if verbose and actual_provider and actual_provider != provider:
            console.print(
                f"[dim yellow]⚠️  Fallback: Using {actual_provider} instead of {provider}[/dim yellow]"
            )

        # Stream the review
        console.print()
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(prompt=prompt, system_prompt=system_prompt, max_tokens=2000)

        review = streamer.stream_markdown(chunks, title="✨ Code Review")

        if verbose:
            console.print(f"\n[dim]Provider: {actual_provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")

        # Export if requested
        if export:
            export_path = Path(export)

            # Build markdown content
            md_content = f"# Code Review\n\n"
            md_content += f"**Date:** {Path().cwd()}\n"
            md_content += f"**Type:** {'Staged' if staged else 'Unstaged'} changes\n"

            if focus:
                md_content += f"**Focus:** {', '.join(focus)}\n"

            md_content += "\n## Review\n\n"
            md_content += review

            export_path.write_text(md_content)
            console.print(f"\n[green]✅ Review exported to:[/green] {export_path}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())


@review_group.command()
@click.argument("file_path", type=click.Path(exists=True), required=True)
@click.option(
    "--focus",
    type=click.Choice(
        ["bugs", "security", "performance", "style", "best_practice", "maintainability"]
    ),
    multiple=True,
    help="Focus on specific areas",
)
@click.option("--export", type=click.Path(), help="Export review to markdown file")
@click.option("--provider", "-p", default="groq", help="LLM provider to use")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def file(file_path: str, focus: Tuple[str], export: Optional[str], provider: str, verbose: bool):
    """Review a specific file"""

    try:
        # Read file
        fc = FileContext()
        file_info = fc.read_file(file_path)

        if verbose:
            console.print(f"File: {file_info.name}")
            console.print(f"Language: {file_info.language}")
            console.print(f"Lines: {file_info.line_count}")
            console.print()

        # Show file preview
        console.print()
        console.print(
            Panel(
                Syntax(
                    file_info.content[:500] + ("..." if len(file_info.content) > 500 else ""),
                    file_info.language,
                    theme="monokai",
                    line_numbers=True,
                ),
                title=f"📄 File: {file_info.name}",
                border_style="cyan",
            )
        )

        # Build prompt
        prompt = PromptTemplates.review_code(
            code=file_info.content,
            file_path=file_info.path,
            language=file_info.language,
            focus=list(focus) if focus else None,
        )

        system_prompt = PromptTemplates.system_prompt("review")

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

        # Stream the review
        console.print()
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(prompt=prompt, system_prompt=system_prompt, max_tokens=2000)

        review = streamer.stream_markdown(chunks, title="✨ Code Review")

        if verbose:
            console.print(f"\n[dim]Provider: {actual_provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")

        # Export if requested
        if export:
            export_path = Path(export)

            # Build markdown content
            md_content = f"# Code Review: {file_info.name}\n\n"
            md_content += f"**File:** `{file_info.path}`\n"
            md_content += f"**Language:** {file_info.language}\n"

            if focus:
                md_content += f"**Focus:** {', '.join(focus)}\n"

            md_content += "\n## Review\n\n"
            md_content += review

            export_path.write_text(md_content)
            console.print(f"\n[green]✅ Review exported to:[/green] {export_path}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())


@review_group.command()
@click.option(
    "--focus",
    type=click.Choice(
        ["bugs", "security", "performance", "style", "best_practice", "maintainability"]
    ),
    multiple=True,
    default=["security"],
    help="Focus areas (default: security)",
)
@click.option("--export", type=click.Path(), help="Export review to markdown file")
@click.option("--provider", "-p", default="groq", help="LLM provider to use")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
def security(focus: Tuple[str], export: Optional[str], provider: str, verbose: bool):
    """Security-focused review of staged changes"""

    try:
        # Initialize git context
        git = GitContext()

        # Check if git repo
        if not git.is_git_repo():
            console.print("[red]Error:[/red] Not a git repository", style="bold")
            return

        # Get staged changes
        diff_text = git.get_current_diff(staged=True)

        if not diff_text or not diff_text.strip():
            console.print("[yellow]No staged changes to review[/yellow]")
            return

        # Get changed files
        diff_files = git.get_diff_files(staged=True)

        if verbose:
            console.print(f"Found changes in {len(diff_files)} file(s)")
            for file_diff in diff_files:
                console.print(
                    f"  • {file_diff.file_path} (+{file_diff.additions}, -{file_diff.deletions})"
                )
            console.print()

        # Show security focus
        console.print()
        console.print(
            Panel(
                f"[red]🔒 Security Review[/red]\n"
                f"{len(diff_files)} file(s) to review\n"
                f"Focus: Security vulnerabilities and risks",
                title="🔍 Security Analysis",
                border_style="red",
            )
        )

        # Build security-focused prompt
        prompt = "Perform a SECURITY-FOCUSED review of the following code changes:\n\n"
        prompt += f"```diff\n{diff_text[:10000]}\n```\n\n"
        prompt += "**Security Review Checklist:**\n"
        prompt += "1. Input validation vulnerabilities\n"
        prompt += "2. SQL injection risks\n"
        prompt += "3. XSS (Cross-Site Scripting) vulnerabilities\n"
        prompt += "4. Authentication/Authorization issues\n"
        prompt += "5. Sensitive data exposure\n"
        prompt += "6. Insecure dependencies\n"
        prompt += "7. Cryptography misuse\n"
        prompt += "8. CSRF vulnerabilities\n"
        prompt += "9. File upload security\n"
        prompt += "10. API security issues\n\n"
        prompt += "**Provide:**\n"
        prompt += "- Severity rating (CRITICAL, HIGH, MEDIUM, LOW)\n"
        prompt += "- Specific vulnerability descriptions\n"
        prompt += "- Exploitation scenarios\n"
        prompt += "- Remediation steps with code examples\n\n"
        prompt += "Be thorough and specific. Focus only on security concerns."

        system_prompt = "You are a security expert specializing in code security reviews. Focus on identifying vulnerabilities and security risks."

        if verbose:
            console.print(f"Prompt length: {len(prompt)} chars")
            console.print(f"Using provider: {provider}\n")

        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)

        # Detect if fallback occurred and notify user
        actual_provider = getattr(llm, "provider_name", provider)
        if verbose and actual_provider and actual_provider != provider:
            console.print(
                f"[dim yellow]⚠️  Fallback: Using {actual_provider} instead of {provider}[/dim yellow]"
            )

        # Stream the security review
        console.print()
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(prompt=prompt, system_prompt=system_prompt, max_tokens=2000)

        review = streamer.stream_markdown(chunks, title="🔒 Security Review")

        if verbose:
            console.print(f"\n[dim]Provider: {actual_provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")

        # Export if requested
        if export:
            export_path = Path(export)

            # Build markdown content
            md_content = f"# Security Review\n\n"
            md_content += f"**Date:** {Path().cwd()}\n"
            md_content += f"**Type:** Security-focused review\n\n"
            md_content += "## Security Analysis\n\n"
            md_content += review

            export_path.write_text(md_content)
            console.print(f"\n[green]✅ Security review exported to:[/green] {export_path}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())


if __name__ == "__main__":
    review_group()
