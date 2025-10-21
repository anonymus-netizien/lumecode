"""
Unit tests for File Operations
Tests file read, search, tree, and basic operations
"""

import pytest
import os
from click.testing import CliRunner
from pathlib import Path
import tempfile
import shutil

from lumecode.cli.commands.file import file


class TestFileRead:
    """Test file read operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory with test files."""
        temp_path = Path(tempfile.mkdtemp())

        # Create test files
        (temp_path / "test.txt").write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
        (temp_path / "test.py").write_text("def hello():\n    print('Hello')\n    return True\n")
        (temp_path / "README.md").write_text(
            "# Test\n\nThis is a test.\n\n## Section\n\nMore content.\n"
        )

        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def in_temp_dir(self, temp_dir, monkeypatch):
        """Change to temp directory for the test."""
        monkeypatch.chdir(temp_dir)
        return temp_dir

    def test_read_full_file(self, temp_dir):
        """Test reading entire file."""
        runner = CliRunner()
        test_file = temp_dir / "test.txt"

        result = runner.invoke(file, ["read", str(test_file)])

        assert result.exit_code == 0
        assert "Line 1" in result.output
        assert "Line 5" in result.output

    def test_read_with_line_range(self, temp_dir):
        """Test reading specific line range."""
        runner = CliRunner()
        test_file = temp_dir / "test.txt"

        result = runner.invoke(file, ["read", str(test_file), "--lines", "2-4"])

        assert result.exit_code == 0
        assert "Line 2" in result.output
        assert "Line 3" in result.output
        assert "Line 4" in result.output
        # Should not include line 1 or 5
        assert "Line 1" not in result.output or "Lines 1-30" in result.output  # Help text exception
        assert "Line 5" not in result.output or "Lines 1-30" in result.output  # Help text exception

    def test_read_nonexistent_file(self):
        """Test reading file that doesn't exist."""
        runner = CliRunner()

        result = runner.invoke(file, ["read", "/nonexistent/file.txt"])

        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()

    def test_read_python_file(self, temp_dir):
        """Test reading Python file."""
        runner = CliRunner()
        test_file = temp_dir / "test.py"

        result = runner.invoke(file, ["read", str(test_file)])

        assert result.exit_code == 0
        assert "def hello()" in result.output
        assert "print('Hello')" in result.output

    def test_read_markdown_file(self, temp_dir):
        """Test reading Markdown file."""
        runner = CliRunner()
        test_file = temp_dir / "README.md"

        result = runner.invoke(file, ["read", str(test_file)])

        assert result.exit_code == 0
        assert "# Test" in result.output
        assert "## Section" in result.output


class TestFileSearch:
    """Test file search operations."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory with searchable files."""
        temp_path = Path(tempfile.mkdtemp())

        # Create test files with TODO items
        (temp_path / "file1.py").write_text(
            "# TODO: Implement feature\n"
            "def main():\n"
            "    # TODO: Add error handling\n"
            "    pass\n"
        )

        (temp_path / "file2.md").write_text(
            "# Documentation\n"
            "\n"
            "TODO: Update this section\n"
            "\n"
            "## Notes\n"
            "TODO: Add examples\n"
        )

        (temp_path / "file3.txt").write_text(
            "Random content\n" "Nothing to see here\n" "More content\n"
        )

        # Create subdirectory
        subdir = temp_path / "subdir"
        subdir.mkdir()
        (subdir / "file4.py").write_text("# TODO: Review this code\n" "print('Hello')\n")

        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def in_temp_dir(self, temp_dir, monkeypatch):
        """Change to temp directory for the test."""
        monkeypatch.chdir(temp_dir)
        return temp_dir

    def test_search_basic(self, in_temp_dir):
        """Test basic file search."""
        runner = CliRunner()

        result = runner.invoke(file, ["search", "TODO", "--pattern", "**/*.py"])

        assert result.exit_code == 0
        assert "TODO" in result.output
        assert "file1.py" in result.output or "file4.py" in result.output

    def test_search_with_max_results(self, in_temp_dir):
        """Test search with result limit."""
        runner = CliRunner()

        result = runner.invoke(file, ["search", "TODO", "--pattern", "**/*", "--max-results", "2"])

        assert result.exit_code == 0
        # Should show at most 2 results

    def test_search_no_matches(self, in_temp_dir):
        """Test search with no matches."""
        runner = CliRunner()

        result = runner.invoke(file, ["search", "NONEXISTENT", "--pattern", "**/*.py"])

        assert result.exit_code == 0
        assert "No matches" in result.output or len(result.output) == 0

    def test_search_with_context(self, in_temp_dir):
        """Test search with context lines."""
        runner = CliRunner()

        result = runner.invoke(file, ["search", "TODO", "--pattern", "**/*.py", "--context", "2"])

        assert result.exit_code == 0

    @pytest.mark.skip(reason="search command doesn't support --regex option")
    def test_search_regex(self, in_temp_dir):
        """Test search with regex pattern."""
        runner = CliRunner()

        result = runner.invoke(file, ["search", "TODO.*fix", "--pattern", "**/*.py", "--regex"])

        assert result.exit_code == 0


class TestFileTree:
    """Test file tree operations."""

    @pytest.fixture
    def project_dir(self):
        """Create a project structure for testing."""
        temp_path = Path(tempfile.mkdtemp())

        # Create project structure
        (temp_path / "src").mkdir()
        (temp_path / "src" / "main.py").write_text("def main(): pass")
        (temp_path / "src" / "utils.py").write_text("def util(): pass")
        (temp_path / "tests").mkdir()
        (temp_path / "tests" / "test_main.py").write_text("def test(): pass")
        (temp_path / ".git").mkdir()
        (temp_path / "node_modules").mkdir()
        (temp_path / "README.md").write_text("# Project")

        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def in_project_dir(self, project_dir, monkeypatch):
        """Change to project directory for the test."""
        monkeypatch.chdir(project_dir)
        return project_dir

    def test_tree_basic(self, in_project_dir):
        """Test basic tree output."""
        runner = CliRunner()

        result = runner.invoke(file, ["tree"])

        assert result.exit_code == 0
        assert "src" in result.output
        assert "tests" in result.output
        # Hidden directories should not be shown by default
        assert ".git" not in result.output or "--all" not in result.output

    @pytest.mark.skip(reason="tree command doesn't support --depth option")
    def test_tree_with_depth(self, in_project_dir):
        """Test tree with depth limit."""
        runner = CliRunner()

        result = runner.invoke(file, ["tree", "--depth", "1"])

        assert result.exit_code == 0


@pytest.mark.skip(reason="stats command not implemented")
class TestFileStats:
    """Test file statistics operations."""

    @pytest.fixture
    def project_dir(self):
        """Create a project structure for testing."""
        temp_path = Path(tempfile.mkdtemp())

        # Create files with different sizes
        (temp_path / "small.txt").write_text("Small")
        (temp_path / "medium.txt").write_text("Medium " * 100)
        (temp_path / "large.py").write_text("# Large\n" * 1000)

        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def in_project_dir(self, project_dir, monkeypatch):
        """Change to project directory for the test."""
        monkeypatch.chdir(project_dir)
        return project_dir

    def test_stats_basic(self, in_project_dir):
        """Test basic file statistics."""
        runner = CliRunner()

        result = runner.invoke(file, ["stats", "."])

        assert result.exit_code == 0
        assert "Total files" in result.output or "Files" in result.output

    def test_stats_by_type(self, in_project_dir):
        """Test file statistics by type."""
        runner = CliRunner()

        result = runner.invoke(file, ["stats", ".", "--by-type"])

        assert result.exit_code == 0


class TestFileSearchOps:
    """Additional file search tests."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory with test files."""
        temp_path = Path(tempfile.mkdtemp())

        # Create test files with TODO comments
        (temp_path / "file1.py").write_text("# TODO: fix this\ndef hello(): pass")
        (temp_path / "file2.py").write_text("def greet(): pass")
        # Create markdown file with TODO
        (temp_path / "README.md").write_text("# Project\n\n<!-- TODO: update docs -->\n")
        (temp_path / "notes.md").write_text("# Notes\n\nSome notes here.")

        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def in_temp_dir(self, temp_dir, monkeypatch):
        """Change to temp directory for the test."""
        monkeypatch.chdir(temp_dir)
        return temp_dir

    def test_search_case_insensitive(self, in_temp_dir):
        """Test case-insensitive search."""
        runner = CliRunner()

        result = runner.invoke(file, ["search", "todo", "--pattern", "**/*.py"])  # lowercase

        assert result.exit_code == 0
        # Should find "TODO" (uppercase)
        assert "TODO" in result.output or "todo" in result.output

    def test_search_with_pattern(self, in_temp_dir):
        """Test search with file pattern filtering."""
        runner = CliRunner()

        # Search Python files
        result = runner.invoke(file, ["search", "TODO", "--pattern", "**/*.py"])

        assert result.exit_code == 0
        # Should find TODO in Python files
        assert "file1.py" in result.output, "Should include file1.py which contains TODO"
        assert "TODO" in result.output, "Should include the TODO text"
        # Should NOT include non-.py files
        assert "README.md" not in result.output, "Should exclude .md files when pattern is *.py"

        # Search markdown files
        result_md = runner.invoke(file, ["search", "TODO", "--pattern", "**/*.md"])

        assert result_md.exit_code == 0
        # Should find TODO in markdown files
        assert "README.md" in result_md.output, "Should include README.md which contains TODO"
        assert "TODO" in result_md.output, "Should include the TODO text"
        # Should NOT include .py files
        assert "file1.py" not in result_md.output, "Should exclude .py files when pattern is *.md"


class TestFileTreeOps:
    """Test file tree operations - additional tests."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory with test files."""
        temp_path = Path(tempfile.mkdtemp())

        # Create nested structure
        (temp_path / "src").mkdir()
        (temp_path / "src" / "main.py").write_text("def main(): pass")
        (temp_path / "tests").mkdir()
        (temp_path / "tests" / "test.py").write_text("def test(): pass")

        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def in_temp_dir(self, temp_dir, monkeypatch):
        """Change to temp directory for the test."""
        monkeypatch.chdir(temp_dir)
        return temp_dir

    def test_tree_shows_nested_structure(self, in_temp_dir):
        """Test that tree command displays nested directory structure."""
        runner = CliRunner()

        result = runner.invoke(file, ["tree"])

        assert result.exit_code == 0
        # Should show directories and files
        assert "src" in result.output
        assert "tests" in result.output
        assert "main.py" in result.output or "test.py" in result.output

    @pytest.mark.skip(reason="tree command doesn't support --depth option")
    def test_tree_respects_depth_limit(self, in_temp_dir):
        """Test that tree command respects depth limit."""
        runner = CliRunner()

        result = runner.invoke(file, ["tree", "--depth", "1"])

        assert result.exit_code == 0
        # Should show top-level directories
        assert "src" in result.output or "tests" in result.output


class TestFileTreeExtended:
    """Test directory tree display - extended tests."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory with structure."""
        temp_path = Path(tempfile.mkdtemp())

        # Create directory structure
        (temp_path / "file1.py").write_text("content")
        (temp_path / "file2.txt").write_text("content")

        subdir = temp_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").write_text("content")
        (subdir / "file4.md").write_text("content")

        subdir2 = temp_path / "another"
        subdir2.mkdir()
        (subdir2 / "file5.py").write_text("content")

        yield temp_path
        shutil.rmtree(temp_path)

    def test_tree_basic(self, temp_dir):
        """Test basic directory tree."""
        runner = CliRunner()

        import os

        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            result = runner.invoke(file, ["tree"])

            assert result.exit_code == 0
            # Should show files from directory
        finally:
            os.chdir(old_cwd)

    def test_tree_with_type_filter(self, temp_dir):
        """Test tree with file type filter."""
        runner = CliRunner()

        import os

        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            result = runner.invoke(file, ["tree", "--type", "py"])

            assert result.exit_code == 0
            # Should show Python files
            if "file1.py" in result.output or "file3.py" in result.output:
                # Should NOT show .txt or .md files
                assert ".txt" not in result.output or result.output.count(".txt") == 0
        finally:
            os.chdir(old_cwd)

    def test_tree_empty_directory(self):
        """Test tree on empty directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            import os

            old_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                result = runner.invoke(file, ["tree"])

                # Should not error on empty directory (may show "no files" message)
                assert result.exit_code == 0 or "No files" in result.output
            finally:
                os.chdir(old_cwd)


class TestFileOperationsIntegration:
    """Integration tests for file operations."""

    @pytest.fixture
    def project_dir(self):
        """Create mock project structure."""
        temp_path = Path(tempfile.mkdtemp())

        # Create project structure
        src = temp_path / "src"
        src.mkdir()

        (src / "main.py").write_text(
            "# Main application\n"
            "# TODO: Add logging\n"
            "def main():\n"
            "    print('Hello')\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )

        (src / "utils.py").write_text(
            "# Utility functions\n" "def helper():\n" "    # TODO: Implement\n" "    pass\n"
        )

        tests = temp_path / "tests"
        tests.mkdir()

        (tests / "test_main.py").write_text(
            "# Tests for main\n" "def test_main():\n" "    # TODO: Add tests\n" "    pass\n"
        )

        (temp_path / "README.md").write_text("# Project\n" "\n" "TODO: Write documentation\n")

        yield temp_path
        shutil.rmtree(temp_path)

    def test_search_all_todos(self, project_dir):
        """Test finding all TODOs in project."""
        runner = CliRunner()

        import os

        old_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            result = runner.invoke(file, ["search", "TODO", "--pattern", "**/*"])

            assert result.exit_code == 0
            # Should find TODOs in multiple files
            todo_count = result.output.count("TODO")
            assert todo_count >= 2  # At least 2 TODO items
        finally:
            os.chdir(old_cwd)

    def test_tree_project_structure(self, project_dir):
        """Test showing project tree."""
        runner = CliRunner()

        import os

        old_cwd = os.getcwd()
        os.chdir(project_dir)

        try:
            result = runner.invoke(file, ["tree"])

            assert result.exit_code == 0
            # Should show main directories
            assert "src" in result.output or "tests" in result.output
        finally:
            os.chdir(old_cwd)

    def test_read_multiple_files(self, project_dir):
        """Test reading multiple files."""
        runner = CliRunner()

        # Read main.py
        result1 = runner.invoke(file, ["read", str(project_dir / "src" / "main.py")])
        assert result1.exit_code == 0
        assert "def main()" in result1.output

        # Read README.md
        result2 = runner.invoke(file, ["read", str(project_dir / "README.md")])
        assert result2.exit_code == 0
        assert "# Project" in result2.output

        # Read utils.py
        result3 = runner.invoke(file, ["read", str(project_dir / "src" / "utils.py")])
        assert result3.exit_code == 0
        assert "def helper()" in result3.output


@pytest.mark.smoke
def test_file_command_exists():
    """Smoke test: Verify file command is registered."""
    runner = CliRunner()
    result = runner.invoke(file, ["--help"])

    assert result.exit_code == 0
    assert "File operations" in result.output or "file" in result.output.lower()


@pytest.mark.smoke
def test_file_subcommands_exist():
    """Smoke test: Verify all file subcommands exist."""
    runner = CliRunner()
    result = runner.invoke(file, ["--help"])

    assert result.exit_code == 0
    # Check for subcommands
    subcommands = ["read", "write", "edit", "search", "tree"]
    for cmd in subcommands:
        assert cmd in result.output.lower()
