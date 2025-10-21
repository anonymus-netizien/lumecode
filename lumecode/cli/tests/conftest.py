from hypothesis import settings

# Disable Hypothesis deadlines globally for CLI tests; CLI + Click runner can be slower
settings.register_profile("ci", deadline=None)
settings.load_profile("ci")
"""
Shared pytest fixtures for Lumecode CLI tests.
Advanced fixtures for comprehensive testing.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# BASIC FIXTURES
# ============================================================================


@pytest.fixture
def runner():
    """Create Click CLI test runner with isolated filesystem."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def isolated_cli(runner):
    """CLI runner with completely isolated filesystem."""
    with runner.isolated_filesystem():
        yield runner


# ============================================================================
# GIT FIXTURES
# ============================================================================


@pytest.fixture
def git_repo(temp_dir):
    """Create a git repository for testing."""
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path)

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=repo_path)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path)

    return repo_path


@pytest.fixture
def git_repo_with_changes(git_repo):
    """Git repo with uncommitted changes."""
    # Add new file
    (git_repo / "new_file.py").write_text("def new_function(): pass")

    # Modify existing file
    (git_repo / "README.md").write_text("# Updated Project\n\nNew content")

    # Stage one file
    subprocess.run(["git", "add", "new_file.py"], cwd=git_repo)

    return git_repo


@pytest.fixture
def git_repo_with_branches(git_repo):
    """Git repo with multiple branches."""
    # Create feature branch
    subprocess.run(["git", "checkout", "-b", "feature/test"], cwd=git_repo)
    (git_repo / "feature.py").write_text("def feature(): pass")
    subprocess.run(["git", "add", "."], cwd=git_repo)
    subprocess.run(["git", "commit", "-m", "Add feature"], cwd=git_repo)

    # Back to main
    subprocess.run(["git", "checkout", "main"], cwd=git_repo)

    return git_repo


# ============================================================================
# FILE FIXTURES
# ============================================================================


@pytest.fixture
def sample_python_file(temp_dir):
    """Create sample Python file for testing."""
    file = temp_dir / "sample.py"
    file.write_text(
        '''
def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b

class Calculator:
    """Simple calculator class."""
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
'''
    )
    return file


@pytest.fixture
def complex_python_file(temp_dir):
    """Create complex Python file with various constructs."""
    file = temp_dir / "complex.py"
    file.write_text(
        '''
import os
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class User:
    """User model."""
    name: str
    email: str
    age: int = 0
    
    def is_adult(self) -> bool:
        """Check if user is adult."""
        return self.age >= 18
    
    def validate_email(self) -> bool:
        """Validate email format."""
        return "@" in self.email and "." in self.email

class UserManager:
    """Manage users."""
    
    def __init__(self):
        self.users: List[User] = []
    
    def add_user(self, user: User) -> None:
        """Add user to list."""
        if not user.validate_email():
            raise ValueError("Invalid email")
        self.users.append(user)
    
    def get_adults(self) -> List[User]:
        """Get all adult users."""
        return [u for u in self.users if u.is_adult()]
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        for user in self.users:
            if user.email == email:
                return user
        return None

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process data with error handling."""
    try:
        result = {
            "status": "success",
            "data": data.get("items", []),
            "count": len(data.get("items", []))
        }
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
'''
    )
    return file


@pytest.fixture
def buggy_python_file(temp_dir):
    """Create Python file with common bugs."""
    file = temp_dir / "buggy.py"
    file.write_text(
        '''
def divide(a, b):
    """Divide without zero check."""
    return a / b  # Bug: no zero check

def unsafe_dict_access(data):
    """Access dict without checking."""
    return data["key"]  # Bug: KeyError possible

def unused_variable():
    """Function with unused variable."""
    x = 10  # Bug: unused variable
    return 5

def infinite_loop():
    """Potential infinite loop."""
    while True:  # Bug: no break condition
        pass
'''
    )
    return file


@pytest.fixture
def sample_project(temp_dir):
    """Create realistic project structure."""
    project = temp_dir / "project"
    project.mkdir()

    # Create src directory
    src = project / "src"
    src.mkdir()

    # Create main module
    (src / "__init__.py").write_text("")
    (src / "main.py").write_text(
        """
import sys
from .utils import helper

def main():
    \"\"\"Main entry point.\"\"\"
    result = helper()
    print(f"Result: {result}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
    )

    (src / "utils.py").write_text(
        """
from typing import List, Dict

def helper() -> str:
    \"\"\"Helper function.\"\"\"
    return "Hello from helper"

def process_list(items: List[int]) -> int:
    \"\"\"Process list of items.\"\"\"
    return sum(items)

def parse_config(config: Dict) -> Dict:
    \"\"\"Parse configuration.\"\"\"
    return {
        "debug": config.get("debug", False),
        "port": config.get("port", 8000)
    }
"""
    )

    # Create tests directory
    tests = project / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")
    (tests / "test_main.py").write_text(
        """
import pytest
from src.main import main

def test_main():
    \"\"\"Test main function.\"\"\"
    assert main() == 0
"""
    )

    # Create config files
    (project / "requirements.txt").write_text("pytest>=7.0.0\nclick>=8.0.0\n")
    (project / "setup.py").write_text("from setuptools import setup\nsetup(name='test-project')")
    (project / "README.md").write_text("# Test Project\n\nA sample project for testing.")

    return project


# ============================================================================
# MOCK LLM FIXTURES
# ============================================================================


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    return {
        "content": "This is a mock AI response.",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "model": "mock-model",
        "provider": "mock",
    }


@pytest.fixture
def mock_provider():
    """Mock LLM provider."""
    provider = MagicMock()
    provider.name = "mock"
    provider.generate.return_value = "Mock AI response"
    provider.stream.return_value = iter(["Mock ", "streaming ", "response"])
    provider.is_available.return_value = True
    return provider


@pytest.fixture
def mock_groq_provider(mock_provider):
    """Mock Groq provider specifically."""
    mock_provider.name = "groq"
    return mock_provider


@pytest.fixture
def mock_openrouter_provider(mock_provider):
    """Mock OpenRouter provider."""
    mock_provider.name = "openrouter"
    return mock_provider


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment without API keys."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LUMECODE_CACHE_DIR", raising=False)
    return monkeypatch


@pytest.fixture
def mock_env_with_keys(monkeypatch):
    """Environment with mock API keys."""
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_123")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_openrouter_key_456")
    return monkeypatch


@pytest.fixture
def temp_cache_dir(temp_dir, monkeypatch):
    """Temporary cache directory."""
    cache_dir = temp_dir / ".lumecode_cache"
    cache_dir.mkdir()
    monkeypatch.setenv("LUMECODE_CACHE_DIR", str(cache_dir))
    return cache_dir


# ============================================================================
# CONFIG FIXTURES
# ============================================================================


@pytest.fixture
def sample_config(temp_dir):
    """Sample configuration file."""
    config_path = temp_dir / "lumecode.json"
    config = {
        "provider": "groq",
        "model": "llama-3.1-70b-versatile",
        "cache_enabled": True,
        "streaming": True,
        "verbose": False,
    }
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def config_with_invalid_data(temp_dir):
    """Config file with invalid data."""
    config_path = temp_dir / "invalid_lumecode.json"
    config_path.write_text("{ invalid json ")
    return config_path


# ============================================================================
# PARAMETRIZATION DATA
# ============================================================================


@pytest.fixture
def provider_list():
    """List of providers for parametrized tests."""
    return ["groq", "openrouter", "mock"]


@pytest.fixture
def severity_levels():
    """Severity levels for review tests."""
    return ["critical", "major", "minor", "all"]


@pytest.fixture
def file_extensions():
    """Common file extensions for testing."""
    return [".py", ".js", ".ts", ".java", ".go", ".rs"]


# ============================================================================
# SUBPROCESS MOCKS
# ============================================================================


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess call."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = b"Success output"
    mock.stderr = b""
    return mock


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess call."""
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = b""
    mock.stderr = b"Error: Command failed"
    return mock


# ============================================================================
# AUTO-USE FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Add singleton resets here if needed
    yield


@pytest.fixture(autouse=True)
def capture_warnings():
    """Capture warnings during tests."""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        yield w
