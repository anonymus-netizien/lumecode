from typing import Dict, List, Any, Optional
import os
import logging
import time
from enum import Enum
from pathlib import Path

# Import the AST parser and helper functions
from .parser import ASTParser, find_nodes_by_type, find_nodes_by_text, find_nodes_by_property
from .rules import RuleEngine, create_default_rules, RuleSeverity, RuleCategory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"


class AnalysisEngine:
    """
    Core analysis engine for Lumecode.
    Handles code parsing, analysis, and result generation.

    Attributes:
        ast_parser: AST parser instance for parsing code files
        rule_engine: Rule engine for applying analysis rules
        config: Configuration dictionary
        logger: Logger instance
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "max_files": 100,
            "timeout": 300,
            "exclude_patterns": ["__pycache__", ".git", "node_modules"],
            "languages_dir": None,
        }
        logger.info("Initializing Analysis Engine")

        # Initialize the AST parser
        try:
            languages_dir = self.config.get("languages_dir")
            self.ast_parser = ASTParser(languages_dir)
            logger.info("AST parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AST parser: {e}")
            self.ast_parser = None

        # Initialize rule engine
        try:
            self.rule_engine = RuleEngine()
            # Add default rules
            default_rules = create_default_rules()
            self.rule_engine.add_rules(default_rules)
            logger.info(f"Rule engine initialized with {len(default_rules)} default rules")
        except Exception as e:
            logger.error(f"Failed to initialize rule engine: {e}")
            self.rule_engine = None

    async def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a file using the AST parser.

        Args:
            file_path: Path to the file to parse

        Returns:
            Dictionary containing the parsed AST and metadata
        """
        if not self.ast_parser:
            logger.error("AST parser not initialized")
            return {"error": "AST parser not initialized"}

        try:
            # Ensure the file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return {"error": f"File not found: {file_path}"}

            # Check if file is excluded based on patterns
            for pattern in self.config.get("exclude_patterns", []):
                if pattern in file_path:
                    logger.info(f"File excluded: {file_path}")
                    return {"excluded": True, "reason": f"Matches exclude pattern: {pattern}"}

            # Parse the file using the enhanced ASTParser
            start_time = time.time()
            ast_result = self.ast_parser.parse_file(file_path)
            parse_time = time.time() - start_time

            # Add analysis engine metadata
            ast_result["analysis_metadata"] = {
                "engine_version": "0.1.0",
                "parse_time": parse_time,
                "timestamp": time.time(),
            }

            logger.info(f"Successfully parsed file: {file_path} (took {parse_time:.2f}s)")
            return ast_result
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return {"error": str(e), "file_path": file_path}

    async def parse_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Parse code string using the AST parser.

        Args:
            code: Code string to parse
            language: Programming language of the code

        Returns:
            Dictionary containing the parsed AST and metadata
        """
        if not self.ast_parser:
            logger.error("AST parser not initialized")
            return {"error": "AST parser not initialized"}

        try:
            # Validate inputs
            if not code or not isinstance(code, str):
                logger.error("Invalid code input: must be a non-empty string")
                return {"error": "Invalid code input: must be a non-empty string"}

            if not language or not isinstance(language, str):
                logger.error("Invalid language input: must be a non-empty string")
                return {"error": "Invalid language input: must be a non-empty string"}

            # Check if language is supported
            if language not in self.ast_parser.SUPPORTED_LANGUAGES:
                logger.error(f"Unsupported language: {language}")
                return {
                    "error": f"Unsupported language: {language}",
                    "supported_languages": list(self.ast_parser.SUPPORTED_LANGUAGES.keys()),
                }

            # Parse the code using the enhanced ASTParser
            start_time = time.time()
            ast_result = self.ast_parser.parse_code(code, language)
            parse_time = time.time() - start_time

            # Add analysis engine metadata
            ast_result["analysis_metadata"] = {
                "engine_version": "0.1.0",
                "parse_time": parse_time,
                "timestamp": time.time(),
            }

            logger.info(f"Successfully parsed {language} code (took {parse_time:.2f}s)")
            return ast_result
        except Exception as e:
            logger.error(f"Failed to parse {language} code: {e}")
            return {"error": str(e), "language": language}

    async def analyze_file(
        self, file_path: str, analysis_type: AnalysisType, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single file using the AST parser and rule engine.

        Args:
            file_path: Path to the file to analyze
            analysis_type: Type of analysis to perform
            options: Additional options for the analysis

        Returns:
            Dictionary containing the analysis results
        """
        options = options or {}
        results = {
            "file_path": file_path,
            "analysis_type": analysis_type.value,
            "timestamp": time.time(),
            "issues": [],
            "metrics": {},
            "metadata": {},
        }

        # Parse the file
        start_time = time.time()
        ast_result = await self.parse_file(file_path)
        results["parse_time"] = time.time() - start_time

        # Check if parsing failed or file was excluded
        if "error" in ast_result:
            results["error"] = ast_result["error"]
            return results

        if "excluded" in ast_result and ast_result["excluded"]:
            results["excluded"] = True
            results["reason"] = ast_result["reason"]
            return results

        # Extract the AST from the result
        ast = ast_result.get("ast", {})
        language = ast_result.get("language", "unknown")

        # Add file metadata
        results["metadata"].update(
            {
                "language": language,
                "file_size": ast_result.get("file_size", 0),
                "ast_metadata": ast_result.get("metadata", {}),
            }
        )

        # Apply rule engine if available
        if self.rule_engine and "root" in ast:
            rule_start_time = time.time()
            issues = self.rule_engine.evaluate(ast["root"], file_path, language)
            results["issues"] = issues
            results["rule_evaluation_time"] = time.time() - rule_start_time
            results["metrics"]["issues_count"] = len(issues)

            # Calculate metrics based on issues
            severity_counts = {severity.value: 0 for severity in RuleSeverity}
            category_counts = {category.value: 0 for category in RuleCategory}

            for issue in issues:
                if issue.get("severity") in severity_counts:
                    severity_counts[issue["severity"]] += 1
                if issue.get("category") in category_counts:
                    category_counts[issue["category"]] += 1

            results["metrics"]["severity_counts"] = severity_counts
            results["metrics"]["category_counts"] = category_counts

        # Perform specific analysis based on type
        if analysis_type == AnalysisType.CODE_QUALITY:
            quality_results = await self._analyze_code_quality([file_path], options)
            results.update(quality_results)
        elif analysis_type == AnalysisType.SECURITY:
            security_results = await self._analyze_security([file_path], options)
            results.update(security_results)
        elif analysis_type == AnalysisType.PERFORMANCE:
            performance_results = await self._analyze_performance([file_path], options)
            results.update(performance_results)
        elif analysis_type == AnalysisType.ARCHITECTURE:
            architecture_results = await self._analyze_architecture([file_path], options)
            results.update(architecture_results)
        elif analysis_type == AnalysisType.DEPENDENCY:
            dependencies_results = await self._analyze_dependencies([file_path], options)
            results.update(dependencies_results)
        else:
            results["error"] = f"Unsupported analysis type: {analysis_type}"

        # Calculate total analysis time
        results["total_analysis_time"] = time.time() - start_time

        logger.info(
            f"Completed analysis of {file_path} (type: {analysis_type.value}, issues: {len(results['issues'])}, time: {results['total_analysis_time']:.2f}s)"
        )

        return results

    async def analyze_code(
        self, code: str, language: str, analysis_type: AnalysisType, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a code string using the AST parser and rule engine.

        Args:
            code: Code string to analyze
            language: Programming language of the code
            analysis_type: Type of analysis to perform
            options: Additional options for the analysis

        Returns:
            Dictionary containing the analysis results
        """
        options = options or {}
        results = {
            "language": language,
            "analysis_type": analysis_type.value,
            "timestamp": time.time(),
            "issues": [],
            "metrics": {},
            "metadata": {},
        }

        # Parse the code
        start_time = time.time()
        ast_result = await self.parse_code(code, language)
        results["parse_time"] = time.time() - start_time

        # Check if parsing failed
        if "error" in ast_result:
            results["error"] = ast_result["error"]
            return results

        # Extract the AST from the result
        ast = ast_result.get("ast", {})

        # Add code metadata
        results["metadata"].update(
            {"code_length": len(code), "ast_metadata": ast_result.get("metadata", {})}
        )

        # Apply rule engine if available
        if self.rule_engine and "root" in ast:
            rule_start_time = time.time()
            # Use a placeholder file path for rule evaluation
            placeholder_path = f"<inline_code>{hash(code)}.{self.ast_parser.SUPPORTED_LANGUAGES.get(language, language)}"
            issues = self.rule_engine.evaluate(ast["root"], placeholder_path, language)
            results["issues"] = issues
            results["rule_evaluation_time"] = time.time() - rule_start_time
            results["metrics"]["issues_count"] = len(issues)

            # Calculate metrics based on issues
            severity_counts = {severity.value: 0 for severity in RuleSeverity}
            category_counts = {category.value: 0 for category in RuleCategory}

            for issue in issues:
                if issue.get("severity") in severity_counts:
                    severity_counts[issue["severity"]] += 1
                if issue.get("category") in category_counts:
                    category_counts[issue["category"]] += 1

            results["metrics"]["severity_counts"] = severity_counts
            results["metrics"]["category_counts"] = category_counts

        # Calculate additional metrics
        results["metrics"]["lines_of_code"] = len(code.strip().split("\n"))
        results["metrics"]["chars_count"] = len(code)

        # Calculate total analysis time
        results["total_analysis_time"] = time.time() - start_time

        logger.info(
            f"Completed analysis of code snippet (language: {language}, type: {analysis_type.value}, issues: {len(results['issues'])}, time: {results['total_analysis_time']:.2f}s)"
        )

        return results

    async def analyze_project(
        self, project_path: str, analysis_type: AnalysisType, options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze a project and return results.

        Args:
            project_path: Path to the project directory
            analysis_type: Type of analysis to perform
            options: Additional options for the analysis

        Returns:
            Analysis results as a dictionary
        """
        logger.info(f"Starting {analysis_type} analysis for project at {project_path}")

        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        options = options or {}

        # Dispatch to specific analysis method based on type
        if analysis_type == AnalysisType.CODE_QUALITY:
            return await self._analyze_code_quality(project_path, options)
        elif analysis_type == AnalysisType.SECURITY:
            return await self._analyze_security(project_path, options)
        elif analysis_type == AnalysisType.PERFORMANCE:
            return await self._analyze_performance(project_path, options)
        elif analysis_type == AnalysisType.ARCHITECTURE:
            return await self._analyze_architecture(project_path, options)
        elif analysis_type == AnalysisType.DEPENDENCY:
            return await self._analyze_dependencies(project_path, options)
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")

    async def _analyze_code_quality(
        self, project_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze code quality using the enhanced AST parser and rule engine.
        """
        logger.info("Performing code quality analysis")

        options = options or {}
        start_time = time.time()

        # Get supported file extensions from the AST parser
        supported_extensions = []
        if self.ast_parser:
            supported_extensions = list(self.ast_parser.SUPPORTED_LANGUAGES.values())

        # Find all supported files in the project
        files_to_analyze = []
        for root, _, files in os.walk(project_path):
            # Skip excluded directories
            rel_root = os.path.relpath(root, project_path)
            if any(pattern in rel_root for pattern in self.exclude_patterns):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Skip excluded files
                rel_path = os.path.relpath(file_path, project_path)
                if any(pattern in rel_path for pattern in self.exclude_patterns):
                    continue

                if ext in supported_extensions:
                    # Apply file limit if specified
                    max_files = options.get("max_files", self.max_files)
                    if max_files > 0 and len(files_to_analyze) >= max_files:
                        logger.warning(f"Reached maximum file limit of {max_files} for analysis")
                        break

                    files_to_analyze.append(file_path)

        logger.info(f"Found {len(files_to_analyze)} files to analyze")

        # Analyze each file
        all_issues = []
        total_complexity = 0
        total_files = len(files_to_analyze)
        files_analyzed = 0
        total_lines = 0
        total_functions = 0
        total_classes = 0

        for file_path in files_to_analyze:
            try:
                # Skip analysis if we've exceeded the timeout
                if self.timeout > 0 and (time.time() - start_time) > self.timeout:
                    logger.warning(f"Analysis timeout reached after {self.timeout} seconds")
                    break

                # Parse the file if AST parser is available
                if self.ast_parser:
                    ast_result = await self.parse_file(file_path)

                    # Skip if file was excluded or parsing failed
                    if "excluded" in ast_result or "error" in ast_result:
                        continue

                    rel_path = os.path.relpath(file_path, project_path)
                    language = ast_result.get("language", "unknown")
                    ast = ast_result.get("ast", {})

                    # Count lines of code
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = len(f.readlines())
                            total_lines += lines
                    except Exception:
                        lines = 0

                    # Calculate more sophisticated complexity metrics
                    if "root" in ast:
                        # Count function and class definitions
                        functions = find_nodes_by_type(
                            ast["root"], ["function_definition", "method_definition"]
                        )
                        classes = find_nodes_by_type(ast["root"], ["class_definition"])
                        total_functions += len(functions)
                        total_classes += len(classes)

                        # Calculate complexity based on branches and loops
                        branch_nodes = find_nodes_by_type(
                            ast["root"],
                            [
                                "if_statement",
                                "for_statement",
                                "while_statement",
                                "switch_statement",
                                "case_statement",
                                "try_statement",
                            ],
                        )

                        # More accurate cyclomatic complexity
                        complexity = len(branch_nodes) + 1  # Base complexity is 1
                        total_complexity += complexity

                        # Apply rules to the AST
                        if self.rule_engine:
                            # Evaluate rules
                            rule_issues = self.rule_engine.evaluate(
                                ast["root"], file_path, language
                            )

                            # Add file path to issues
                            for issue in rule_issues:
                                issue["file_path"] = rel_path

                            all_issues.extend(rule_issues)

                            if rule_issues:
                                logger.info(f"Found {len(rule_issues)} issues in {rel_path}")

                    files_analyzed += 1
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")

        # Calculate metrics
        avg_complexity = total_complexity / files_analyzed if files_analyzed > 0 else 0
        avg_functions_per_file = total_functions / files_analyzed if files_analyzed > 0 else 0
        avg_lines_per_file = total_lines / files_analyzed if files_analyzed > 0 else 0

        # Group issues by category and severity using our enums
        issues_by_category = {category.value: 0 for category in RuleCategory}
        issues_by_severity = {severity.value: 0 for severity in RuleSeverity}

        for issue in all_issues:
            if issue.get("category") in issues_by_category:
                issues_by_category[issue["category"]] += 1
            if issue.get("severity") in issues_by_severity:
                issues_by_severity[issue["severity"]] += 1

        # Calculate maintainability index (simplified version based on multiple factors)
        # Lower complexity and fewer issues lead to higher maintainability
        maintainability = 100
        if avg_complexity > 10:
            maintainability -= min(30, (avg_complexity - 10) * 3)  # Complexity impact
        if len(all_issues) > 0:
            maintainability -= min(40, len(all_issues) * 2)  # Issues impact
        if avg_functions_per_file > 10:
            maintainability -= min(20, (avg_functions_per_file - 10) * 2)  # Function density impact
        maintainability = max(0, min(100, maintainability))

        return {
            "type": "code_quality",
            "summary": f"Code quality analysis completed with {len(all_issues)} issues found in {files_analyzed} files",
            "timestamp": time.time(),
            "metrics": {
                "maintainability_index": round(maintainability, 2),
                "cyclomatic_complexity": {
                    "average": round(avg_complexity, 2),
                    "total": total_complexity,
                },
                "code_smells": len(all_issues),
                "files_analyzed": files_analyzed,
                "total_files": total_files,
                "total_lines": total_lines,
                "avg_lines_per_file": round(avg_lines_per_file, 2),
                "total_functions": total_functions,
                "total_classes": total_classes,
                "avg_functions_per_file": round(avg_functions_per_file, 2),
                "issues_by_severity": issues_by_severity,
                "issues_by_category": issues_by_category,
                "analysis_time": round(time.time() - start_time, 2),
            },
            "issues": all_issues,
            "files_analyzed_list": [
                os.path.relpath(f, project_path) for f in files_to_analyze[:files_analyzed]
            ],
        }

    def _count_nodes(self, ast_node: Dict[str, Any]) -> int:
        """
        Count the number of nodes in an AST.

        Args:
            ast_node: The AST node to count

        Returns:
            Number of nodes
        """
        count = 1  # Count this node

        if "children" in ast_node:
            for child in ast_node["children"]:
                count += self._count_nodes(child)

        return count

    async def _analyze_security(self, project_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze security vulnerabilities using AST parsing and rule-based detection.
        """
        logger.info("Performing security analysis")

        options = options or {}
        start_time = time.time()

        # Get supported file extensions from the AST parser
        supported_extensions = []
        if self.ast_parser:
            supported_extensions = list(self.ast_parser.SUPPORTED_LANGUAGES.values())

        # Find all supported files in the project
        files_to_analyze = []
        for root, _, files in os.walk(project_path):
            # Skip excluded directories
            rel_root = os.path.relpath(root, project_path)
            if any(pattern in rel_root for pattern in self.exclude_patterns):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Skip excluded files
                rel_path = os.path.relpath(file_path, project_path)
                if any(pattern in rel_path for pattern in self.exclude_patterns):
                    continue

                if ext in supported_extensions:
                    # Apply file limit if specified
                    max_files = options.get("max_files", self.max_files)
                    if max_files > 0 and len(files_to_analyze) >= max_files:
                        logger.warning(f"Reached maximum file limit of {max_files} for analysis")
                        break

                    files_to_analyze.append(file_path)

        logger.info(f"Found {len(files_to_analyze)} files to analyze")

        # Analyze each file for security vulnerabilities
        vulnerabilities = []
        total_files = len(files_to_analyze)
        files_analyzed = 0

        # CWE (Common Weakness Enumeration) mapping for common vulnerabilities
        cwe_mapping = {
            "hardcoded_password": "CWE-259",
            "sql_injection": "CWE-89",
            "xss": "CWE-79",
            "command_injection": "CWE-77",
            "insecure_cookie": "CWE-614",
            "insecure_random": "CWE-330",
            "unvalidated_input": "CWE-20",
            "path_traversal": "CWE-22",
        }

        for file_path in files_to_analyze:
            try:
                # Skip analysis if we've exceeded the timeout
                if self.timeout > 0 and (time.time() - start_time) > self.timeout:
                    logger.warning(f"Analysis timeout reached after {self.timeout} seconds")
                    break

                # Parse the file if AST parser is available
                if self.ast_parser:
                    ast_result = await self.parse_file(file_path)

                    # Skip if file was excluded or parsing failed
                    if "excluded" in ast_result or "error" in ast_result:
                        continue

                    rel_path = os.path.relpath(file_path, project_path)
                    language = ast_result.get("language", "unknown")
                    ast = ast_result.get("ast", {})

                    # Apply security-focused AST analysis
                    if "root" in ast:
                        # Use our rule engine for security rules
                        if self.rule_engine:
                            # Evaluate rules
                            security_issues = self.rule_engine.evaluate(
                                ast["root"], file_path, language
                            )

                            # Filter for security-related issues
                            security_vulnerabilities = [
                                issue
                                for issue in security_issues
                                if issue.get("category") == "security"
                            ]

                            # Add file path and CWE information to vulnerabilities
                            for vuln in security_vulnerabilities:
                                vuln["file_path"] = rel_path
                                vuln_type = vuln.get("type", "unknown").lower()

                                # Add CWE if known
                                if vuln_type in cwe_mapping:
                                    vuln["cwe"] = cwe_mapping[vuln_type]

                                # Map our severity to standard security severity levels
                                if vuln.get("severity") == "critical":
                                    vuln["security_severity"] = "high"
                                elif vuln.get("severity") == "error":
                                    vuln["security_severity"] = "medium"
                                else:
                                    vuln["security_severity"] = "low"

                            vulnerabilities.extend(security_vulnerabilities)

                            if security_vulnerabilities:
                                logger.info(
                                    f"Found {len(security_vulnerabilities)} security vulnerabilities in {rel_path}"
                                )

                        # Perform additional security-specific AST analysis
                        security_findings = await self._perform_security_ast_analysis(
                            ast["root"], file_path, language, options
                        )
                        vulnerabilities.extend(security_findings)

                    files_analyzed += 1
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")

        # Calculate metrics
        severity_counts = {"high": 0, "medium": 0, "low": 0}

        for vuln in vulnerabilities:
            severity = vuln.get("security_severity", "low")
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Count vulnerabilities by type
        vuln_types = {}
        for vuln in vulnerabilities:
            vuln_type = vuln.get("type", "unknown")
            vuln_types[vuln_type] = vuln_types.get(vuln_type, 0) + 1

        # Count by CWE
        cwe_counts = {}
        for vuln in vulnerabilities:
            if "cwe" in vuln:
                cwe = vuln["cwe"]
                cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1

        return {
            "type": "security",
            "summary": f"Security analysis completed with {len(vulnerabilities)} vulnerabilities found in {files_analyzed} files",
            "timestamp": time.time(),
            "vulnerabilities": vulnerabilities,
            "metrics": {
                "high_severity": severity_counts["high"],
                "medium_severity": severity_counts["medium"],
                "low_severity": severity_counts["low"],
                "total_vulnerabilities": len(vulnerabilities),
                "files_analyzed": files_analyzed,
                "total_files": total_files,
                "vulnerabilities_by_type": vuln_types,
                "vulnerabilities_by_cwe": cwe_counts,
                "analysis_time": round(time.time() - start_time, 2),
            },
            "files_analyzed_list": [
                os.path.relpath(f, project_path) for f in files_to_analyze[:files_analyzed]
            ],
        }

    async def _perform_security_ast_analysis(
        self, ast_root: Dict[str, Any], file_path: str, language: str, options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Perform additional security-specific AST analysis beyond the rule engine.

        Args:
            ast_root: Root node of the AST
            file_path: Path to the analyzed file
            language: Programming language
            options: Additional analysis options

        Returns:
            List of security findings
        """
        findings = []
        rel_path = os.path.relpath(file_path)

        # Example: Look for potential SQL injection patterns
        if language in ["python", "javascript", "php"]:
            # Search for string concatenation in SQL queries
            # This is a simplified example - real detection would be more sophisticated
            string_nodes = find_nodes_by_type(ast_root, ["string_literal", "template_string"])

            for string_node in string_nodes:
                text = string_node.get("text", "").lower()
                if any(
                    keyword in text
                    for keyword in ["select ", "insert ", "update ", "delete ", "drop "]
                ):
                    # Check if this string is part of a potential SQL query
                    # In a real implementation, we would check the context more thoroughly
                    findings.append(
                        {
                            "type": "sql_injection",
                            "file_path": rel_path,
                            "line": string_node.get("start_pos", {}).get("row", 0),
                            "column": string_node.get("start_pos", {}).get("column", 0),
                            "message": "Potential SQL injection vulnerability detected in string containing SQL keywords",
                            "severity": "error",
                            "category": "security",
                            "security_severity": "medium",
                            "cwe": "CWE-89",
                            "recommendation": "Use parameterized queries or prepared statements instead of string concatenation",
                        }
                    )

        # Example: Look for potential hardcoded credentials
        # This complements the existing rule but adds more context
        credential_patterns = [
            "password=",
            "secret=",
            "api_key=",
            "token=",
            "auth=",
            "pwd=",
            "key=",
            "private_key",
            "client_secret",
        ]

        for pattern in credential_patterns:
            pattern_nodes = find_nodes_by_text(ast_root, pattern, case_sensitive=False)

            for node in pattern_nodes:
                findings.append(
                    {
                        "type": "hardcoded_credential",
                        "file_path": rel_path,
                        "line": node.get("start_pos", {}).get("row", 0),
                        "column": node.get("start_pos", {}).get("column", 0),
                        "message": f"Potential hardcoded credential detected near '{pattern}'",
                        "severity": "critical",
                        "category": "security",
                        "security_severity": "high",
                        "cwe": "CWE-259",
                        "recommendation": "Store credentials in environment variables or secure secret management systems",
                    }
                )

        return findings

    async def _analyze_performance(
        self, project_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze performance issues using AST parsing and rule-based detection.
        """
        logger.info("Performing performance analysis")

        options = options or {}
        start_time = time.time()

        # Get supported file extensions from the AST parser
        supported_extensions = []
        if self.ast_parser:
            supported_extensions = list(self.ast_parser.SUPPORTED_LANGUAGES.values())

        # Find all supported files in the project
        files_to_analyze = []
        for root, _, files in os.walk(project_path):
            # Skip excluded directories
            rel_root = os.path.relpath(root, project_path)
            if any(pattern in rel_root for pattern in self.exclude_patterns):
                continue

            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # Skip excluded files
                rel_path = os.path.relpath(file_path, project_path)
                if any(pattern in rel_path for pattern in self.exclude_patterns):
                    continue

                if ext in supported_extensions:
                    # Apply file limit if specified
                    max_files = options.get("max_files", self.max_files)
                    if max_files > 0 and len(files_to_analyze) >= max_files:
                        logger.warning(f"Reached maximum file limit of {max_files} for analysis")
                        break

                    files_to_analyze.append(file_path)

        logger.info(f"Found {len(files_to_analyze)} files to analyze")

        # Analyze each file for performance issues
        performance_hotspots = []
        total_files = len(files_to_analyze)
        files_analyzed = 0

        # Categories of performance issues we look for
        performance_categories = {
            "database": 0,
            "algorithm": 0,
            "memory": 0,
            "concurrency": 0,
            "io": 0,
            "network": 0,
            "rendering": 0,
        }

        for file_path in files_to_analyze:
            try:
                # Skip analysis if we've exceeded the timeout
                if self.timeout > 0 and (time.time() - start_time) > self.timeout:
                    logger.warning(f"Analysis timeout reached after {self.timeout} seconds")
                    break

                # Parse the file if AST parser is available
                if self.ast_parser:
                    ast_result = await self.parse_file(file_path)

                    # Skip if file was excluded or parsing failed
                    if "excluded" in ast_result or "error" in ast_result:
                        continue

                    rel_path = os.path.relpath(file_path, project_path)
                    language = ast_result.get("language", "unknown")
                    ast = ast_result.get("ast", {})

                    # Apply performance-focused AST analysis
                    if "root" in ast:
                        # Use our rule engine for performance rules
                        if self.rule_engine:
                            # Evaluate rules
                            performance_issues = self.rule_engine.evaluate(
                                ast["root"], file_path, language
                            )

                            # Filter for performance-related issues
                            performance_findings = [
                                issue
                                for issue in performance_issues
                                if issue.get("category") == "performance"
                            ]

                            # Add file path and categorize findings
                            for finding in performance_findings:
                                finding["file_path"] = rel_path
                                finding["type"] = finding.get("type", "general_performance")

                                # Map to performance category
                                category = self._map_performance_type_to_category(finding["type"])
                                finding["performance_category"] = category
                                if category in performance_categories:
                                    performance_categories[category] += 1

                            performance_hotspots.extend(performance_findings)

                            if performance_findings:
                                logger.info(
                                    f"Found {len(performance_findings)} performance issues in {rel_path}"
                                )

                        # Perform additional performance-specific AST analysis
                        additional_hotspots = await self._perform_performance_ast_analysis(
                            ast["root"], file_path, language, options
                        )
                        performance_hotspots.extend(additional_hotspots)

                        # Increment category counts for additional hotspots
                        for hotspot in additional_hotspots:
                            category = hotspot.get("performance_category", "general_performance")
                            if category in performance_categories:
                                performance_categories[category] += 1

                    files_analyzed += 1
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")

        # Calculate metrics
        severity_counts = {"high": 0, "medium": 0, "low": 0}

        for hotspot in performance_hotspots:
            # Map our severity to performance impact levels
            if hotspot.get("severity") == "critical":
                impact = "high"
            elif hotspot.get("severity") == "error":
                impact = "medium"
            else:
                impact = "low"

            severity_counts[impact] += 1
            hotspot["performance_impact"] = impact

        # Count issues by type
        issue_types = {}
        for hotspot in performance_hotspots:
            issue_type = hotspot.get("type", "unknown")
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        return {
            "type": "performance",
            "summary": f"Performance analysis completed with {len(performance_hotspots)} hotspots found in {files_analyzed} files",
            "timestamp": time.time(),
            "hotspots": performance_hotspots,
            "metrics": {
                "high_impact": severity_counts["high"],
                "medium_impact": severity_counts["medium"],
                "low_impact": severity_counts["low"],
                "total_hotspots": len(performance_hotspots),
                "files_analyzed": files_analyzed,
                "total_files": total_files,
                "hotspots_by_type": issue_types,
                "hotspots_by_category": {k: v for k, v in performance_categories.items() if v > 0},
                "analysis_time": round(time.time() - start_time, 2),
            },
            "files_analyzed_list": [
                os.path.relpath(f, project_path) for f in files_to_analyze[:files_analyzed]
            ],
        }

    def _map_performance_type_to_category(self, issue_type: str) -> str:
        """
        Map performance issue types to broader categories.
        """
        issue_type_lower = issue_type.lower()

        if any(keyword in issue_type_lower for keyword in ["db", "database", "query", "sql"]):
            return "database"
        elif any(keyword in issue_type_lower for keyword in ["algo", "algorithm", "complexity"]):
            return "algorithm"
        elif any(keyword in issue_type_lower for keyword in ["memory", "gc", "garbage", "leak"]):
            return "memory"
        elif any(
            keyword in issue_type_lower
            for keyword in ["thread", "concurrency", "parallel", "async"]
        ):
            return "concurrency"
        elif any(keyword in issue_type_lower for keyword in ["io", "file", "disk"]):
            return "io"
        elif any(
            keyword in issue_type_lower for keyword in ["network", "http", "request", "response"]
        ):
            return "network"
        elif any(keyword in issue_type_lower for keyword in ["render", "ui", "dom", "reflow"]):
            return "rendering"
        else:
            return "general_performance"

    async def _perform_performance_ast_analysis(
        self, ast_root: Dict[str, Any], file_path: str, language: str, options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Perform additional performance-specific AST analysis beyond the rule engine.

        Args:
            ast_root: Root node of the AST
            file_path: Path to the analyzed file
            language: Programming language
            options: Additional analysis options

        Returns:
            List of performance hotspots
        """
        hotspots = []
        rel_path = os.path.relpath(file_path)

        # Example: Look for potential N+1 database query patterns
        if language in ["python", "javascript", "php"]:
            # This is a simplified example - real detection would be more sophisticated
            # Search for loops that might contain database queries
            loop_nodes = find_nodes_by_type(
                ast_root, ["for_statement", "while_statement", "do_statement"]
            )

            for loop_node in loop_nodes:
                loop_start = loop_node.get("start_pos", {}).get("row", 0)
                loop_end = loop_node.get("end_pos", {}).get("row", 0)

                # Search for database query patterns within the loop
                # Look for common database method calls
                db_keywords = ["query", "find", "get", "fetch", "select", "execute", "raw"]

                # Get all nodes within the loop's line range
                potential_queries = find_nodes_by_property(
                    ast_root, "start_pos.row", lambda x: x >= loop_start and x <= loop_end
                )

                for node in potential_queries:
                    node_text = node.get("text", "").lower()
                    if any(keyword in node_text for keyword in db_keywords):
                        # In a real implementation, we would check the context more thoroughly
                        hotspots.append(
                            {
                                "type": "n_plus_one_query",
                                "file_path": rel_path,
                                "line": loop_start,
                                "column": loop_node.get("start_pos", {}).get("column", 0),
                                "message": "Potential N+1 database query detected inside loop",
                                "severity": "error",
                                "category": "performance",
                                "performance_category": "database",
                                "performance_impact": "medium",
                                "recommendation": "Use eager loading or batch fetching to reduce the number of database queries",
                            }
                        )
                        break  # Only report once per loop

        # Example: Look for inefficient algorithm patterns
        # Search for nested loops (O(n^2) complexity)
        nested_loops = []
        loops = find_nodes_by_type(ast_root, ["for_statement", "while_statement"])

        for outer_loop in loops:
            outer_start = outer_loop.get("start_pos", {}).get("row", 0)
            outer_end = outer_loop.get("end_pos", {}).get("row", 0)

            for inner_loop in loops:
                inner_start = inner_loop.get("start_pos", {}).get("row", 0)
                if inner_start > outer_start and inner_start < outer_end:
                    # This inner loop is inside the outer loop
                    hotspots.append(
                        {
                            "type": "nested_loops",
                            "file_path": rel_path,
                            "line": outer_start,
                            "column": outer_loop.get("start_pos", {}).get("column", 0),
                            "message": "Nested loops detected (potential O(n^2) time complexity)",
                            "severity": "warning",
                            "category": "performance",
                            "performance_category": "algorithm",
                            "performance_impact": "medium",
                            "recommendation": "Consider using more efficient algorithms or data structures to reduce time complexity",
                        }
                    )

        # Example: Look for potential memory issues
        # Search for large array initializations or repeated string concatenation
        if language == "javascript":
            # Check for repeated string concatenation in loops
            string_concat_patterns = find_nodes_by_type(ast_root, ["binary_expression"])
            for node in string_concat_patterns:
                if (
                    node.get("operator") == "+"
                    and node.get("left", {}).get("type") == "string_literal"
                ):
                    # Check if this is inside a loop
                    node_line = node.get("start_pos", {}).get("row", 0)

                    for loop in loops:
                        loop_start = loop.get("start_pos", {}).get("row", 0)
                        loop_end = loop.get("end_pos", {}).get("row", 0)

                        if node_line >= loop_start and node_line <= loop_end:
                            hotspots.append(
                                {
                                    "type": "string_concatenation_in_loop",
                                    "file_path": rel_path,
                                    "line": node_line,
                                    "column": node.get("start_pos", {}).get("column", 0),
                                    "message": "Repeated string concatenation detected inside loop (potential memory issue)",
                                    "severity": "warning",
                                    "category": "performance",
                                    "performance_category": "memory",
                                    "performance_impact": "low",
                                    "recommendation": "Use StringBuilder or array.join() for more efficient string construction",
                                }
                            )
                            break

        return hotspots

    async def _analyze_architecture(
        self, project_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze code architecture and structure.
        """
        logger.info("Performing architecture analysis")

        # Placeholder for actual implementation
        return {
            "type": "architecture",
            "summary": "Architecture analysis completed",
            "metrics": {"coupling": "medium", "cohesion": "high", "modularity": 0.75},
            "components": [
                {"name": "API Layer", "files": 12, "dependencies": ["Data Layer"]},
                {"name": "Data Layer", "files": 8, "dependencies": []},
            ],
            "issues": [
                {
                    "type": "circular_dependency",
                    "components": ["UserService", "AuthService"],
                    "severity": "medium",
                }
            ],
        }

    async def _analyze_dependencies(
        self, project_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze project dependencies.
        """
        logger.info("Performing dependency analysis")

        # Placeholder for actual implementation
        return {
            "type": "dependency",
            "summary": "Dependency analysis completed",
            "dependencies": [
                {
                    "name": "fastapi",
                    "version": "0.95.0",
                    "latest": "0.95.1",
                    "update_available": True,
                    "licenses": ["MIT"],
                    "vulnerabilities": [],
                },
                {
                    "name": "requests",
                    "version": "2.27.1",
                    "latest": "2.28.2",
                    "update_available": True,
                    "licenses": ["Apache-2.0"],
                    "vulnerabilities": [
                        {"id": "CVE-2022-12345", "severity": "medium", "fixed_in": "2.28.0"}
                    ],
                },
            ],
            "metrics": {
                "outdated_dependencies": 2,
                "vulnerable_dependencies": 1,
                "license_issues": 0,
            },
        }
