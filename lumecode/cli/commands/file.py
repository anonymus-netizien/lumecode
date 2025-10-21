"""
File operations with AI assistance
Read, write, edit, and search files using AI
"""

import click
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List
import re

from lumecode.cli.core.llm import get_provider_with_fallback
from lumecode.cli.core.ui import StreamingDisplay


console = Console()


@click.group()
def file():
    """File operations with AI assistance."""
    pass


@file.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--lines", "-l", help="Show specific lines (e.g., 10-50)")
@click.option("--syntax", "-s", is_flag=True, help="Show with syntax highlighting")
def read(path: str, lines: Optional[str], syntax: bool):
    """
    Read and display file contents.

    Examples:
        lumecode file read src/main.py
        lumecode file read src/main.py --lines 10-50
        lumecode file read src/main.py --syntax
    """
    file_path = Path(path)

    try:
        content = file_path.read_text()

        # Filter lines if specified
        if lines:
            match = re.match(r"(\d+)-(\d+)", lines)
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                content_lines = content.split("\n")
                content = "\n".join(content_lines[start - 1 : end])

        # Display with syntax highlighting
        if syntax:
            lexer = file_path.suffix[1:] if file_path.suffix else "text"
            syntax_obj = Syntax(content, lexer, theme="monokai", line_numbers=True, word_wrap=True)
            console.print(Panel(syntax_obj, title=str(file_path), border_style="blue"))
        else:
            console.print(content)

    except Exception as e:
        console.print(f"[red]Error reading file: {str(e)}[/red]")


@file.command()
@click.argument("path", type=click.Path())
@click.option("--prompt", "-p", required=True, help="What to write in the file")
@click.option("--model", "-m", help="AI model to use")
@click.option("--force", "-f", is_flag=True, help="Overwrite if file exists")
def write(path: str, prompt: str, model: Optional[str], force: bool):
    """
    Create new file with AI-generated content.

    Examples:
        lumecode file write src/auth.py --prompt "Create user authentication module"
        lumecode file write tests/test_auth.py --prompt "Write tests for auth module"
    """
    file_path = Path(path)

    # Check if file exists
    if file_path.exists() and not force:
        console.print(f"[yellow]File already exists: {path}[/yellow]")
        console.print("Use --force to overwrite")
        return

    try:
        # Get AI provider
        provider = get_provider_with_fallback(model)

        # Build context-aware prompt
        file_type = file_path.suffix[1:] if file_path.suffix else "text"

        full_prompt = f"""
Create a new {file_type} file at {path}.

Requirements:
{prompt}

Provide ONLY the file content, no explanations or markdown formatting.
Write production-ready, well-documented code.
"""

        console.print(f"[blue]Generating {path}...[/blue]")

        # Generate content with streaming
        streamer = StreamingDisplay(console)
        chunks = provider.stream_complete(full_prompt, max_tokens=2000, temperature=0.7)

        # Show generation progress
        response = streamer.stream_text(chunks, style="dim cyan")

        # Extract code from response (remove markdown if present)
        code = _extract_code_content(response)

        # Create directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path.write_text(code)

        console.print(f"[green]✓ Created {path}[/green]")
        console.print(f"  Lines: {len(code.split(chr(10)))}")
        console.print(f"  Size: {len(code)} bytes")

    except Exception as e:
        console.print(f"[red]Error creating file: {str(e)}[/red]")


@file.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--prompt", "-p", required=True, help="What changes to make")
@click.option("--model", "-m", help="AI model to use")
@click.option("--backup/--no-backup", default=True, help="Create backup before editing")
def edit(path: str, prompt: str, model: Optional[str], backup: bool):
    """
    Edit existing file with AI assistance.

    Examples:
        lumecode file edit src/main.py --prompt "Add error handling"
        lumecode file edit README.md --prompt "Add installation instructions"
    """
    file_path = Path(path)

    try:
        # Read current content
        current_content = file_path.read_text()

        # Get AI provider
        provider = get_provider_with_fallback(model)

        # Build prompt with context
        full_prompt = f"""
Edit this file: {path}

Current content:
```
{current_content}
```

Instructions:
{prompt}

Provide ONLY the complete updated file content, no explanations.
Maintain the existing code style and structure.
"""

        console.print(f"[blue]Editing {path}...[/blue]")

        # Generate updated content with streaming
        streamer = StreamingDisplay(console)
        chunks = provider.stream_complete(full_prompt, max_tokens=3000, temperature=0.7)

        # Show generation progress
        response = streamer.stream_text(chunks, style="dim cyan")
        code = _extract_code_content(response)

        # Create backup if requested
        if backup:
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            backup_path.write_text(current_content)
            console.print(f"[dim]Backup saved to {backup_path}[/dim]")

        # Write updated content
        file_path.write_text(code)

        console.print(f"[green]✓ Modified {path}[/green]")

        # Show diff summary
        old_lines = len(current_content.split("\n"))
        new_lines = len(code.split("\n"))
        diff = new_lines - old_lines

        if diff > 0:
            console.print(f"  [green]+{diff} lines added[/green]")
        elif diff < 0:
            console.print(f"  [red]{diff} lines removed[/red]")
        else:
            console.print(f"  Lines unchanged: {new_lines}")

    except Exception as e:
        console.print(f"[red]Error editing file: {str(e)}[/red]")


@file.command()
@click.argument("query")
@click.option("--pattern", "-i", default="**/*.py", help="File pattern to search")
@click.option("--max-results", "-n", default=50, help="Maximum results to show")
@click.option("--context", "-C", default=0, help="Lines of context around match")
def search(query: str, pattern: str, max_results: int, context: int):
    """
    Search for text across files.

    Examples:
        lumecode file search "database connection"
        lumecode file search "TODO" --pattern "**/*.py"
        lumecode file search "class User" --context 3
    """
    matches = []

    try:
        # Search in files
        for file_path in Path(".").rglob(pattern):
            if file_path.is_file() and not _should_ignore(file_path):
                try:
                    content = file_path.read_text()
                    lines = content.split("\n")

                    for i, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            # Get context lines
                            start = max(0, i - context - 1)
                            end = min(len(lines), i + context)
                            context_lines = lines[start:end]

                            matches.append(
                                {
                                    "path": file_path,
                                    "line": i,
                                    "content": line.strip(),
                                    "context": context_lines if context > 0 else None,
                                }
                            )

                            if len(matches) >= max_results:
                                break

                except Exception:
                    continue

            if len(matches) >= max_results:
                break

        # Display results
        if matches:
            console.print(f"\n[green]Found {len(matches)} matches:[/green]\n")

            for match in matches:
                console.print(f"[cyan]{match['path']}:{match['line']}[/cyan]")

                if match["context"]:
                    for ctx_line in match["context"]:
                        console.print(f"  {ctx_line}")
                else:
                    console.print(f"  {match['content']}")

                console.print()
        else:
            console.print("[yellow]No matches found.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error searching files: {str(e)}[/red]")


@file.command()
@click.option("--pattern", "-i", default="**/*", help="File pattern")
@click.option("--type", "-t", help="Filter by file type (e.g., py, js, md)")
def tree(pattern: str, type: Optional[str]):
    """
    Display directory tree.

    Examples:
        lumecode file tree
        lumecode file tree --pattern "src/**/*"
        lumecode file tree --type py
    """
    try:
        files = []

        for file_path in Path(".").rglob(pattern):
            if file_path.is_file() and not _should_ignore(file_path):
                if type and not file_path.suffix.endswith(type):
                    continue
                files.append(file_path)

        # Build tree structure
        console.print(f"\n[blue]Found {len(files)} files:[/blue]\n")

        # Group by directory
        dirs = {}
        for f in files:
            dir_name = str(f.parent)
            if dir_name not in dirs:
                dirs[dir_name] = []
            dirs[dir_name].append(f.name)

        # Display
        for dir_name in sorted(dirs.keys()):
            console.print(f"[cyan]{dir_name}/[/cyan]")
            for file_name in sorted(dirs[dir_name]):
                console.print(f"  {file_name}")
            console.print()

    except Exception as e:
        console.print(f"[red]Error building tree: {str(e)}[/red]")


def _extract_code_content(response: str) -> str:
    """Extract code from AI response, removing markdown formatting."""
    # Remove markdown code blocks
    if "```" in response:
        # Find code between backticks
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

    return response.strip()


def _should_ignore(path: Path) -> bool:
    """Check if path should be ignored in search."""
    ignore_patterns = [
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        "*.pyc",
        ".DS_Store",
    ]

    path_str = str(path)

    for pattern in ignore_patterns:
        if pattern in path_str:
            return True

    return False


if __name__ == "__main__":
    file()
