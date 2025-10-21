import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.docs.generator import (
    DocFormat,
    DocSection,
    DocItem,
    DocTemplate,
    DocParser,
    DocGenerator,
    DocServer,
    DocManager,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    file_path = os.path.join(temp_dir, "sample.py")
    with open(file_path, "w") as f:
        f.write(
            '"""Sample module docstring."""\n\nclass SampleClass:\n    """Sample class docstring."""\n    \n    def __init__(self, param1, param2=None):\n        """Initialize the class.\n        \n        Args:\n            param1: First parameter\n            param2: Second parameter (optional)\n        """\n        self.param1 = param1\n        self.param2 = param2\n    \n    def sample_method(self, arg1):\n        """Sample method docstring.\n        \n        Args:\n            arg1: First argument\n            \n        Returns:\n            Sample return value\n        """\n        return arg1\n\n\ndef sample_function(arg1, arg2=None):\n    """Sample function docstring.\n    \n    Args:\n        arg1: First argument\n        arg2: Second argument (optional)\n        \n    Returns:\n        Sample return value\n    """\n    return arg1'
        )

    return file_path


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure for testing."""
    # Create main module
    os.makedirs(os.path.join(temp_dir, "main_module"))
    with open(os.path.join(temp_dir, "main_module", "__init__.py"), "w") as f:
        f.write('"""Main module docstring."""\n')

    # Create submodule
    os.makedirs(os.path.join(temp_dir, "main_module", "submodule"))
    with open(os.path.join(temp_dir, "main_module", "submodule", "__init__.py"), "w") as f:
        f.write('"""Submodule docstring."""\n')

    # Create a module file
    with open(os.path.join(temp_dir, "main_module", "module.py"), "w") as f:
        f.write(
            '"""Module docstring."""\n\nclass TestClass:\n    """Test class docstring."""\n    \n    def test_method(self):\n        """Test method docstring."""\n        pass\n\n\ndef test_function():\n    """Test function docstring."""\n    pass'
        )

    return temp_dir


class TestDocItem:
    """Tests for DocItem class."""

    def test_init(self):
        """Test initialization."""
        doc_item = DocItem(
            name="test",
            path="test/path",
            doc_string="Test docstring",
            signature="test(arg1, arg2)",
            item_type="function",
            source_code="def test(): pass",
            line_numbers=(1, 2),
            metadata={"key": "value"},
        )

        assert doc_item.name == "test"
        assert doc_item.path == "test/path"
        assert doc_item.doc_string == "Test docstring"
        assert doc_item.signature == "test(arg1, arg2)"
        assert doc_item.item_type == "function"
        assert doc_item.source_code == "def test(): pass"
        assert doc_item.line_numbers == (1, 2)
        assert doc_item.metadata == {"key": "value"}
        assert doc_item.children == []

    def test_to_dict(self):
        """Test conversion to dictionary."""
        doc_item = DocItem(
            name="test",
            path="test/path",
            doc_string="Test docstring",
            signature="test(arg1, arg2)",
            item_type="function",
            line_numbers=(1, 2),
            metadata={"key": "value"},
        )

        child_item = DocItem(name="child", path="child/path", item_type="function")
        doc_item.children.append(child_item)

        result = doc_item.to_dict()

        assert result["name"] == "test"
        assert result["path"] == "test/path"
        assert result["doc_string"] == "Test docstring"
        assert result["signature"] == "test(arg1, arg2)"
        assert result["item_type"] == "function"
        assert result["line_numbers"] == (1, 2)
        assert result["metadata"] == {"key": "value"}
        assert len(result["children"]) == 1
        assert result["children"][0]["name"] == "child"


class TestDocTemplate:
    """Tests for DocTemplate class."""

    def test_init(self):
        """Test initialization."""
        template = DocTemplate(
            name="test",
            format=DocFormat.MARKDOWN,
            content="# {title}\n\n{content}",
            variables={"title": "Test", "content": "Test content"},
            sections=[DocSection.API, DocSection.CLASSES],
            metadata={"key": "value"},
        )

        assert template.name == "test"
        assert template.format == DocFormat.MARKDOWN
        assert template.content == "# {title}\n\n{content}"
        assert template.variables == {"title": "Test", "content": "Test content"}
        assert template.sections == [DocSection.API, DocSection.CLASSES]
        assert template.metadata == {"key": "value"}


class TestDocParser:
    """Tests for DocParser class."""

    def test_init(self):
        """Test initialization."""
        parser = DocParser()

        assert parser.parsed_modules == {}
        assert "__pycache__" in parser.ignored_dirs
        assert "__pycache__" in parser.ignored_files
        assert ".py" in parser.file_extensions

    def test_parse_file(self, sample_python_file):
        """Test parsing a single file."""
        parser = DocParser()
        doc_item = parser.parse_file(sample_python_file)

        assert doc_item is not None
        assert doc_item.name == "sample"
        assert doc_item.item_type == "module"
        assert "Sample module docstring." in doc_item.doc_string

        # Check children
        assert len(doc_item.children) == 2

        # Check class
        class_item = next(c for c in doc_item.children if c.item_type == "class")
        assert class_item.name == "SampleClass"
        assert "Sample class docstring." in class_item.doc_string

        # Check class methods
        assert len(class_item.children) == 2
        init_method = next(m for m in class_item.children if m.name == "__init__")
        assert "Initialize the class." in init_method.doc_string

        sample_method = next(m for m in class_item.children if m.name == "sample_method")
        assert "Sample method docstring." in sample_method.doc_string

        # Check function
        function_item = next(f for f in doc_item.children if f.item_type == "function")
        assert function_item.name == "sample_function"
        assert "Sample function docstring." in function_item.doc_string

    def test_parse_directory(self, sample_project):
        """Test parsing a directory."""
        parser = DocParser()
        doc_items = parser.parse_directory(sample_project)

        # Check that we found the modules
        assert len(doc_items) >= 3  # __init__.py, __init__.py, module.py

        # Find the module.py file
        module_item = next((item for item in doc_items if item.name == "module"), None)
        assert module_item is not None
        assert "Module docstring." in module_item.doc_string

        # Check children
        assert len(module_item.children) == 2

        # Check class
        class_item = next(c for c in module_item.children if c.item_type == "class")
        assert class_item.name == "TestClass"
        assert "Test class docstring." in class_item.doc_string

        # Check function
        function_item = next(f for f in module_item.children if f.item_type == "function")
        assert function_item.name == "test_function"
        assert "Test function docstring." in function_item.doc_string


class TestDocGenerator:
    """Tests for DocGenerator class."""

    def test_init(self):
        """Test initialization."""
        generator = DocGenerator()

        assert generator.parser is not None
        assert len(generator.templates) >= 2
        assert "markdown_api" in generator.templates
        assert "markdown_overview" in generator.templates

    def test_add_template(self):
        """Test adding a template."""
        generator = DocGenerator()
        template = DocTemplate(
            name="test_template",
            format=DocFormat.HTML,
            content="<h1>{title}</h1>",
            variables={"title": "Test"},
        )

        generator.add_template(template)

        assert "test_template" in generator.templates
        assert generator.templates["test_template"] == template

    def test_generate_from_directory(self, sample_project, temp_dir):
        """Test generating documentation from a directory."""
        generator = DocGenerator()
        output_path = os.path.join(temp_dir, "output.md")

        result = generator.generate_from_directory(sample_project, "markdown_api", output_path)

        assert result == output_path
        assert os.path.exists(output_path)

        # Check content
        with open(output_path, "r") as f:
            content = f.read()

        assert "# API Documentation" in content
        assert "## Modules" in content
        assert "## Classes" in content
        assert "## Functions" in content

        # Check that we found some modules
        assert "### module" in content or "### __init__" in content

        # Check that we found some classes
        assert "### TestClass" in content

        # Check that we found some functions
        assert "### `test_function()`" in content or "test_function" in content


class TestDocServer:
    """Tests for DocServer class."""

    @patch("http.server.SimpleHTTPRequestHandler")
    @patch("socketserver.TCPServer")
    @patch("threading.Thread")
    def test_start_stop(self, mock_thread, mock_server, mock_handler, temp_dir):
        """Test starting and stopping the server."""
        server = DocServer(temp_dir)

        # Mock the server
        mock_server_instance = MagicMock()
        mock_server.return_value = mock_server_instance

        # Start the server
        url = server.start()

        assert url == "http://localhost:8080"
        mock_server.assert_called_once()
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

        # Stop the server
        server.stop()

        mock_server_instance.shutdown.assert_called_once()
        mock_server_instance.server_close.assert_called_once()


class TestDocManager:
    """Tests for DocManager class."""

    def test_init(self, temp_dir):
        """Test initialization."""
        manager = DocManager(temp_dir)

        assert manager.project_root == os.path.abspath(temp_dir)
        assert manager.output_dir == os.path.join(os.path.abspath(temp_dir), "docs", "generated")
        assert manager.parser is not None
        assert manager.generator is not None
        assert manager.server is None

    def test_generate_api_docs(self, sample_project, temp_dir):
        """Test generating API documentation."""
        manager = DocManager(sample_project, output_dir=os.path.join(temp_dir, "output"))

        result = manager.generate_api_docs()

        assert os.path.exists(result)
        assert result == os.path.join(temp_dir, "output", "api.md")

        # Check content
        with open(result, "r") as f:
            content = f.read()

        assert "# API Documentation" in content

    def test_generate_overview_docs(self, sample_project, temp_dir):
        """Test generating overview documentation."""
        manager = DocManager(sample_project, output_dir=os.path.join(temp_dir, "output"))

        result = manager.generate_overview_docs()

        assert os.path.exists(result)
        assert result == os.path.join(temp_dir, "output", "overview.md")

        # Check content
        with open(result, "r") as f:
            content = f.read()

        assert "# Project Overview" in content

    def test_generate_all(self, sample_project, temp_dir):
        """Test generating all documentation."""
        manager = DocManager(sample_project, output_dir=os.path.join(temp_dir, "output"))

        results = manager.generate_all()

        assert len(results) >= 2
        assert "markdown_api" in results
        assert "markdown_overview" in results
        assert os.path.exists(results["markdown_api"])
        assert os.path.exists(results["markdown_overview"])

    @patch.object(DocServer, "start")
    def test_serve_docs(self, mock_start, sample_project, temp_dir):
        """Test serving documentation."""
        mock_start.return_value = "http://localhost:8080"

        manager = DocManager(sample_project, output_dir=os.path.join(temp_dir, "output"))
        url = manager.serve_docs()

        assert url == "http://localhost:8080"
        assert manager.server is not None
        mock_start.assert_called_once()

    @patch.object(DocServer, "stop")
    def test_stop_server(self, mock_stop, sample_project, temp_dir):
        """Test stopping the documentation server."""
        manager = DocManager(sample_project, output_dir=os.path.join(temp_dir, "output"))
        manager.server = MagicMock()

        manager.stop_server()

        assert manager.server is None
        mock_stop.assert_called_once()
