"""Context manager for handling file context with token limits.

This module provides the ContextManager class which manages files in context,
ensures token limits are respected, and prioritizes files for optimal AI interaction.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .prioritizer import get_file_summary, prioritize_files
from .tokenizer import (
    count_tokens,
    estimate_tokens_from_chars,
    get_context_budget,
    truncate_to_tokens,
)


class ContextManager:
    """Manages file context with intelligent token management.

    Features:
    - Tracks files in context
    - Enforces token limits
    - Prioritizes files by relevance
    - Auto-truncates when needed
    - Provides token usage statistics

    Example:
        >>> manager = ContextManager(model='gpt-4')
        >>> manager.add_file(Path('main.py'))
        True
        >>> manager.get_token_count()
        450
        >>> context = manager.get_context()
    """

    def __init__(self, model: str = "gpt-3.5-turbo", max_tokens: Optional[int] = None):
        """Initialize ContextManager.

        Args:
            model: AI model name (determines token limits)
            max_tokens: Optional custom max tokens (overrides model default)
        """
        self.model = model
        self.files: List[Path] = []
        self.file_contents: Dict[Path, str] = {}
        self._max_tokens = max_tokens or get_context_budget(model)
        self._current_tokens = 0

    def add_file(self, file_path: Path, priority: bool = False) -> bool:
        """Add a file to context.

        Args:
            file_path: Path to file to add
            priority: If True, prioritize this file (add first)

        Returns:
            True if added successfully, False if would exceed token limit

        Example:
            >>> manager.add_file(Path('utils.py'))
            True
        """
        # Validate file
        if not file_path.exists():
            return False

        # Check if already added
        if file_path in self.files:
            return True

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False

        # Count tokens
        tokens = count_tokens(content, self.model)

        # Check if adding would exceed limit
        if self._current_tokens + tokens > self._max_tokens:
            # Try to make space by truncating other files
            if not self._make_space_for_tokens(tokens):
                return False

        # Add file
        if priority:
            self.files.insert(0, file_path)
        else:
            self.files.append(file_path)

        self.file_contents[file_path] = content
        self._current_tokens += tokens

        return True

    def remove_file(self, file_path: Path) -> bool:
        """Remove a file from context.

        Args:
            file_path: Path to file to remove

        Returns:
            True if removed, False if not in context

        Example:
            >>> manager.remove_file(Path('utils.py'))
            True
        """
        if file_path not in self.files:
            return False

        # Remove from lists
        self.files.remove(file_path)
        content = self.file_contents.pop(file_path)

        # Update token count
        tokens = count_tokens(content, self.model)
        self._current_tokens -= tokens

        return True

    def clear(self) -> None:
        """Clear all files from context.

        Example:
            >>> manager.clear()
        """
        self.files.clear()
        self.file_contents.clear()
        self._current_tokens = 0

    def get_context(self, format: str = "markdown") -> str:
        """Get formatted context string for AI.

        Args:
            format: Output format ('markdown', 'plain', or 'xml')

        Returns:
            Formatted context string with all files

        Example:
            >>> context = manager.get_context()
            >>> print(context)
            # Context Files

            ## File: main.py
            ```python
            def main():
                pass
            ```
        """
        if not self.files:
            return ""

        # Prioritize files
        prioritized = prioritize_files(self.files)

        # Build context
        if format == "markdown":
            return self._format_context_markdown(prioritized)
        elif format == "xml":
            return self._format_context_xml(prioritized)
        else:
            return self._format_context_plain(prioritized)

    def get_token_count(self) -> int:
        """Get current token count.

        Returns:
            Number of tokens used by current context

        Example:
            >>> manager.get_token_count()
            1234
        """
        return self._current_tokens

    def get_max_tokens(self) -> int:
        """Get maximum token limit.

        Returns:
            Maximum tokens allowed
        """
        return self._max_tokens

    def get_usage_percentage(self) -> float:
        """Get percentage of token budget used.

        Returns:
            Percentage (0.0 to 100.0)

        Example:
            >>> manager.get_usage_percentage()
            45.5
        """
        if self._max_tokens == 0:
            return 0.0
        return (self._current_tokens / self._max_tokens) * 100

    def get_summary(self) -> Dict[str, Any]:
        """Get detailed summary of context state.

        Returns:
            Dict with context statistics

        Example:
            >>> summary = manager.get_summary()
            >>> print(summary['file_count'])
            3
        """
        file_summaries = [get_file_summary(f) for f in self.files]

        return {
            "model": self.model,
            "file_count": len(self.files),
            "files": file_summaries,
            "current_tokens": self._current_tokens,
            "max_tokens": self._max_tokens,
            "usage_percentage": self.get_usage_percentage(),
            "available_tokens": self._max_tokens - self._current_tokens,
        }

    def can_add_file(self, file_path: Path) -> bool:
        """Check if a file can be added without exceeding limit.

        Args:
            file_path: Path to file to check

        Returns:
            True if file can be added

        Example:
            >>> manager.can_add_file(Path('large.py'))
            False
        """
        if not file_path.exists():
            return False

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tokens = count_tokens(content, self.model)
            return (self._current_tokens + tokens) <= self._max_tokens
        except Exception:
            return False

    def _make_space_for_tokens(self, needed_tokens: int) -> bool:
        """Try to make space by truncating or removing files.

        Args:
            needed_tokens: Number of tokens needed

        Returns:
            True if enough space created
        """
        available = self._max_tokens - self._current_tokens

        if available >= needed_tokens:
            return True

        # Try truncating least important files
        files_by_priority = prioritize_files(self.files)
        files_by_priority.reverse()  # Start with lowest priority

        for file_path in files_by_priority:
            if available >= needed_tokens:
                return True

            # Try truncating to 50% of original
            content = self.file_contents[file_path]
            current_tokens = count_tokens(content, self.model)
            target_tokens = current_tokens // 2

            if target_tokens < 100:  # Too small, remove instead
                self.remove_file(file_path)
                available = self._max_tokens - self._current_tokens
            else:
                # Truncate
                truncated = truncate_to_tokens(content, target_tokens, self.model)
                self.file_contents[file_path] = truncated

                # Update token count
                new_tokens = count_tokens(truncated, self.model)
                self._current_tokens = self._current_tokens - current_tokens + new_tokens
                available = self._max_tokens - self._current_tokens

        return available >= needed_tokens

    def _format_context_markdown(self, files: List[Path]) -> str:
        """Format context as markdown."""
        parts = ["# Context Files\n"]

        for file_path in files:
            content = self.file_contents.get(file_path, "")
            ext = file_path.suffix.lstrip(".")

            parts.append(f"\n## File: {file_path.name}\n")
            parts.append(f"Path: `{file_path}`\n")
            parts.append(f"\n```{ext}\n{content}\n```\n")

        return "\n".join(parts)

    def _format_context_xml(self, files: List[Path]) -> str:
        """Format context as XML."""
        parts = ["<context>"]

        for file_path in files:
            content = self.file_contents.get(file_path, "")
            parts.append(f"  <file path='{file_path}'>")
            parts.append(f"    <![CDATA[{content}]]>")
            parts.append("  </file>")

        parts.append("</context>")
        return "\n".join(parts)

    def _format_context_plain(self, files: List[Path]) -> str:
        """Format context as plain text."""
        parts = []

        for file_path in files:
            content = self.file_contents.get(file_path, "")
            parts.append(f"=== File: {file_path} ===\n")
            parts.append(content)
            parts.append("\n" + "=" * 50 + "\n")

        return "\n".join(parts)
