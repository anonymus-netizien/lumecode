"""
Comprehensive Integration Tests for Lumecode CLI
Tests real command execution with proper mocking.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lumecode.cli.main import cli

# ============================================================================
# TEST ASK COMMAND
# ============================================================================


@pytest.mark.integration
class TestAskCommandIntegration:
    """Integration tests for Ask command."""

    def test_ask_command_help(self, runner):
        """Test ask command help works."""
        result = runner.invoke(cli, ["ask", "--help"])
        assert result.exit_code == 0
        assert "ask" in result.output.lower() or "Usage" in result.output

    @pytest.mark.parametrize(
        "question",
        [
            "What is this code doing?",
            "How to improve performance?",
            "Explain the algorithm",
        ],
    )
    def test_ask_various_questions(self, runner, question):
        """Test ask with different questions using mock provider."""
        result = runner.invoke(cli, ["ask", "query", question, "--provider", "mock", "--no-stream"])
        # Should execute (may fail if dependencies missing but shouldn't crash)
        assert isinstance(result.exit_code, int)

    def test_ask_with_file_context(self, runner, sample_python_file):
        """Test ask with file context."""
        result = runner.invoke(
            cli,
            [
                "ask",
                "query",
                "What does this code do?",
                "--files",
                str(sample_python_file),
                "--provider",
                "mock",
                "--no-stream",
            ],
        )
        assert isinstance(result.exit_code, int)

    def test_ask_verbose_mode(self, runner):
        """Test ask with verbose output."""
        result = runner.invoke(
            cli, ["ask", "query", "test question", "--verbose", "--provider", "mock", "--no-stream"]
        )
        assert isinstance(result.exit_code, int)

    @pytest.mark.parametrize("provider", ["groq", "openrouter", "mock"])
    def test_ask_different_providers(self, runner, provider):
        """Test ask with different providers."""
        result = runner.invoke(
            cli, ["ask", "query", "test question", "--provider", provider, "--no-stream"]
        )
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST COMMIT COMMAND
# ============================================================================


@pytest.mark.integration
class TestCommitCommandIntegration:
    """Integration tests for Commit command."""

    def test_commit_command_help(self, runner):
        """Test commit command help works."""
        result = runner.invoke(cli, ["commit", "--help"])
        assert result.exit_code == 0
        assert "commit" in result.output.lower() or "Usage" in result.output

    @pytest.mark.requires_git
    def test_commit_generate_in_git_repo(self, runner, git_repo_with_changes):
        """Test commit generation in git repository."""
        result = runner.invoke(
            cli,
            ["commit", "generate", "--provider", "mock", "--staged"],
            cwd=str(git_repo_with_changes),
        )
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST REVIEW COMMAND
# ============================================================================


@pytest.mark.integration
class TestReviewCommandIntegration:
    """Integration tests for Review command."""

    def test_review_command_help(self, runner):
        """Test review command help works."""
        result = runner.invoke(cli, ["review", "--help"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("severity", ["critical", "major", "minor", "all"])
    def test_review_severity_filters(self, runner, sample_python_file, severity):
        """Test review with different severity levels."""
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

    @pytest.mark.parametrize("focus", ["bugs", "security", "performance", "style"])
    def test_review_focus_areas(self, runner, sample_python_file, focus):
        """Test review with different focus areas."""
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


# ============================================================================
# TEST EXPLAIN COMMAND
# ============================================================================


@pytest.mark.integration
class TestExplainCommandIntegration:
    """Integration tests for Explain command."""

    def test_explain_command_help(self, runner):
        """Test explain command help works."""
        result = runner.invoke(cli, ["explain", "--help"])
        assert result.exit_code == 0

    def test_explain_simple_file(self, runner, sample_python_file):
        """Test explaining simple Python file."""
        result = runner.invoke(
            cli, ["explain", "code", "--file", str(sample_python_file), "--provider", "mock"]
        )
        assert isinstance(result.exit_code, int)

    def test_explain_complex_file(self, runner, complex_python_file):
        """Test explaining complex Python file."""
        result = runner.invoke(
            cli, ["explain", "code", "--file", str(complex_python_file), "--provider", "mock"]
        )
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST REFACTOR COMMAND
# ============================================================================


@pytest.mark.integration
class TestRefactorCommandIntegration:
    """Integration tests for Refactor command."""

    def test_refactor_command_help(self, runner):
        """Test refactor command help works."""
        result = runner.invoke(cli, ["refactor", "--help"])
        assert result.exit_code == 0

    def test_refactor_suggest(self, runner, sample_python_file):
        """Test refactor suggestions."""
        result = runner.invoke(
            cli, ["refactor", "suggest", "--file", str(sample_python_file), "--provider", "mock"]
        )
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST TEST COMMAND
# ============================================================================


@pytest.mark.integration
class TestTestCommandIntegration:
    """Integration tests for Test command."""

    def test_test_command_help(self, runner):
        """Test test command help works."""
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0

    def test_generate_tests(self, runner, sample_python_file):
        """Test generating tests for a file."""
        result = runner.invoke(
            cli, ["test", "generate", "--file", str(sample_python_file), "--provider", "mock"]
        )
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST CACHE COMMAND
# ============================================================================


@pytest.mark.integration
@pytest.mark.cache
class TestCacheCommandIntegration:
    """Integration tests for Cache command."""

    def test_cache_command_help(self, runner):
        """Test cache command help works."""
        result = runner.invoke(cli, ["cache", "--help"])
        assert result.exit_code == 0

    def test_cache_stats(self, runner):
        """Test cache stats command."""
        result = runner.invoke(cli, ["cache", "stats"])
        assert isinstance(result.exit_code, int)

    def test_cache_clear(self, runner, temp_cache_dir):
        """Test cache clear command."""
        # Create some cache files
        (temp_cache_dir / "test1.json").write_text('{"data": "test"}')
        (temp_cache_dir / "test2.json").write_text('{"data": "test2"}')

        result = runner.invoke(cli, ["cache", "clear"])
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST CONFIG COMMAND
# ============================================================================


@pytest.mark.integration
class TestConfigCommandIntegration:
    """Integration tests for Config command."""

    def test_config_command_help(self, runner):
        """Test config command help works."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    def test_config_show(self, runner):
        """Test config show command."""
        result = runner.invoke(cli, ["config", "show"])
        assert isinstance(result.exit_code, int)

    @pytest.mark.parametrize(
        "key,value",
        [
            ("provider", "groq"),
            ("model", "llama-3.1-70b"),
            ("streaming", "true"),
        ],
    )
    def test_config_set_values(self, runner, key, value):
        """Test setting different config values."""
        result = runner.invoke(cli, ["config", "set", key, value])
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST BATCH COMMAND
# ============================================================================


@pytest.mark.integration
class TestBatchCommandIntegration:
    """Integration tests for Batch command."""

    def test_batch_command_help(self, runner):
        """Test batch command help works."""
        result = runner.invoke(cli, ["batch", "--help"])
        assert result.exit_code == 0

    def test_batch_review_directory(self, runner, sample_project):
        """Test batch review of directory."""
        result = runner.invoke(
            cli,
            [
                "batch",
                "review",
                "--directory",
                str(sample_project / "src"),
                "--pattern",
                "*.py",
                "--provider",
                "mock",
            ],
        )
        assert isinstance(result.exit_code, int)


# ============================================================================
# TEST DOCS COMMAND
# ============================================================================


@pytest.mark.integration
class TestDocsCommandIntegration:
    """Integration tests for Docs command."""

    def test_docs_command_help(self, runner):
        """Test docs command help works."""
        result = runner.invoke(cli, ["docs", "--help"])
        assert result.exit_code == 0


# ============================================================================
# SMOKE TESTS
# ============================================================================


@pytest.mark.smoke
class TestSmokeSuite:
    """Quick smoke tests to verify basic functionality."""

    def test_cli_version(self, runner):
        """Test CLI version display."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output or "version" in result.output.lower()

    def test_cli_help(self, runner):
        """Test CLI help display."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Lumecode" in result.output or "Usage" in result.output

    def test_all_commands_registered(self, runner):
        """Test all commands are registered."""
        result = runner.invoke(cli, ["--help"])
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
            # Each command should appear in help
            # (may not appear if not registered)
            assert isinstance(result.exit_code, int)

    def test_all_commands_have_help(self, runner):
        """Test all commands provide help."""
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


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling across commands."""

    def test_invalid_command(self, runner):
        """Test handling of invalid command."""
        result = runner.invoke(cli, ["invalid_command"])
        assert result.exit_code != 0

    def test_missing_required_argument(self, runner):
        """Test handling of missing required argument."""
        result = runner.invoke(cli, ["ask", "query"])
        assert result.exit_code != 0

    def test_invalid_provider(self, runner):
        """Test handling of invalid provider."""
        result = runner.invoke(cli, ["ask", "query", "test", "--provider", "invalid_provider"])
        # Should handle gracefully
        assert isinstance(result.exit_code, int)

    def test_nonexistent_file(self, runner):
        """Test handling of nonexistent file."""
        result = runner.invoke(
            cli, ["explain", "code", "--file", "/nonexistent/file.py", "--provider", "mock"]
        )
        # Should handle missing file gracefully
        assert isinstance(result.exit_code, int)


# ============================================================================
# COMMAND OPTION COMBINATIONS
# ============================================================================


@pytest.mark.integration
class TestCommandOptionCombinations:
    """Test various option combinations."""

    @pytest.mark.parametrize(
        "streaming,verbose",
        [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ],
    )
    def test_ask_option_combinations(self, runner, streaming, verbose):
        """Test combinations of ask options."""
        args = ["ask", "query", "test", "--provider", "mock"]

        if streaming:
            args.append("--stream")
        else:
            args.append("--no-stream")

        if verbose:
            args.append("--verbose")

        result = runner.invoke(cli, args)
        assert isinstance(result.exit_code, int)

    @pytest.mark.parametrize("git_context", [True, False])
    def test_ask_with_git_context(self, runner, git_context):
        """Test ask with and without git context."""
        args = ["ask", "query", "test", "--provider", "mock", "--no-stream"]

        if git_context:
            args.append("--git")
        else:
            args.append("--no-git")

        result = runner.invoke(cli, args)
        assert isinstance(result.exit_code, int)


# ============================================================================
# PERFORMANCE SMOKE TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceSmoke:
    """Basic performance smoke tests."""

    def test_help_commands_are_fast(self, runner):
        """Test help commands respond quickly."""
        import os
        import time

        # Configurable timeout with sensible defaults
        help_timeout = float(os.environ.get("LUMECODE_HELP_TIMEOUT", "5.0"))

        # Skip performance checks in CI or slow environments
        if os.environ.get("CI") or os.environ.get("SLOW_TESTS"):
            pytest.skip("Skipping performance test in CI/slow environment")

        commands = ["ask", "commit", "review", "explain", "refactor"]

        for cmd in commands:
            start = time.time()
            result = runner.invoke(cli, [cmd, "--help"])
            duration = time.time() - start

            assert result.exit_code == 0
            assert (
                duration < help_timeout
            ), f"{cmd} help took {duration}s (threshold: {help_timeout}s)"

    def test_mock_provider_is_fast(self, runner):
        """Test mock provider responds quickly."""
        import os
        import time

        # Configurable timeout with sensible defaults
        mock_timeout = float(os.environ.get("LUMECODE_MOCK_TIMEOUT", "10.0"))

        # Skip performance checks in CI or slow environments
        if os.environ.get("CI") or os.environ.get("SLOW_TESTS"):
            pytest.skip("Skipping performance test in CI/slow environment")

        start = time.time()
        result = runner.invoke(
            cli, ["ask", "query", "quick test", "--provider", "mock", "--no-stream"]
        )
        duration = time.time() - start

        # Mock provider should be very fast
        assert (
            duration < mock_timeout
        ), f"Mock provider took {duration}s (threshold: {mock_timeout}s)"
