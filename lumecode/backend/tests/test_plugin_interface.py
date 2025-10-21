import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from plugins.interface import (
    PluginType,
    PluginStatus,
    PluginMetadata,
    PluginResult,
    PluginInterface,
    AnalyzerPlugin,
    PluginManager,
)


class TestPluginMetadata(unittest.TestCase):
    def test_initialization(self):
        """Test PluginMetadata initialization"""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            plugin_type=PluginType.ANALYZER,
            author="Test Author",
            homepage="https://example.com",
            repository="https://github.com/example/test-plugin",
            dependencies=["dep1", "dep2"],
            supported_languages=["python", "javascript"],
            tags=["test", "example"],
        )

        self.assertEqual(metadata.name, "test-plugin")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.description, "Test plugin")
        self.assertEqual(metadata.plugin_type, PluginType.ANALYZER)
        self.assertEqual(metadata.author, "Test Author")
        self.assertEqual(metadata.homepage, "https://example.com")
        self.assertEqual(metadata.repository, "https://github.com/example/test-plugin")
        self.assertEqual(metadata.dependencies, ["dep1", "dep2"])
        self.assertEqual(metadata.supported_languages, ["python", "javascript"])
        self.assertEqual(metadata.tags, ["test", "example"])

    def test_to_dict(self):
        """Test conversion to dictionary"""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            plugin_type=PluginType.ANALYZER,
        )

        data = metadata.to_dict()
        self.assertEqual(data["name"], "test-plugin")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["description"], "Test plugin")
        self.assertEqual(data["type"], "analyzer")

    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "type": "analyzer",
            "author": "Test Author",
            "tags": ["test"],
        }

        metadata = PluginMetadata.from_dict(data)
        self.assertEqual(metadata.name, "test-plugin")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.description, "Test plugin")
        self.assertEqual(metadata.plugin_type, PluginType.ANALYZER)
        self.assertEqual(metadata.author, "Test Author")
        self.assertEqual(metadata.tags, ["test"])


class TestPluginResult(unittest.TestCase):
    def test_initialization(self):
        """Test PluginResult initialization"""
        result = PluginResult(
            success=True, data={"key": "value"}, error=None, metadata={"time": 123}
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data, {"key": "value"})
        self.assertIsNone(result.error)
        self.assertEqual(result.metadata, {"time": 123})

    def test_success_result(self):
        """Test success result factory method"""
        result = PluginResult.success_result({"key": "value"}, {"time": 123})

        self.assertTrue(result.success)
        self.assertEqual(result.data, {"key": "value"})
        self.assertIsNone(result.error)
        self.assertEqual(result.metadata, {"time": 123})

    def test_error_result(self):
        """Test error result factory method"""
        result = PluginResult.error_result("Something went wrong", {"time": 123})

        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error, "Something went wrong")
        self.assertEqual(result.metadata, {"time": 123})

    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = PluginResult(
            success=True, data={"key": "value"}, error=None, metadata={"time": 123}
        )

        data = result.to_dict()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"], {"key": "value"})
        self.assertIsNone(data["error"])
        self.assertEqual(data["metadata"], {"time": 123})


class MockPlugin(PluginInterface):
    """Mock plugin for testing"""

    def get_metadata(self):
        return PluginMetadata(
            name="mock-plugin",
            version="1.0.0",
            description="Mock plugin for testing",
            plugin_type=PluginType.ANALYZER,
        )

    def initialize(self, config):
        self.config = config
        self.status = PluginStatus.INITIALIZED
        return True

    def execute(self, context):
        if "fail" in context:
            return PluginResult.error_result("Execution failed")
        return PluginResult.success_result({"result": "success"})


class MockAnalyzerPlugin(AnalyzerPlugin):
    """Mock analyzer plugin for testing"""

    def get_metadata(self):
        return PluginMetadata(
            name="mock-analyzer",
            version="1.0.0",
            description="Mock analyzer plugin",
            plugin_type=PluginType.ANALYZER,
        )

    def initialize(self, config):
        self.config = config
        self.status = PluginStatus.INITIALIZED
        return True

    def execute(self, context):
        return self.analyze_file(context.get("file_path", ""))

    def analyze_file(self, file_path, options=None):
        if not file_path:
            return PluginResult.error_result("No file path provided")
        return PluginResult.success_result({"issues": 0})

    def analyze_code(self, code, language, options=None):
        if not code:
            return PluginResult.error_result("No code provided")
        return PluginResult.success_result({"issues": 0})


class TestPluginInterface(unittest.TestCase):
    def test_plugin_lifecycle(self):
        """Test plugin lifecycle"""
        plugin = MockPlugin()

        # Initial state
        self.assertEqual(plugin.status, PluginStatus.LOADED)

        # Initialize
        config = {"key": "value"}
        self.assertTrue(plugin.initialize(config))
        self.assertEqual(plugin.status, PluginStatus.INITIALIZED)
        self.assertEqual(plugin.config, config)

        # Execute
        result = plugin.execute({"data": "test"})
        self.assertTrue(result.success)
        self.assertEqual(result.data, {"result": "success"})

        # Execute with failure
        result = plugin.execute({"fail": True})
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Execution failed")

        # Cleanup
        self.assertTrue(plugin.cleanup())


class TestAnalyzerPlugin(unittest.TestCase):
    def test_analyzer_methods(self):
        """Test analyzer plugin methods"""
        plugin = MockAnalyzerPlugin()

        # Initialize
        self.assertTrue(plugin.initialize({}))

        # Analyze file
        result = plugin.analyze_file("test.py")
        self.assertTrue(result.success)
        self.assertEqual(result.data, {"issues": 0})

        # Analyze file with error
        result = plugin.analyze_file("")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "No file path provided")

        # Analyze code
        result = plugin.analyze_code("print('hello')", "python")
        self.assertTrue(result.success)
        self.assertEqual(result.data, {"issues": 0})

        # Analyze code with error
        result = plugin.analyze_code("", "python")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "No code provided")

        # Analyze project (default implementation)
        result = plugin.analyze_project("project/")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "analyze_project not implemented")


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path("temp_plugins")
        self.manager = PluginManager(self.temp_dir)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    def test_discover_plugins(self, mock_iterdir, mock_exists):
        """Test plugin discovery"""
        # Mock directory structure
        mock_exists.return_value = True

        # Create mock directory entries
        mock_dir1 = MagicMock(spec=Path)
        mock_dir1.is_dir.return_value = True
        mock_dir1.name = "plugin1"
        mock_dir1.__truediv__.return_value.exists.return_value = True

        mock_file1 = MagicMock(spec=Path)
        mock_file1.is_dir.return_value = False
        mock_file1.is_file.return_value = True
        mock_file1.suffix = ".py"
        mock_file1.name = "plugin2.py"
        mock_file1.stem = "plugin2"

        mock_file2 = MagicMock(spec=Path)
        mock_file2.is_dir.return_value = False
        mock_file2.is_file.return_value = True
        mock_file2.suffix = ".py"
        mock_file2.name = "__init__.py"

        mock_iterdir.return_value = [mock_dir1, mock_file1, mock_file2]

        # Test discovery
        discovered = self.manager.discover_plugins()
        self.assertEqual(len(discovered), 2)
        self.assertIn("plugin1", discovered)
        self.assertIn("plugin2", discovered)

    def test_register_trigger_hook(self):
        """Test hook registration and triggering"""
        # Register hooks
        hook1_called = False
        hook2_called = False

        def hook1_callback(arg):
            nonlocal hook1_called
            hook1_called = True
            return arg

        def hook2_callback(arg):
            nonlocal hook2_called
            hook2_called = True
            return arg * 2

        self.manager.register_hook("test_hook", hook1_callback)
        self.manager.register_hook("test_hook", hook2_callback)

        # Trigger hook
        results = self.manager.trigger_hook("test_hook", 5)

        # Check results
        self.assertTrue(hook1_called)
        self.assertTrue(hook2_called)
        self.assertEqual(results, [5, 10])

        # Trigger non-existent hook
        results = self.manager.trigger_hook("nonexistent_hook")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
