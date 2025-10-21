"""
Batch Operations Command
Process multiple files at once
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.panel import Panel

from ..core.context import FileContext, CodeParser
from ..core.llm import get_provider_with_fallback, get_provider  # get_provider for tests patching
from ..core.prompts import PromptTemplates

console = Console()


@click.group(name="batch")
def batch_group():
    """📦 Process multiple files at once"""
    pass


@batch_group.command(name="review")
@click.argument("pattern", default="**/*.py")
@click.option("--focus", "-f", multiple=True, help="Focus areas (bugs, security, performance)")
@click.option("--provider", "-p", default="groq", help="LLM provider")
@click.option("--output", "-o", help="Output file for results")
@click.option("--max-files", "-n", type=int, default=10, help="Maximum files to process")
def batch_review(pattern, focus, provider, output, max_files):
    """
    Review multiple files at once.

    Examples:
        # Review all Python files
        lume batch review "**/*.py"

        # Review with specific focus
        lume batch review "src/**/*.py" --focus security --focus bugs

        # Limit to 5 files
        lume batch review "**/*.py" --max-files 5

        # Save results to file
        lume batch review "**/*.py" -o review_results.md
    """
    try:
        # Find files
        console.print(f"\n🔍 Finding files matching: [cyan]{pattern}[/cyan]...")

        file_ctx = FileContext()
        files = list(Path.cwd().glob(pattern))

        if not files:
            console.print(f"[yellow]No files found matching pattern[/yellow]")
            return

        # Limit files
        if len(files) > max_files:
            console.print(
                f"[yellow]Found {len(files)} files, processing first {max_files}[/yellow]"
            )
            files = files[:max_files]
        else:
            console.print(f"[green]Found {len(files)} files[/green]")

        # Process files
        results = []
        llm = get_provider_with_fallback(preferred_provider=provider)
        system_prompt = PromptTemplates.system_prompt("review")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            task = progress.add_task("Reviewing files...", total=len(files))

            for file_path in files:
                progress.update(task, description=f"Reviewing {file_path.name}...")

                try:
                    # Read file
                    file_info = file_ctx.read_file(str(file_path))

                    if not file_info:
                        results.append(
                            {
                                "file": str(file_path),
                                "status": "error",
                                "message": "Could not read file",
                            }
                        )
                        continue

                    # Generate review prompt
                    focus_areas = list(focus) if focus else None
                    prompt = PromptTemplates.review_code(
                        code=file_info.content,
                        file_path=str(file_path),
                        language=file_info.language,
                        focus=focus_areas,
                    )

                    # Get review
                    review = llm.complete(
                        prompt=prompt, max_tokens=1500, temperature=0.7, system_prompt=system_prompt
                    )

                    results.append({"file": str(file_path), "status": "success", "review": review})

                except Exception as e:
                    results.append({"file": str(file_path), "status": "error", "message": str(e)})

                progress.update(task, advance=1)

        # Display results
        console.print("\n")

        for i, result in enumerate(results, 1):
            if result["status"] == "success":
                console.print(
                    Panel(
                        result["review"],
                        title=f"📝 Review {i}/{len(results)}: {Path(result['file']).name}",
                        border_style="green",
                    )
                )
                console.print()
            else:
                console.print(
                    f"[red]❌ {result['file']}: {result.get('message', 'Unknown error')}[/red]"
                )

        # Save to file if requested
        if output:
            with open(output, "w") as f:
                f.write(f"# Batch Review Results\n\n")
                f.write(f"**Pattern:** `{pattern}`\n")
                f.write(f"**Files processed:** {len(results)}\n\n")

                for i, result in enumerate(results, 1):
                    f.write(f"## {i}. {Path(result['file']).name}\n\n")

                    if result["status"] == "success":
                        f.write(result["review"])
                        f.write("\n\n")
                    else:
                        f.write(f"**Error:** {result.get('message', 'Unknown error')}\n\n")

            console.print(f"✅ Results saved to [cyan]{output}[/cyan]")

        # Summary
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful

        console.print(f"\n✨ Batch review complete!")
        console.print(f"   Successful: [green]{successful}[/green]")
        if failed > 0:
            console.print(f"   Failed: [red]{failed}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@batch_group.command(name="test")
@click.argument("pattern", default="**/*.py")
@click.option("--framework", "-f", default="pytest", help="Test framework")
@click.option("--provider", "-p", default="groq", help="LLM provider")
@click.option("--output-dir", "-o", help="Output directory for tests")
@click.option("--max-files", "-n", type=int, default=10, help="Maximum files to process")
def batch_test(pattern, framework, provider, output_dir, max_files):
    """
    Generate tests for multiple files.

    Examples:
        # Generate tests for all Python files
        lume batch test "src/**/*.py"

        # Save to specific directory
        lume batch test "src/**/*.py" -o tests/

        # Limit to 5 files
        lume batch test "**/*.py" --max-files 5
    """
    try:
        # Find files
        console.print(f"\n🔍 Finding files matching: [cyan]{pattern}[/cyan]...")

        files = list(Path.cwd().glob(pattern))

        # Filter out test files
        files = [f for f in files if not f.name.startswith("test_")]

        if not files:
            console.print(f"[yellow]No files found matching pattern[/yellow]")
            return

        # Limit files
        if len(files) > max_files:
            console.print(
                f"[yellow]Found {len(files)} files, processing first {max_files}[/yellow]"
            )
            files = files[:max_files]
        else:
            console.print(f"[green]Found {len(files)} files[/green]")

        # Set output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path.cwd() / "tests"

        output_path.mkdir(parents=True, exist_ok=True)

        # Process files
        results = []
        file_ctx = FileContext()
        parser = CodeParser()
        llm = get_provider_with_fallback(preferred_provider=provider)
        system_prompt = PromptTemplates.system_prompt("test")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:

            task = progress.add_task("Generating tests...", total=len(files))

            for file_path in files:
                progress.update(task, description=f"Generating tests for {file_path.name}...")

                try:
                    # Read file
                    file_info = file_ctx.read_file(str(file_path))

                    if not file_info:
                        results.append(
                            {
                                "file": str(file_path),
                                "status": "error",
                                "message": "Could not read file",
                            }
                        )
                        continue

                    # Get symbols
                    all_symbols = parser.list_symbols(file_info.content)
                    functions = all_symbols.get("functions", [])
                    classes = all_symbols.get("classes", [])

                    # Generate test prompt
                    prompt = f"""Generate comprehensive unit tests for this Python code.

**Code to Test:**
```python
{file_info.content}
```

**Context:**
- File: {file_path.name}
- Framework: {framework}
- Functions: {len(functions)}
- Classes: {len(classes)}

**Requirements:**
1. Use {framework} framework
2. Test happy paths and edge cases
3. Test error handling
4. Use clear, descriptive test names
5. Add docstrings to test functions
6. Mock external dependencies
7. Aim for high code coverage

Generate complete, production-ready test code:"""

                    # Get tests
                    tests = llm.complete(
                        prompt=prompt, max_tokens=2000, temperature=0.7, system_prompt=system_prompt
                    )

                    # Extract code from markdown
                    import re

                    code_blocks = re.findall(r"```(?:python)?\n(.*?)```", tests, re.DOTALL)

                    if code_blocks:
                        test_code = code_blocks[0].strip()
                    else:
                        test_code = tests

                    # Save test file
                    test_filename = f"test_{file_path.stem}.py"
                    test_path = output_path / test_filename
                    test_path.write_text(test_code)

                    results.append(
                        {"file": str(file_path), "test_file": str(test_path), "status": "success"}
                    )

                except Exception as e:
                    results.append({"file": str(file_path), "status": "error", "message": str(e)})

                progress.update(task, advance=1)

        # Display results
        console.print("\n")

        table = Table(title="📊 Batch Test Generation Results")
        table.add_column("Source File", style="cyan")
        table.add_column("Test File", style="green")
        table.add_column("Status", style="bold")

        for result in results:
            if result["status"] == "success":
                table.add_row(Path(result["file"]).name, Path(result["test_file"]).name, "✅")
            else:
                table.add_row(Path(result["file"]).name, result.get("message", "Error"), "❌")

        console.print(table)

        # Summary
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful

        console.print(f"\n✨ Batch test generation complete!")
        console.print(f"   Successful: [green]{successful}[/green]")
        if failed > 0:
            console.print(f"   Failed: [red]{failed}[/red]")
        console.print(f"   Output directory: [cyan]{output_path}[/cyan]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    batch_group()
