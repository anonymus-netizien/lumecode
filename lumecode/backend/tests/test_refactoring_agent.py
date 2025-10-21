import os
import unittest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from lumecode.backend.agents.refactoring import RefactoringAgent
from lumecode.backend.agents.base import AgentStatus, AgentType


class TestRefactoringAgent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.agent_id = "test-refactoring-agent"

        # Create a test Python file
        self.test_file = os.path.join(self.temp_dir, "test_file.py")
        with open(self.test_file, "w") as f:
            f.write(
                """
# Test file with a long function
def very_long_function():
    # This is a placeholder for a long function
    a = 1
    b = 2
    c = 3
    # ... imagine 50 more lines here
    return a + b + c
            """
            )

        # Create the agent with mocked dependencies
        self.agent = RefactoringAgent(self.agent_id, self.temp_dir)

        # Mock the analysis engine and parser
        self.agent.analysis_engine = MagicMock()

        # Setup mock AST
        self.mock_function = MagicMock()
        self.mock_function.start_line = 3
        self.mock_function.end_line = 60  # Simulating a long function
        self.mock_function.name = "very_long_function"

        self.mock_ast = MagicMock()
        self.mock_ast.functions = [self.mock_function]

        # Configure the mock to return our mock AST
        self.agent.analysis_engine.parse_file.return_value = self.mock_ast

    def tearDown(self):
        # Clean up temp directory
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_initialization(self):
        """Test that the agent initializes correctly"""
        self.assertEqual(self.agent.agent_id, self.agent_id)
        self.assertEqual(self.agent.agent_type, AgentType.REFACTORING)
        self.assertEqual(self.agent.status, AgentStatus.CREATED)
        self.assertIsNotNone(self.agent.refactoring_patterns)
        self.assertTrue("python" in self.agent.refactoring_patterns)
        self.assertTrue("javascript" in self.agent.refactoring_patterns)

    def test_get_language_from_extension(self):
        """Test language detection from file extension"""
        self.assertEqual(self.agent._get_language_from_extension(".py"), "python")
        self.assertEqual(self.agent._get_language_from_extension(".js"), "javascript")
        self.assertEqual(self.agent._get_language_from_extension(".ts"), "javascript")
        self.assertEqual(self.agent._get_language_from_extension(".unknown"), None)

    def test_find_refactoring_opportunities(self):
        """Test finding refactoring opportunities in code"""
        suggestions = self.agent._find_refactoring_opportunities(self.mock_ast, "python")

        # Should find one long function suggestion
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["type"], "long_function")
        self.assertEqual(suggestions[0]["location"]["name"], "very_long_function")

    def test_async_start_stop(self):
        """Test async start and stop methods"""
        loop = asyncio.get_event_loop()

        # Test start
        start_result = loop.run_until_complete(self.agent.start())
        self.assertTrue(start_result)
        self.assertEqual(self.agent.status, AgentStatus.RUNNING)

        # Test stop
        stop_result = loop.run_until_complete(self.agent.stop())
        self.assertTrue(stop_result)
        self.assertEqual(self.agent.status, AgentStatus.STOPPED)

    def test_analyze_file(self):
        """Test analyzing a file for refactoring opportunities"""
        loop = asyncio.get_event_loop()

        # Mock sandbox validation to always pass
        self.agent.sandbox.validate_file_access = MagicMock(return_value=True)

        result = loop.run_until_complete(self.agent.analyze_file(self.test_file))

        # Verify the result structure
        self.assertEqual(result["file"], self.test_file)
        self.assertEqual(result["language"], "python")
        self.assertIn("suggestions", result)
        self.assertEqual(len(result["suggestions"]), 1)  # Should find one issue

    def test_analyze_nonexistent_file(self):
        """Test analyzing a file that doesn't exist"""
        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(self.agent.analyze_file("/path/to/nonexistent/file.py"))

        # Should return an error
        self.assertIn("error", result)
        self.assertTrue("not found" in result["error"])

    def test_process_task_analyze(self):
        """Test processing an analyze task"""
        loop = asyncio.get_event_loop()

        # Mock analyze_file to return a predetermined result
        self.agent.analyze_file = AsyncMock(
            return_value={
                "file": self.test_file,
                "language": "python",
                "suggestions": [{"type": "long_function"}],
            }
        )

        task_data = {"type": "analyze", "file_paths": [self.test_file]}

        result = loop.run_until_complete(self.agent.process_task(task_data))

        # Verify the result
        self.assertEqual(result["status"], "completed")
        self.assertIn("results", result)
        self.assertIn(self.test_file, result["results"])

    def test_process_task_apply(self):
        """Test processing an apply task"""
        loop = asyncio.get_event_loop()

        # Mock apply_refactoring to return a predetermined result
        self.agent.apply_refactoring = AsyncMock(
            return_value={
                "file": self.test_file,
                "refactoring_id": "split_long_function",
                "status": "not_implemented",
            }
        )

        task_data = {
            "type": "apply",
            "file_path": self.test_file,
            "refactoring_id": "split_long_function",
        }

        result = loop.run_until_complete(self.agent.process_task(task_data))

        # Verify the result
        self.assertEqual(result["status"], "completed")
        self.assertIn("result", result)


if __name__ == "__main__":
    unittest.main()
