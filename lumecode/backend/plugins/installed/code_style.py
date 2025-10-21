from typing import Dict, List, Any, Optional
import logging
import re

from ..base import PluginInterface

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeStylePlugin(PluginInterface):
    """
    Plugin for checking code style and formatting.
    """
    
    @property
    def name(self) -> str:
        return "code_style"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def description(self) -> str:
        return "Checks code style and formatting against configurable rules"
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the plugin with the provided configuration.
        """
        self.config = config
        self.rules = config.get("rules", self._get_default_rules())
        logger.info(f"Initialized CodeStylePlugin with {len(self.rules)} rules")
    
    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """
        Get default code style rules.
        """
        return [
            {
                "id": "line_length",
                "description": "Line length should not exceed 100 characters",
                "language": "*",
                "severity": "warning"
            },
            {
                "id": "trailing_whitespace",
                "description": "Lines should not have trailing whitespace",
                "language": "*",
                "severity": "info"
            },
            {
                "id": "py_indent",
                "description": "Python code should use 4 spaces for indentation",
                "language": "python",
                "severity": "warning"
            },
            {
                "id": "js_indent",
                "description": "JavaScript code should use 2 spaces for indentation",
                "language": "javascript",
                "severity": "warning"
            }
        ]
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plugin with the provided context.
        
        Args:
            context: Contains code files to check and other metadata
            
        Returns:
            Code style check results
        """
        logger.info("Starting code style check")
        
        if "files" not in context:
            raise ValueError("No files provided for style check")
        
        files = context["files"]
        
        # Results will contain style issues for each file
        results = {
            "summary": {
                "files_checked": len(files),
                "issues_found": 0,
                "warnings": 0,
                "infos": 0
            },
            "files": []
        }
        
        # Process each file
        for file_info in files:
            file_path = file_info.get("path")
            file_content = file_info.get("content")
            
            if not file_path or not file_content:
                logger.warning(f"Skipping file with missing path or content")
                continue
            
            # Determine file language
            language = self._get_file_language(file_path)
            
            # Check the file against applicable rules
            file_results = self._check_file(file_path, file_content, language)
            
            # Update summary statistics
            results["summary"]["issues_found"] += len(file_results["issues"])
            for issue in file_results["issues"]:
                severity = issue.get("severity", "info")
                if severity == "warning":
                    results["summary"]["warnings"] += 1
                else:
                    results["summary"]["infos"] += 1
            
            # Add file results to overall results
            results["files"].append(file_results)
        
        logger.info(f"Code style check completed. Found {results['summary']['issues_found']} issues")
        return results
    
    def _get_file_language(self, file_path: str) -> str:
        """
        Determine the language of a file based on its extension.
        """
        ext = file_path.split(".")[-1].lower()
        
        if ext in ["py", "pyw"]:
            return "python"
        elif ext in ["js", "jsx"]:
            return "javascript"
        elif ext in ["ts", "tsx"]:
            return "typescript"
        elif ext in ["html", "htm"]:
            return "html"
        elif ext in ["css"]:
            return "css"
        elif ext in ["json"]:
            return "json"
        elif ext in ["md", "markdown"]:
            return "markdown"
        elif ext in ["yml", "yaml"]:
            return "yaml"
        else:
            return "text"
    
    def _check_file(self, file_path: str, file_content: str, language: str) -> Dict[str, Any]:
        """
        Check a file against applicable style rules.
        """
        issues = []
        lines = file_content.splitlines()
        
        # Apply each rule that's applicable to this language
        for rule in self.rules:
            rule_language = rule.get("language", "*")
            
            # Skip rules that don't apply to this language
            if rule_language != "*" and rule_language != language:
                continue
            
            rule_id = rule.get("id")
            severity = rule.get("severity", "info")
            
            # Apply specific rules
            if rule_id == "line_length":
                max_length = rule.get("max_length", 100)
                for i, line in enumerate(lines):
                    if len(line) > max_length:
                        issues.append({
                            "line": i + 1,
                            "column": max_length + 1,
                            "message": f"Line exceeds maximum length of {max_length} characters",
                            "rule_id": rule_id,
                            "severity": severity
                        })
            
            elif rule_id == "trailing_whitespace":
                for i, line in enumerate(lines):
                    if line and line[-1].isspace():
                        issues.append({
                            "line": i + 1,
                            "column": len(line),
                            "message": "Line has trailing whitespace",
                            "rule_id": rule_id,
                            "severity": severity
                        })
            
            elif rule_id == "py_indent" and language == "python":
                for i, line in enumerate(lines):
                    if line.startswith(" ") and not line.startswith("    ") and not re.match(r"^ *$", line):
                        issues.append({
                            "line": i + 1,
                            "column": 1,
                            "message": "Python indentation should be 4 spaces",
                            "rule_id": rule_id,
                            "severity": severity
                        })
            
            elif rule_id == "js_indent" and language in ["javascript", "typescript"]:
                for i, line in enumerate(lines):
                    if line.startswith(" ") and not line.startswith("  ") and not re.match(r"^ *$", line):
                        issues.append({
                            "line": i + 1,
                            "column": 1,
                            "message": "JavaScript/TypeScript indentation should be 2 spaces",
                            "rule_id": rule_id,
                            "severity": severity
                        })
        
        return {
            "path": file_path,
            "language": language,
            "issues": issues,
            "summary": {
                "issues_count": len(issues),
                "lines_checked": len(lines)
            }
        }