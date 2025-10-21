"""
File Context Extraction
Reads and analyzes files for AI context.
"""

import os
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class FileInfo:
    """Information about a file"""
    path: str
    name: str
    extension: str
    language: str
    size_bytes: int
    line_count: int
    content: str


class FileContext:
    """Extract context from files"""
    
    # Language detection by extension
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.md': 'markdown',
        '.txt': 'text',
        '.sql': 'sql',
        '.r': 'r',
        '.m': 'matlab',
        '.vim': 'vim',
        '.lua': 'lua',
        '.pl': 'perl',
        '.asm': 'assembly',
    }
    
    def __init__(self, workspace: Optional[str] = None):
        """
        Initialize file context extractor.
        
        Args:
            workspace: Workspace directory (default: current directory)
        """
        self.workspace = workspace or os.getcwd()
    
    def read_file(self, file_path: str, max_lines: Optional[int] = None) -> FileInfo:
        """
        Read a file and extract context.
        
        Args:
            file_path: Path to file (relative or absolute)
            max_lines: Maximum lines to read (None = all)
            
        Returns:
            FileInfo object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If file is binary
        """
        # Make path absolute
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.workspace, file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = ''.join(lines)
            else:
                content = f.read()
        
        # Get file info
        path_obj = Path(file_path)
        extension = path_obj.suffix
        language = self.LANGUAGE_MAP.get(extension.lower(), 'unknown')
        
        return FileInfo(
            path=str(path_obj),
            name=path_obj.name,
            extension=extension,
            language=language,
            size_bytes=os.path.getsize(file_path),
            line_count=content.count('\n') + 1,
            content=content
        )
    
    def read_multiple_files(
        self,
        file_paths: List[str],
        max_lines_per_file: Optional[int] = None
    ) -> List[FileInfo]:
        """
        Read multiple files.
        
        Args:
            file_paths: List of file paths
            max_lines_per_file: Max lines per file
            
        Returns:
            List of FileInfo objects
        """
        files = []
        for path in file_paths:
            try:
                files.append(self.read_file(path, max_lines_per_file))
            except (FileNotFoundError, UnicodeDecodeError) as e:
                # Skip files that can't be read
                continue
        return files
    
    def find_files(
        self,
        pattern: str = "*",
        exclude_dirs: Optional[List[str]] = None
    ) -> List[str]:
        """
        Find files matching pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.py", "src/**/*.js")
            exclude_dirs: Directories to exclude
            
        Returns:
            List of file paths
        """
        exclude_dirs = exclude_dirs or [
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'dist', 'build', '.next', '.cache', 'coverage'
        ]
        
        workspace_path = Path(self.workspace)
        files = []
        
        for file_path in workspace_path.rglob(pattern):
            if file_path.is_file():
                # Check if file is in excluded directory
                skip = False
                for exclude in exclude_dirs:
                    if exclude in file_path.parts:
                        skip = True
                        break
                
                if not skip:
                    files.append(str(file_path.relative_to(workspace_path)))
        
        return files
    
    def get_file_structure(self, file_path: str) -> Dict:
        """
        Analyze file structure (functions, classes, imports).
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with structure info
        """
        file_info = self.read_file(file_path)
        
        structure = {
            'language': file_info.language,
            'line_count': file_info.line_count,
            'functions': [],
            'classes': [],
            'imports': []
        }
        
        # Simple pattern matching for Python
        if file_info.language == 'python':
            for line in file_info.content.split('\n'):
                line = line.strip()
                
                if line.startswith('def '):
                    # Extract function name
                    func_name = line[4:].split('(')[0]
                    structure['functions'].append(func_name)
                
                elif line.startswith('class '):
                    # Extract class name
                    class_name = line[6:].split('(')[0].split(':')[0]
                    structure['classes'].append(class_name)
                
                elif line.startswith('import ') or line.startswith('from '):
                    structure['imports'].append(line)
        
        # Simple pattern matching for JavaScript/TypeScript
        elif file_info.language in ['javascript', 'typescript']:
            for line in file_info.content.split('\n'):
                line = line.strip()
                
                if 'function ' in line or '=>' in line:
                    structure['functions'].append(line[:50])
                
                elif line.startswith('class '):
                    class_name = line[6:].split('{')[0].strip()
                    structure['classes'].append(class_name)
                
                elif line.startswith('import '):
                    structure['imports'].append(line)
        
        return structure
    
    def get_related_files(self, file_path: str, max_files: int = 5) -> List[str]:
        """
        Find files related to the given file.
        
        Args:
            file_path: Path to file
            max_files: Maximum number of related files to return
            
        Returns:
            List of related file paths
        """
        file_info = self.read_file(file_path)
        related = []
        
        # Find files in the same directory
        dir_path = Path(file_path).parent
        same_dir_files = list(Path(self.workspace).joinpath(dir_path).glob(f"*{file_info.extension}"))
        
        for related_file in same_dir_files[:max_files]:
            if related_file.name != file_info.name:
                related.append(str(related_file.relative_to(self.workspace)))
        
        return related
