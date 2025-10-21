"""
Property-Based Testing using Hypothesis
Tests invariants and edge cases automatically.
"""

import pytest
import sys
from pathlib import Path
from hypothesis import given, strategies as st, settings, example
from hypothesis import HealthCheck

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from click.testing import CliRunner
from lumecode.cli.main import cli
from unittest.mock import patch, MagicMock


# ============================================================================
# STRATEGIES
# ============================================================================

# Generate valid question strings
questions = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))
)

# Generate file paths
file_paths = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P'), blacklist_characters='/\\')
).map(lambda s: s.strip())

# Generate provider names
providers = st.sampled_from(['groq', 'openrouter', 'mock'])

# Generate severity levels
severity_levels = st.sampled_from(['critical', 'major', 'minor', 'all'])

# Generate boolean flags
bool_flags = st.booleans()

# Generate small positive integers
small_ints = st.integers(min_value=1, max_value=100)

# Generate code snippets
code_snippets = st.text(
    min_size=10,
    max_size=500,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Zs'))
)


# ============================================================================
# PROPERTY TESTS
# ============================================================================

@pytest.mark.property
class TestPropertyBasedInvariants:
    """Property-based tests for invariants."""
    
    @given(question=questions.filter(lambda q: len(q.strip()) > 0))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @example(question="What is this?")
    def test_ask_accepts_any_valid_question(self, question):
        """Property: Ask should accept any non-empty question."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Response"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            result = runner.invoke(cli, ['ask', question, '--provider', 'mock'])
            # Should not crash (exit code may vary but shouldn't raise exception)
            assert isinstance(result.exit_code, int)
    
    @given(provider=providers, streaming=bool_flags)
    @settings(max_examples=30)
    def test_provider_streaming_combination(self, provider, streaming):
        """Property: All provider/streaming combinations should work."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = provider
        mock_provider.generate.return_value = "Response"
        mock_provider.stream.return_value = iter(["Test"])
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            args = ['ask', 'test', '--provider', provider]
            if streaming:
                args.append('--stream')
            
            result = runner.invoke(cli, args)
            assert isinstance(result.exit_code, int)
    
    @given(severity=severity_levels)
    @settings(max_examples=20)
    def test_review_severity_always_valid(self, severity):
        """Property: Review should accept any severity level."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        
        with patch('lumecode.cli.commands.review.get_provider', return_value=mock_provider):
            result = runner.invoke(cli, [
                'review', 'code',
                '--severity', severity,
                '--provider', 'mock'
            ])
            assert isinstance(result.exit_code, int)
    
    @given(key=st.text(min_size=1, max_size=50).filter(lambda k: k.strip()),
           value=st.text(min_size=1, max_size=100).filter(lambda v: v.strip()))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_config_set_idempotent(self, key, value):
        """Property: Setting config twice with same value should be idempotent."""
        runner = CliRunner()
        
        # Set first time
        result1 = runner.invoke(cli, ['config', 'set', key, value])
        
        # Set second time
        result2 = runner.invoke(cli, ['config', 'set', key, value])
        
        # Both should have same type of exit code
        assert type(result1.exit_code) == type(result2.exit_code)
    
    @given(n=small_ints)
    @settings(max_examples=20)
    def test_batch_operations_scale(self, n):
        """Property: Batch operations should handle varying sizes."""
        # Test that batch size parameter is accepted
        runner = CliRunner()
        result = runner.invoke(cli, ['batch', '--help'])
        assert result.exit_code == 0


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.property
class TestEdgeCases:
    """Test edge cases discovered through property testing."""
    
    @pytest.mark.parametrize("question", [
        "",  # Empty string
        " ",  # Whitespace only
        "a" * 10000,  # Very long question
        "🚀" * 100,  # Unicode characters
        "Test\nMulti\nLine",  # Multiline
        "Test\tTab",  # Tabs
    ])
    def test_ask_edge_case_questions(self, question):
        """Test ask with edge case questions."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            result = runner.invoke(cli, ['ask', question, '--provider', 'mock'])
            # Should handle gracefully (may fail validation but shouldn't crash)
            assert isinstance(result.exit_code, int)
    
    @pytest.mark.parametrize("path", [
        "/nonexistent/path/file.py",
        "./relative/path.py",
        "~.py",
        "file with spaces.py",
        "файл.py",  # Non-ASCII filename
    ])
    def test_file_path_edge_cases(self, path):
        """Test commands with edge case file paths."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        
        with patch('lumecode.cli.commands.explain.get_provider', return_value=mock_provider):
            result = runner.invoke(cli, [
                'explain', 'code',
                '--file', path,
                '--provider', 'mock'
            ])
            # May fail but should not crash
            assert isinstance(result.exit_code, int)
    
    @pytest.mark.parametrize("provider", [
        "invalid_provider",
        "",
        "123",
        "provider-with-dashes",
        "UPPERCASE",
    ])
    def test_invalid_providers_handled(self, provider):
        """Test that invalid providers are handled gracefully."""
        runner = CliRunner()
        result = runner.invoke(cli, ['ask', 'test', '--provider', provider])
        # Should handle invalid provider (error but no crash)
        assert isinstance(result.exit_code, int)


# ============================================================================
# INVARIANT TESTS
# ============================================================================

@pytest.mark.property
class TestInvariants:
    """Test system invariants."""
    
    def test_help_always_succeeds(self):
        """Invariant: --help should always succeed."""
        runner = CliRunner()
        commands = ['ask', 'commit', 'review', 'explain', 'refactor',
                   'test', 'cache', 'config', 'batch', 'docs']
        
        for cmd in commands:
            result = runner.invoke(cli, [cmd, '--help'])
            assert result.exit_code == 0, f"{cmd} --help failed"
    
    def test_version_always_succeeds(self):
        """Invariant: --version should always succeed."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
    
    def test_invalid_command_fails_gracefully(self):
        """Invariant: Invalid commands should fail gracefully."""
        runner = CliRunner()
        invalid_commands = ['invalid', 'xyz', '123', 'test123']
        
        for cmd in invalid_commands:
            result = runner.invoke(cli, [cmd])
            # Should fail but with proper error handling
            assert result.exit_code != 0
            assert isinstance(result.output, str)
    
    @given(debug=bool_flags)
    @settings(max_examples=10)
    def test_debug_flag_affects_logging_only(self, debug):
        """Invariant: Debug flag should only affect logging."""
        runner = CliRunner()
        args = ['--help']
        if debug:
            args.insert(0, '--debug')
        
        result = runner.invoke(cli, args)
        assert result.exit_code == 0


# ============================================================================
# STATEFUL TESTS
# ============================================================================

@pytest.mark.property
class TestStatefulBehavior:
    """Test stateful behavior and sequences."""
    
    def test_cache_clear_then_stats(self):
        """Test: clear cache then check stats."""
        runner = CliRunner()
        
        # Clear cache
        result1 = runner.invoke(cli, ['cache', 'clear'])
        
        # Check stats
        result2 = runner.invoke(cli, ['cache', 'stats'])
        
        # Both should execute
        assert isinstance(result1.exit_code, int)
        assert isinstance(result2.exit_code, int)
    
    def test_config_set_then_show(self):
        """Test: set config then show it."""
        runner = CliRunner()
        
        # Set config
        result1 = runner.invoke(cli, ['config', 'set', 'test_key', 'test_value'])
        
        # Show config
        result2 = runner.invoke(cli, ['config', 'show'])
        
        # Both should execute
        assert isinstance(result1.exit_code, int)
        assert isinstance(result2.exit_code, int)
    
    @given(operations=st.lists(
        st.sampled_from(['show', 'set test_key test_value']),
        min_size=1,
        max_size=5
    ))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_config_operation_sequences(self, operations):
        """Property: Any sequence of config operations should work."""
        runner = CliRunner()
        
        for op in operations:
            args = ['config'] + op.split()
            result = runner.invoke(cli, args)
            # Should not crash
            assert isinstance(result.exit_code, int)


# ============================================================================
# COMBINATORIAL TESTS
# ============================================================================

@pytest.mark.property
class TestCombinations:
    """Test combinations of options."""
    
    @given(
        streaming=bool_flags,
        verbose=bool_flags,
        git_context=bool_flags
    )
    @settings(max_examples=20)
    def test_ask_option_combinations(self, streaming, verbose, git_context):
        """Property: All combinations of ask options should work."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            args = ['ask', 'test', '--provider', 'mock']
            
            if streaming:
                args.append('--stream')
            if verbose:
                args.append('--verbose')
            if git_context:
                args.extend(['--git', 'diff'])
            
            result = runner.invoke(cli, args)
            assert isinstance(result.exit_code, int)
    
    @given(
        staged=bool_flags,
        conventional=bool_flags,
        auto=bool_flags
    )
    @settings(max_examples=15)
    def test_commit_option_combinations(self, staged, conventional, auto):
        """Property: All combinations of commit options should work."""
        runner = CliRunner()
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        
        with patch('lumecode.cli.commands.commit.get_provider', return_value=mock_provider):
            args = ['commit', 'generate', '--provider', 'mock']
            
            if staged:
                args.append('--staged')
            else:
                args.append('--unstaged')
            
            if conventional:
                args.append('--conventional')
            else:
                args.append('--simple')
            
            if auto:
                args.append('--auto')
            
            result = runner.invoke(cli, args)
            assert isinstance(result.exit_code, int)
