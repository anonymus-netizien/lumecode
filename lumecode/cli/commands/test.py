"""
Test Generation Command
Generate and improve unit tests using AI
"""

from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from ..core.context import CodeParser, FileContext
from ..core.llm import get_provider, get_provider_with_fallback  # get_provider for tests patching
from ..core.prompts import PromptTemplates
from ..core.ui import StreamingDisplay

console = Console()


@click.group(name="test")
def test_group():
    """🧪 Generate and improve unit tests using AI"""
    pass


@test_group.command(name="generate")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--target", "-t", help="Target to test (function/class name)")
@click.option("--framework", "-f", default="pytest", help="Test framework (pytest, unittest)")
@click.option("--provider", "-p", default="groq", help="LLM provider (groq, openrouter, mock)")
@click.option("--model", "-m", help="Model to use")
@click.option("--output", "-o", help="Output file path for generated tests")
@click.option("--coverage", "-c", is_flag=True, help="Focus on coverage gaps")
def generate(file_path, target, framework, provider, model, output, coverage):
    """
    Generate unit tests for a file, class, or function.

    Examples:
        # Generate tests for entire file
        lume test generate src/utils.py

        # Generate tests for specific function
        lume test generate src/utils.py --target calculate_total

        # Generate tests for class
        lume test generate src/models.py --target UserModel

        # Save to specific file
        lume test generate src/app.py -o tests/test_app.py

        # Focus on coverage gaps
        lume test generate src/core.py --coverage
    """
    try:
        console.print(f"\n🧪 Generating tests for [cyan]{file_path}[/cyan]...")

        # Parse file and extract code
        file_ctx = FileContext()
        file_info = file_ctx.read_file(file_path)

        if not file_info:
            console.print("[red]❌ Could not read file[/red]")
            return

        parser = CodeParser()
        content = file_info.content

        # Build test generation prompt
        if target:
            # Generate tests for specific symbol
            # Try function first
            symbol = parser.extract_function(content, target)
            if not symbol:
                # Try class
                symbol = parser.extract_class(content, target)

            if not symbol:
                console.print(f"[red]❌ Could not find '{target}' in file[/red]")
                return

            code_to_test = symbol.code
            symbol_type = symbol.type
            context_info = f"Generating tests for {symbol_type}: {target}"
        else:
            # Generate tests for entire file
            code_to_test = content
            context_info = f"Generating tests for entire file: {Path(file_path).name}"

        # Get all symbols
        all_symbols = parser.list_symbols(content)
        imports = all_symbols.get("imports", [])
        functions = all_symbols.get("functions", [])
        classes = all_symbols.get("classes", [])

        # Build comprehensive prompt
        prompt = f"""Generate comprehensive unit tests for this Python code.

**Code to Test:**
```python
{code_to_test}
```

**Context:**
- File: {Path(file_path).name}
- Framework: {framework}
- {context_info}
- Imports found: {len(imports)}
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
{"8. Focus on coverage gaps and untested branches" if coverage else ""}

**Output Format:**
- Start with necessary imports
- Include fixtures if needed
- Group related tests in classes
- Add comments explaining complex tests
- Follow {framework} best practices

Generate complete, production-ready test code:"""

        system_prompt = PromptTemplates.get_system_prompt("test")

        # Stream test generation
        llm = get_provider_with_fallback(preferred_provider=provider)
        if model:
            llm.model = model

        console.print(f"\n🤖 Generating {framework} tests...\n")

        display = StreamingDisplay()
        response = display.stream_markdown(
            llm.stream_complete(
                prompt=prompt, max_tokens=2000, temperature=0.7, system_prompt=system_prompt
            )
        )

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract code blocks from response
            import re

            code_blocks = re.findall(r"```(?:python)?\n(.*?)```", response, re.DOTALL)

            if code_blocks:
                test_code = code_blocks[0].strip()
                output_path.write_text(test_code)
                console.print(f"\n✅ Tests saved to [cyan]{output}[/cyan]")
            else:
                output_path.write_text(response)
                console.print(f"\n✅ Response saved to [cyan]{output}[/cyan]")

        console.print(f"\n✨ Test generation complete!")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@test_group.command(name="improve")
@click.argument("test_file", type=click.Path(exists=True))
@click.option("--focus", "-f", help="Focus area (coverage, edge-cases, performance, readability)")
@click.option("--provider", "-p", default="groq", help="LLM provider")
@click.option("--model", "-m", help="Model to use")
@click.option("--output", "-o", help="Output file path")
def improve(test_file, focus, provider, model, output):
    """
    Improve existing unit tests.

    Examples:
        # Improve test coverage
        lume test improve tests/test_utils.py --focus coverage

        # Improve edge case testing
        lume test improve tests/test_models.py --focus edge-cases

        # Improve test readability
        lume test improve tests/test_core.py --focus readability

        # Save to new file
        lume test improve tests/test_app.py -o tests/test_app_v2.py
    """
    try:
        console.print(f"\n🔧 Analyzing tests in [cyan]{test_file}[/cyan]...")

        # Read existing tests
        test_path = Path(test_file)
        test_code = test_path.read_text()

        # Build improvement prompt
        focus_prompts = {
            "coverage": "Improve code coverage by adding tests for untested branches and edge cases",
            "edge-cases": "Add tests for edge cases, boundary conditions, and error scenarios",
            "performance": "Add performance tests and optimize slow tests",
            "readability": "Improve test readability with better names, docstrings, and structure",
        }

        focus_instruction = focus_prompts.get(focus, "Improve overall test quality")

        prompt = f"""Analyze and improve these unit tests.

**Current Tests:**
```python
{test_code}
```

**Improvement Focus:** {focus_instruction}

**Requirements:**
1. Keep existing tests that are good
2. Improve or replace weak tests
3. Add missing test cases
4. Improve test organization
5. Add helpful comments
6. Follow pytest/unittest best practices
7. Ensure tests are maintainable

**Provide:**
1. Analysis of current test quality
2. Specific improvements made
3. New tests added
4. Complete improved test code

Generate the improved test suite:"""

        system_prompt = PromptTemplates.get_system_prompt("test")

        # Stream improvements
        llm = get_provider_with_fallback(preferred_provider=provider)
        if model:
            llm.model = model

        console.print(f"\n🤖 Improving tests (focus: {focus or 'general'})...\n")

        display = StreamingDisplay()
        response = display.stream_markdown(
            llm.stream_complete(
                prompt=prompt, max_tokens=2000, temperature=0.7, system_prompt=system_prompt
            )
        )

        # Save if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Extract code blocks
            import re

            code_blocks = re.findall(r"```(?:python)?\n(.*?)```", response, re.DOTALL)

            if code_blocks:
                improved_code = code_blocks[-1].strip()  # Get last code block (improved version)
                output_path.write_text(improved_code)
                console.print(f"\n✅ Improved tests saved to [cyan]{output}[/cyan]")
            else:
                output_path.write_text(response)
                console.print(f"\n✅ Response saved to [cyan]{output}[/cyan]")

        console.print(f"\n✨ Test improvement complete!")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


@test_group.command(name="coverage")
@click.argument("source_file", type=click.Path(exists=True))
@click.argument("test_file", type=click.Path(exists=True))
@click.option("--provider", "-p", default="groq", help="LLM provider")
@click.option("--model", "-m", help="Model to use")
def coverage(source_file, test_file, provider, model):
    """
    Analyze coverage gaps between source and tests.

    Examples:
        # Check coverage gaps
        lume test coverage src/utils.py tests/test_utils.py

        # Analyze coverage for models
        lume test coverage src/models.py tests/test_models.py
    """
    try:
        console.print("\n📊 Analyzing test coverage...\n")

        # Read both files
        source_path = Path(source_file)
        test_path = Path(test_file)

        source_code = source_path.read_text()
        test_code = test_path.read_text()

        # Parse both files
        parser = CodeParser()

        source_symbols = parser.list_symbols(source_code)
        test_symbols = parser.list_symbols(test_code)

        source_functions = source_symbols.get("functions", [])
        source_classes = source_symbols.get("classes", [])
        test_functions = test_symbols.get("functions", [])

        # Build coverage analysis prompt
        prompt = f"""Analyze test coverage for this code.

**Source Code:**
```python
{source_code}
```

**Current Tests:**
```python
{test_code}
```

**Coverage Analysis Required:**

1. **Functions Coverage:**
   - Source has {len(source_functions)} functions
   - Tests have {len(test_functions)} test functions
   - Which functions are tested?
   - Which functions are missing tests?

2. **Classes Coverage:**
   - Source has {len(source_classes)} classes
   - Which classes are tested?
   - Which methods are missing tests?

3. **Edge Cases:**
   - What edge cases are tested?
   - What edge cases are missing?

4. **Error Handling:**
   - Are error paths tested?
   - What error scenarios are missing?

5. **Recommendations:**
   - What tests should be added?
   - What's the estimated coverage %?
   - Priority order for new tests

Provide detailed coverage analysis:"""

        system_prompt = PromptTemplates.get_system_prompt("test")

        # Stream analysis
        llm = get_provider_with_fallback(preferred_provider=provider)
        if model:
            llm.model = model

        console.print("🤖 Analyzing coverage...\n")

        display = StreamingDisplay()
        display.stream_markdown(
            llm.stream_complete(
                prompt=prompt, max_tokens=1500, temperature=0.7, system_prompt=system_prompt
            )
        )

        console.print("\n✨ Coverage analysis complete!")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    test_group()
