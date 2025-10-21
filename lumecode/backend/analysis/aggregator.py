import logging
import time
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """Types of results that can be aggregated."""
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    REFACTORING = "refactoring"
    CODE_REVIEW = "code_review"
    CUSTOM = "custom"


class ResultPriority(Enum):
    """Priority levels for results."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ResultAggregator:
    """Aggregates and manages results from various analysis sources.
    
    This class is responsible for collecting, organizing, and providing access to
    results from different analysis engines, agents, and plugins.
    """
    
    def __init__(self, workspace_path: Union[str, Path]):
        """Initialize the ResultAggregator.
        
        Args:
            workspace_path: Path to the workspace directory
        """
        self.workspace_path = Path(workspace_path)
        self.results: Dict[str, Dict[str, Any]] = {}
        self.result_index: Dict[str, List[str]] = {}
        self.result_count = 0
        self.last_updated = time.time()
    
    def add_result(self, 
                  result_type: Union[ResultType, str], 
                  source: str, 
                  data: Dict[str, Any],
                  file_path: Optional[Union[str, Path]] = None,
                  priority: Optional[Union[ResultPriority, str]] = None,
                  tags: Optional[List[str]] = None) -> str:
        """Add a result to the aggregator.
        
        Args:
            result_type: Type of the result
            source: Source of the result (e.g., agent ID, plugin name)
            data: Result data
            file_path: Path to the file associated with the result
            priority: Priority of the result
            tags: Tags for categorizing the result
            
        Returns:
            Result ID
        """
        # Convert enums to strings if needed
        if isinstance(result_type, ResultType):
            result_type = result_type.value
            
        if isinstance(priority, ResultPriority):
            priority = priority.value
        elif priority is None:
            priority = ResultPriority.MEDIUM.value
            
        # Generate a unique result ID
        result_id = f"{result_type}_{source}_{self.result_count}"
        self.result_count += 1
        
        # Create the result entry
        result = {
            "id": result_id,
            "type": result_type,
            "source": source,
            "data": data,
            "file_path": str(file_path) if file_path else None,
            "priority": priority,
            "tags": tags or [],
            "timestamp": time.time()
        }
        
        # Store the result
        self.results[result_id] = result
        
        # Update indexes for faster lookup
        if result_type not in self.result_index:
            self.result_index[result_type] = []
        self.result_index[result_type].append(result_id)
        
        self.last_updated = time.time()
        logger.debug(f"Added result {result_id} of type {result_type} from {source}")
        
        return result_id
    
    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific result by ID.
        
        Args:
            result_id: ID of the result to retrieve
            
        Returns:
            Result data or None if not found
        """
        return self.results.get(result_id)
    
    def get_results_by_type(self, result_type: Union[ResultType, str]) -> List[Dict[str, Any]]:
        """Get all results of a specific type.
        
        Args:
            result_type: Type of results to retrieve
            
        Returns:
            List of results
        """
        if isinstance(result_type, ResultType):
            result_type = result_type.value
            
        result_ids = self.result_index.get(result_type, [])
        return [self.results[result_id] for result_id in result_ids]
    
    def get_results_by_file(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Get all results for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of results
        """
        file_path_str = str(file_path)
        return [result for result in self.results.values() if result["file_path"] == file_path_str]
    
    def get_results_by_priority(self, priority: Union[ResultPriority, str]) -> List[Dict[str, Any]]:
        """Get all results with a specific priority.
        
        Args:
            priority: Priority level
            
        Returns:
            List of results
        """
        if isinstance(priority, ResultPriority):
            priority = priority.value
            
        return [result for result in self.results.values() if result["priority"] == priority]
    
    def get_results_by_source(self, source: str) -> List[Dict[str, Any]]:
        """Get all results from a specific source.
        
        Args:
            source: Source identifier
            
        Returns:
            List of results
        """
        return [result for result in self.results.values() if result["source"] == source]
    
    def get_results_by_tags(self, tags: List[str], match_all: bool = False) -> List[Dict[str, Any]]:
        """Get all results with specific tags.
        
        Args:
            tags: List of tags to match
            match_all: If True, all tags must match; if False, any tag can match
            
        Returns:
            List of results
        """
        if match_all:
            return [result for result in self.results.values() 
                   if all(tag in result["tags"] for tag in tags)]
        else:
            return [result for result in self.results.values() 
                   if any(tag in result["tags"] for tag in tags)]
    
    def update_result(self, result_id: str, data: Dict[str, Any]) -> bool:
        """Update an existing result.
        
        Args:
            result_id: ID of the result to update
            data: New data to merge with existing result
            
        Returns:
            True if update was successful, False otherwise
        """
        if result_id not in self.results:
            logger.warning(f"Cannot update non-existent result: {result_id}")
            return False
        
        # Update the result data
        self.results[result_id]["data"].update(data)
        self.results[result_id]["timestamp"] = time.time()
        
        self.last_updated = time.time()
        logger.debug(f"Updated result {result_id}")
        
        return True
    
    def remove_result(self, result_id: str) -> bool:
        """Remove a result.
        
        Args:
            result_id: ID of the result to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        if result_id not in self.results:
            logger.warning(f"Cannot remove non-existent result: {result_id}")
            return False
        
        # Get the result type for index cleanup
        result_type = self.results[result_id]["type"]
        
        # Remove from index
        if result_type in self.result_index and result_id in self.result_index[result_type]:
            self.result_index[result_type].remove(result_id)
        
        # Remove the result
        del self.results[result_id]
        
        self.last_updated = time.time()
        logger.debug(f"Removed result {result_id}")
        
        return True
    
    def clear_results(self, result_type: Optional[Union[ResultType, str]] = None) -> int:
        """Clear results, optionally filtering by type.
        
        Args:
            result_type: Type of results to clear (if None, clear all)
            
        Returns:
            Number of results cleared
        """
        if result_type is None:
            # Clear all results
            count = len(self.results)
            self.results = {}
            self.result_index = {}
            self.last_updated = time.time()
            logger.info(f"Cleared all {count} results")
            return count
        
        # Convert enum to string if needed
        if isinstance(result_type, ResultType):
            result_type = result_type.value
        
        # Get result IDs of the specified type
        result_ids = self.result_index.get(result_type, [])
        count = len(result_ids)
        
        # Remove each result
        for result_id in result_ids:
            if result_id in self.results:
                del self.results[result_id]
        
        # Clear the index for this type
        self.result_index[result_type] = []
        
        self.last_updated = time.time()
        logger.info(f"Cleared {count} results of type {result_type}")
        
        return count
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all results.
        
        Returns:
            Summary dictionary
        """
        # Count results by type
        type_counts = {}
        for result_type, result_ids in self.result_index.items():
            type_counts[result_type] = len(result_ids)
        
        # Count results by priority
        priority_counts = {priority.value: 0 for priority in ResultPriority}
        for result in self.results.values():
            priority = result["priority"]
            if priority in priority_counts:
                priority_counts[priority] += 1
        
        return {
            "total_results": len(self.results),
            "by_type": type_counts,
            "by_priority": priority_counts,
            "last_updated": self.last_updated
        }
    
    def export_results(self, format_type: str = "json") -> str:
        """Export results in the specified format.
        
        Args:
            format_type: Format to export (currently only 'json' is supported)
            
        Returns:
            Exported results as a string
        """
        if format_type.lower() == "json":
            return json.dumps({
                "results": list(self.results.values()),
                "summary": self.get_summary()
            }, indent=2)
        else:
            logger.warning(f"Unsupported export format: {format_type}")
            return ""
    
    def import_results(self, data: str, format_type: str = "json") -> int:
        """Import results from the specified format.
        
        Args:
            data: Data to import
            format_type: Format of the data (currently only 'json' is supported)
            
        Returns:
            Number of results imported
        """
        if format_type.lower() == "json":
            try:
                imported_data = json.loads(data)
                imported_results = imported_data.get("results", [])
                
                # Clear existing results first
                self.clear_results()
                
                # Import each result
                for result in imported_results:
                    result_id = result["id"]
                    self.results[result_id] = result
                    
                    # Update index
                    result_type = result["type"]
                    if result_type not in self.result_index:
                        self.result_index[result_type] = []
                    self.result_index[result_type].append(result_id)
                
                # Update counter to avoid ID conflicts
                self.result_count = len(self.results)
                self.last_updated = time.time()
                
                logger.info(f"Imported {len(imported_results)} results")
                return len(imported_results)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON data: {e}")
                return 0
        else:
            logger.warning(f"Unsupported import format: {format_type}")
            return 0