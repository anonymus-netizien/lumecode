"""Tests for prioritizer module."""

import pytest
from pathlib import Path
import tempfile
import time
from lumecode.cli.core.context.prioritizer import (
    prioritize_files,
    calculate_priority_score,
    filter_files_by_pattern,
    get_file_summary,
    _calculate_recency_score,
    _calculate_size_score,
    _calculate_type_score,
    _calculate_relevance_score,
)


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files."""
    # Create test files with different properties
    files = {}

    # Small recent Python file
    py_file = tmp_path / "test.py"
    py_file.write_text("def test(): pass")
    files["py_small"] = py_file

    # Larger Python file (>10KB to test size scoring)
    py_large = tmp_path / "large.py"
    py_large.write_text("# Code\n" * 2000)  # Larger file
    files["py_large"] = py_large

    # Markdown file
    md_file = tmp_path / "README.md"
    md_file.write_text("# README\n\nDocumentation")
    files["md"] = md_file

    # Config file
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text('{"key": "value"}')
    files["json"] = cfg_file

    # Old file (modify timestamp)
    old_file = tmp_path / "old.py"
    old_file.write_text("# Old code")
    # Make it look old (7 days ago)
    old_time = time.time() - (7 * 24 * 3600)
    import os

    os.utime(old_file, (old_time, old_time))
    files["old"] = old_file

    return files


class TestPrioritizeFiles:
    """Test file prioritization."""

    def test_prioritize_empty_list(self):
        """Test prioritizing empty file list."""
        result = prioritize_files([])
        assert result == []

    def test_prioritize_single_file(self, temp_files):
        """Test prioritizing single file."""
        files = [temp_files["py_small"]]
        result = prioritize_files(files)
        assert result == files

    def test_prioritize_by_type(self, temp_files):
        """Test that Python files are prioritized over others."""
        files = [
            temp_files["json"],
            temp_files["py_small"],
            temp_files["md"],
        ]
        result = prioritize_files(files)

        # Python file should be first
        assert result[0] == temp_files["py_small"]

    def test_prioritize_by_size(self, temp_files):
        """Test that smaller files get better size scores."""
        # Compare a small file with a large one
        small_score = _calculate_size_score(temp_files["py_small"])
        large_score = _calculate_size_score(temp_files["py_large"])

        # Small file (<10KB) should have perfect score of 1.0
        assert small_score == 1.0, f"Small file should have score 1.0, got {small_score}"

        # Large file should have lower score (score = 10KB / actual_size)
        # For ~14KB file: score = 10240/14000 ≈ 0.73
        assert (
            large_score < small_score
        ), f"Large file score ({large_score}) should be less than small file ({small_score})"
        assert (
            0.5 < large_score < 1.0
        ), f"Large file score should be between 0.5 and 1.0, got {large_score}"

    def test_prioritize_by_recency(self, temp_files):
        """Test that recent files are prioritized."""
        files = [
            temp_files["old"],
            temp_files["py_small"],
        ]
        result = prioritize_files(files)

        # Recent file should be first
        assert result[0] == temp_files["py_small"]

    def test_prioritize_filters_nonexistent(self, tmp_path):
        """Test that nonexistent files are filtered out."""
        files = [
            tmp_path / "exists.py",
            tmp_path / "nonexistent.py",
        ]
        files[0].write_text("code")

        result = prioritize_files(files)
        assert len(result) == 1
        assert result[0] == files[0]

    def test_prioritize_with_query(self, temp_files):
        """Test prioritization with query string."""
        files = list(temp_files.values())
        result = prioritize_files(files, query="README")

        # README.md should be first due to query match
        assert temp_files["md"] in result[:2]


class TestCalculatePriorityScore:
    """Test priority score calculation."""

    def test_calculate_score_returns_float(self, temp_files):
        """Test that score is a float between 0 and 1."""
        score = calculate_priority_score(temp_files["py_small"])
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_py_file_scores_higher(self, temp_files):
        """Test that .py files score higher than others."""
        py_score = calculate_priority_score(temp_files["py_small"])
        json_score = calculate_priority_score(temp_files["json"])

        assert py_score > json_score

    def test_nonexistent_file_scores_zero(self, tmp_path):
        """Test that nonexistent files score 0."""
        fake_file = tmp_path / "nonexistent.py"
        score = calculate_priority_score(fake_file)
        assert score == 0.0


class TestCalculateRecencyScore:
    """Test recency score calculation."""

    def test_recent_file_scores_high(self, temp_files):
        """Test that recently modified files score high."""
        score = _calculate_recency_score(temp_files["py_small"])
        assert score > 0.8  # Should be close to 1.0

    def test_old_file_scores_lower(self, temp_files):
        """Test that old files score lower."""
        score = _calculate_recency_score(temp_files["old"])
        assert score < 0.5  # Should decay


class TestCalculateSizeScore:
    """Test size score calculation."""

    def test_small_file_scores_high(self, temp_files):
        """Test that small files score high."""
        score = _calculate_size_score(temp_files["py_small"])
        assert score > 0.8

    def test_large_file_scores_lower(self, temp_files):
        """Test that large files score lower than small ones."""
        small_score = _calculate_size_score(temp_files["py_small"])
        large_score = _calculate_size_score(temp_files["py_large"])

        # Large file should have lower score than small file
        assert large_score < small_score


class TestCalculateTypeScore:
    """Test file type scoring."""

    def test_py_file_scores_highest(self, temp_files):
        """Test that .py files get highest type score."""
        score = _calculate_type_score(temp_files["py_small"])
        assert score == 1.0

    def test_md_file_scores_medium(self, temp_files):
        """Test that .md files get medium score."""
        score = _calculate_type_score(temp_files["md"])
        assert 0.7 <= score <= 0.9

    def test_json_file_scores_medium_low(self, temp_files):
        """Test that config files get medium-low score."""
        score = _calculate_type_score(temp_files["json"])
        assert 0.5 <= score <= 0.7

    def test_unknown_extension(self, tmp_path):
        """Test unknown file extension gets default score."""
        file = tmp_path / "file.xyz"
        file.write_text("data")
        score = _calculate_type_score(file)
        assert score == 0.4  # Default


class TestCalculateRelevanceScore:
    """Test relevance score calculation."""

    def test_no_query_returns_neutral(self, temp_files):
        """Test that no query returns neutral score."""
        score = _calculate_relevance_score(temp_files["py_small"], None)
        assert score == 0.5

    def test_exact_filename_match_scores_high(self, temp_files):
        """Test that exact filename match scores high."""
        score = _calculate_relevance_score(temp_files["md"], "README")
        assert score == 1.0

    def test_path_match_scores_medium(self, temp_files):
        """Test that path match scores medium-high."""
        score = _calculate_relevance_score(temp_files["py_small"], "test")
        assert score >= 0.8

    def test_no_match_scores_low(self, temp_files):
        """Test that no match scores low."""
        score = _calculate_relevance_score(temp_files["py_small"], "completely_different")
        assert score < 0.5


class TestFilterFilesByPattern:
    """Test file pattern filtering."""

    def test_filter_include_patterns(self, temp_files):
        """Test filtering with include patterns."""
        files = list(temp_files.values())
        result = filter_files_by_pattern(files, include_patterns=["*.py"])

        # Should only include .py files
        for f in result:
            assert f.suffix == ".py"

    def test_filter_exclude_patterns(self, temp_files):
        """Test filtering with exclude patterns."""
        files = list(temp_files.values())
        result = filter_files_by_pattern(files, exclude_patterns=["*.json"])

        # Should not include .json files
        for f in result:
            assert f.suffix != ".json"

    def test_filter_both_patterns(self, temp_files):
        """Test filtering with both include and exclude."""
        files = list(temp_files.values())
        result = filter_files_by_pattern(
            files, include_patterns=["*.py", "*.md"], exclude_patterns=["*old*"]
        )

        # Should include .py and .md, but not files with 'old'
        for f in result:
            assert f.suffix in [".py", ".md"]
            assert "old" not in f.name


class TestGetFileSummary:
    """Test file summary generation."""

    def test_get_summary_existing_file(self, temp_files):
        """Test getting summary for existing file."""
        summary = get_file_summary(temp_files["py_small"])

        assert "name" in summary
        assert "path" in summary
        assert "size" in summary
        assert "modified" in summary
        assert "type" in summary
        assert "exists" in summary
        assert "priority_score" in summary

        assert summary["exists"] is True
        assert summary["name"] == "test.py"
        assert summary["type"] == ".py"
        assert summary["size"] > 0

    def test_get_summary_nonexistent_file(self, tmp_path):
        """Test getting summary for nonexistent file."""
        fake_file = tmp_path / "nonexistent.py"
        summary = get_file_summary(fake_file)

        assert "name" in summary
        assert "exists" in summary
        assert summary["exists"] is False


class TestPrioritizerIntegration:
    """Integration tests for prioritizer."""

    def test_full_prioritization_workflow(self, temp_files):
        """Test complete prioritization workflow."""
        # Get all files
        files = list(temp_files.values())

        # Prioritize
        result = prioritize_files(files)

        # Should have all files
        assert len(result) == len(files)

        # Should be sorted by priority
        scores = [calculate_priority_score(f) for f in result]
        assert scores == sorted(scores, reverse=True)

    def test_prioritization_with_large_file_filter(self, tmp_path):
        """Test that very large files are filtered out."""
        # Create files
        small = tmp_path / "small.py"
        small.write_text("code")

        large = tmp_path / "large.py"
        large.write_text("x" * (11 * 1024 * 1024))  # 11MB

        files = [small, large]
        result = prioritize_files(files, max_file_size=10 * 1024 * 1024)

        # Large file should be filtered out
        assert len(result) == 1
        assert result[0] == small

    def test_summary_for_multiple_files(self, temp_files):
        """Test getting summaries for multiple files."""
        files = [temp_files["py_small"], temp_files["md"]]
        summaries = [get_file_summary(f) for f in files]

        assert len(summaries) == 2
        for summary in summaries:
            assert summary["exists"] is True
            assert "priority_score" in summary
