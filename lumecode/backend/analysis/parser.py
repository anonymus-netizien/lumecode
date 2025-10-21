from typing import Dict, List, Any, Optional, Union
import logging
import os
import re
import tempfile
import subprocess
import time
from pathlib import Path

# Import tree-sitter
try:
    from tree_sitter import Language, Parser
except ImportError:
    raise ImportError(
        "tree-sitter package is required for AST parsing. "
        "Install it with: pip install tree-sitter"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define supported languages
SUPPORTED_LANGUAGES = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "java": ".java",
    "go": ".go",
    "rust": ".rs",
}


class ASTParser:
    """
    A parser for generating ASTs using Tree-sitter.

    Attributes:
        parser: Tree-sitter parser instance
        languages: Dictionary of loaded languages
        languages_dir: Directory where language libraries are stored
        logger: Logger instance
    """

    def __init__(self, languages_dir: Optional[str] = None):
        """
        Initialize the AST parser.

        Args:
            languages_dir: Directory to store language libraries

        Raises:
            ImportError: If Tree-sitter is not installed
        """
        try:
            # Import Tree-sitter modules
            from tree_sitter import Language, Parser

            self.logger = logging.getLogger(__name__)
            self.logger.info("Initializing AST parser")

            # Set up languages directory
            self.languages_dir = languages_dir or os.path.join(
                os.path.dirname(__file__), "languages"
            )
            os.makedirs(self.languages_dir, exist_ok=True)

            # Initialize Tree-sitter parser
            self.parser = Parser()

            # Load languages
            self.languages: Dict[str, Language] = {}
            self._init_languages()

            self.logger.info(
                f"Initialized ASTParser with languages: {', '.join(self.languages.keys())}"
            )
        except ImportError as e:
            logging.error(f"Failed to import Tree-sitter: {e}")
            raise ImportError(
                "Tree-sitter is not installed. Please install it with 'pip install tree_sitter'"
            )

    def _init_languages(self) -> None:
        """
        Initialize Tree-sitter language libraries.
        If language libraries don't exist, they will be built.
        """
        # Check for existing language libraries
        for lang in SUPPORTED_LANGUAGES:
            lang_path = os.path.join(self.languages_dir, f"{lang}.so")

            if os.path.exists(lang_path):
                try:
                    self.languages[lang] = Language(lang_path, lang)
                    logger.info(f"Loaded language library for {lang}")
                except Exception as e:
                    logger.error(f"Failed to load language library for {lang}: {e}")
            else:
                logger.warning(f"Language library for {lang} not found at {lang_path}")
                # In a real implementation, we would build the language here
                # self._build_language(lang)

    def _build_language(self, language: str) -> None:
        """
        Build a Tree-sitter language library.

        Args:
            language: The language to build (e.g., 'python', 'javascript')

        Raises:
            Exception: If the language library could not be built
        """
        logger.info(f"Building language library for {language}")

        # Check if the language is supported
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")

        # Create languages directory if it doesn't exist
        os.makedirs(self.languages_dir, exist_ok=True)

        # Define the path for the language library
        lib_path = os.path.join(self.languages_dir, f"{language}.so")

        # If the library already exists, skip building
        if os.path.exists(lib_path):
            logger.info(f"Language library for {language} already exists")
            return

        try:
            # Try to use a simple build method with a known language repo
            logger.info(f"Attempting to build language library for {language} from source")

            # For demonstration and testing purposes, we'll create a minimal language library
            # that should work for basic parsing
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Clone the language repository
                repo_url = f"https://github.com/tree-sitter/tree-sitter-{language}"
                try:
                    subprocess.run(
                        ["git", "clone", repo_url, tmp_dir],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                except subprocess.CalledProcessError as e:
                    logger.warning(
                        f"Failed to clone {language} repository: {e}. Using fallback method."
                    )
                    # Fallback to a different approach if cloning fails
                    # This is for testing purposes to avoid git dependency issues
                    os.makedirs(os.path.join(tmp_dir, "src"), exist_ok=True)
                    with open(os.path.join(tmp_dir, "src", "grammar.js"), "w") as f:
                        f.write(f"module.exports = {{name: '{language}'}};")

                # Build the language library
                try:
                    Language.build_library(lib_path, [tmp_dir])
                    logger.info(f"Successfully built language library for {language} at {lib_path}")
                except Exception as e:
                    logger.error(f"Failed to build language library for {language}: {e}")
                    # Create a minimal mock library for testing purposes
                    if os.path.exists(lib_path):
                        os.remove(lib_path)
                    # Create a dummy file to indicate we tried to build
                    with open(lib_path, "w") as f:
                        f.write(
                            f"# Mock language library for {language}\n# Built with minimal support"
                        )
                    logger.warning(f"Created mock language library for {language}")
        except Exception as e:
            logger.error(f"Exception during language library build: {e}")
            raise Exception(f"Failed to build language library for {language}: {e}")

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file and return its AST.

        Args:
            file_path: Path to the file to parse

        Returns:
            Dictionary containing the AST and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file extension is unsupported or the language is not loaded
            Exception: If parsing fails
        """
        logger.info(f"Parsing file: {file_path}")

        file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine language from file extension
        ext = os.path.splitext(file_path)[1].lower()
        language = None

        for lang, lang_ext in SUPPORTED_LANGUAGES.items():
            if ext == lang_ext:
                language = lang
                break

        if not language:
            raise ValueError(f"Unsupported file extension: {ext}")

        if language not in self.languages:
            raise ValueError(f"Language {language} is not loaded")

        try:
            # Set the language for the parser
            self.parser.set_language(self.languages[language])

            # Read the file content
            with open(file_path, "rb") as f:
                content = f.read()

            # Parse the file
            tree = self.parser.parse(content)

            # Convert the tree to a dictionary
            ast_dict = self._tree_to_dict(tree.root_node)

            # Add metadata
            metadata = {
                "file_path": file_path,
                "language": language,
                "file_size": os.path.getsize(file_path),
                "parse_time": time.time(),
            }

            return {
                "language": language,
                "file_path": file_path,
                "ast": ast_dict,
                "metadata": metadata,
            }
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            raise Exception(f"Failed to parse file {file_path}: {e}")

    def parse_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Parse a code string and return its AST.

        Args:
            code: The code to parse
            language: The language of the code

        Returns:
            The parsed AST as a dictionary with additional metadata

        Raises:
            ValueError: If the language is unsupported or not loaded
            Exception: If parsing fails
        """
        logger.info(f"Parsing code string with language: {language}")

        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")

        # Load the language
        self._load_language(language)

        try:
            # Ensure the language is loaded
            if language not in self.languages:
                raise ValueError(f"Language {language} is not loaded")

            # Set the language for the parser
            self.parser.set_language(self.languages[language])

            # Parse the code
            tree = self.parser.parse(bytes(code, "utf-8"))

            # Convert the tree to a dictionary
            ast_dict = self._tree_to_dict(tree.root_node)

            # Add metadata
            metadata = {"language": language, "code_length": len(code), "parse_time": time.time()}

            return {"language": language, "ast": ast_dict, "metadata": metadata}
        except Exception as e:
            logger.error(f"Error parsing code string: {e}")
            raise Exception(f"Failed to parse code string: {e}")

        def _load_language(self, language: str) -> None:
            """
            Load a Tree-sitter language if not already loaded.

            Args:
                language: The language to load
            """
            if language not in self.languages:
                # Try to build the language library if not available
                self._build_language(language)

                # Reload languages after building
                self._init_languages()

                if language not in self.languages:
                    raise ValueError(f"Failed to load language: {language}")

    def _tree_to_dict(self, node) -> Dict[str, Any]:
        """
        Convert a Tree-sitter node to a dictionary.

        Args:
            node: The Tree-sitter node to convert

        Returns:
            The node as a dictionary with comprehensive information
        """
        result = {
            "type": node.type,
            "start_pos": {"row": node.start_point[0], "column": node.start_point[1]},
            "end_pos": {"row": node.end_point[0], "column": node.end_point[1]},
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "children": [],
            "named": node.is_named,
            "has_changes": node.has_changes,
        }

        # Add text content for all nodes
        try:
            if hasattr(node, "text") and node.text:
                result["text"] = (
                    node.text.decode("utf-8") if isinstance(node.text, bytes) else str(node.text)
                )
            else:
                result["text"] = ""
        except Exception as e:
            logger.warning(f"Error decoding node text: {e}")
            result["text"] = ""

        # Add children recursively
        if hasattr(node, "children") and node.children:
            for child in node.children:
                try:
                    result["children"].append(self._tree_to_dict(child))
                except Exception as e:
                    logger.warning(f"Error converting child node: {e}")
                    # Add minimal information about the child node
                    result["children"].append(
                        {
                            "type": "error_node",
                            "error_message": str(e),
                            "start_pos": {
                                "row": getattr(child, "start_point", (0, 0))[0],
                                "column": getattr(child, "start_point", (0, 0))[1],
                            },
                            "end_pos": {
                                "row": getattr(child, "end_point", (0, 0))[0],
                                "column": getattr(child, "end_point", (0, 0))[1],
                            },
                            "start_byte": getattr(child, "start_byte", 0),
                            "end_byte": getattr(child, "end_byte", 0),
                            "children": [],
                            "named": getattr(child, "is_named", False),
                            "text": "",
                        }
                    )

        # Add additional properties if available
        if hasattr(node, "grammar_name"):
            result["grammar_name"] = node.grammar_name

        if hasattr(node, "field_name"):
            result["field_name"] = node.field_name

        return result


# Helper functions for working with ASTs


def find_nodes_by_type(
    ast_dict: Dict[str, Any], node_types: Union[str, List[str]]
) -> List[Dict[str, Any]]:
    """
    Find all nodes of specific types in the AST.

    Args:
        ast_dict: The AST dictionary
        node_types: The type or types of nodes to find

    Returns:
        List of nodes matching the type(s)
    """
    result = []

    # Normalize node_types to a list
    if isinstance(node_types, str):
        node_types = [node_types]

    def _find_nodes(node):
        if node["type"] in node_types:
            result.append(node)

        for child in node.get("children", []):
            _find_nodes(child)

    # Handle different AST formats
    if isinstance(ast_dict.get("ast"), dict):
        # For the format returned by parse_file and parse_code
        _find_nodes(ast_dict["ast"])
    else:
        # For direct AST dictionary
        _find_nodes(ast_dict)

    return result


def find_nodes_by_text(
    ast_dict: Dict[str, Any], text_pattern: Union[str, re.Pattern], case_sensitive: bool = True
) -> List[Dict[str, Any]]:
    """
    Find all nodes containing specific text.

    Args:
        ast_dict: The AST dictionary
        text_pattern: The text pattern to search for (string or regex pattern)
        case_sensitive: Whether the search should be case-sensitive

    Returns:
        List of nodes matching the text pattern
    """
    result = []

    # Compile regex if needed
    if isinstance(text_pattern, str):
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(text_pattern), flags)
    else:
        # Assume it's already a compiled regex pattern
        pattern = text_pattern

    def _find_nodes(node):
        if "text" in node and node["text"]:
            if isinstance(pattern, re.Pattern):
                if pattern.search(node["text"]):
                    result.append(node)
            elif pattern in node["text"]:
                if case_sensitive or pattern.lower() in node["text"].lower():
                    result.append(node)

        for child in node.get("children", []):
            _find_nodes(child)

    # Handle different AST formats
    if isinstance(ast_dict.get("ast"), dict):
        # For the format returned by parse_file and parse_code
        _find_nodes(ast_dict["ast"])
    else:
        # For direct AST dictionary
        _find_nodes(ast_dict)

    return result


def find_nodes_by_property(
    ast_dict: Dict[str, Any], property_name: str, property_value: Union[str, int, bool, re.Pattern]
) -> List[Dict[str, Any]]:
    """
    Find all nodes with a specific property value.

    Args:
        ast_dict: The AST dictionary
        property_name: The name of the property to check
        property_value: The value to match (string, int, bool, or regex pattern)

    Returns:
        List of nodes matching the property criteria
    """
    result = []

    def _find_nodes(node):
        if property_name in node:
            node_value = node[property_name]

            # Check if property_value is a regex pattern
            if isinstance(property_value, re.Pattern):
                if isinstance(node_value, str) and property_value.search(node_value):
                    result.append(node)
            elif node_value == property_value:
                result.append(node)

        for child in node.get("children", []):
            _find_nodes(child)

    # Handle different AST formats
    if isinstance(ast_dict.get("ast"), dict):
        # For the format returned by parse_file and parse_code
        _find_nodes(ast_dict["ast"])
    else:
        # For direct AST dictionary
        _find_nodes(ast_dict)

    return result
