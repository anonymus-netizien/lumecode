"""
Refactor Command
AI-powered code refactoring suggestions.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from typing import Optional

from lumecode.cli.core.context import FileContext, CodeParser
from lumecode.cli.core.prompts import PromptTemplates
from lumecode.cli.core.llm import get_provider
from lumecode.cli.core.refactor import RefactorParser
from lumecode.cli.core.ui import StreamingDisplay


console = Console()


@click.group(name='refactor')
def refactor_group():
    """AI-powered code refactoring suggestions"""
    pass


@refactor_group.command(name='suggest')
@click.argument('target', type=str)
@click.option(
    '--type', '-t',
    'refactor_type',
    type=click.Choice(['all', 'extract', 'simplify', 'naming', 'types', 'performance']),
    default='all',
    help='Type of refactoring to suggest'
)
@click.option(
    '--lines', '-l',
    help='Specific line range (e.g., 10-50, 10:50)'
)
@click.option(
    '--export', '-e',
    type=click.Path(),
    help='Export suggestions to markdown file'
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
def suggest(target: str, refactor_type: str, lines: str, export: str, provider: str, verbose: bool):
    """Suggest refactoring improvements for code.
    
    TARGET can be:
    - File path: path/to/file.py
    - Function: path/to/file.py::function_name
    - Class: path/to/file.py::ClassName
    
    Examples:
    
        lume refactor suggest main.py
        
        lume refactor suggest main.py::process_data
        
        lume refactor suggest main.py --lines 10-50
        
        lume refactor suggest main.py --type naming --export suggestions.md
    """
    try:
        # Parse target
        if '::' in target:
            file_path_str, symbol = target.split('::', 1)
            file_path = Path(file_path_str).resolve()
            
            # Validate file exists
            if not file_path.exists():
                console.print(f"[red]Error:[/red] File not found: {file_path}")
                raise click.Abort()
            
            # Read file content first
            file_ctx = FileContext()
            file_info = file_ctx.read_file(str(file_path))
            
            # Extract specific symbol
            parser = CodeParser()
            if symbol[0].isupper():  # Class
                code_data = parser.extract_class(file_info.content, symbol)
            else:  # Function
                code_data = parser.extract_function(file_info.content, symbol)
            
            if not code_data:
                console.print(f"[red]Error:[/red] Symbol '{symbol}' not found in {file_path.name}")
                raise click.Abort()
            
            context_info = f"{'Class' if symbol[0].isupper() else 'Function'}: {symbol}"
            code = code_data.code
            line_start = code_data.start_line
            line_end = code_data.end_line
            
        elif lines:
            # Specific line range
            file_path = Path(target).resolve()
            
            if not file_path.exists():
                console.print(f"[red]Error:[/red] File not found: {file_path}")
                raise click.Abort()
            
            # Read file content
            file_ctx = FileContext()
            file_info = file_ctx.read_file(str(file_path))
            
            # Parse line range
            parser = CodeParser()
            line_range_tuple = parser.parse_line_range(lines)
            
            if not line_range_tuple:
                console.print(f"[red]Error:[/red] Invalid line range: {lines}")
                console.print("Use format: 10-50, 10:50, or 10..50")
                raise click.Abort()
            
            line_start, line_end = line_range_tuple
            code = parser.extract_lines(file_info.content, line_start, line_end)
            context_info = f"Lines: {lines}"
            
        else:
            # Entire file
            file_path = Path(target).resolve()
            
            if not file_path.exists():
                console.print(f"[red]Error:[/red] File not found: {file_path}")
                raise click.Abort()
            
            file_ctx = FileContext()
            file_info = file_ctx.read_file(str(file_path))
            code = file_info.content
            context_info = "Entire file"
            line_start = 1
            line_end = file_info.line_count
        
        # Map refactor types to focus areas
        focus_map = {
            'extract': 'extract method refactoring',
            'simplify': 'code simplification and readability',
            'naming': 'variable and function naming improvements',
            'types': 'type hint additions and improvements',
            'performance': 'performance optimization opportunities'
        }
        
        focus = focus_map.get(refactor_type, 'all refactoring opportunities')
        
        # Build prompt
        prompt = f"""Analyze the following Python code and suggest refactoring improvements.

**File:** {file_path.name}
**Context:** {context_info}
**Focus:** {focus}

**Code:**
```python
{code}
```

Please provide specific, actionable refactoring suggestions following this format for EACH suggestion:

## Suggestion N: [Clear, concise title]
**Lines:** [start_line]-[end_line]
**Impact:** [High/Medium/Low]
**Type:** [extract_method/simplify/improve_naming/add_type_hints/etc]

**Description:** [Brief description of what to change]

**Current Code:**
```python
[The actual code that needs refactoring]
```

**Suggested Code:**
```python
[The refactored version]
```

**Reasoning:** [Why this improves the code - be specific about benefits]

Focus on:
1. Code clarity and readability
2. Maintainability improvements
3. Reducing complexity
4. Following Python best practices
5. Type safety (if applicable)

Provide 3-5 high-value suggestions that would have the most impact.
"""

        system_prompt = PromptTemplates.system_prompt("refactor")
        
        if verbose:
            console.print(f"[dim]File: {file_path.name}[/dim]")
            console.print(f"[dim]Context: {context_info}[/dim]")
            console.print(f"[dim]Focus: {focus}[/dim]")
            console.print(f"[dim]Provider: {provider}[/dim]\n")
        
        # Show analysis header
        console.print(Panel(
            f"[cyan]Analyzing code for refactoring opportunities...\n\n"
            f"📄 **File:** [yellow]{file_path.name}[/yellow]\n"
            f"🎯 **Focus:** [green]{focus}[/green]\n"
            f"📏 **Lines:** {line_start}-{line_end}",
            title="🔧 Refactor Analysis",
            border_style="cyan"
        ))
        console.print()
        
        # Get AI suggestions with streaming
        llm = get_provider(provider)
        chunks = llm.stream_complete(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3000
        )
        
        streamer = StreamingDisplay(console)
        response = streamer.stream_markdown(chunks, title="💡 Refactoring Suggestions")
        
        if verbose:
            console.print(f"\n[dim]Provider: {provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")
        
        # Export if requested
        if export:
            export_path = Path(export)
            
            # Build export content
            export_content = f"# Refactoring Suggestions: {file_path.name}\n\n"
            export_content += f"**Generated:** {Path().cwd()}\n"
            export_content += f"**Context:** {context_info}\n"
            export_content += f"**Focus:** {focus}\n\n"
            export_content += "---\n\n"
            export_content += response
            
            export_path.write_text(export_content)
            console.print(f"\n✅ Exported to [cyan]{export_path}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


@refactor_group.command(name='patterns')
@click.argument('file_path', type=click.Path(exists=True))
@click.option(
    '--export', '-e',
    type=click.Path(),
    help='Export analysis to markdown file'
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
def patterns(file_path: str, export: str, provider: str, verbose: bool):
    """Detect code smells and anti-patterns.
    
    Analyzes code for common issues:
    - Code duplication
    - Complex functions (high cyclomatic complexity)
    - Long parameter lists
    - God classes
    - Dead code
    - Magic numbers
    - Deep nesting
    
    Examples:
    
        lume refactor patterns main.py
        
        lume refactor patterns src/api.py --export analysis.md
    """
    try:
        file_path = Path(file_path).resolve()
        
        # Read file
        file_ctx = FileContext()
        file_info = file_ctx.read_file(str(file_path))
        
        # Build prompt
        templates = PromptTemplates()
        prompt = f"""Analyze the following Python code for code smells, anti-patterns, and quality issues.

**File:** {file_path.name}
**Lines:** {file_info.line_count}

**Code:**
```python
{file_info.content}
```

Please identify and document:

## 1. Code Smells
- **Duplicated Code:** Repeated logic that could be extracted
- **Long Methods:** Functions that are too long and do too much
- **Long Parameter Lists:** Functions with too many parameters
- **Large Classes:** Classes with too many responsibilities
- **Feature Envy:** Methods using more data from other classes than their own
- **Data Clumps:** Groups of data items that appear together repeatedly

## 2. Anti-Patterns
- **God Class:** Classes that know/do too much
- **Spaghetti Code:** Complex control flow
- **Magic Numbers:** Hard-coded values without explanation
- **Dead Code:** Unused functions, variables, or imports
- **Nested Hell:** Deeply nested conditionals or loops
- **Copy-Paste Programming:** Duplicated logic

## 3. Complexity Issues
- **High Cyclomatic Complexity:** Too many decision points
- **Deep Nesting:** Code indented more than 3-4 levels
- **Long Functions:** Functions over 20-30 lines

## 4. Maintainability Concerns
- **Poor Naming:** Unclear variable/function names
- **Missing Documentation:** Functions without docstrings
- **Inconsistent Style:** Mixed coding styles
- **Tight Coupling:** Strong dependencies between components

For each issue found, provide:
- **Severity:** Critical/Major/Minor
- **Location:** Line number(s)
- **Description:** What's wrong
- **Impact:** Why it matters
- **Suggestion:** How to fix it

Format as clear markdown sections. Be specific and constructive.
"""

        system_prompt = "You are a code quality expert specializing in identifying code smells and anti-patterns. Be thorough but constructive."
        
        if verbose:
            console.print(f"[dim]File: {file_path.name}[/dim]")
            console.print(f"[dim]Lines: {file_info.line_count}[/dim]")
            console.print(f"[dim]Provider: {provider}[/dim]\n")
        
        console.print(Panel(
            f"[cyan]Detecting code smells and anti-patterns...\n\n"
            f"📄 **File:** [yellow]{file_path.name}[/yellow]\n"
            f"📏 **Lines:** {file_info.line_count}",
            title="🔍 Pattern Analysis",
            border_style="cyan"
        ))
        console.print()
        
        # Get AI analysis with streaming
        llm = get_provider(provider)
        chunks = llm.stream_complete(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=3000
        )
        
        streamer = StreamingDisplay(console)
        response = streamer.stream_markdown(chunks, title="📊 Code Quality Analysis")
        
        if verbose:
            console.print(f"\n[dim]Provider: {provider}[/dim]")
            console.print(f"[dim]Model: {llm.model}[/dim]")
        
        # Export if requested
        if export:
            export_path = Path(export)
            
            export_content = f"# Code Quality Analysis: {file_path.name}\n\n"
            export_content += f"**Generated:** {Path().cwd()}\n"
            export_content += f"**File:** {file_path}\n"
            export_content += f"**Lines:** {file_info.line_count}\n\n"
            export_content += "---\n\n"
            export_content += response
            
            export_path.write_text(export_content)
            console.print(f"\n✅ Exported to [cyan]{export_path}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


@refactor_group.command(name='interactive')
@click.argument('file_path', type=click.Path(exists=True))
def interactive(file_path: str):
    """Interactive refactoring session (Coming Soon).
    
    This feature will allow you to:
    - Get suggestions one-by-one
    - Apply refactorings interactively
    - Preview changes before applying
    - Undo/redo changes
    
    Currently in development for Day 5!
    """
    console.print("[yellow]⚠️  Interactive mode coming in Day 5![/yellow]")
    console.print("\nFor now, use these commands:")
    console.print("  • [cyan]lume refactor suggest <file>[/cyan] - Get refactoring suggestions")
    console.print("  • [cyan]lume refactor patterns <file>[/cyan] - Detect code smells")
    console.print("\nThen apply changes manually in your editor.")
