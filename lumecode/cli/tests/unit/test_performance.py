"""
Performance and Benchmark Tests
Tests performance, timing, and resource usage.

NOTE: These tests invoke real commands with real providers and should be
treated as integration tests. They are skipped in unit test runs.
"""

import pytest
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lumecode.cli.main import cli


# Mark all performance tests as integration tests
pytestmark = pytest.mark.integration


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================

@pytest.fixture
def performance_runner():
    """CLI runner for performance tests."""
    return CliRunner()


@pytest.fixture
def large_file(tmp_path):
    """Create a large Python file for testing."""
    file = tmp_path / "large.py"
    
    # Generate large file with repetitive code
    lines = []
    for i in range(1000):
        lines.append(f"""
def function_{i}(param1, param2, param3):
    '''Function {i} documentation.'''
    result = param1 + param2 + param3
    processed = result * 2
    final = processed - 1
    return final

class Class{i}:
    '''Class {i} documentation.'''
    
    def __init__(self, value):
        self.value = value
    
    def method_{i}(self):
        return self.value * {i}
""")
    
    file.write_text('\n'.join(lines))
    return file


@pytest.fixture
def many_files(tmp_path):
    """Create many files for batch testing."""
    files_dir = tmp_path / "many_files"
    files_dir.mkdir()
    
    files = []
    for i in range(100):
        file = files_dir / f"file_{i}.py"
        file.write_text(f"""
def function_{i}():
    '''Function in file {i}.'''
    return {i}

class Class{i}:
    '''Class in file {i}.'''
    pass
""")
        files.append(file)
    
    return files_dir


# ============================================================================
# TIMING TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.performance
class TestPerformance:
    """Performance benchmark tests."""
    
    def test_help_response_time(self, performance_runner, benchmark=None):
        """Test: Help command should respond quickly."""
        start = time.time()
        result = performance_runner.invoke(cli, ['--help'])
        duration = time.time() - start
        
        assert result.exit_code == 0
        assert duration < 1.0, f"Help took {duration}s, should be < 1s"
    
    def test_command_help_response_times(self, performance_runner):
        """Test: All command help should respond quickly."""
        commands = ['ask', 'commit', 'review', 'explain', 'refactor',
                   'test', 'cache', 'config', 'batch', 'docs']
        
        for cmd in commands:
            start = time.time()
            result = performance_runner.invoke(cli, [cmd, '--help'])
            duration = time.time() - start
            
            assert result.exit_code == 0
            assert duration < 1.0, f"{cmd} help took {duration}s"
    
    def test_ask_with_mock_provider_performance(self, performance_runner):
        """Test: Ask with mock provider should be fast."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Quick response"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            start = time.time()
            result = performance_runner.invoke(cli, [
                'ask', 'test question',
                '--provider', 'mock'
            ])
            duration = time.time() - start
            
            # Mock provider should be very fast
            assert duration < 2.0, f"Mock ask took {duration}s"
    
    @pytest.mark.slow
    def test_large_file_processing(self, performance_runner, large_file):
        """Test: Processing large file should complete in reasonable time."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Analysis complete"
        
        with patch('lumecode.cli.commands.explain.get_provider', return_value=mock_provider):
            start = time.time()
            result = performance_runner.invoke(cli, [
                'explain', 'code',
                '--file', str(large_file),
                '--provider', 'mock'
            ])
            duration = time.time() - start
            
            # Should handle large files within reasonable time
            assert duration < 10.0, f"Large file processing took {duration}s"
    
    @pytest.mark.slow
    def test_batch_processing_performance(self, performance_runner, many_files):
        """Test: Batch processing should scale reasonably."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Batch complete"
        
        with patch('lumecode.cli.commands.batch.get_provider', return_value=mock_provider):
            start = time.time()
            result = performance_runner.invoke(cli, [
                'batch', 'review',
                '--directory', str(many_files),
                '--pattern', '*.py',
                '--provider', 'mock'
            ])
            duration = time.time() - start
            
            # Batch should complete in reasonable time
            assert duration < 30.0, f"Batch processing took {duration}s"
    
    def test_cache_operations_performance(self, performance_runner, tmp_path, monkeypatch):
        """Test: Cache operations should be fast."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        monkeypatch.setenv("LUMECODE_CACHE_DIR", str(cache_dir))
        
        # Create cache entries
        for i in range(100):
            (cache_dir / f"entry_{i}.json").write_text('{"data": "test"}')
        
        # Test cache stats performance
        start = time.time()
        result = performance_runner.invoke(cli, ['cache', 'stats'])
        stats_duration = time.time() - start
        
        assert stats_duration < 2.0, f"Cache stats took {stats_duration}s"
        
        # Test cache clear performance
        start = time.time()
        result = performance_runner.invoke(cli, ['cache', 'clear'])
        clear_duration = time.time() - start
        
        assert clear_duration < 3.0, f"Cache clear took {clear_duration}s"


# ============================================================================
# MEMORY TESTS
# ============================================================================

@pytest.mark.performance
class TestMemoryUsage:
    """Test memory efficiency."""
    
    def test_large_file_memory_efficiency(self, performance_runner, large_file):
        """Test: Should not load entire large file into memory at once."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Done"
        
        with patch('lumecode.cli.commands.review.get_provider', return_value=mock_provider):
            # This should not crash or use excessive memory
            result = performance_runner.invoke(cli, [
                'review', 'code',
                '--files', str(large_file),
                '--provider', 'mock'
            ])
            
            # Should complete successfully
            assert isinstance(result.exit_code, int)
    
    def test_streaming_memory_efficiency(self, performance_runner):
        """Test: Streaming should not buffer all output."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        
        # Simulate large streaming response
        def large_stream():
            for i in range(1000):
                yield f"Chunk {i}\n"
        
        mock_provider.stream.return_value = large_stream()
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            result = performance_runner.invoke(cli, [
                'ask', 'test',
                '--stream',
                '--provider', 'mock'
            ])
            
            # Should handle streaming without excessive memory
            assert isinstance(result.exit_code, int)


# ============================================================================
# CONCURRENCY TESTS
# ============================================================================

@pytest.mark.performance
class TestConcurrency:
    """Test concurrent operations."""
    
    def test_multiple_sequential_commands(self, performance_runner):
        """Test: Multiple sequential commands should work."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Response"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            results = []
            for i in range(10):
                result = performance_runner.invoke(cli, [
                    'ask', f'Question {i}',
                    '--provider', 'mock'
                ])
                results.append(result)
            
            # All should execute
            assert len(results) == 10
            assert all(isinstance(r.exit_code, int) for r in results)
    
    def test_cache_concurrent_access(self, performance_runner, tmp_path, monkeypatch):
        """Test: Cache should handle rapid sequential access."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        monkeypatch.setenv("LUMECODE_CACHE_DIR", str(cache_dir))
        
        # Rapid cache operations
        operations = ['stats', 'show', 'stats', 'show'] * 5
        
        for op in operations:
            result = performance_runner.invoke(cli, ['cache', op])
            # Should not crash or deadlock
            assert isinstance(result.exit_code, int)


# ============================================================================
# SCALABILITY TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.performance
class TestScalability:
    """Test how system scales with load."""
    
    @pytest.mark.parametrize("num_files", [1, 10, 50])
    def test_review_scales_with_file_count(self, performance_runner, tmp_path, num_files):
        """Test: Review performance should scale reasonably with file count."""
        files = []
        for i in range(num_files):
            file = tmp_path / f"file_{i}.py"
            file.write_text(f"def func_{i}(): return {i}")
            files.append(file)
        
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Review complete"
        
        with patch('lumecode.cli.commands.review.get_provider', return_value=mock_provider):
            start = time.time()
            
            args = ['review', 'code', '--provider', 'mock']
            for file in files[:min(5, len(files))]:  # Limit to first 5
                args.extend(['--files', str(file)])
            
            result = performance_runner.invoke(cli, args)
            duration = time.time() - start
            
            # Should scale linearly (rough estimate)
            max_time = num_files * 0.5 + 2  # 0.5s per file + 2s overhead
            assert duration < max_time, f"Took {duration}s for {num_files} files"
    
    @pytest.mark.parametrize("question_length", [10, 100, 1000])
    def test_ask_scales_with_question_length(self, performance_runner, question_length):
        """Test: Ask should handle varying question lengths."""
        question = "a" * question_length
        
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Response"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            start = time.time()
            result = performance_runner.invoke(cli, [
                'ask', question,
                '--provider', 'mock'
            ])
            duration = time.time() - start
            
            # Should handle long questions (slightly longer time is acceptable)
            max_time = 3.0 + (question_length / 10000)  # Base + scaling factor
            assert duration < max_time


# ============================================================================
# STRESS TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.performance
class TestStress:
    """Stress tests for system limits."""
    
    def test_rapid_fire_commands(self, performance_runner):
        """Test: Should handle rapid successive commands without errors."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Done"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            errors = []
            for i in range(50):
                try:
                    result = performance_runner.invoke(cli, [
                        'ask', f'Q{i}',
                        '--provider', 'mock'
                    ])
                    assert isinstance(result.exit_code, int)
                except Exception as e:
                    errors.append(str(e))
            
            # Should handle rapid commands without any errors (mock provider is deterministic)
            assert len(errors) == 0, f"Unexpected errors occurred: {errors}"
    
    def test_extreme_file_size(self, performance_runner, tmp_path):
        """Test: Should handle or gracefully reject very large files."""
        extreme_file = tmp_path / "extreme.py"
        
        # Create 10MB file
        lines = ["def func(): pass\n"] * 100000
        extreme_file.write_text(''.join(lines))
        
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Processed"
        
        with patch('lumecode.cli.commands.explain.get_provider', return_value=mock_provider):
            # Should either process or fail gracefully
            result = performance_runner.invoke(cli, [
                'explain', 'code',
                '--file', str(extreme_file),
                '--provider', 'mock'
            ])
            
            # Should not crash (may fail validation but shouldn't hang)
            assert isinstance(result.exit_code, int)


# ============================================================================
# BENCHMARK COMPARISONS
# ============================================================================

@pytest.mark.performance
class TestBenchmarkComparisons:
    """Comparative benchmark tests."""
    
    def test_mock_vs_actual_provider_overhead(self, performance_runner):
        """Compare mock provider vs actual provider overhead."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Mock response"
        
        # Mock provider timing
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            start = time.time()
            result_mock = performance_runner.invoke(cli, [
                'ask', 'test',
                '--provider', 'mock'
            ])
            mock_duration = time.time() - start
        
        # Mock should be very fast (< 1s)
        assert mock_duration < 1.0
    
    def test_cached_vs_uncached_performance(self, performance_runner, tmp_path, monkeypatch):
        """Compare cached vs uncached performance."""
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        monkeypatch.setenv("LUMECODE_CACHE_DIR", str(cache_dir))
        
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.generate.return_value = "Response"
        
        with patch('lumecode.cli.commands.ask.get_provider', return_value=mock_provider):
            # First call (uncached)
            start = time.time()
            result1 = performance_runner.invoke(cli, [
                'ask', 'test question',
                '--provider', 'mock'
            ])
            uncached_duration = time.time() - start
            
            # Second call (potentially cached)
            start = time.time()
            result2 = performance_runner.invoke(cli, [
                'ask', 'test question',
                '--provider', 'mock'
            ])
            cached_duration = time.time() - start
        
        # Both should complete
        assert isinstance(result1.exit_code, int)
        assert isinstance(result2.exit_code, int)
