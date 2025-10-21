"""Tests for ContextManager."""

import pytest
from pathlib import Path
from lumecode.cli.core.context.manager import ContextManager


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files."""
    files = {}

    # Small file (~100 tokens)
    small = tmp_path / "small.py"
    small.write_text("def hello():\n    print('Hello')\n    return True")
    files["small"] = small

    # Medium file (~500 tokens estimate)
    medium = tmp_path / "medium.py"
    medium.write_text("# Python code\n" * 100)
    files["medium"] = medium

    # Large file (~2000 tokens estimate)
    large = tmp_path / "large.py"
    large.write_text("# Large Python file\n" * 400)
    files["large"] = large

    return files


class TestContextManagerInit:
    """Test ContextManager initialization."""

    def test_init_default(self):
        """Test default initialization."""
        manager = ContextManager()
        assert manager.model == "gpt-3.5-turbo"
        assert len(manager.files) == 0
        assert manager.get_token_count() == 0

    def test_init_with_model(self):
        """Test initialization with specific model."""
        manager = ContextManager(model="gpt-4")
        assert manager.model == "gpt-4"
        assert manager.get_max_tokens() > 4096

    def test_init_with_custom_max_tokens(self):
        """Test initialization with custom max tokens."""
        manager = ContextManager(max_tokens=2000)
        assert manager.get_max_tokens() == 2000


class TestAddFile:
    """Test adding files to context."""

    def test_add_file_success(self, temp_files):
        """Test successfully adding a file."""
        manager = ContextManager()
        result = manager.add_file(temp_files["small"])

        assert result is True
        assert len(manager.files) == 1
        assert temp_files["small"] in manager.files
        assert manager.get_token_count() > 0

    def test_add_file_nonexistent(self, tmp_path):
        """Test adding nonexistent file fails."""
        manager = ContextManager()
        fake_file = tmp_path / "nonexistent.py"
        result = manager.add_file(fake_file)

        assert result is False
        assert len(manager.files) == 0

    def test_add_file_duplicate(self, temp_files):
        """Test adding same file twice."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        result = manager.add_file(temp_files["small"])

        assert result is True  # Should succeed (already added)
        assert len(manager.files) == 1  # But not duplicate

    def test_add_multiple_files(self, temp_files):
        """Test adding multiple files."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])

        assert len(manager.files) == 2
        assert manager.get_token_count() > 0

    def test_add_file_with_priority(self, temp_files):
        """Test adding file with priority."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"], priority=True)

        # Priority file should be first
        assert manager.files[0] == temp_files["medium"]

    def test_add_file_exceeds_limit(self, temp_files):
        """Test adding file that would exceed token limit."""
        # Create manager with very small limit
        manager = ContextManager(max_tokens=100)

        # Add large file (should try to make space or fail)
        result = manager.add_file(temp_files["large"])

        # Behavior: may succeed with truncation or fail
        # Either way, should not exceed limit
        assert manager.get_token_count() <= manager.get_max_tokens()


class TestRemoveFile:
    """Test removing files from context."""

    def test_remove_file_success(self, temp_files):
        """Test successfully removing a file."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        initial_tokens = manager.get_token_count()
        result = manager.remove_file(temp_files["small"])

        assert result is True
        assert len(manager.files) == 0
        assert manager.get_token_count() == 0
        assert manager.get_token_count() < initial_tokens

    def test_remove_file_not_in_context(self, temp_files):
        """Test removing file not in context."""
        manager = ContextManager()
        result = manager.remove_file(temp_files["small"])

        assert result is False

    def test_remove_one_of_multiple(self, temp_files):
        """Test removing one file when multiple present."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])

        manager.remove_file(temp_files["small"])

        assert len(manager.files) == 1
        assert temp_files["medium"] in manager.files
        assert temp_files["small"] not in manager.files


class TestClear:
    """Test clearing context."""

    def test_clear_empty_context(self):
        """Test clearing empty context."""
        manager = ContextManager()
        manager.clear()

        assert len(manager.files) == 0
        assert manager.get_token_count() == 0

    def test_clear_with_files(self, temp_files):
        """Test clearing context with files."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])

        manager.clear()

        assert len(manager.files) == 0
        assert manager.get_token_count() == 0


class TestGetContext:
    """Test getting context string."""

    def test_get_context_empty(self):
        """Test getting context when empty."""
        manager = ContextManager()
        context = manager.get_context()

        assert context == ""

    def test_get_context_markdown(self, temp_files):
        """Test getting context in markdown format."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        context = manager.get_context(format="markdown")

        assert "# Context Files" in context
        assert "small.py" in context
        assert "```py" in context
        assert "def hello()" in context

    def test_get_context_plain(self, temp_files):
        """Test getting context in plain format."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        context = manager.get_context(format="plain")

        assert "=== File:" in context
        assert "small.py" in context
        assert "def hello()" in context

    def test_get_context_xml(self, temp_files):
        """Test getting context in XML format."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        context = manager.get_context(format="xml")

        assert "<context>" in context
        assert "<file path=" in context
        assert "<![CDATA[" in context
        assert "def hello()" in context

    def test_get_context_multiple_files(self, temp_files):
        """Test getting context with multiple files."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])

        context = manager.get_context()

        assert "small.py" in context
        assert "medium.py" in context


class TestTokenCounting:
    """Test token counting methods."""

    def test_get_token_count_empty(self):
        """Test token count for empty context."""
        manager = ContextManager()
        assert manager.get_token_count() == 0

    def test_get_token_count_with_files(self, temp_files):
        """Test token count with files."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        count = manager.get_token_count()
        assert count > 0
        assert count < 200  # Small file should be < 200 tokens

    def test_get_max_tokens(self):
        """Test getting max token limit."""
        manager = ContextManager(model="gpt-4")
        max_tokens = manager.get_max_tokens()

        assert max_tokens == 6144  # 75% of 8192

    def test_get_usage_percentage_empty(self):
        """Test usage percentage when empty."""
        manager = ContextManager()
        assert manager.get_usage_percentage() == 0.0

    def test_get_usage_percentage_with_files(self, temp_files):
        """Test usage percentage with files."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        percentage = manager.get_usage_percentage()
        assert 0.0 < percentage < 100.0


class TestGetSummary:
    """Test getting context summary."""

    def test_get_summary_empty(self):
        """Test summary for empty context."""
        manager = ContextManager()
        summary = manager.get_summary()

        assert summary["file_count"] == 0
        assert summary["current_tokens"] == 0
        assert summary["model"] == "gpt-3.5-turbo"
        assert "max_tokens" in summary
        assert "usage_percentage" in summary
        assert "available_tokens" in summary

    def test_get_summary_with_files(self, temp_files):
        """Test summary with files."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])

        summary = manager.get_summary()

        assert summary["file_count"] == 2
        assert summary["current_tokens"] > 0
        assert len(summary["files"]) == 2

        # Check file summaries
        for file_summary in summary["files"]:
            assert "name" in file_summary
            assert "size" in file_summary
            assert "exists" in file_summary


class TestCanAddFile:
    """Test checking if file can be added."""

    def test_can_add_small_file(self, temp_files):
        """Test that small file can be added."""
        manager = ContextManager()
        assert manager.can_add_file(temp_files["small"]) is True

    def test_can_add_when_near_limit(self, temp_files):
        """Test checking when near token limit."""
        manager = ContextManager(max_tokens=500)
        manager.add_file(temp_files["medium"])

        # May or may not be able to add another file
        result = manager.can_add_file(temp_files["small"])
        assert isinstance(result, bool)

    def test_cannot_add_nonexistent(self, tmp_path):
        """Test that nonexistent file cannot be added."""
        manager = ContextManager()
        fake_file = tmp_path / "nonexistent.py"
        assert manager.can_add_file(fake_file) is False


class TestContextManagerIntegration:
    """Integration tests for ContextManager."""

    def test_full_workflow(self, temp_files):
        """Test complete workflow with multiple operations."""
        manager = ContextManager(model="gpt-4")

        # Add files
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])

        # Check state
        assert len(manager.files) == 2
        assert manager.get_token_count() > 0

        # Get context
        context = manager.get_context()
        assert len(context) > 0

        # Get summary
        summary = manager.get_summary()
        assert summary["file_count"] == 2

        # Remove file
        manager.remove_file(temp_files["small"])
        assert len(manager.files) == 1

        # Clear
        manager.clear()
        assert len(manager.files) == 0
        assert manager.get_token_count() == 0

    def test_token_limit_enforcement(self, temp_files):
        """Test that token limits are enforced."""
        manager = ContextManager(max_tokens=1000)

        # Try adding files
        manager.add_file(temp_files["small"])
        manager.add_file(temp_files["medium"])
        manager.add_file(temp_files["large"])

        # Should not exceed limit
        assert manager.get_token_count() <= manager.get_max_tokens()

    def test_context_formats(self, temp_files):
        """Test all context output formats."""
        manager = ContextManager()
        manager.add_file(temp_files["small"])

        markdown = manager.get_context(format="markdown")
        plain = manager.get_context(format="plain")
        xml = manager.get_context(format="xml")

        # All formats should contain the file content
        assert "def hello()" in markdown
        assert "def hello()" in plain
        assert "def hello()" in xml

        # Each should have its own markers
        assert "```" in markdown
        assert "===" in plain
        assert "<context>" in xml

    def test_usage_calculation(self, temp_files):
        """Test usage percentage calculation."""
        manager = ContextManager(max_tokens=1000)

        # Empty
        assert manager.get_usage_percentage() == 0.0

        # Add file
        manager.add_file(temp_files["small"])
        usage1 = manager.get_usage_percentage()
        assert usage1 > 0.0

        # Add another
        manager.add_file(temp_files["medium"])
        usage2 = manager.get_usage_percentage()
        assert usage2 > usage1

        # Should not exceed 100%
        assert usage2 <= 100.0
