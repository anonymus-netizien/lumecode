import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .base import BaseAgent, AgentType, AgentStatus
from .sandbox import Sandbox
from ..analysis.core import AnalysisEngine
from ..analysis.parser import ASTParser

logger = logging.getLogger(__name__)


class RefactoringAgent(BaseAgent):
    """Agent responsible for code refactoring tasks.
    
    This agent analyzes code and suggests or applies refactoring improvements
    based on best practices and code quality metrics.
    """
    
    def __init__(self, 
                 agent_id: str, 
                 workspace_path: Union[str, Path],
                 config: Optional[Dict[str, Any]] = None):
        """Initialize the RefactoringAgent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            workspace_path: Path to the workspace directory
            config: Configuration options for the agent
        """
        super().__init__(agent_id, AgentType.REFACTORING, workspace_path, config)
        self.analysis_engine = AnalysisEngine(workspace_path)
        self.sandbox = Sandbox()
        self.sandbox.allowed_paths = [str(workspace_path)]
        self.refactoring_patterns = self._load_refactoring_patterns()
        
    def _load_refactoring_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load refactoring patterns and rules.
        
        Returns:
            Dictionary of refactoring patterns by language
        """
        # In a real implementation, these would be loaded from a database or config files
        # For now, we'll define some basic patterns inline
        return {
            "python": {
                "long_function": {
                    "description": "Function is too long and should be split",
                    "threshold": 50,  # lines
                    "suggestion": "Consider breaking this function into smaller, more focused functions"
                },
                "complex_function": {
                    "description": "Function is too complex",
                    "threshold": 10,  # cyclomatic complexity
                    "suggestion": "Reduce complexity by extracting helper functions"
                },
                "unused_import": {
                    "description": "Unused import statement",
                    "suggestion": "Remove unused import"
                }
            },
            "javascript": {
                "long_function": {
                    "description": "Function is too long and should be split",
                    "threshold": 40,  # lines
                    "suggestion": "Consider breaking this function into smaller, more focused functions"
                },
                "nested_callbacks": {
                    "description": "Deeply nested callbacks",
                    "threshold": 3,  # nesting level
                    "suggestion": "Refactor using Promises or async/await"
                }
            }
        }
    
    async def start(self) -> bool:
        """Start the refactoring agent.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            self.status = AgentStatus.RUNNING
            logger.info(f"RefactoringAgent {self.agent_id} started")
            return True
        except Exception as e:
            logger.error(f"Failed to start RefactoringAgent: {e}")
            self.status = AgentStatus.FAILED
            return False
    
    async def stop(self) -> bool:
        """Stop the refactoring agent.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            self.status = AgentStatus.STOPPED
            self.sandbox.cleanup()
            logger.info(f"RefactoringAgent {self.agent_id} stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop RefactoringAgent: {e}")
            return False
    
    async def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Analyze a file for potential refactoring opportunities.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary containing refactoring suggestions
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}
                
            # Validate file access through sandbox
            self.sandbox.validate_file_access(str(file_path))
            
            # Determine language from file extension
            language = self._get_language_from_extension(file_path.suffix)
            if not language or language not in self.refactoring_patterns:
                return {"error": f"Unsupported language for file: {file_path}"}
            
            # Parse the file
            ast = self.analysis_engine.parse_file(file_path)
            if not ast:
                return {"error": f"Failed to parse file: {file_path}"}
            
            # Analyze for refactoring opportunities
            suggestions = self._find_refactoring_opportunities(ast, language)
            
            return {
                "file": str(file_path),
                "language": language,
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {"error": str(e)}
    
    def _get_language_from_extension(self, extension: str) -> Optional[str]:
        """Determine programming language from file extension.
        
        Args:
            extension: File extension including the dot (e.g., '.py')
            
        Returns:
            Language identifier or None if unsupported
        """
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript"
        }
        return extension_map.get(extension.lower())
    
    def _find_refactoring_opportunities(self, ast: Any, language: str) -> List[Dict[str, Any]]:
        """Find refactoring opportunities in the AST.
        
        Args:
            ast: Abstract Syntax Tree of the code
            language: Programming language identifier
            
        Returns:
            List of refactoring suggestions
        """
        suggestions = []
        patterns = self.refactoring_patterns.get(language, {})
        
        # This is a simplified implementation
        # In a real system, we would traverse the AST and apply more sophisticated analysis
        
        # Example: Check for long functions
        if "long_function" in patterns and hasattr(ast, "functions"):
            for func in ast.functions:
                if func.end_line - func.start_line > patterns["long_function"]["threshold"]:
                    suggestions.append({
                        "type": "long_function",
                        "description": patterns["long_function"]["description"],
                        "suggestion": patterns["long_function"]["suggestion"],
                        "location": {
                            "start_line": func.start_line,
                            "end_line": func.end_line,
                            "name": func.name
                        }
                    })
        
        # More pattern checks would be implemented here
        
        return suggestions
    
    async def apply_refactoring(self, file_path: Union[str, Path], refactoring_id: str) -> Dict[str, Any]:
        """Apply a specific refactoring to a file.
        
        Args:
            file_path: Path to the file to refactor
            refactoring_id: ID of the refactoring to apply
            
        Returns:
            Result of the refactoring operation
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}
                
            # Validate file access through sandbox
            self.sandbox.validate_file_access(str(file_path))
            
            # In a real implementation, we would:
            # 1. Load the file content
            # 2. Parse it to AST
            # 3. Apply the specific refactoring transformation
            # 4. Generate the modified code
            # 5. Write it back to the file or return the diff
            
            # For now, we'll just return a placeholder result
            return {
                "file": str(file_path),
                "refactoring_id": refactoring_id,
                "status": "not_implemented",
                "message": "Refactoring application is not yet implemented"
            }
            
        except Exception as e:
            logger.error(f"Error applying refactoring to {file_path}: {e}")
            return {"error": str(e)}
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a refactoring task.
        
        Args:
            task_data: Task data containing file paths and refactoring options
            
        Returns:
            Task processing results
        """
        try:
            task_type = task_data.get("type")
            
            if task_type == "analyze":
                file_paths = task_data.get("file_paths", [])
                results = {}
                
                for file_path in file_paths:
                    results[file_path] = await self.analyze_file(file_path)
                
                return {
                    "status": "completed",
                    "results": results
                }
                
            elif task_type == "apply":
                file_path = task_data.get("file_path")
                refactoring_id = task_data.get("refactoring_id")
                
                if not file_path or not refactoring_id:
                    return {"error": "Missing file_path or refactoring_id"}
                
                result = await self.apply_refactoring(file_path, refactoring_id)
                
                return {
                    "status": "completed",
                    "result": result
                }
                
            else:
                return {"error": f"Unknown task type: {task_type}"}
                
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }