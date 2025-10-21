import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from backend.analysis.aggregator import ResultAggregator, ResultType, ResultPriority


class TestResultAggregator(unittest.TestCase):
    """Test cases for the ResultAggregator class."""

    def setUp(self):
        """Set up test environment before each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.temp_dir.name)
        self.aggregator = ResultAggregator(self.workspace_path)

    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()

    def test_initialization(self):
        """Test that the aggregator initializes correctly."""
        self.assertEqual(self.aggregator.workspace_path, self.workspace_path)
        self.assertEqual(self.aggregator.results, {})
        self.assertEqual(self.aggregator.result_index, {})
        self.assertEqual(self.aggregator.result_count, 0)
        self.assertIsNotNone(self.aggregator.last_updated)

    def test_add_result(self):
        """Test adding a result."""
        # Add a result with enum types
        result_id1 = self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Test issue", "line": 10},
            file_path="test.py",
            priority=ResultPriority.HIGH,
            tags=["test", "quality"],
        )

        # Add a result with string types
        result_id2 = self.aggregator.add_result(
            result_type="security",
            source="test_plugin",
            data={"message": "Security issue", "severity": "high"},
            file_path=Path("test2.py"),
            priority="medium",
            tags=["security"],
        )

        # Verify results were added
        self.assertEqual(len(self.aggregator.results), 2)
        self.assertEqual(self.aggregator.result_count, 2)

        # Verify result content
        result1 = self.aggregator.get_result(result_id1)
        self.assertEqual(result1["type"], "code_quality")
        self.assertEqual(result1["source"], "test_agent")
        self.assertEqual(result1["data"]["message"], "Test issue")
        self.assertEqual(result1["file_path"], "test.py")
        self.assertEqual(result1["priority"], "high")
        self.assertEqual(result1["tags"], ["test", "quality"])

        # Verify indexing
        code_quality_results = self.aggregator.get_results_by_type(ResultType.CODE_QUALITY)
        self.assertEqual(len(code_quality_results), 1)
        self.assertEqual(code_quality_results[0]["id"], result_id1)

        security_results = self.aggregator.get_results_by_type("security")
        self.assertEqual(len(security_results), 1)
        self.assertEqual(security_results[0]["id"], result_id2)

    def test_get_results_by_file(self):
        """Test getting results by file path."""
        # Add results for different files
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Test issue 1"},
            file_path="file1.py",
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY,
            source="test_agent",
            data={"message": "Test issue 2"},
            file_path="file1.py",
        )

        self.aggregator.add_result(
            result_type=ResultType.PERFORMANCE,
            source="test_agent",
            data={"message": "Test issue 3"},
            file_path="file2.py",
        )

        # Get results for file1.py
        file1_results = self.aggregator.get_results_by_file("file1.py")
        self.assertEqual(len(file1_results), 2)

        # Get results for file2.py
        file2_results = self.aggregator.get_results_by_file(Path("file2.py"))
        self.assertEqual(len(file2_results), 1)
        self.assertEqual(file2_results[0]["data"]["message"], "Test issue 3")

        # Get results for non-existent file
        file3_results = self.aggregator.get_results_by_file("file3.py")
        self.assertEqual(len(file3_results), 0)

    def test_get_results_by_priority(self):
        """Test getting results by priority."""
        # Add results with different priorities
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Critical issue"},
            priority=ResultPriority.CRITICAL,
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY,
            source="test_agent",
            data={"message": "High issue"},
            priority=ResultPriority.HIGH,
        )

        self.aggregator.add_result(
            result_type=ResultType.PERFORMANCE,
            source="test_agent",
            data={"message": "Another high issue"},
            priority=ResultPriority.HIGH,
        )

        # Get critical results
        critical_results = self.aggregator.get_results_by_priority(ResultPriority.CRITICAL)
        self.assertEqual(len(critical_results), 1)
        self.assertEqual(critical_results[0]["data"]["message"], "Critical issue")

        # Get high priority results
        high_results = self.aggregator.get_results_by_priority("high")
        self.assertEqual(len(high_results), 2)

    def test_get_results_by_source(self):
        """Test getting results by source."""
        # Add results from different sources
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY, source="agent1", data={"message": "Agent 1 issue"}
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY, source="agent2", data={"message": "Agent 2 issue 1"}
        )

        self.aggregator.add_result(
            result_type=ResultType.PERFORMANCE, source="agent2", data={"message": "Agent 2 issue 2"}
        )

        # Get results from agent1
        agent1_results = self.aggregator.get_results_by_source("agent1")
        self.assertEqual(len(agent1_results), 1)
        self.assertEqual(agent1_results[0]["data"]["message"], "Agent 1 issue")

        # Get results from agent2
        agent2_results = self.aggregator.get_results_by_source("agent2")
        self.assertEqual(len(agent2_results), 2)

    def test_get_results_by_tags(self):
        """Test getting results by tags."""
        # Add results with different tags
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Issue 1"},
            tags=["security", "critical"],
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY,
            source="test_agent",
            data={"message": "Issue 2"},
            tags=["security", "performance"],
        )

        self.aggregator.add_result(
            result_type=ResultType.PERFORMANCE,
            source="test_agent",
            data={"message": "Issue 3"},
            tags=["performance"],
        )

        # Get results with any matching tag
        security_results = self.aggregator.get_results_by_tags(["security"])
        self.assertEqual(len(security_results), 2)

        # Get results with all matching tags
        security_perf_results = self.aggregator.get_results_by_tags(
            ["security", "performance"], match_all=True
        )
        self.assertEqual(len(security_perf_results), 1)
        self.assertEqual(security_perf_results[0]["data"]["message"], "Issue 2")

    def test_update_result(self):
        """Test updating a result."""
        # Add a result
        result_id = self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Original message", "count": 1},
        )

        # Update the result
        success = self.aggregator.update_result(
            result_id=result_id, data={"message": "Updated message", "new_field": "new value"}
        )

        # Verify update was successful
        self.assertTrue(success)

        # Verify result was updated
        updated_result = self.aggregator.get_result(result_id)
        self.assertEqual(updated_result["data"]["message"], "Updated message")
        self.assertEqual(updated_result["data"]["count"], 1)  # Original field preserved
        self.assertEqual(updated_result["data"]["new_field"], "new value")  # New field added

        # Try updating non-existent result
        success = self.aggregator.update_result(
            result_id="non_existent_id", data={"message": "This should fail"}
        )
        self.assertFalse(success)

    def test_remove_result(self):
        """Test removing a result."""
        # Add results
        result_id1 = self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY, source="test_agent", data={"message": "Issue 1"}
        )

        result_id2 = self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY, source="test_agent", data={"message": "Issue 2"}
        )

        # Remove one result
        success = self.aggregator.remove_result(result_id1)
        self.assertTrue(success)

        # Verify result was removed
        self.assertIsNone(self.aggregator.get_result(result_id1))
        self.assertEqual(len(self.aggregator.get_results_by_type(ResultType.CODE_QUALITY)), 1)

        # Try removing non-existent result
        success = self.aggregator.remove_result("non_existent_id")
        self.assertFalse(success)

    def test_clear_results(self):
        """Test clearing results."""
        # Add results of different types
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Quality issue"},
        )

        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Another quality issue"},
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY, source="test_agent", data={"message": "Security issue"}
        )

        # Clear results of a specific type
        count = self.aggregator.clear_results(ResultType.CODE_QUALITY)
        self.assertEqual(count, 2)

        # Verify only code quality results were cleared
        self.assertEqual(len(self.aggregator.get_results_by_type(ResultType.CODE_QUALITY)), 0)
        self.assertEqual(len(self.aggregator.get_results_by_type(ResultType.SECURITY)), 1)

        # Clear all results
        count = self.aggregator.clear_results()
        self.assertEqual(count, 1)

        # Verify all results were cleared
        self.assertEqual(len(self.aggregator.results), 0)
        self.assertEqual(len(self.aggregator.result_index), 0)

    def test_get_summary(self):
        """Test getting a summary of results."""
        # Add results of different types and priorities
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Issue 1"},
            priority=ResultPriority.HIGH,
        )

        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Issue 2"},
            priority=ResultPriority.MEDIUM,
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY,
            source="test_agent",
            data={"message": "Issue 3"},
            priority=ResultPriority.CRITICAL,
        )

        # Get summary
        summary = self.aggregator.get_summary()

        # Verify summary content
        self.assertEqual(summary["total_results"], 3)
        self.assertEqual(summary["by_type"]["code_quality"], 2)
        self.assertEqual(summary["by_type"]["security"], 1)
        self.assertEqual(summary["by_priority"]["critical"], 1)
        self.assertEqual(summary["by_priority"]["high"], 1)
        self.assertEqual(summary["by_priority"]["medium"], 1)
        self.assertEqual(summary["by_priority"]["low"], 0)
        self.assertEqual(summary["by_priority"]["info"], 0)

    def test_export_import_results(self):
        """Test exporting and importing results."""
        # Add some results
        self.aggregator.add_result(
            result_type=ResultType.CODE_QUALITY,
            source="test_agent",
            data={"message": "Issue 1"},
            priority=ResultPriority.HIGH,
        )

        self.aggregator.add_result(
            result_type=ResultType.SECURITY,
            source="test_agent",
            data={"message": "Issue 2"},
            priority=ResultPriority.CRITICAL,
        )

        # Export results
        exported_data = self.aggregator.export_results()

        # Create a new aggregator
        new_aggregator = ResultAggregator(self.workspace_path)

        # Import results
        count = new_aggregator.import_results(exported_data)

        # Verify import was successful
        self.assertEqual(count, 2)
        self.assertEqual(len(new_aggregator.results), 2)
        self.assertEqual(len(new_aggregator.get_results_by_type(ResultType.CODE_QUALITY)), 1)
        self.assertEqual(len(new_aggregator.get_results_by_type(ResultType.SECURITY)), 1)

        # Test importing invalid data
        with patch("json.loads") as mock_loads:
            mock_loads.side_effect = json.JSONDecodeError("Test error", "", 0)
            count = new_aggregator.import_results("invalid json")
            self.assertEqual(count, 0)

        # Test unsupported format
        count = new_aggregator.import_results("data", format_type="xml")
        self.assertEqual(count, 0)

        # Test unsupported export format
        exported_data = self.aggregator.export_results(format_type="xml")
        self.assertEqual(exported_data, "")


if __name__ == "__main__":
    unittest.main()
