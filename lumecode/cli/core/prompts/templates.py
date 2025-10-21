"""
Prompt Templates
Pre-built prompts for different AI tasks.
"""

from typing import Dict, List, Optional


class PromptTemplates:
    """Collection of prompt templates for various tasks"""

    @staticmethod
    def ask_about_code(
        question: str, file_context: Optional[str] = None, git_context: Optional[str] = None
    ) -> str:
        """
        Generate prompt for asking questions about code.

        Args:
            question: User's question
            file_context: Code files context
            git_context: Git changes context

        Returns:
            Formatted prompt
        """
        prompt = f"You are a helpful coding assistant. Answer the user's question about their codebase.\n\n"

        if file_context:
            prompt += f"**Code Context:**\n```\n{file_context}\n```\n\n"

        if git_context:
            prompt += f"**Git Changes:**\n```\n{git_context}\n```\n\n"

        prompt += f"**Question:** {question}\n\n"
        prompt += "Provide a clear, concise answer. Use code examples if helpful."

        return prompt

    @staticmethod
    def generate_commit_message(
        diff: str, staged_files: List[str], conventional: bool = True
    ) -> str:
        """
        Generate prompt for commit message generation.

        Args:
            diff: Git diff text
            staged_files: List of staged files
            conventional: Use conventional commits format

        Returns:
            Formatted prompt
        """
        prompt = "Generate a commit message for the following changes.\n\n"

        if conventional:
            prompt += "**Format:** Use Conventional Commits format (feat:, fix:, docs:, etc.)\n\n"

        prompt += f"**Staged files:**\n"
        for file in staged_files:
            prompt += f"  - {file}\n"

        prompt += f"\n**Changes:**\n```diff\n{diff}\n```\n\n"

        if conventional:
            prompt += "**Instructions:**\n"
            prompt += "1. Start with type (feat/fix/docs/style/refactor/test/chore)\n"
            prompt += "2. Brief summary (50 chars max)\n"
            prompt += "3. Optional body explaining what and why\n"
            prompt += "4. One commit message, no alternatives\n\n"
            prompt += "Generate ONLY the commit message, no explanations."
        else:
            prompt += "Generate a clear, concise commit message (50-72 chars)."

        return prompt

    @staticmethod
    def explain_code(
        code: str, file_path: Optional[str] = None, language: Optional[str] = None
    ) -> str:
        """
        Generate prompt for code explanation.

        Args:
            code: Code to explain
            file_path: Path to file
            language: Programming language

        Returns:
            Formatted prompt
        """
        prompt = "Explain the following code in detail.\n\n"

        if file_path:
            prompt += f"**File:** {file_path}\n"

        if language:
            prompt += f"**Language:** {language}\n"

        prompt += f"\n**Code:**\n```{language or ''}\n{code}\n```\n\n"
        prompt += "**Instructions:**\n"
        prompt += "1. What does this code do?\n"
        prompt += "2. How does it work?\n"
        prompt += "3. Any notable patterns or techniques?\n"
        prompt += "4. Potential improvements?\n\n"
        prompt += "Explain in clear, beginner-friendly language."

        return prompt

    @staticmethod
    def review_code(
        code: str,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        focus: Optional[List[str]] = None,
    ) -> str:
        """
        Generate prompt for code review.

        Args:
            code: Code to review
            file_path: Path to file
            language: Programming language
            focus: Specific focus areas (bugs, security, performance, style)

        Returns:
            Formatted prompt
        """
        prompt = "Review the following code and provide detailed feedback.\n\n"

        if file_path:
            prompt += f"**File:** {file_path}\n"

        if language:
            prompt += f"**Language:** {language}\n"

        prompt += f"\n**Code:**\n```{language or ''}\n{code}\n```\n\n"

        if focus:
            prompt += "**Focus on:**\n"
            focus_areas = {
                "bugs": "Bugs and potential errors",
                "security": "Security vulnerabilities and risks",
                "performance": "Performance issues and optimizations",
                "style": "Code style and readability",
                "best_practice": "Best practices and design patterns",
                "maintainability": "Maintainability and technical debt",
            }
            for area in focus:
                if area in focus_areas:
                    prompt += f"- {focus_areas[area]}\n"
            prompt += "\n"
        else:
            prompt += "**Review for:**\n"
            prompt += "1. Bugs and potential errors\n"
            prompt += "2. Code quality and best practices\n"
            prompt += "3. Performance issues\n"
            prompt += "4. Security concerns\n"
            prompt += "5. Maintainability\n\n"

        prompt += "**Instructions:**\n"
        prompt += "- Categorize issues by severity (critical, major, minor)\n"
        prompt += "- Provide specific, actionable suggestions\n"
        prompt += "- Include code examples where helpful\n"
        prompt += "- Be constructive and educational\n"

        return prompt

    @staticmethod
    def suggest_improvements(
        code: str,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        focus: Optional[str] = None,
    ) -> str:
        """
        Generate prompt for code improvement suggestions.

        Args:
            code: Code to improve
            file_path: Path to file
            language: Programming language
            focus: Specific focus area (performance, readability, etc.)

        Returns:
            Formatted prompt
        """
        prompt = "Suggest improvements for the following code.\n\n"

        if file_path:
            prompt += f"**File:** {file_path}\n"

        if language:
            prompt += f"**Language:** {language}\n"

        if focus:
            prompt += f"**Focus:** {focus}\n"

        prompt += f"\n**Code:**\n```{language or ''}\n{code}\n```\n\n"
        prompt += "**Provide:**\n"
        prompt += "1. Specific improvement suggestions\n"
        prompt += "2. Refactored code examples\n"
        prompt += "3. Explanation of why each change helps\n\n"
        prompt += "Focus on practical, high-impact improvements."

        return prompt

    @staticmethod
    def system_prompt(command_type: str = "general") -> str:
        """
        Generate system prompt for different command types.

        Args:
            command_type: Type of command (ask, commit, explain, review, refactor, etc.)

        Returns:
            System prompt
        """
        base = (
            "You are an expert programming assistant integrated into a CLI tool called Lumecode. "
        )

        prompts = {
            "ask": base
            + "You answer questions about code clearly and concisely. Focus on practical, actionable information.",
            "commit": base
            + "You generate clear, professional commit messages following best practices.",
            "explain": base
            + "You explain code in a clear, educational way suitable for developers of all levels.",
            "review": base
            + "You review code constructively, focusing on improvements and best practices.",
            "refactor": base
            + "You suggest practical refactoring improvements with clear before/after examples and reasoning. Focus on high-impact changes.",
            "test": base
            + "You generate comprehensive, production-ready unit tests with good coverage, clear naming, and best practices. Focus on edge cases and maintainability.",
            "improve": base + "You suggest practical code improvements with clear explanations.",
            "general": base + "You help developers understand and improve their code.",
        }

        return prompts.get(command_type, prompts["general"])

    @staticmethod
    def get_system_prompt(command_type: str = "general") -> str:
        """Alias for system_prompt() for backward compatibility"""
        return PromptTemplates.system_prompt(command_type)
