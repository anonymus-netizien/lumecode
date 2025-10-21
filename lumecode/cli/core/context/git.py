"""
Git Context Extraction
Extracts context from Git repository for AI analysis.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime


@dataclass
class GitDiff:
    """Represents a git diff"""

    file_path: str
    old_content: str
    new_content: str
    diff_text: str
    additions: int
    deletions: int


@dataclass
class GitCommit:
    """Represents a git commit"""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: List[str]


@dataclass
class GitStatus:
    """Represents git status"""

    staged: List[str]
    unstaged: List[str]
    untracked: List[str]


class GitContext:
    """Extract context from Git repository"""

    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize Git context extractor.

        Args:
            repo_path: Path to git repository (default: current directory)
        """
        self.repo_path = repo_path or os.getcwd()

    def _run_git(self, *args: str) -> str:
        """
        Run a git command and return output.

        Args:
            *args: Git command arguments

        Returns:
            Command output

        Raises:
            RuntimeError: If git command fails
        """
        try:
            result = subprocess.run(
                ["git", "-C", self.repo_path] + list(args),
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")

    def is_git_repo(self) -> bool:
        """Check if directory is a git repository"""
        try:
            self._run_git("rev-parse", "--git-dir")
            return True
        except RuntimeError:
            return False

    def get_current_diff(self, staged: bool = False) -> str:
        """
        Get current uncommitted changes.

        Args:
            staged: If True, get staged changes; if False, get unstaged

        Returns:
            Diff text
        """
        if staged:
            return self._run_git("diff", "--cached")
        return self._run_git("diff")

    def get_diff_files(self, staged: bool = False) -> List[GitDiff]:
        """
        Get list of changed files with their diffs.

        Args:
            staged: If True, get staged changes; if False, get unstaged

        Returns:
            List of GitDiff objects
        """
        diff_text = self.get_current_diff(staged)
        if not diff_text:
            return []

        diffs = []
        current_file = None
        current_diff = []
        additions = 0
        deletions = 0

        for line in diff_text.split("\n"):
            if line.startswith("diff --git"):
                if current_file:
                    diffs.append(
                        GitDiff(
                            file_path=current_file,
                            old_content="",
                            new_content="",
                            diff_text="\n".join(current_diff),
                            additions=additions,
                            deletions=deletions,
                        )
                    )
                # Extract file path from "diff --git a/path b/path"
                parts = line.split()
                current_file = parts[2][2:] if len(parts) > 2 else ""
                current_diff = [line]
                additions = 0
                deletions = 0
            else:
                current_diff.append(line)
                if line.startswith("+") and not line.startswith("+++"):
                    additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

        # Don't forget last file
        if current_file:
            diffs.append(
                GitDiff(
                    file_path=current_file,
                    old_content="",
                    new_content="",
                    diff_text="\n".join(current_diff),
                    additions=additions,
                    deletions=deletions,
                )
            )

        return diffs

    def get_status(self) -> GitStatus:
        """
        Get git status.

        Returns:
            GitStatus object with staged, unstaged, and untracked files
        """
        status_output = self._run_git("status", "--short")

        staged = []
        unstaged = []
        untracked = []

        for line in status_output.split("\n"):
            if not line:
                continue

            status = line[:2]
            file_path = line[3:].strip()

            # First char is staged status, second is unstaged
            if status[0] in ["A", "M", "D", "R", "C"]:
                staged.append(file_path)
            if status[1] in ["M", "D"]:
                unstaged.append(file_path)
            if status == "??":
                untracked.append(file_path)

        return GitStatus(staged=staged, unstaged=unstaged, untracked=untracked)

    def get_recent_commits(self, count: int = 5) -> List[GitCommit]:
        """
        Get recent commits.

        Args:
            count: Number of commits to retrieve

        Returns:
            List of GitCommit objects
        """
        # Format: hash|author|date|message
        log_output = self._run_git(
            "log", f"-{count}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"
        )

        commits = []
        for line in log_output.split("\n"):
            if not line:
                continue

            parts = line.split("|", 3)
            if len(parts) < 4:
                continue

            commit_hash = parts[0]

            # Get files changed in this commit
            files_output = self._run_git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash
            )
            files_changed = [f for f in files_output.split("\n") if f]

            # Parse date
            try:
                date_obj = datetime.fromisoformat(parts[2].replace(" ", "T", 1))
            except:
                date_obj = datetime.now()

            commits.append(
                GitCommit(
                    hash=commit_hash,
                    author=parts[1],
                    date=date_obj,
                    message=parts[3],
                    files_changed=files_changed,
                )
            )

        return commits

    def get_commit_diff(self, commit_hash: str) -> str:
        """
        Get diff for a specific commit.

        Args:
            commit_hash: Commit hash or reference (HEAD, HEAD~1, etc.)

        Returns:
            Diff text
        """
        return self._run_git("show", commit_hash)

    def get_file_history(self, file_path: str, count: int = 5) -> List[GitCommit]:
        """
        Get commit history for a specific file.

        Args:
            file_path: Path to file
            count: Number of commits to retrieve

        Returns:
            List of GitCommit objects
        """
        log_output = self._run_git(
            "log", f"-{count}", "--pretty=format:%H|%an|%ad|%s", "--date=iso", "--", file_path
        )

        commits = []
        for line in log_output.split("\n"):
            if not line:
                continue

            parts = line.split("|", 3)
            if len(parts) < 4:
                continue

            # Parse date
            try:
                date_obj = datetime.fromisoformat(parts[2].replace(" ", "T", 1))
            except:
                date_obj = datetime.now()

            commits.append(
                GitCommit(
                    hash=parts[0],
                    author=parts[1],
                    date=date_obj,
                    message=parts[3],
                    files_changed=[file_path],
                )
            )

        return commits

    def get_branch_name(self) -> str:
        """Get current branch name"""
        return self._run_git("rev-parse", "--abbrev-ref", "HEAD")

    def get_remote_url(self) -> Optional[str]:
        """Get remote URL if available"""
        try:
            return self._run_git("config", "--get", "remote.origin.url")
        except RuntimeError:
            return None
