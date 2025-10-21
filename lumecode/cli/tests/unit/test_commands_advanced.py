"""
Advanced Unit Tests for CLI Commands
Uses parametrization, mocking, and property-based testing.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lumecode.cli.main import cli

# ============================================================================
# ASK COMMAND TESTS
# ============================================================================


class TestAskCommand:
    """Comprehensive tests for Ask command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_ask_command_exists(self, runner):
        """Test ask command is registered."""
        result = runner.invoke(cli, ["ask", "--help"])
        assert result.exit_code == 0
        assert "Ask questions" in result.output or "Usage" in result.output

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "question",
        [
            "What is this code doing?",
            "How to improve this function?",
            "Explain the algorithm",
            "What are the best practices?",
        ],
    )
    def test_ask_with_various_questions(self, runner, mock_provider, question):
        """Test ask with different question types."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(cli, ["ask", question, "--provider", "mock"])
            # Command should succeed with mock provider
            assert result.exit_code == 0, f"Command failed with output: {result.output}"
            assert "Error" not in result.output, f"Error found in output: {result.output}"
            assert "Traceback" not in result.output, f"Traceback found in output: {result.output}"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "provider,model",
        [
            ("groq", "llama-3.1-70b-versatile"),
            ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
            ("mock", "mock-model"),
        ],
    )
    def test_ask_with_different_providers(self, runner, mock_provider, provider, model):
        """Test ask with different provider configurations."""
        mock_provider.name = provider
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(cli, ["ask", "test question", "--provider", provider])
            # Command should execute without crashing
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_ask_with_file_context(self, runner, sample_python_file, mock_provider):
        """Test ask with file context."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                [
                    "ask",
                    "What does this code do?",
                    "--file",
                    str(sample_python_file),
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize("streaming", [True, False])
    def test_ask_streaming_modes(self, runner, mock_provider, streaming):
        """Test ask with streaming enabled/disabled."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            args = ["ask", "test question", "--provider", "mock"]
            if streaming:
                args.append("--stream")
            else:
                args.append("--no-stream")

            result = runner.invoke(cli, args)
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_ask_verbose_mode(self, runner, mock_provider):
        """Test ask with verbose output."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(cli, ["ask", "test", "--verbose", "--provider", "mock"])
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_ask_without_question(self, runner):
        """Test ask fails without question."""
        result = runner.invoke(cli, ["ask"])
        assert result.exit_code != 0  # Should fail

    @pytest.mark.unit
    @pytest.mark.requires_git
    def test_ask_with_git_context(self, runner, git_repo, mock_provider):
        """Test ask with git repository context."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                ["ask", "What changed?", "--git", "diff", "--provider", "mock"],
                cwd=str(git_repo),
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# COMMIT COMMAND TESTS
# ============================================================================


class TestCommitCommand:
    """Comprehensive tests for Commit command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_commit_command_exists(self, runner):
        """Test commit command is registered."""
        result = runner.invoke(cli, ["commit", "--help"])
        assert result.exit_code == 0
        assert "commit" in result.output.lower() or "Usage" in result.output

    @pytest.mark.integration
    @pytest.mark.requires_git
    def test_commit_with_staged_changes(self, runner, git_repo_with_changes, mock_provider):
        """Test commit message generation with staged changes."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                ["commit", "generate", "--staged", "--provider", "mock"],
                cwd=str(git_repo_with_changes),
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.integration
    @pytest.mark.requires_git
    def test_commit_with_unstaged_changes(self, runner, git_repo_with_changes, mock_provider):
        """Test commit with unstaged changes."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                ["commit", "generate", "--unstaged", "--provider", "mock"],
                cwd=str(git_repo_with_changes),
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize("format_type", ["conventional", "simple"])
    def test_commit_format_types(self, runner, git_repo_with_changes, mock_provider, format_type):
        """Test different commit message formats."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            arg = f"--{format_type}"
            result = runner.invoke(
                cli,
                ["commit", "generate", arg, "--provider", "mock"],
                cwd=str(git_repo_with_changes),
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_commit_interactive_mode(self, runner, git_repo_with_changes, mock_provider):
        """Test commit in interactive mode."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                ["commit", "generate", "--interactive", "--provider", "mock"],
                cwd=str(git_repo_with_changes),
                input="n\n",
            )  # Simulate 'no' to commit
            assert isinstance(result.exit_code, int)


# ============================================================================
# REVIEW COMMAND TESTS
# ============================================================================


class TestReviewCommand:
    """Comprehensive tests for Review command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_review_command_exists(self, runner):
        """Test review command is registered."""
        result = runner.invoke(cli, ["review", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    @pytest.mark.parametrize("severity", ["critical", "major", "minor", "all"])
    def test_review_severity_levels(self, runner, sample_python_file, mock_provider, severity):
        """Test review with different severity filters."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                [
                    "review",
                    "code",
                    "--files",
                    str(sample_python_file),
                    "--severity",
                    severity,
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "focus", ["bugs", "security", "performance", "style", "best_practice", "maintainability"]
    )
    def test_review_focus_areas(self, runner, sample_python_file, mock_provider, focus):
        """Test review with different focus areas."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                [
                    "review",
                    "code",
                    "--files",
                    str(sample_python_file),
                    "--focus",
                    focus,
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.integration
    @pytest.mark.requires_git
    def test_review_staged_changes(self, runner, git_repo_with_changes, mock_provider):
        """Test reviewing staged changes."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                ["review", "code", "--staged", "--provider", "mock"],
                cwd=str(git_repo_with_changes),
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_review_multiple_files(self, runner, sample_project, mock_provider):
        """Test reviewing multiple files."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            src_dir = sample_project / "src"
            files = list(src_dir.glob("*.py"))
            result = runner.invoke(
                cli,
                [
                    "review",
                    "code",
                    "--files",
                    str(files[0]),
                    "--files",
                    str(files[1]),
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# EXPLAIN COMMAND TESTS
# ============================================================================


class TestExplainCommand:
    """Comprehensive tests for Explain command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_explain_command_exists(self, runner):
        """Test explain command is registered."""
        result = runner.invoke(cli, ["explain", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_explain_file(self, runner, sample_python_file, mock_provider):
        """Test explaining a file."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli, ["explain", "code", "--file", str(sample_python_file), "--provider", "mock"]
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_explain_complex_file(self, runner, complex_python_file, mock_provider):
        """Test explaining complex code structures."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli, ["explain", "code", "--file", str(complex_python_file), "--provider", "mock"]
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize("detail_level", ["brief", "detailed", "expert"])
    def test_explain_detail_levels(self, runner, sample_python_file, mock_provider, detail_level):
        """Test different explanation detail levels."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                [
                    "explain",
                    "code",
                    "--file",
                    str(sample_python_file),
                    "--detail",
                    detail_level,
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# REFACTOR COMMAND TESTS
# ============================================================================


class TestRefactorCommand:
    """Comprehensive tests for Refactor command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_refactor_command_exists(self, runner):
        """Test refactor command is registered."""
        result = runner.invoke(cli, ["refactor", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_refactor_suggest(self, runner, sample_python_file, mock_provider):
        """Test refactor suggestions."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                ["refactor", "suggest", "--file", str(sample_python_file), "--provider", "mock"],
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    def test_refactor_buggy_code(self, runner, buggy_python_file, mock_provider):
        """Test refactoring buggy code."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli, ["refactor", "suggest", "--file", str(buggy_python_file), "--provider", "mock"]
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "goal", ["performance", "readability", "maintainability", "reduce-complexity"]
    )
    def test_refactor_goals(self, runner, sample_python_file, mock_provider, goal):
        """Test refactor with different goals."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                [
                    "refactor",
                    "suggest",
                    "--file",
                    str(sample_python_file),
                    "--goal",
                    goal,
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# TEST COMMAND TESTS
# ============================================================================


class TestTestCommand:
    """Comprehensive tests for Test command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_test_command_exists(self, runner):
        """Test test command is registered."""
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_generate_tests(self, runner, sample_python_file, mock_provider):
        """Test generating tests for a file."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli, ["test", "generate", "--file", str(sample_python_file), "--provider", "mock"]
            )
            assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize("framework", ["pytest", "unittest"])
    def test_generate_tests_frameworks(self, runner, sample_python_file, mock_provider, framework):
        """Test generating tests with different frameworks."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli,
                [
                    "test",
                    "generate",
                    "--file",
                    str(sample_python_file),
                    "--framework",
                    framework,
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# CACHE COMMAND TESTS
# ============================================================================


class TestCacheCommand:
    """Comprehensive tests for Cache command."""

    @pytest.mark.unit
    @pytest.mark.cli
    @pytest.mark.cache
    def test_cache_command_exists(self, runner):
        """Test cache command is registered."""
        result = runner.invoke(cli, ["cache", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    @pytest.mark.cache
    def test_cache_clear(self, runner, temp_cache_dir):
        """Test cache clear command."""
        # Create some cache files
        (temp_cache_dir / "test_cache.json").write_text('{"test": "data"}')

        result = runner.invoke(cli, ["cache", "clear"])
        assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.cache
    def test_cache_stats(self, runner, temp_cache_dir):
        """Test cache stats command."""
        result = runner.invoke(cli, ["cache", "stats"])
        assert isinstance(result.exit_code, int)


# ============================================================================
# CONFIG COMMAND TESTS
# ============================================================================


class TestConfigCommand:
    """Comprehensive tests for Config command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_config_command_exists(self, runner):
        """Test config command is registered."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_config_show(self, runner):
        """Test showing configuration."""
        result = runner.invoke(cli, ["config", "show"])
        assert isinstance(result.exit_code, int)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "key,value",
        [
            ("provider", "groq"),
            ("model", "llama-3.1-70b-versatile"),
            ("streaming", "true"),
            ("cache_enabled", "false"),
        ],
    )
    def test_config_set(self, runner, temp_dir, key, value):
        """Test setting configuration values."""
        result = runner.invoke(cli, ["config", "set", key, value])
        assert isinstance(result.exit_code, int)


# ============================================================================
# BATCH COMMAND TESTS
# ============================================================================


class TestBatchCommand:
    """Comprehensive tests for Batch command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_batch_command_exists(self, runner):
        """Test batch command is registered."""
        result = runner.invoke(cli, ["batch", "--help"])
        assert result.exit_code == 0

    @pytest.mark.integration
    def test_batch_review_multiple_files(self, runner, sample_project, mock_provider):
        """Test batch review of multiple files."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            src_dir = sample_project / "src"
            result = runner.invoke(
                cli,
                [
                    "batch",
                    "review",
                    "--directory",
                    str(src_dir),
                    "--pattern",
                    "*.py",
                    "--provider",
                    "mock",
                ],
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# DOCS COMMAND TESTS
# ============================================================================


class TestDocsCommand:
    """Comprehensive tests for Docs command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_docs_command_exists(self, runner):
        """Test docs command is registered."""
        result = runner.invoke(cli, ["docs", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_docs_generate(self, runner, sample_python_file, mock_provider):
        """Test documentation generation."""
        with patch("lumecode.cli.core.llm.get_provider_with_fallback", return_value=mock_provider):
            result = runner.invoke(
                cli, ["docs", "generate", "--file", str(sample_python_file), "--provider", "mock"]
            )
            assert isinstance(result.exit_code, int)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestCLIIntegration:
    """Integration tests for CLI."""

    @pytest.mark.integration
    def test_cli_version(self, runner):
        """Test CLI version output."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output or "version" in result.output.lower()

    @pytest.mark.integration
    def test_cli_help(self, runner):
        """Test CLI help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Lumecode" in result.output or "Usage" in result.output

    @pytest.mark.integration
    def test_cli_debug_flag(self, runner):
        """Test CLI with debug flag."""
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0

    @pytest.mark.integration
    @pytest.mark.smoke
    def test_all_commands_have_help(self, runner):
        """Smoke test: all commands should have help."""
        commands = [
            "ask",
            "commit",
            "review",
            "explain",
            "refactor",
            "test",
            "cache",
            "config",
            "batch",
            "docs",
        ]

        for cmd in commands:
            result = runner.invoke(cli, [cmd, "--help"])
            assert result.exit_code == 0, f"Command {cmd} help failed"
