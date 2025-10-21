from typing import Dict, List, Any, Optional
import logging
import os
import json

from .base import BaseAgent, AgentType, agent_registry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeReviewAgent(BaseAgent):
    """
    Agent for performing automated code reviews.
    """

    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config)
        self.review_rules = self.config.get("review_rules", [])
        logger.info(f"Initialized CodeReviewAgent with {len(self.review_rules)} rules")

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run code review on the provided code.

        Args:
            context: Contains code files to review and other metadata

        Returns:
            Code review results
        """
        logger.info("Starting code review")

        if "files" not in context:
            raise ValueError("No files provided for review")

        files = context["files"]
        project_path = context.get("project_path")
        commit_hash = context.get("commit_hash")

        # Results will contain review findings for each file
        results = {
            "summary": {
                "files_reviewed": len(files),
                "issues_found": 0,
                "critical_issues": 0,
                "major_issues": 0,
                "minor_issues": 0,
            },
            "files": [],
        }

        # Process each file
        for file_info in files:
            file_path = file_info.get("path")
            file_content = file_info.get("content")

            if not file_path or not file_content:
                logger.warning(f"Skipping file with missing path or content")
                continue

            # Perform the actual code review for this file
            file_results = await self._review_file(file_path, file_content)

            # Update summary statistics
            results["summary"]["issues_found"] += len(file_results["issues"])
            for issue in file_results["issues"]:
                severity = issue.get("severity", "minor")
                if severity == "critical":
                    results["summary"]["critical_issues"] += 1
                elif severity == "major":
                    results["summary"]["major_issues"] += 1
                else:
                    results["summary"]["minor_issues"] += 1

            # Add file results to overall results
            results["files"].append(file_results)

        logger.info(f"Code review completed. Found {results['summary']['issues_found']} issues")
        return results

    async def _review_file(self, file_path: str, file_content: str) -> Dict[str, Any]:
        """
        Review a single file and return issues found.
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        # In a real implementation, this would use language-specific analyzers
        # For now, we'll just provide some mock results based on file extension

        issues = []

        # Mock code review logic
        if file_ext in [".py", ".pyw"]:
            # Python-specific checks
            if "import *" in file_content:
                issues.append(
                    {
                        "line": file_content.find("import *") + 1,
                        "message": "Wildcard imports are discouraged",
                        "severity": "minor",
                        "rule_id": "PY001",
                    }
                )

            if "except:" in file_content:
                issues.append(
                    {
                        "line": file_content.find("except:") + 1,
                        "message": "Bare except clause should be avoided",
                        "severity": "major",
                        "rule_id": "PY002",
                    }
                )

        elif file_ext in [".js", ".jsx", ".ts", ".tsx"]:
            # JavaScript/TypeScript checks
            if "eval(" in file_content:
                issues.append(
                    {
                        "line": file_content.find("eval(") + 1,
                        "message": "Avoid using eval() for security reasons",
                        "severity": "critical",
                        "rule_id": "JS001",
                    }
                )

            if "var " in file_content:
                issues.append(
                    {
                        "line": file_content.find("var ") + 1,
                        "message": "Use 'let' or 'const' instead of 'var'",
                        "severity": "minor",
                        "rule_id": "JS002",
                    }
                )

        # Apply custom review rules from config
        for rule in self.review_rules:
            pattern = rule.get("pattern")
            if pattern and pattern in file_content:
                issues.append(
                    {
                        "line": file_content.find(pattern) + 1,
                        "message": rule.get("message", "Custom rule violation"),
                        "severity": rule.get("severity", "minor"),
                        "rule_id": rule.get("id", "CUSTOM"),
                    }
                )

        return {
            "path": file_path,
            "issues": issues,
            "summary": {
                "issues_count": len(issues),
                "lines_reviewed": len(file_content.splitlines()),
            },
        }


# Register the agent with the registry
agent_registry.register(AgentType.CODE_REVIEW, CodeReviewAgent)
