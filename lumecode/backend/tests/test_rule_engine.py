import os
import sys
import unittest
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis import Rule, PatternRule, FunctionRule, RuleEngine, RuleSeverity, RuleCategory

class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.rule_engine = RuleEngine()
        
        # Create a simple test AST
        self.test_ast = {
            "type": "module",
            "children": [
                {
                    "type": "function_definition",
                    "name": "test_function",
                    "start_line": 1,
                    "start_column": 0,
                    "body": {
                        "type": "block",
                        "children": [
                            {"type": "expression_statement", "start_line": 2},
                            {"type": "expression_statement", "start_line": 3},
                            {"type": "expression_statement", "start_line": 4}
                        ]
                    }
                },
                {
                    "type": "assignment",
                    "target": {"name": "password"},
                    "value": {"type": "string", "value": "secret123"},
                    "start_line": 6,
                    "start_column": 0
                }
            ]
        }
        
        self.context = {
            "file_path": "test_file.py",
            "language": "python"
        }
    
    def test_pattern_rule(self):
        # Create a pattern rule to find hardcoded passwords
        rule = PatternRule(
            rule_id="TEST001",
            name="Test Pattern Rule",
            description="Test pattern rule",
            category=RuleCategory.SECURITY,
            severity=RuleSeverity.ERROR,
            node_type="assignment",
            pattern={
                "type": "assignment",
                "target": {"name": "password"}
            }
        )
        
        # Add the rule to the engine
        self.rule_engine.add_rule(rule)
        
        # Evaluate the rule
        issues = self.rule_engine.evaluate(self.test_ast, self.context)
        
        # Check that the rule found the issue
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["rule_id"], "TEST001")
        self.assertEqual(issues[0]["file"], "test_file.py")
        self.assertEqual(issues[0]["line"], 6)
    
    def test_function_rule(self):
        # Create a function to check if a function is too short
        def check_function_length(node, context):
            if "body" in node and "children" in node["body"]:
                if len(node["body"]["children"]) < 5:  # Less than 5 statements
                    return f"Function '{node.get('name', 'unknown')}' is too short ({len(node['body']['children'])} statements)"
            return None
        
        # Create a function rule
        rule = FunctionRule(
            rule_id="TEST002",
            name="Function Too Short",
            description="Test function rule",
            category=RuleCategory.QUALITY,
            severity=RuleSeverity.WARNING,
            node_types=["function_definition"],
            evaluation_fn=check_function_length
        )
        
        # Add the rule to the engine
        self.rule_engine.add_rule(rule)
        
        # Evaluate the rule
        issues = self.rule_engine.evaluate(self.test_ast, self.context)
        
        # Check that the rule found the issue
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["rule_id"], "TEST002")
        self.assertEqual(issues[0]["file"], "test_file.py")
        self.assertEqual(issues[0]["line"], 1)
    
    def test_multiple_rules(self):
        # Create both rules from the previous tests
        pattern_rule = PatternRule(
            rule_id="TEST001",
            name="Test Pattern Rule",
            description="Test pattern rule",
            category=RuleCategory.SECURITY,
            severity=RuleSeverity.ERROR,
            node_type="assignment",
            pattern={
                "type": "assignment",
                "target": {"name": "password"}
            }
        )
        
        def check_function_length(node, context):
            if "body" in node and "children" in node["body"]:
                if len(node["body"]["children"]) < 5:  # Less than 5 statements
                    return f"Function '{node.get('name', 'unknown')}' is too short ({len(node['body']['children'])} statements)"
            return None
        
        function_rule = FunctionRule(
            rule_id="TEST002",
            name="Function Too Short",
            description="Test function rule",
            category=RuleCategory.QUALITY,
            severity=RuleSeverity.WARNING,
            node_types=["function_definition"],
            evaluation_fn=check_function_length
        )
        
        # Add both rules to the engine
        self.rule_engine.add_rules([pattern_rule, function_rule])
        
        # Evaluate the rules
        issues = self.rule_engine.evaluate(self.test_ast, self.context)
        
        # Check that both rules found issues
        self.assertEqual(len(issues), 2)
        
        # Check that the issues have the correct rule IDs
        rule_ids = [issue["rule_id"] for issue in issues]
        self.assertIn("TEST001", rule_ids)
        self.assertIn("TEST002", rule_ids)

if __name__ == "__main__":
    unittest.main()