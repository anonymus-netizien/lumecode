"""
Prompt Context Builder
Combines file and git context into prompts.
"""

from typing import List, Optional

from ..context import FileContext, FileInfo, GitContext, GitStatus


class PromptContext:
    """Build context-aware prompts"""

    def __init__(self, workspace: Optional[str] = None):
        """
        Initialize prompt context builder.

        Args:
            workspace: Workspace directory
        """
        self.git = GitContext(workspace)
        self.files = FileContext(workspace)

    def build_file_context(self, file_paths: List[str], max_lines_per_file: int = 100) -> str:
        """
        Build file context string.

        Args:
            file_paths: List of file paths
            max_lines_per_file: Max lines to include per file

        Returns:
            Formatted context string
        """
        if not file_paths:
            return ""

        files = self.files.read_multiple_files(file_paths, max_lines_per_file)

        context = ""
        for file in files:
            context += f"**{file.path}** ({file.language}, {file.line_count} lines):\n"
            context += f"```{file.language}\n"
            context += file.content
            context += "\n```\n\n"

        return context

    def build_git_context(
        self,
        include_diff: bool = True,
        include_status: bool = True,
        include_commits: int = 0,
        max_diff_size: int = 10000,  # Limit diff to ~10K chars
    ) -> str:
        """
        Build git context string.

        Args:
            include_diff: Include current diff
            include_status: Include git status
            include_commits: Number of recent commits to include
            max_diff_size: Maximum characters for diff (default 10K)

        Returns:
            Formatted context string
        """
        if not self.git.is_git_repo():
            return ""

        context = ""

        if include_status:
            status = self.git.get_status()
            if status.staged or status.unstaged or status.untracked:
                context += "**Git Status:**\n"
                if status.staged:
                    context += f"  Staged: {', '.join(status.staged)}\n"
                if status.unstaged:
                    context += f"  Unstaged: {', '.join(status.unstaged)}\n"
                if status.untracked:
                    context += f"  Untracked: {', '.join(status.untracked)}\n"
                context += "\n"

        if include_diff:
            diff = self.git.get_current_diff(staged=False)
            if diff:
                # Truncate if too large
                if len(diff) > max_diff_size:
                    diff = diff[:max_diff_size]
                    diff += f"\n... (diff truncated, showing first {max_diff_size:,} chars)"

                context += "**Current Changes:**\n"
                context += f"```diff\n{diff}\n```\n\n"

        if include_commits > 0:
            commits = self.git.get_recent_commits(include_commits)
            if commits:
                context += "**Recent Commits:**\n"
                for commit in commits:
                    context += f"  - {commit.hash[:7]}: {commit.message}\n"
                context += "\n"

        return context

    def build_combined_context(
        self,
        file_paths: Optional[List[str]] = None,
        include_git: bool = True,
        max_lines_per_file: int = 100,
    ) -> str:
        """
        Build combined file and git context.

        Args:
            file_paths: Files to include
            include_git: Include git context
            max_lines_per_file: Max lines per file

        Returns:
            Combined context string
        """
        context = ""

        if file_paths:
            file_ctx = self.build_file_context(file_paths, max_lines_per_file)
            if file_ctx:
                context += file_ctx

        if include_git:
            git_ctx = self.build_git_context(
                include_diff=True, include_status=True, include_commits=3
            )
            if git_ctx:
                context += git_ctx

        return context
