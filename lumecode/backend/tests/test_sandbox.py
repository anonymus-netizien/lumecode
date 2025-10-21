import os
import sys
import unittest
import tempfile
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.sandbox import Sandbox, NetworkSandbox, ResourceLimits, SandboxException


class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox = Sandbox()
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_file.txt")
        with open(self.test_file, "w") as f:
            f.write("test content")

    def tearDown(self):
        self.sandbox.cleanup()
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_validate_file_access(self):
        # Test valid file access
        self.sandbox.allowed_paths = [self.temp_dir]
        self.assertTrue(self.sandbox.validate_file_access(self.test_file))
        
        # Test invalid file access
        self.sandbox.allowed_paths = ["/different/path"]
        with self.assertRaises(SandboxException):
            self.sandbox.validate_file_access(self.test_file)

    @patch('subprocess.run')
    def test_execute_command(self, mock_run):
        # Setup mock
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "command output"
        mock_run.return_value = mock_process
        
        # Test successful command execution
        result = self.sandbox.execute_command("echo test")
        self.assertEqual(result.returncode, 0)
        
        # Test with timeout
        self.sandbox.execute_command("echo test", timeout=1)
        mock_run.assert_called_with(
            "echo test", 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=1
        )

    def test_run_python_code(self):
        # Test running valid Python code
        code = "result = 2 + 2"
        namespace = {}
        self.sandbox.run_python_code(code, namespace)
        self.assertEqual(namespace.get("result"), 4)
        
        # Test running code with syntax error
        with self.assertRaises(SandboxException):
            self.sandbox.run_python_code("this is not valid python", {})


class TestResourceLimits(unittest.TestCase):
    def setUp(self):
        self.resource_limits = ResourceLimits()

    @patch('resource.setrlimit')
    def test_set_memory_limit(self, mock_setrlimit):
        self.resource_limits.set_memory_limit(100)  # 100 MB
        mock_setrlimit.assert_called()

    @patch('resource.setrlimit')
    def test_set_cpu_time_limit(self, mock_setrlimit):
        self.resource_limits.set_cpu_time_limit(10)  # 10 seconds
        mock_setrlimit.assert_called()


class TestNetworkSandbox(unittest.TestCase):
    def setUp(self):
        self.network_sandbox = NetworkSandbox()

    def test_validate_url(self):
        # Test allowed domain
        self.network_sandbox.allowed_domains = ["example.com"]
        self.assertTrue(self.network_sandbox.validate_url("https://example.com/api"))
        
        # Test disallowed domain
        self.network_sandbox.allowed_domains = ["example.com"]
        with self.assertRaises(SandboxException):
            self.network_sandbox.validate_url("https://malicious.com")

    @patch('requests.get')
    def test_safe_request(self, mock_get):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "response data"
        mock_get.return_value = mock_response
        
        # Test successful request
        self.network_sandbox.allowed_domains = ["api.example.com"]
        response = self.network_sandbox.safe_request("https://api.example.com/data")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "response data")
        
        # Test disallowed domain
        self.network_sandbox.allowed_domains = ["api.example.com"]
        with self.assertRaises(SandboxException):
            self.network_sandbox.safe_request("https://malicious.com/data")


if __name__ == "__main__":
    unittest.main()