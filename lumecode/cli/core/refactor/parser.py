"""
Refactoring Parser
Parse and structure refactoring suggestions from LLM responses.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class RefactorType(Enum):
    """Types of refactoring suggestions."""

    EXTRACT_METHOD = "extract_method"
    RENAME = "rename"
    SIMPLIFY = "simplify"
    REMOVE_DUPLICATION = "remove_duplication"
    IMPROVE_NAMING = "improve_naming"
    ADD_TYPE_HINTS = "add_type_hints"
    OPTIMIZE_PERFORMANCE = "optimize_performance"
    IMPROVE_READABILITY = "improve_readability"
    EXTRACT_VARIABLE = "extract_variable"
    INLINE = "inline"
    MOVE_METHOD = "move_method"


@dataclass
class RefactorSuggestion:
    """A single refactoring suggestion."""

    type: RefactorType
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    original_code: str
    suggested_code: str
    reasoning: str
    impact: str  # "high", "medium", "low"

    def __str__(self) -> str:
        """String representation."""
        return f"{self.impact.upper()}: {self.title} (lines {self.line_start}-{self.line_end})"


class RefactorParser:
    """Parse LLM refactoring suggestions into structured format."""

    # Impact emoji mapping
    IMPACT_EMOJI = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢",
        "critical": "🔴",
        "major": "🟡",
        "minor": "🟢",
    }

    # Type emoji mapping
    TYPE_EMOJI = {
        RefactorType.EXTRACT_METHOD: "🔧",
        RefactorType.RENAME: "✏️",
        RefactorType.SIMPLIFY: "🎯",
        RefactorType.REMOVE_DUPLICATION: "♻️",
        RefactorType.IMPROVE_NAMING: "💭",
        RefactorType.ADD_TYPE_HINTS: "🏷️",
        RefactorType.OPTIMIZE_PERFORMANCE: "⚡",
        RefactorType.IMPROVE_READABILITY: "📖",
        RefactorType.EXTRACT_VARIABLE: "📦",
        RefactorType.INLINE: "➡️",
        RefactorType.MOVE_METHOD: "🔀",
    }

    def parse_suggestions(self, response: str, file_path: str) -> List[RefactorSuggestion]:
        """
        Parse refactoring suggestions from LLM response.

        Expected format:
        ## Suggestion 1: Extract Method
        **Lines:** 10-25
        **Impact:** High
        **Type:** extract_method

        **Description:** Extract complex logic into separate method

        **Current Code:**
        ```python
        ... code ...
        ```

        **Suggested Code:**
        ```python
        ... code ...
        ```

        **Reasoning:** ...

        Args:
            response: LLM response text
            file_path: Path to file being refactored

        Returns:
            List of parsed RefactorSuggestion objects
        """
        suggestions = []

        # Split by suggestion headers
        pattern = r"## Suggestion \d+:"
        sections = re.split(pattern, response)

        # Skip first section (intro text)
        sections = sections[1:] if len(sections) > 1 else sections

        for section in sections:
            try:
                suggestion = self._parse_single_suggestion(section, file_path)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                # Skip malformed suggestions
                continue

        return suggestions

    def _parse_single_suggestion(self, text: str, file_path: str) -> Optional[RefactorSuggestion]:
        """Parse a single suggestion section."""

        # Extract title (first line)
        title_match = re.search(r"^([^\n]+)", text.strip())
        title = title_match.group(1).strip() if title_match else "Refactoring Suggestion"

        # Extract lines
        lines_match = re.search(r"\*\*Lines?:\*\*\s*(\d+)[-:](\d+)", text)
        if not lines_match:
            return None
        line_start = int(lines_match.group(1))
        line_end = int(lines_match.group(2))

        # Extract impact
        impact_match = re.search(r"\*\*Impact:\*\*\s*(\w+)", text, re.IGNORECASE)
        impact = impact_match.group(1).lower() if impact_match else "medium"
        if impact not in ["high", "medium", "low"]:
            impact = "medium"

        # Extract type
        type_match = re.search(r"\*\*Type:\*\*\s*(\w+)", text, re.IGNORECASE)
        type_str = type_match.group(1).lower() if type_match else "simplify"
        try:
            refactor_type = RefactorType(type_str)
        except ValueError:
            refactor_type = RefactorType.SIMPLIFY

        # Extract description
        desc_match = re.search(r"\*\*Description:\*\*\s*([^\*]+)", text)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract current code
        current_match = re.search(
            r"\*\*Current Code:\*\*\s*```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL
        )
        original_code = current_match.group(1).strip() if current_match else ""

        # Extract suggested code
        suggested_match = re.search(
            r"\*\*Suggested Code:\*\*\s*```(?:python)?\s*\n(.*?)\n```", text, re.DOTALL
        )
        suggested_code = suggested_match.group(1).strip() if suggested_match else ""

        # Extract reasoning
        reasoning_match = re.search(r"\*\*Reasoning:\*\*\s*([^\*\n]+)", text)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        return RefactorSuggestion(
            type=refactor_type,
            title=title,
            description=description,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            original_code=original_code,
            suggested_code=suggested_code,
            reasoning=reasoning,
            impact=impact,
        )

    def format_suggestion(self, suggestion: RefactorSuggestion) -> str:
        """
        Format suggestion for display with Rich.

        Args:
            suggestion: RefactorSuggestion to format

        Returns:
            Formatted markdown string
        """
        impact_emoji = self.IMPACT_EMOJI.get(suggestion.impact, "⚪")
        type_emoji = self.TYPE_EMOJI.get(suggestion.type, "🔧")

        output = f"""
{impact_emoji} {type_emoji} **{suggestion.title}**
*{suggestion.type.value.replace('_', ' ').title()}*

📍 **Location:** `{suggestion.file_path}:{suggestion.line_start}-{suggestion.line_end}`  
💡 **Impact:** {suggestion.impact.title()}

**Description:**
{suggestion.description}

**Current Code:**
```python
{suggestion.original_code}
```

**Suggested Code:**
```python
{suggestion.suggested_code}
```

**Reasoning:**
{suggestion.reasoning}

---
"""
        return output

    def format_summary(self, suggestions: List[RefactorSuggestion]) -> str:
        """
        Format a summary of all suggestions.

        Args:
            suggestions: List of suggestions

        Returns:
            Formatted summary string
        """
        if not suggestions:
            return "✅ No refactoring suggestions - code looks good!"

        # Count by impact
        high = len([s for s in suggestions if s.impact == "high"])
        medium = len([s for s in suggestions if s.impact == "medium"])
        low = len([s for s in suggestions if s.impact == "low"])

        summary = f"""
## Refactoring Summary

**Total Suggestions:** {len(suggestions)}

**By Impact:**
- 🔴 High: {high}
- 🟡 Medium: {medium}
- 🟢 Low: {low}

**Suggestions:**
"""
        for i, suggestion in enumerate(suggestions, 1):
            emoji = self.IMPACT_EMOJI.get(suggestion.impact, "⚪")
            summary += f"{i}. {emoji} {suggestion.title} (lines {suggestion.line_start}-{suggestion.line_end})\n"

        return summary
