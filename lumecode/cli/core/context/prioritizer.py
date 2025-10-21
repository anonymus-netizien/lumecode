"""File prioritization utilities for context management.

This module provides utilities for prioritizing files based on various factors
like modification time, file size, and file type.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def prioritize_files(
    files: List[Path], query: Optional[str] = None, max_file_size: int = 10 * 1024 * 1024  # 10MB
) -> List[Path]:
    """Prioritize files based on multiple factors.

    Scoring factors:
    - Recently modified (40%)
    - File size (30% - smaller is better)
    - File type (20% - .py > .txt > .md > others)
    - Query relevance (10% - future feature)

    Args:
        files: List of file paths to prioritize
        query: Optional query string for relevance scoring
        max_file_size: Maximum file size to consider (skip larger files)

    Returns:
        Sorted list of files (highest priority first)

    Example:
        >>> files = [Path('old.py'), Path('new.py')]
        >>> prioritize_files(files)
        [Path('new.py'), Path('old.py')]
    """
    if not files:
        return []

    # Filter out files that are too large or don't exist
    valid_files = [f for f in files if f.exists() and f.stat().st_size <= max_file_size]

    if not valid_files:
        return []

    # Calculate scores for each file
    scored_files = []
    for file_path in valid_files:
        score = calculate_priority_score(file_path, query)
        scored_files.append((score, file_path))

    # Sort by score (highest first)
    scored_files.sort(reverse=True, key=lambda x: x[0])

    return [f for _, f in scored_files]


def calculate_priority_score(file_path: Path, query: Optional[str] = None) -> float:
    """Calculate priority score for a file.

    Args:
        file_path: Path to the file
        query: Optional query string for relevance

    Returns:
        Priority score (0.0 to 1.0, higher is better)

    Example:
        >>> calculate_priority_score(Path('test.py'))
        0.85
    """
    if not file_path.exists():
        return 0.0

    # Component scores
    recency_score = _calculate_recency_score(file_path)
    size_score = _calculate_size_score(file_path)
    type_score = _calculate_type_score(file_path)
    relevance_score = _calculate_relevance_score(file_path, query) if query else 0.5

    # Weighted combination
    total_score = (
        recency_score * 0.4  # 40% weight
        + size_score * 0.3  # 30% weight
        + type_score * 0.2  # 20% weight
        + relevance_score * 0.1  # 10% weight
    )

    return total_score


def _calculate_recency_score(file_path: Path) -> float:
    """Calculate recency score based on modification time.

    More recently modified files get higher scores.
    Uses exponential decay: score = e^(-days/30)

    Args:
        file_path: Path to the file

    Returns:
        Score from 0.0 to 1.0
    """
    try:
        mtime = file_path.stat().st_mtime
        current_time = time.time()

        # Days since modification
        days_ago = (current_time - mtime) / (24 * 3600)

        # Exponential decay (half-life of 7 days)
        import math

        score = math.exp(-days_ago / 7)

        return min(1.0, max(0.0, score))
    except Exception:
        return 0.5  # Default if can't determine


def _calculate_size_score(file_path: Path) -> float:
    """Calculate size score (smaller files are better).

    Smaller files are easier to fit in context window.

    Args:
        file_path: Path to the file

    Returns:
        Score from 0.0 to 1.0
    """
    try:
        size_bytes = file_path.stat().st_size

        # Optimal size: < 10KB
        optimal_size = 10 * 1024

        if size_bytes <= optimal_size:
            return 1.0

        # Decay for larger files
        # 100KB -> 0.5, 1MB -> 0.1
        import math

        score = optimal_size / size_bytes
        return min(1.0, max(0.0, score))
    except Exception:
        return 0.5


def _calculate_type_score(file_path: Path) -> float:
    """Calculate type score based on file extension.

    Python files are most relevant, followed by common text formats.

    Args:
        file_path: Path to the file

    Returns:
        Score from 0.0 to 1.0
    """
    ext = file_path.suffix.lower()

    # Priority by file type
    type_scores = {
        # Code files (high priority)
        ".py": 1.0,
        ".pyx": 0.95,
        ".pyi": 0.9,
        # Documentation (medium-high)
        ".md": 0.8,
        ".rst": 0.75,
        ".txt": 0.7,
        # Config files (medium)
        ".yml": 0.6,
        ".yaml": 0.6,
        ".toml": 0.6,
        ".json": 0.6,
        ".ini": 0.55,
        ".cfg": 0.55,
        # Other code (medium-low)
        ".js": 0.5,
        ".ts": 0.5,
        ".java": 0.5,
        ".cpp": 0.5,
        ".c": 0.5,
        # Data files (low)
        ".csv": 0.3,
        ".xml": 0.3,
        ".html": 0.3,
        # Binary/other (very low)
        ".log": 0.2,
    }

    return type_scores.get(ext, 0.4)  # Default for unknown types


def _calculate_relevance_score(file_path: Path, query: Optional[str]) -> float:
    """Calculate relevance score based on query match.

    Future enhancement: Could use semantic similarity, keyword matching, etc.
    Currently: Simple filename/path matching.

    Args:
        file_path: Path to the file
        query: Query string

    Returns:
        Score from 0.0 to 1.0
    """
    if not query:
        return 0.5  # Neutral score if no query

    query_lower = query.lower()
    file_str = str(file_path).lower()
    file_name = file_path.name.lower()

    # Check for direct matches
    if query_lower in file_name:
        return 1.0

    if query_lower in file_str:
        return 0.8

    # Check for partial word matches
    query_words = set(query_lower.split())
    file_words = set(file_name.replace("_", " ").replace("-", " ").split())

    if query_words & file_words:  # Intersection
        overlap = len(query_words & file_words) / len(query_words)
        return 0.5 + (overlap * 0.3)  # 0.5 to 0.8

    return 0.3  # Default low relevance


def filter_files_by_pattern(
    files: List[Path],
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[Path]:
    """Filter files by glob patterns.

    Args:
        files: List of file paths
        include_patterns: Patterns to include (e.g., ['*.py', '*.md'])
        exclude_patterns: Patterns to exclude (e.g., ['*test*', '*__pycache__*'])

    Returns:
        Filtered list of files

    Example:
        >>> filter_files_by_pattern(files, include_patterns=['*.py'])
        [Path('main.py'), Path('utils.py')]
    """
    filtered = list(files)

    # Apply include patterns
    if include_patterns:
        included = []
        for pattern in include_patterns:
            for file_path in filtered:
                if file_path.match(pattern):
                    included.append(file_path)
        filtered = included

    # Apply exclude patterns
    if exclude_patterns:
        for pattern in exclude_patterns:
            filtered = [f for f in filtered if not f.match(pattern)]

    return filtered


def get_file_summary(file_path: Path) -> dict:
    """Get summary information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dict with file metadata

    Example:
        >>> get_file_summary(Path('test.py'))
        {
            'name': 'test.py',
            'size': 1234,
            'modified': '2025-10-17T10:30:00',
            'type': '.py'
        }
    """
    if not file_path.exists():
        return {"name": file_path.name, "exists": False}

    stat = file_path.stat()

    return {
        "name": file_path.name,
        "path": str(file_path),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "type": file_path.suffix,
        "exists": True,
        "priority_score": calculate_priority_score(file_path),
    }
