import os
import shutil
import asyncio
import unittest
from pathlib import Path

from lumecode.backend.analysis import ASTParser, AnalysisEngine

class TestASTParser(unittest.TestCase):
    def setUp(self):
        self.parser = ASTParser()
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        self.test_file_path = os.path.join(self.test_dir, "sample.py")
        
        # Create test directory and file if they don't exist
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create a simple Python file for testing
        with open(self.test_file_path, "w") as f:
            f.write("""
# Sample Python file for testing

def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self, name):
        self.name = name
        
    def greet(self):
        return f"Hello, {self.name}!"
        
# Call the function
hello_world()
""")
    
    def tearDown(self):
        """Clean up test files and directories"""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        if os.path.exists(self.test_dir) and not os.listdir(self.test_dir):
            os.rmdir(self.test_dir)
    
    def test_parse_code(self):
        """Test parsing code directly"""
        code = "def test(): return True"
        result = self.parser.parse_code(code, "python")
        
        self.assertEqual(result["language"], "python")
        self.assertIn("ast", result)
        self.assertEqual(result["ast"]["type"], "module")
    
    def test_parse_file(self):
        """Test parsing a file"""
        result = self.parser.parse_file(self.test_file_path)
        
        self.assertEqual(result["language"], "python")
        self.assertIn("ast", result)
        self.assertEqual(result["ast"]["type"], "module")
        self.assertEqual(result["file_path"], self.test_file_path)

class TestAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AnalysisEngine()
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data_engine")
        self.test_file_path = os.path.join(self.test_dir, "sample.py")
        
        # Create test directory and file for this test class
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create a simple Python file for testing
        with open(self.test_file_path, "w") as f:
            f.write("""
# Sample Python file for testing

def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self, name):
        self.name = name
        
    def greet(self):
        return f"Hello, {self.name}!"
        
# Call the function
hello_world()
""")
    
    def tearDown(self):
        """Clean up test files and directories"""
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        if os.path.exists(self.test_dir):
            # Remove directory even if not empty
            shutil.rmtree(self.test_dir)
    
    def test_parse_file(self):
        """Test parsing a file using the analysis engine"""
        result = asyncio.run(self.engine.parse_file(self.test_file_path))
        
        self.assertEqual(result["language"], "python")
        self.assertIn("ast", result)
        self.assertEqual(result["ast"]["type"], "module")
        self.assertEqual(result["file_path"], self.test_file_path)
    
    def test_parse_code(self):
        """Test parsing code using the analysis engine"""
        code = "def test(): return True"
        result = asyncio.run(self.engine.parse_code(code, "python"))
        
        self.assertEqual(result["language"], "python")
        self.assertIn("ast", result)
        self.assertEqual(result["ast"]["type"], "module")

if __name__ == "__main__":
    unittest.main()