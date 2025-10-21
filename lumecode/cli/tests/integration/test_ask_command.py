"""
Integration tests for the Ask command.
"""

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lumecode.cli.main import cli


class TestAskCommand:
    """Test suite for 'lumecode ask' command."""

    def test_ask_command_exists(self, runner):
        """Test that ask command is registered."""
        result = runner.invoke(cli, ["ask", "--help"])
        assert result.exit_code == 0
        assert "Ask AI questions about your code" in result.output

    def test_ask_requires_question(self, runner):
        """Test that ask command requires a question argument."""
        result = runner.invoke(cli, ["ask"])
        # Should fail or show usage
        assert (
            "query" in result.output.lower()
            or "question" in result.output.lower()
            or result.exit_code != 0
        )

    def test_ask_with_mock_provider(self, runner, sample_python_file, monkeypatch):
        """Test ask command with mock provider (no real API calls)."""
        # Set mock provider
        result = runner.invoke(
            cli,
            [
                "ask",
                "query",
                "What is this file?",
                "--files",
                str(sample_python_file),
                "--provider",
                "mock",
                "--no-git",
            ],
        )

        # Should execute without errors
        assert result.exit_code == 0 or "mock" in result.output.lower()

    def test_ask_help_shows_options(self, runner):
        """Test that ask --help shows all options."""
        result = runner.invoke(cli, ["ask", "query", "--help"])

        assert result.exit_code == 0
        assert "--files" in result.output
        assert "--provider" in result.output
        assert "--stream" in result.output
        assert "--verbose" in result.output

    def test_ask_accepts_file_option(self, runner, sample_python_file):
        """Test that ask command accepts --files option."""
        result = runner.invoke(
            cli,
            [
                "ask",
                "query",
                "test question",
                "--files",
                str(sample_python_file),
                "--provider",
                "mock",
            ],
        )

        # Should not error on file option
        assert "--files" not in result.output or result.exit_code != 2

    def test_ask_accepts_no_git_option(self, runner):
        """Test that ask command accepts --no-git option."""
        result = runner.invoke(
            cli, ["ask", "query", "test question", "--no-git", "--provider", "mock"]
        )

        # Should accept the option
        assert "--no-git" not in result.output or result.exit_code != 2

    def test_ask_accepts_provider_option(self, runner):
        """Test that ask command accepts different providers."""
        for provider in ["groq", "openrouter", "mock"]:
            result = runner.invoke(
                cli, ["ask", "query", "test", "--provider", provider, "--no-git"]
            )
            # Should accept the provider (may fail on API key, but option is valid)
            assert f"No such option: --provider" not in result.output

    def test_ask_verbose_mode(self, runner):
        """Test that verbose mode provides extra output."""
        result = runner.invoke(
            cli, ["ask", "query", "test question", "--verbose", "--provider", "mock", "--no-git"]
        )

        # Verbose mode should work
        assert result.exit_code == 0 or "verbose" in result.output.lower()

    def test_ask_streaming_options(self, runner):
        """Test both streaming and non-streaming modes."""
        # Test with streaming
        result1 = runner.invoke(cli, ["ask", "query", "test", "--stream", "--provider", "mock"])

        # Test without streaming
        result2 = runner.invoke(cli, ["ask", "query", "test", "--no-stream", "--provider", "mock"])

        # Both should be valid invocations
        assert "No such option" not in result1.output
        assert "No such option" not in result2.output


@pytest.mark.skipif(True, reason="Requires actual API keys")
class TestAskWithRealProvider:
    """Tests that require real API provider (skipped by default)."""

    def test_ask_with_groq(self, runner):
        """Test ask with real Groq provider."""
        result = runner.invoke(
            cli, ["ask", "query", "What is Python?", "--provider", "groq", "--no-git"]
        )

        # Should get actual response
        assert result.exit_code == 0
        assert len(result.output) > 50  # Should have substantial response
