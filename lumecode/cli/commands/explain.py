"""
Explain Command
AI-powered code explanations.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from pathlib import Path
from typing import Optional

from lumecode.cli.core.context import FileContext, CodeParser
from lumecode.cli.core.prompts import PromptTemplates
from lumecode.cli.core.llm import get_provider_with_fallback
from lumecode.cli.core.ui import StreamingDisplay


console = Console()


@click.group(name='explain')
def explain_group():
    """Explain code in detail"""
    pass


@explain_group.command()
@click.argument('file_path', type=click.Path(exists=True), required=True)
@click.option(
    '--lines', '-l',
    help='Line range to explain (e.g., 10-50, 10:50)'
)
@click.option(
    '--function', '-f', 'function_name',
    help='Specific function name to explain'
)
@click.option(
    '--class', '-c', 'class_name',
    help='Specific class name to explain'
)
@click.option(
    '--examples/--no-examples',
    default=True,
    help='Include usage examples'
)
@click.option(
    '--export',
    type=click.Path(),
    help='Export explanation to markdown file'
)
@click.option(
    '--provider', '-p',
    default='groq',
    help='LLM provider to use'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Show verbose output'
)
def code(
    file_path: str,
    lines: Optional[str],
    function_name: Optional[str],
    class_name: Optional[str],
    examples: bool,
    export: Optional[str],
    provider: str,
    verbose: bool
):
    """Explain code in a file"""
    
    try:
        # Read file
        fc = FileContext()
        file_info = fc.read_file(file_path)
        
        if verbose:
            console.print(f"File: {file_info.name}")
            console.print(f"Language: {file_info.language}")
            console.print(f"Lines: {file_info.line_count}")
            console.print()
        
        # Initialize code parser
        parser = CodeParser(language=file_info.language)
        
        # Determine what to explain
        code_to_explain = None
        explanation_target = None
        
        if function_name:
            # Extract specific function
            symbol = parser.extract_function(file_info.content, function_name)
            if symbol:
                code_to_explain = symbol.code
                explanation_target = f"function `{function_name}`"
                if verbose:
                    console.print(f"Extracted {explanation_target} (lines {symbol.start_line}-{symbol.end_line})")
            else:
                console.print(f"[red]Error:[/red] Function '{function_name}' not found", style="bold")
                return
        
        elif class_name:
            # Extract specific class
            symbol = parser.extract_class(file_info.content, class_name)
            if symbol:
                code_to_explain = symbol.code
                explanation_target = f"class `{class_name}`"
                if verbose:
                    console.print(f"Extracted {explanation_target} (lines {symbol.start_line}-{symbol.end_line})")
            else:
                console.print(f"[red]Error:[/red] Class '{class_name}' not found", style="bold")
                return
        
        elif lines:
            # Extract line range
            line_range = parser.parse_line_range(lines)
            if line_range:
                start, end = line_range
                code_to_explain = parser.extract_lines(file_info.content, start, end)
                explanation_target = f"lines {start}-{end}"
                if verbose:
                    console.print(f"Extracted {explanation_target}")
            else:
                console.print(f"[red]Error:[/red] Invalid line range format. Use: 10-50, 10:50, or 10..50", style="bold")
                return
        
        else:
            # Explain entire file
            code_to_explain = file_info.content
            explanation_target = f"file `{file_info.name}`"
            if verbose:
                console.print(f"Explaining entire file")
        
        # Show code preview
        console.print()
        console.print(Panel(
            Syntax(
                code_to_explain[:500] + ("..." if len(code_to_explain) > 500 else ""),
                file_info.language,
                theme="monokai",
                line_numbers=True
            ),
            title=f"📄 Code: {explanation_target}",
            border_style="cyan"
        ))
        
        # Build prompt
        prompt = PromptTemplates.explain_code(
            code=code_to_explain,
            file_path=file_info.path,
            language=file_info.language
        )
        
        if examples:
            prompt += "\n\n**Include:** Practical usage examples and common patterns."
        
        system_prompt = PromptTemplates.system_prompt("explain")
        
        if verbose:
            console.print(f"\nPrompt length: {len(prompt)} chars")
            console.print(f"Using provider: {provider}\n")
        
        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)
        
        # Get explanation with streaming
        console.print(Panel(
            "[yellow]Generating explanation...[/yellow]",
            border_style="yellow"
        ))
        console.print()
        
        # Stream the explanation
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(
            prompt=prompt, 
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        explanation = streamer.stream_markdown(chunks, title="✨ Code Explanation")
        
        if verbose:
            console.print(f"\n[dim]Provider: {provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")
        
        # Export if requested
        if export:
            export_path = Path(export)
            
            # Build markdown content
            md_content = f"# Code Explanation: {explanation_target}\n\n"
            md_content += f"**File:** `{file_info.path}`\n"
            md_content += f"**Language:** {file_info.language}\n\n"
            md_content += "## Code\n\n"
            md_content += f"```{file_info.language}\n{code_to_explain}\n```\n\n"
            md_content += "## Explanation\n\n"
            md_content += explanation
            
            export_path.write_text(md_content)
            console.print(f"\n[green]✅ Explanation exported to:[/green] {export_path}")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


@explain_group.command()
@click.argument('question', required=True)
@click.option(
    '--provider', '-p',
    default='groq',
    help='LLM provider to use'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Show verbose output'
)
def concept(question: str, provider: str, verbose: bool):
    """Explain a programming concept"""
    
    try:
        if verbose:
            console.print(f"Using provider: {provider}\n")
        
        # Build prompt
        prompt = f"Explain the following programming concept in detail:\n\n"
        prompt += f"**Concept:** {question}\n\n"
        prompt += "**Instructions:**\n"
        prompt += "1. Clear definition\n"
        prompt += "2. How it works\n"
        prompt += "3. When to use it\n"
        prompt += "4. Code examples\n"
        prompt += "5. Common pitfalls\n\n"
        prompt += "Explain in a clear, educational way with examples."
        
        system_prompt = PromptTemplates.system_prompt("explain")
        
        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)
        
        # Display question
        console.print(Panel(
            f"[cyan]Concept:[/cyan] {question}",
            title="❓ Question",
            border_style="cyan"
        ))
        console.print()
        
        # Stream the explanation
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(
            prompt=prompt, 
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        explanation = streamer.stream_markdown(chunks, title="✨ Concept Explanation")
        
        if verbose:
            console.print(f"\n[dim]Provider: {provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


@explain_group.command()
@click.option(
    '--staged/--unstaged',
    default=True,
    help='Explain staged or unstaged changes'
)
@click.option(
    '--provider', '-p',
    default='groq',
    help='LLM provider to use'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Show verbose output'
)
def diff(staged: bool, provider: str, verbose: bool):
    """Explain what changed in a git diff"""
    
    try:
        from lumecode.cli.core.context import GitContext
        
        # Initialize git context
        git = GitContext()
        
        # Check if git repo
        if not git.is_git_repo():
            console.print("[red]Error:[/red] Not a git repository", style="bold")
            return
        
        # Get diff
        diff_text = git.get_current_diff(staged=staged)
        
        if not diff_text or not diff_text.strip():
            console.print(f"[yellow]No {'staged' if staged else 'unstaged'} changes to explain[/yellow]")
            return
        
        # Get changed files
        files = git.get_diff_files(staged=staged)
        
        if verbose:
            console.print(f"Found changes in {len(files)} file(s)")
            for file_diff in files:
                console.print(f"  • {file_diff.file_path} (+{file_diff.additions}, -{file_diff.deletions})")
            console.print()
        
        # Show diff preview
        console.print(Panel(
            f"[cyan]Explaining {'staged' if staged else 'unstaged'} changes[/cyan]\n{len(files)} file(s) modified",
            title="📝 Git Diff",
            border_style="cyan"
        ))
        
        # Build prompt
        prompt = f"Explain what changed in this git diff:\n\n"
        prompt += f"```diff\n{diff_text[:5000]}\n```\n\n"  # Limit to first 5000 chars
        prompt += "**Explain:**\n"
        prompt += "1. What files were changed\n"
        prompt += "2. What was added/removed/modified\n"
        prompt += "3. What is the purpose of these changes\n"
        prompt += "4. Potential impact\n\n"
        prompt += "Be concise and focus on the key changes."
        
        system_prompt = PromptTemplates.system_prompt("explain")
        
        if verbose:
            console.print(f"Prompt length: {len(prompt)} chars")
            console.print(f"Using provider: {provider}\n")
        
        # Get LLM provider (with automatic fallback)
        llm = get_provider_with_fallback(provider, verbose=verbose)
        
        # Stream the explanation
        console.print(Panel(
            "[yellow]Analyzing changes...[/yellow]",
            border_style="yellow"
        ))
        console.print()
        
        streamer = StreamingDisplay(console)
        chunks = llm.stream_complete(
            prompt=prompt, 
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        explanation = streamer.stream_markdown(chunks, title="✨ Change Explanation")
        
        if verbose:
            console.print(f"\n[dim]Provider: {provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


if __name__ == '__main__':
    explain_group()
