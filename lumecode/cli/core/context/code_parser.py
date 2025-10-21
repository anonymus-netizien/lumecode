"""
Code Parser
Extract code elements for analysis.
"""

import ast
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, etc.)"""
    name: str
    type: str  # 'function', 'class', 'method', 'import'
    start_line: int
    end_line: int
    code: str
    docstring: Optional[str] = None


class CodeParser:
    """Parse and extract code elements"""
    
    def __init__(self, language: str = "python"):
        """
        Initialize code parser.
        
        Args:
            language: Programming language (only python fully supported for now)
        """
        self.language = language.lower()
    
    def extract_lines(self, content: str, start: int, end: int) -> str:
        """
        Extract specific line range.
        
        Args:
            content: Source code
            start: Start line (1-indexed)
            end: End line (1-indexed, inclusive)
            
        Returns:
            Extracted code
        """
        lines = content.split('\n')
        # Convert to 0-indexed
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        return '\n'.join(lines[start_idx:end_idx])
    
    def extract_function(self, content: str, function_name: str) -> Optional[CodeSymbol]:
        """
        Extract function code by name (Python only).
        
        Args:
            content: Source code
            function_name: Name of function to extract
            
        Returns:
            CodeSymbol if found, None otherwise
        """
        if self.language != "python":
            return None
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Get line numbers
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    
                    # Extract code
                    code = self.extract_lines(content, start_line, end_line)
                    
                    # Get docstring
                    docstring = ast.get_docstring(node)
                    
                    return CodeSymbol(
                        name=function_name,
                        type='function',
                        start_line=start_line,
                        end_line=end_line,
                        code=code,
                        docstring=docstring
                    )
        
        except SyntaxError:
            pass
        
        return None
    
    def extract_class(self, content: str, class_name: str) -> Optional[CodeSymbol]:
        """
        Extract class code by name (Python only).
        
        Args:
            content: Source code
            class_name: Name of class to extract
            
        Returns:
            CodeSymbol if found, None otherwise
        """
        if self.language != "python":
            return None
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Get line numbers
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    
                    # Extract code
                    code = self.extract_lines(content, start_line, end_line)
                    
                    # Get docstring
                    docstring = ast.get_docstring(node)
                    
                    return CodeSymbol(
                        name=class_name,
                        type='class',
                        start_line=start_line,
                        end_line=end_line,
                        code=code,
                        docstring=docstring
                    )
        
        except SyntaxError:
            pass
        
        return None
    
    def list_symbols(self, content: str) -> Dict[str, List[CodeSymbol]]:
        """
        List all symbols (functions, classes, imports) in code.
        
        Args:
            content: Source code
            
        Returns:
            Dict with 'functions', 'classes', 'imports' keys
        """
        symbols = {
            'functions': [],
            'classes': [],
            'imports': []
        }
        
        if self.language != "python":
            return symbols
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Functions
                if isinstance(node, ast.FunctionDef):
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    code = self.extract_lines(content, start_line, end_line)
                    docstring = ast.get_docstring(node)
                    
                    symbols['functions'].append(CodeSymbol(
                        name=node.name,
                        type='function',
                        start_line=start_line,
                        end_line=end_line,
                        code=code,
                        docstring=docstring
                    ))
                
                # Classes
                elif isinstance(node, ast.ClassDef):
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    code = self.extract_lines(content, start_line, end_line)
                    docstring = ast.get_docstring(node)
                    
                    symbols['classes'].append(CodeSymbol(
                        name=node.name,
                        type='class',
                        start_line=start_line,
                        end_line=end_line,
                        code=code,
                        docstring=docstring
                    ))
                
                # Imports
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    code = self.extract_lines(content, start_line, end_line)
                    
                    # Get import names
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                        name = ', '.join(names)
                    else:  # ImportFrom
                        module = node.module or ''
                        names = [alias.name for alias in node.names]
                        name = f"from {module} import {', '.join(names)}"
                    
                    symbols['imports'].append(CodeSymbol(
                        name=name,
                        type='import',
                        start_line=start_line,
                        end_line=end_line,
                        code=code
                    ))
        
        except SyntaxError:
            pass
        
        return symbols
    
    def parse_line_range(self, line_range: str) -> Optional[Tuple[int, int]]:
        """
        Parse line range string (e.g., "10-50" or "10:50").
        
        Args:
            line_range: Line range string
            
        Returns:
            Tuple of (start, end) or None if invalid
        """
        # Try different formats
        patterns = [
            r'(\d+)-(\d+)',  # 10-50
            r'(\d+):(\d+)',  # 10:50
            r'(\d+)\.\.(\d+)',  # 10..50
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line_range.strip())
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                return (start, end)
        
        return None
