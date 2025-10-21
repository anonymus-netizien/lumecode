import os
import sys
import json
import time
import signal
import logging
import resource
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class SandboxException(Exception):
    """Exception raised for sandbox-related errors"""

    pass


class ResourceLimits:
    """Resource limits for sandboxed execution"""

    def __init__(
        self,
        cpu_time_seconds: int = 30,
        memory_mb: int = 512,
        file_size_mb: int = 10,
        num_processes: int = 10,
        num_files: int = 100,
    ):
        """Initialize resource limits

        Args:
            cpu_time_seconds: Maximum CPU time in seconds
            memory_mb: Maximum memory usage in MB
            file_size_mb: Maximum file size in MB
            num_processes: Maximum number of processes
            num_files: Maximum number of open files
        """
        self.cpu_time_seconds = cpu_time_seconds
        self.memory_mb = memory_mb
        self.file_size_mb = file_size_mb
        self.num_processes = num_processes
        self.num_files = num_files


class Sandbox:
    """Sandbox for executing agent code safely"""

    def __init__(self, workspace_dir: str, resource_limits: Optional[ResourceLimits] = None):
        """Initialize the sandbox

        Args:
            workspace_dir: Directory for sandbox workspace
            resource_limits: Resource limits for sandboxed execution
        """
        self.workspace_dir = workspace_dir
        self.resource_limits = resource_limits or ResourceLimits()

        # Create workspace directory if it doesn't exist
        os.makedirs(self.workspace_dir, exist_ok=True)

        # Set up logging
        self.log_file = os.path.join(self.workspace_dir, "sandbox.log")
        self.file_handler = logging.FileHandler(self.log_file)
        self.file_handler.setLevel(logging.INFO)
        logger.addHandler(self.file_handler)

        logger.info(f"Sandbox initialized with workspace: {self.workspace_dir}")

    def _set_resource_limits(self):
        """Set resource limits for the current process"""
        # Set CPU time limit
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (self.resource_limits.cpu_time_seconds, self.resource_limits.cpu_time_seconds),
        )

        # Set memory limit
        memory_bytes = self.resource_limits.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

        # Set file size limit
        file_size_bytes = self.resource_limits.file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_bytes, file_size_bytes))

        # Set process limit
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (self.resource_limits.num_processes, self.resource_limits.num_processes),
        )

        # Set open files limit
        resource.setrlimit(
            resource.RLIMIT_NOFILE, (self.resource_limits.num_files, self.resource_limits.num_files)
        )

    def _preexec_fn(self):
        """Function to call before executing a command in a subprocess"""
        # Set resource limits
        self._set_resource_limits()

        # Create a new process group
        os.setsid()

    def run_command(
        self, command: List[str], timeout: int = 30, env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """Run a command in the sandbox

        Args:
            command: Command to run as a list of strings
            timeout: Timeout in seconds
            env: Environment variables

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        logger.info(f"Running command: {' '.join(command)}")

        # Set up environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Add workspace to PATH
        process_env["PATH"] = f"{self.workspace_dir}:{process_env.get('PATH', '')}"

        try:
            # Run the command
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.workspace_dir,
                env=process_env,
                preexec_fn=self._preexec_fn,
            )

            # Wait for the process to complete with timeout
            stdout, stderr = process.communicate(timeout=timeout)

            return process.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")

        except subprocess.TimeoutExpired:
            # Kill the process group if it times out
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                time.sleep(0.5)
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, AttributeError):
                pass

            return -1, "", "Command timed out"

        except Exception as e:
            logger.error(f"Error running command: {e}")
            return -1, "", str(e)

    def run_python_code(
        self, code: str, timeout: int = 30, env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """Run Python code in the sandbox

        Args:
            code: Python code to run
            timeout: Timeout in seconds
            env: Environment variables

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        # Write code to a temporary file
        code_file = os.path.join(self.workspace_dir, "code.py")
        with open(code_file, "w") as f:
            f.write(code)

        # Run the code
        return self.run_command([sys.executable, code_file], timeout, env)

    def run_python_function(
        self,
        function_code: str,
        function_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        timeout: int = 30,
    ) -> Any:
        """Run a Python function in the sandbox and return its result

        Args:
            function_code: Code defining the function
            function_name: Name of the function to call
            args: Positional arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            timeout: Timeout in seconds

        Returns:
            Function result
        """
        args = args or []
        kwargs = kwargs or {}

        # Create a wrapper script that calls the function and serializes the result
        wrapper_code = f"""
{function_code}

import json
import sys

try:
    result = {function_name}(*{args}, **{kwargs})
    print(json.dumps({{
        "status": "success",
        "result": result
    }}))
    sys.exit(0)
except Exception as e:
    print(json.dumps({{
        "status": "error",
        "error": str(e)
    }}))
    sys.exit(1)
"""

        # Run the wrapper script
        return_code, stdout, stderr = self.run_python_code(wrapper_code, timeout)

        if return_code != 0:
            raise SandboxException(f"Function execution failed: {stderr}")

        try:
            # Parse the result
            result = json.loads(stdout.strip())

            if result["status"] == "success":
                return result["result"]
            else:
                raise SandboxException(f"Function execution failed: {result['error']}")

        except json.JSONDecodeError:
            raise SandboxException(f"Failed to parse function result: {stdout}")

    def validate_file_access(self, file_path: str, allowed_paths: List[str] = None) -> bool:
        """Validate that a file path is within allowed paths

        Args:
            file_path: Path to validate
            allowed_paths: List of allowed paths, defaults to workspace_dir

        Returns:
            True if the file path is valid, False otherwise
        """
        allowed_paths = allowed_paths or [self.workspace_dir]

        # Resolve the absolute path
        abs_path = os.path.abspath(file_path)

        # Check if the path is within any allowed path
        for allowed_path in allowed_paths:
            allowed_abs_path = os.path.abspath(allowed_path)
            if abs_path.startswith(allowed_abs_path):
                return True

        return False

    def safe_read_file(self, file_path: str, allowed_paths: List[str] = None) -> str:
        """Safely read a file

        Args:
            file_path: Path to the file to read
            allowed_paths: List of allowed paths, defaults to workspace_dir

        Returns:
            File contents
        """
        if not self.validate_file_access(file_path, allowed_paths):
            raise SandboxException(f"Access denied: {file_path} is outside allowed paths")

        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            raise SandboxException(f"Failed to read file {file_path}: {e}")

    def safe_write_file(
        self, file_path: str, content: str, allowed_paths: List[str] = None
    ) -> None:
        """Safely write to a file

        Args:
            file_path: Path to the file to write
            content: Content to write
            allowed_paths: List of allowed paths, defaults to workspace_dir
        """
        if not self.validate_file_access(file_path, allowed_paths):
            raise SandboxException(f"Access denied: {file_path} is outside allowed paths")

        try:
            with open(file_path, "w") as f:
                f.write(content)
        except Exception as e:
            raise SandboxException(f"Failed to write to file {file_path}: {e}")

    def cleanup(self):
        """Clean up the sandbox"""
        logger.info("Cleaning up sandbox")

        # Remove the file handler
        logger.removeHandler(self.file_handler)
        self.file_handler.close()


class NetworkSandbox(Sandbox):
    """Sandbox with network access control"""

    def __init__(
        self,
        workspace_dir: str,
        resource_limits: Optional[ResourceLimits] = None,
        allowed_hosts: List[str] = None,
        allowed_ports: List[int] = None,
    ):
        """Initialize the network sandbox

        Args:
            workspace_dir: Directory for sandbox workspace
            resource_limits: Resource limits for sandboxed execution
            allowed_hosts: List of allowed hosts
            allowed_ports: List of allowed ports
        """
        super().__init__(workspace_dir, resource_limits)
        self.allowed_hosts = allowed_hosts or []
        self.allowed_ports = allowed_ports or [80, 443]  # Default to HTTP/HTTPS

    def run_command(
        self, command: List[str], timeout: int = 30, env: Optional[Dict[str, str]] = None
    ) -> Tuple[int, str, str]:
        """Run a command with network restrictions

        Args:
            command: Command to run as a list of strings
            timeout: Timeout in seconds
            env: Environment variables

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        # Set up environment with network restrictions
        process_env = env or {}

        # Set allowed hosts and ports as environment variables
        process_env["ALLOWED_HOSTS"] = ",".join(self.allowed_hosts)
        process_env["ALLOWED_PORTS"] = ",".join(map(str, self.allowed_ports))

        # Run the command with the modified environment
        return super().run_command(command, timeout, process_env)
