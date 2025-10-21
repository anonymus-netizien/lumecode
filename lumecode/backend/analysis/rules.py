from enum import Enum
from typing import Dict, List, Any, Callable, Optional, Union
import re
import logging

logger = logging.getLogger(__name__)

class RuleSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class RuleCategory(Enum):
    SECURITY = "security"
    QUALITY = "quality"
    STYLE = "style"
    PERFORMANCE = "performance"
    COMPLEXITY = "complexity"

class Rule:
    """Base class for all rules"""
    
    def __init__(self, 
                 rule_id: str,
                 name: str,
                 description: str,
                 category: RuleCategory,
                 severity: RuleSeverity):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.category = category
        self.severity = severity
        self.enabled = True
    
    def evaluate(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate the rule against an AST node
        
        Args:
            ast_node: The AST node to evaluate
            context: Additional context information
            
        Returns:
            List of issues found
        """
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def format_issue(self, node: Dict[str, Any], message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Format an issue found by this rule
        
        Args:
            node: The AST node where the issue was found
            message: The issue message
            context: Additional context information
            
        Returns:
            Formatted issue
        """
        file_path = context.get("file_path", "unknown")
        line = node.get("start_line", 0)
        column = node.get("start_column", 0)
        
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "file": file_path,
            "line": line,
            "column": column,
            "message": message
        }

class PatternRule(Rule):
    """Rule that matches patterns in the AST"""
    
    def __init__(self, 
                 rule_id: str,
                 name: str,
                 description: str,
                 category: RuleCategory,
                 severity: RuleSeverity,
                 node_type: str,
                 pattern: Dict[str, Any]):
        super().__init__(rule_id, name, description, category, severity)
        self.node_type = node_type
        self.pattern = pattern
    
    def evaluate(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        
        # Check if this node matches the pattern
        if self._match_node(ast_node, self.pattern):
            message = f"{self.name}: Found pattern match"
            issues.append(self.format_issue(ast_node, message, context))
        
        # Recursively check children
        if "children" in ast_node:
            for child in ast_node["children"]:
                issues.extend(self.evaluate(child, context))
        
        return issues
    
    def _match_node(self, node: Dict[str, Any], pattern: Dict[str, Any]) -> bool:
        """Check if a node matches a pattern
        
        Args:
            node: The AST node to check
            pattern: The pattern to match
            
        Returns:
            True if the node matches the pattern, False otherwise
        """
        # Check node type
        if "type" in pattern and node.get("type") != pattern["type"]:
            return False
        
        # Check other properties
        for key, value in pattern.items():
            if key == "type":
                continue
                
            if key not in node:
                return False
                
            if isinstance(value, dict):
                if not isinstance(node[key], dict):
                    return False
                if not self._match_node(node[key], value):
                    return False
            elif isinstance(value, list):
                if not isinstance(node[key], list):
                    return False
                if len(value) != len(node[key]):
                    return False
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        if not self._match_node(node[key][i], item):
                            return False
                    elif node[key][i] != item:
                        return False
            elif node[key] != value:
                return False
        
        return True

class FunctionRule(Rule):
    """Rule that uses a function to evaluate nodes"""
    
    def __init__(self, 
                 rule_id: str,
                 name: str,
                 description: str,
                 category: RuleCategory,
                 severity: RuleSeverity,
                 node_types: List[str],
                 evaluation_fn: Callable[[Dict[str, Any], Dict[str, Any]], Optional[str]]):
        super().__init__(rule_id, name, description, category, severity)
        self.node_types = node_types
        self.evaluation_fn = evaluation_fn
    
    def evaluate(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        
        # Check if this node is of a type we're interested in
        if ast_node.get("type") in self.node_types:
            # Call the evaluation function
            message = self.evaluation_fn(ast_node, context)
            if message:
                issues.append(self.format_issue(ast_node, message, context))
        
        # Recursively check children
        if "children" in ast_node:
            for child in ast_node["children"]:
                issues.extend(self.evaluate(child, context))
        
        return issues

class RuleEngine:
    """Engine for evaluating rules against AST nodes"""
    
    def __init__(self):
        self.rules = []
    
    def add_rule(self, rule: Rule):
        """Add a rule to the engine
        
        Args:
            rule: The rule to add
        """
        self.rules.append(rule)
    
    def add_rules(self, rules: List[Rule]):
        """Add multiple rules to the engine
        
        Args:
            rules: The rules to add
        """
        self.rules.extend(rules)
    
    def evaluate(self, ast_node: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all rules against an AST node
        
        Args:
            ast_node: The AST node to evaluate
            context: Additional context information
            
        Returns:
            List of issues found
        """
        issues = []
        
        for rule in self.rules:
            if rule.enabled:
                try:
                    rule_issues = rule.evaluate(ast_node, context)
                    issues.extend(rule_issues)
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
        
        return issues

# Example rules
def create_default_rules() -> List[Rule]:
    """Create a set of default rules
    
    Returns:
        List of default rules
    """
    rules = []
    
    # Example pattern rule: Find hardcoded passwords
    rules.append(PatternRule(
        rule_id="SEC001",
        name="Hardcoded Password",
        description="Avoid hardcoding passwords in source code",
        category=RuleCategory.SECURITY,
        severity=RuleSeverity.ERROR,
        node_type="assignment",
        pattern={
            "type": "assignment",
            "target": {"name": re.compile(r".*password.*", re.IGNORECASE)},
            "value": {"type": "string"}
        }
    ))
    
    # Example function rule: Function too long
    def check_function_length(node: Dict[str, Any], context: Dict[str, Any]) -> Optional[str]:
        if "body" in node and "children" in node["body"]:
            if len(node["body"]["children"]) > 50:  # More than 50 statements
                return f"Function '{node.get('name', 'unknown')}' is too long ({len(node['body']['children'])} statements)"
        return None
    
    rules.append(FunctionRule(
        rule_id="QUAL001",
        name="Function Too Long",
        description="Functions should not be too long",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.WARNING,
        node_types=["function_definition", "method_definition"],
        evaluation_fn=check_function_length
    ))
    
    return rules