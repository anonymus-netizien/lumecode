"""
Review Parser
Parse and structure code review output from LLM.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class Severity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class Category(str, Enum):
    """Issue categories"""
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"
    MAINTAINABILITY = "maintainability"


@dataclass
class ReviewIssue:
    """Represents a code review issue"""
    severity: Severity
    category: Category
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    description: str = ""
    suggestion: str = ""
    code_snippet: Optional[str] = None


class ReviewParser:
    """Parse LLM review output into structured issues"""
    
    def __init__(self):
        """Initialize review parser"""
        pass
    
    def parse_review(self, review_text: str) -> List[ReviewIssue]:
        """
        Parse LLM review into structured issues.
        
        This is a simple parser that looks for common patterns.
        In production, you might use a more sophisticated approach.
        
        Args:
            review_text: Raw review text from LLM
            
        Returns:
            List of ReviewIssue objects
        """
        issues = []
        
        # Simple pattern matching for common review formats
        # Look for severity markers
        severity_patterns = {
            Severity.CRITICAL: r'(?i)(critical|severe|dangerous|unsafe)',
            Severity.MAJOR: r'(?i)(major|important|significant)',
            Severity.MINOR: r'(?i)(minor|small|trivial)',
        }
        
        category_patterns = {
            Category.BUG: r'(?i)(bug|error|issue|problem|incorrect)',
            Category.SECURITY: r'(?i)(security|vulnerability|exploit|injection)',
            Category.PERFORMANCE: r'(?i)(performance|slow|inefficient|optimize)',
            Category.STYLE: r'(?i)(style|formatting|convention|readability)',
            Category.BEST_PRACTICE: r'(?i)(best.practice|pattern|design)',
            Category.MAINTAINABILITY: r'(?i)(maintainability|complexity|technical.debt)',
        }
        
        # Split into sections/paragraphs
        sections = review_text.split('\n\n')
        
        for section in sections:
            if not section.strip():
                continue
            
            # Detect severity
            severity = Severity.INFO
            for sev, pattern in severity_patterns.items():
                if re.search(pattern, section):
                    severity = sev
                    break
            
            # Detect category
            category = Category.BEST_PRACTICE
            for cat, pattern in category_patterns.items():
                if re.search(pattern, section):
                    category = cat
                    break
            
            # Extract file path if mentioned
            file_match = re.search(r'(?:file|in)\s+[`"]?([a-zA-Z0-9_/\-.]+\.[a-z]+)[`"]?', section)
            file_path = file_match.group(1) if file_match else None
            
            # Extract line number if mentioned
            line_match = re.search(r'line\s+(\d+)', section)
            line_number = int(line_match.group(1)) if line_match else None
            
            # Create issue
            issue = ReviewIssue(
                severity=severity,
                category=category,
                file_path=file_path,
                line_number=line_number,
                description=section[:200],  # First 200 chars
                suggestion=""
            )
            
            issues.append(issue)
        
        return issues
    
    def format_issue(self, issue: ReviewIssue) -> str:
        """
        Format a review issue for display.
        
        Args:
            issue: ReviewIssue to format
            
        Returns:
            Formatted string
        """
        # Severity emoji
        severity_emoji = {
            Severity.CRITICAL: "🔴",
            Severity.MAJOR: "🟠",
            Severity.MINOR: "🟡",
            Severity.INFO: "ℹ️"
        }
        
        # Category emoji
        category_emoji = {
            Category.BUG: "🐛",
            Category.SECURITY: "🔒",
            Category.PERFORMANCE: "⚡",
            Category.STYLE: "🎨",
            Category.BEST_PRACTICE: "✨",
            Category.MAINTAINABILITY: "🔧"
        }
        
        emoji = severity_emoji.get(issue.severity, "ℹ️")
        cat_emoji = category_emoji.get(issue.category, "📝")
        
        output = f"{emoji} **{issue.severity.value.upper()}** {cat_emoji} {issue.category.value.replace('_', ' ').title()}\n"
        
        if issue.file_path:
            output += f"**File:** `{issue.file_path}`"
            if issue.line_number:
                output += f" (line {issue.line_number})"
            output += "\n"
        
        output += f"\n{issue.description}\n"
        
        if issue.suggestion:
            output += f"\n**Suggestion:** {issue.suggestion}\n"
        
        return output
