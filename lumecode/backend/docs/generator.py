import os
import re
import ast
import json
import inspect
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path


class DocFormat(Enum):
    """Documentation format types."""

    MARKDOWN = "markdown"
    HTML = "html"
    RST = "rst"  # reStructuredText
    PLAIN = "plain"
    JSON = "json"


class DocSection(Enum):
    """Documentation section types."""

    OVERVIEW = "overview"
    ARCHITECTURE = "architecture"
    API = "api"
    CLASSES = "classes"
    FUNCTIONS = "functions"
    MODULES = "modules"
    PLUGINS = "plugins"
    AGENTS = "agents"
    EXAMPLES = "examples"
    CONFIGURATION = "configuration"
    DEPLOYMENT = "deployment"
    CONTRIBUTING = "contributing"


@dataclass
class DocItem:
    """Represents a documentation item."""

    name: str
    path: str
    doc_string: Optional[str] = None
    signature: Optional[str] = None
    item_type: str = ""  # class, function, module, etc.
    source_code: Optional[str] = None
    line_numbers: Tuple[int, int] = (0, 0)  # start, end
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List[Any] = field(default_factory=list)  # List[DocItem]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "path": self.path,
            "doc_string": self.doc_string,
            "signature": self.signature,
            "item_type": self.item_type,
            "line_numbers": self.line_numbers,
            "metadata": self.metadata,
        }

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result


@dataclass
class DocTemplate:
    """Template for documentation generation."""

    name: str
    format: DocFormat
    content: str
    variables: Dict[str, Any] = field(default_factory=dict)
    sections: List[DocSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocParser:
    """Parser for extracting documentation from code."""

    def __init__(self):
        self.parsed_modules: Dict[str, DocItem] = {}
        self.ignored_dirs: Set[str] = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
        self.ignored_files: Set[str] = {"__pycache__"}
        self.file_extensions: Set[str] = {".py"}

    def parse_directory(self, directory_path: str) -> List[DocItem]:
        """Parse all files in a directory recursively.

        Args:
            directory_path: Path to the directory to parse

        Returns:
            List of DocItem objects representing the parsed modules
        """
        directory_path = os.path.abspath(directory_path)
        result = []

        for root, dirs, files in os.walk(directory_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]

            for file in files:
                if file in self.ignored_files:
                    continue

                _, ext = os.path.splitext(file)
                if ext not in self.file_extensions:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory_path)

                try:
                    doc_item = self.parse_file(file_path, relative_path)
                    if doc_item:
                        result.append(doc_item)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

        return result

    def parse_file(self, file_path: str, relative_path: str = None) -> Optional[DocItem]:
        """Parse a single file.

        Args:
            file_path: Path to the file to parse
            relative_path: Relative path for documentation purposes

        Returns:
            DocItem object representing the parsed module or None if parsing failed
        """
        if relative_path is None:
            relative_path = file_path

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            module = ast.parse(content)
            module_name = os.path.basename(file_path).split(".")[0]

            doc_item = DocItem(
                name=module_name,
                path=relative_path,
                doc_string=ast.get_docstring(module),
                item_type="module",
                source_code=content,
                line_numbers=(1, len(content.splitlines())),
            )

            # Parse classes and functions
            for node in module.body:
                if isinstance(node, ast.ClassDef):
                    class_item = self._parse_class(node, content)
                    doc_item.children.append(class_item)
                elif isinstance(node, ast.FunctionDef):
                    func_item = self._parse_function(node, content)
                    doc_item.children.append(func_item)

            return doc_item
        except SyntaxError:
            print(f"Syntax error in {file_path}")
            return None

    def _parse_class(self, node: ast.ClassDef, source: str) -> DocItem:
        """Parse a class definition.

        Args:
            node: AST node for the class
            source: Source code string

        Returns:
            DocItem representing the class
        """
        class_item = DocItem(
            name=node.name,
            path=f"{node.name}",
            doc_string=ast.get_docstring(node),
            item_type="class",
            line_numbers=(
                node.lineno,
                node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
            ),
        )

        # Get class source code
        source_lines = source.splitlines()
        class_source = "\n".join(
            source_lines[node.lineno - 1 : node.end_lineno if hasattr(node, "end_lineno") else -1]
        )
        class_item.source_code = class_source

        # Parse methods
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method_item = self._parse_function(child, source)
                class_item.children.append(method_item)

        return class_item

    def _parse_function(self, node: ast.FunctionDef, source: str) -> DocItem:
        """Parse a function definition.

        Args:
            node: AST node for the function
            source: Source code string

        Returns:
            DocItem representing the function
        """
        # Build function signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        signature = f"{node.name}({', '.join(args)})"

        func_item = DocItem(
            name=node.name,
            path=f"{node.name}",
            doc_string=ast.get_docstring(node),
            signature=signature,
            item_type="function",
            line_numbers=(
                node.lineno,
                node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
            ),
        )

        # Get function source code
        source_lines = source.splitlines()
        func_source = "\n".join(
            source_lines[node.lineno - 1 : node.end_lineno if hasattr(node, "end_lineno") else -1]
        )
        func_item.source_code = func_source

        return func_item


class DocGenerator:
    """Generator for creating documentation from parsed code."""

    def __init__(self, parser: DocParser = None):
        self.parser = parser or DocParser()
        self.templates: Dict[str, DocTemplate] = {}
        self.load_default_templates()

    def load_default_templates(self):
        """Load default documentation templates."""
        # Markdown API template
        self.templates["markdown_api"] = DocTemplate(
            name="markdown_api",
            format=DocFormat.MARKDOWN,
            content="""# {title}

{description}

## Modules

{modules}

## Classes

{classes}

## Functions

{functions}
""",
            variables={
                "title": "API Documentation",
                "description": "Generated API documentation for the project.",
                "modules": "",
                "classes": "",
                "functions": "",
            },
            sections=[DocSection.API, DocSection.MODULES, DocSection.CLASSES, DocSection.FUNCTIONS],
        )

        # Markdown Overview template
        self.templates["markdown_overview"] = DocTemplate(
            name="markdown_overview",
            format=DocFormat.MARKDOWN,
            content="""# {title}

{description}

## Architecture

{architecture}

## Components

{components}

## Getting Started

{getting_started}
""",
            variables={
                "title": "Project Overview",
                "description": "Overview of the project architecture and components.",
                "architecture": "Project architecture description goes here.",
                "components": "Project components description goes here.",
                "getting_started": "Getting started guide goes here.",
            },
            sections=[DocSection.OVERVIEW, DocSection.ARCHITECTURE],
        )

    def add_template(self, template: DocTemplate):
        """Add a new template.

        Args:
            template: DocTemplate to add
        """
        self.templates[template.name] = template

    def generate_from_directory(
        self, directory_path: str, template_name: str, output_path: str
    ) -> str:
        """Generate documentation from a directory using a template.

        Args:
            directory_path: Path to the directory to parse
            template_name: Name of the template to use
            output_path: Path to save the generated documentation

        Returns:
            Path to the generated documentation file
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")

        # Parse the directory
        doc_items = self.parser.parse_directory(directory_path)

        # Generate documentation
        template = self.templates[template_name]
        content = self._generate_content(doc_items, template)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return output_path

    def _generate_content(self, doc_items: List[DocItem], template: DocTemplate) -> str:
        """Generate content from doc items using a template.

        Args:
            doc_items: List of DocItem objects
            template: DocTemplate to use

        Returns:
            Generated documentation content
        """
        variables = template.variables.copy()

        if DocSection.MODULES in template.sections:
            variables["modules"] = self._generate_modules_section(doc_items)

        if DocSection.CLASSES in template.sections:
            variables["classes"] = self._generate_classes_section(doc_items)

        if DocSection.FUNCTIONS in template.sections:
            variables["functions"] = self._generate_functions_section(doc_items)

        return template.content.format(**variables)

    def _generate_modules_section(self, doc_items: List[DocItem]) -> str:
        """Generate the modules section.

        Args:
            doc_items: List of DocItem objects

        Returns:
            Generated modules section content
        """
        result = []

        for item in doc_items:
            result.append(f"### {item.name}")

            if item.doc_string:
                result.append(f"\n{item.doc_string}\n")

            result.append(f"**Path:** `{item.path}`\n")

        return "\n".join(result)

    def _generate_classes_section(self, doc_items: List[DocItem]) -> str:
        """Generate the classes section.

        Args:
            doc_items: List of DocItem objects

        Returns:
            Generated classes section content
        """
        result = []

        for module in doc_items:
            for class_item in [c for c in module.children if c.item_type == "class"]:
                result.append(f"### {class_item.name}")

                if class_item.doc_string:
                    result.append(f"\n{class_item.doc_string}\n")

                result.append(f"**Defined in:** `{module.path}`\n")

                # Methods
                if class_item.children:
                    result.append("#### Methods\n")

                    for method in class_item.children:
                        result.append(f"##### `{method.signature}`")

                        if method.doc_string:
                            result.append(f"\n{method.doc_string}\n")

        return "\n".join(result)

    def _generate_functions_section(self, doc_items: List[DocItem]) -> str:
        """Generate the functions section.

        Args:
            doc_items: List of DocItem objects

        Returns:
            Generated functions section content
        """
        result = []

        for module in doc_items:
            for func in [f for f in module.children if f.item_type == "function"]:
                result.append(f"### `{func.signature}`")

                if func.doc_string:
                    result.append(f"\n{func.doc_string}\n")

                result.append(f"**Defined in:** `{module.path}`\n")

        return "\n".join(result)


class DocServer:
    """Server for serving generated documentation."""

    def __init__(self, doc_path: str, host: str = "localhost", port: int = 8080):
        self.doc_path = doc_path
        self.host = host
        self.port = port
        self.server = None

    def start(self):
        """Start the documentation server."""
        import http.server
        import socketserver
        import threading

        handler = http.server.SimpleHTTPRequestHandler

        class DocHTTPServer(socketserver.TCPServer):
            allow_reuse_address = True

        os.chdir(self.doc_path)
        self.server = DocHTTPServer((self.host, self.port), handler)

        # Run server in a separate thread
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        print(f"Documentation server started at http://{self.host}:{self.port}")

        return f"http://{self.host}:{self.port}"

    def stop(self):
        """Stop the documentation server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("Documentation server stopped")


class DocManager:
    """Manager for documentation generation and serving."""

    def __init__(self, project_root: str, output_dir: str = None):
        self.project_root = os.path.abspath(project_root)
        self.output_dir = output_dir or os.path.join(self.project_root, "docs", "generated")
        self.parser = DocParser()
        self.generator = DocGenerator(self.parser)
        self.server = None

    def generate_all(self) -> Dict[str, str]:
        """Generate all documentation.

        Returns:
            Dictionary mapping template names to output paths
        """
        os.makedirs(self.output_dir, exist_ok=True)
        results = {}

        for template_name, template in self.generator.templates.items():
            output_path = os.path.join(self.output_dir, f"{template_name}.{template.format.value}")
            result_path = self.generator.generate_from_directory(
                self.project_root, template_name, output_path
            )
            results[template_name] = result_path

        return results

    def generate_api_docs(self) -> str:
        """Generate API documentation.

        Returns:
            Path to the generated API documentation
        """
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "api.md")

        return self.generator.generate_from_directory(
            self.project_root, "markdown_api", output_path
        )

    def generate_overview_docs(self) -> str:
        """Generate overview documentation.

        Returns:
            Path to the generated overview documentation
        """
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "overview.md")

        return self.generator.generate_from_directory(
            self.project_root, "markdown_overview", output_path
        )

    def serve_docs(self, host: str = "localhost", port: int = 8080) -> str:
        """Serve the generated documentation.

        Args:
            host: Host to serve on
            port: Port to serve on

        Returns:
            URL to the documentation server
        """
        if not os.path.exists(self.output_dir):
            self.generate_all()

        self.server = DocServer(self.output_dir, host, port)
        return self.server.start()

    def stop_server(self):
        """Stop the documentation server."""
        if self.server:
            self.server.stop()
            self.server = None
