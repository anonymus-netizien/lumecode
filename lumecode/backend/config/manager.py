import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigScope(Enum):
    """Configuration scope levels."""
    SYSTEM = "system"      # System-wide settings
    USER = "user"          # User-specific settings
    PROJECT = "project"    # Project-specific settings
    SESSION = "session"    # Current session only


class ConfigManager:
    """Manages configuration settings for the Lumecode platform.
    
    Handles loading, saving, and accessing configuration at different scopes:
    - System: Global settings for all users
    - User: User-specific settings
    - Project: Settings for a specific project
    - Session: Temporary settings for the current session
    
    Configuration is stored in a hierarchical structure and follows an override
    pattern where more specific scopes override more general ones.
    """
    
    def __init__(self, 
                 base_dir: Optional[Union[str, Path]] = None,
                 project_dir: Optional[Union[str, Path]] = None):
        """Initialize the ConfigManager.
        
        Args:
            base_dir: Base directory for configuration files
            project_dir: Current project directory
        """
        # Set up base directories
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Default to ~/.lumecode
            self.base_dir = Path.home() / ".lumecode"
        
        # Create base directory if it doesn't exist
        self.base_dir.mkdir(exist_ok=True, parents=True)
        
        # Set up project directory
        self.project_dir = Path(project_dir) if project_dir else None
        
        # Initialize configuration storage
        self._config: Dict[str, Dict[str, Any]] = {
            ConfigScope.SYSTEM.value: {},
            ConfigScope.USER.value: {},
            ConfigScope.PROJECT.value: {},
            ConfigScope.SESSION.value: {}
        }
        
        # Load configurations
        self._load_system_config()
        self._load_user_config()
        if self.project_dir:
            self._load_project_config()
    
    def _get_system_config_path(self) -> Path:
        """Get the path to the system configuration file."""
        return self.base_dir / "system.json"
    
    def _get_user_config_path(self) -> Path:
        """Get the path to the user configuration file."""
        return self.base_dir / "user.json"
    
    def _get_project_config_path(self) -> Path:
        """Get the path to the project configuration file."""
        if not self.project_dir:
            raise ValueError("Project directory not set")
        return self.project_dir / ".lumecode" / "config.json"
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
        """
        if not file_path.exists():
            logger.debug(f"Configuration file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading configuration file {file_path}: {e}")
            return {}
    
    def _save_config_file(self, file_path: Path, config: Dict[str, Any]) -> bool:
        """Save configuration to a file.
        
        Args:
            file_path: Path to the configuration file
            config: Configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(exist_ok=True, parents=True)
            
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving configuration file {file_path}: {e}")
            return False
    
    def _load_system_config(self):
        """Load system configuration."""
        system_config = self._load_config_file(self._get_system_config_path())
        self._config[ConfigScope.SYSTEM.value] = system_config
    
    def _load_user_config(self):
        """Load user configuration."""
        user_config = self._load_config_file(self._get_user_config_path())
        self._config[ConfigScope.USER.value] = user_config
    
    def _load_project_config(self):
        """Load project configuration."""
        if not self.project_dir:
            return
        
        project_config = self._load_config_file(self._get_project_config_path())
        self._config[ConfigScope.PROJECT.value] = project_config
    
    def get(self, key: str, default: Any = None, scope: Optional[Union[ConfigScope, str]] = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (can use dot notation for nested keys)
            default: Default value if key is not found
            scope: Specific scope to get the value from (if None, use override hierarchy)
            
        Returns:
            Configuration value or default
        """
        # If scope is specified, only look in that scope
        if scope:
            scope_value = scope.value if isinstance(scope, ConfigScope) else scope
            return self._get_from_scope(scope_value, key, default)
        
        # Otherwise, use the override hierarchy (session > project > user > system)
        for scope_value in [ConfigScope.SESSION.value, ConfigScope.PROJECT.value, 
                           ConfigScope.USER.value, ConfigScope.SYSTEM.value]:
            value = self._get_from_scope(scope_value, key, None)
            if value is not None:
                return value
        
        return default
    
    def _get_from_scope(self, scope: str, key: str, default: Any = None) -> Any:
        """Get a value from a specific scope.
        
        Args:
            scope: Configuration scope
            key: Configuration key (can use dot notation for nested keys)
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        if scope not in self._config:
            return default
        
        # Handle nested keys with dot notation
        keys = key.split('.')
        value = self._config[scope]
        
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return default
            value = value[k]
        
        return value
    
    def set(self, key: str, value: Any, scope: Union[ConfigScope, str] = ConfigScope.SESSION) -> bool:
        """Set a configuration value.
        
        Args:
            key: Configuration key (can use dot notation for nested keys)
            value: Value to set
            scope: Configuration scope to set the value in
            
        Returns:
            True if successful, False otherwise
        """
        scope_value = scope.value if isinstance(scope, ConfigScope) else scope
        
        if scope_value not in self._config:
            logger.error(f"Invalid configuration scope: {scope_value}")
            return False
        
        # Handle nested keys with dot notation
        keys = key.split('.')
        config = self._config[scope_value]
        
        # Navigate to the nested dictionary
        for i, k in enumerate(keys[:-1]):
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save the configuration if it's not session scope
        if scope_value != ConfigScope.SESSION.value:
            return self._save_scope(scope_value)
        
        return True
    
    def _save_scope(self, scope: str) -> bool:
        """Save a specific configuration scope.
        
        Args:
            scope: Configuration scope to save
            
        Returns:
            True if successful, False otherwise
        """
        if scope == ConfigScope.SYSTEM.value:
            return self._save_config_file(
                self._get_system_config_path(), 
                self._config[ConfigScope.SYSTEM.value]
            )
        elif scope == ConfigScope.USER.value:
            return self._save_config_file(
                self._get_user_config_path(), 
                self._config[ConfigScope.USER.value]
            )
        elif scope == ConfigScope.PROJECT.value:
            if not self.project_dir:
                logger.error("Cannot save project configuration: project directory not set")
                return False
            return self._save_config_file(
                self._get_project_config_path(), 
                self._config[ConfigScope.PROJECT.value]
            )
        elif scope == ConfigScope.SESSION.value:
            # Session configuration is not persisted
            return True
        else:
            logger.error(f"Invalid configuration scope: {scope}")
            return False
    
    def delete(self, key: str, scope: Union[ConfigScope, str] = ConfigScope.SESSION) -> bool:
        """Delete a configuration value.
        
        Args:
            key: Configuration key (can use dot notation for nested keys)
            scope: Configuration scope to delete the value from
            
        Returns:
            True if successful, False otherwise
        """
        scope_value = scope.value if isinstance(scope, ConfigScope) else scope
        
        if scope_value not in self._config:
            logger.error(f"Invalid configuration scope: {scope_value}")
            return False
        
        # Handle nested keys with dot notation
        keys = key.split('.')
        config = self._config[scope_value]
        
        # Navigate to the parent dictionary
        parent = None
        for i, k in enumerate(keys[:-1]):
            if k not in config or not isinstance(config[k], dict):
                # Key doesn't exist, nothing to delete
                return True
            parent = config
            config = config[k]
        
        # Delete the key if it exists
        if keys[-1] in config:
            del config[keys[-1]]
            
            # Save the configuration if it's not session scope
            if scope_value != ConfigScope.SESSION.value:
                return self._save_scope(scope_value)
        
        return True
    
    def get_all(self, scope: Optional[Union[ConfigScope, str]] = None) -> Dict[str, Any]:
        """Get all configuration values.
        
        Args:
            scope: Specific scope to get values from (if None, merge all scopes)
            
        Returns:
            Configuration dictionary
        """
        if scope:
            scope_value = scope.value if isinstance(scope, ConfigScope) else scope
            if scope_value not in self._config:
                logger.error(f"Invalid configuration scope: {scope_value}")
                return {}
            return self._config[scope_value].copy()
        
        # Merge all scopes with the correct override hierarchy
        result = {}
        for scope_value in [ConfigScope.SYSTEM.value, ConfigScope.USER.value, 
                           ConfigScope.PROJECT.value, ConfigScope.SESSION.value]:
            self._deep_update(result, self._config[scope_value])
        
        return result
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep update a dictionary.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def reset(self, scope: Union[ConfigScope, str] = ConfigScope.SESSION) -> bool:
        """Reset a configuration scope.
        
        Args:
            scope: Configuration scope to reset
            
        Returns:
            True if successful, False otherwise
        """
        scope_value = scope.value if isinstance(scope, ConfigScope) else scope
        
        if scope_value not in self._config:
            logger.error(f"Invalid configuration scope: {scope_value}")
            return False
        
        self._config[scope_value] = {}
        
        # Save the configuration if it's not session scope
        if scope_value != ConfigScope.SESSION.value:
            return self._save_scope(scope_value)
        
        return True
    
    def reload(self) -> bool:
        """Reload all configuration files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._load_system_config()
            self._load_user_config()
            if self.project_dir:
                self._load_project_config()
            return True
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            return False
    
    def set_project_dir(self, project_dir: Union[str, Path]) -> bool:
        """Set the project directory and load project configuration.
        
        Args:
            project_dir: Project directory path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.project_dir = Path(project_dir)
            self._load_project_config()
            return True
        except Exception as e:
            logger.error(f"Error setting project directory: {e}")
            return False
    
    def get_default_config(self, scope: Union[ConfigScope, str] = ConfigScope.USER) -> Dict[str, Any]:
        """Get the default configuration for a scope.
        
        Args:
            scope: Configuration scope
            
        Returns:
            Default configuration dictionary
        """
        scope_value = scope.value if isinstance(scope, ConfigScope) else scope
        
        if scope_value == ConfigScope.SYSTEM.value:
            return {
                "logging": {
                    "level": "INFO",
                    "file": "${base_dir}/logs/lumecode.log",
                    "max_size": 10485760,  # 10 MB
                    "backup_count": 5
                },
                "security": {
                    "sandbox_enabled": True,
                    "network_access": "restricted",
                    "max_cpu_percent": 80,
                    "max_memory_percent": 70
                },
                "updates": {
                    "check_automatically": True,
                    "check_interval_days": 1
                }
            }
        elif scope_value == ConfigScope.USER.value:
            return {
                "editor": {
                    "theme": "light",
                    "font_size": 14,
                    "tab_size": 4,
                    "use_spaces": True,
                    "word_wrap": False
                },
                "agents": {
                    "code_review": {
                        "enabled": True,
                        "severity_threshold": "info"
                    },
                    "refactoring": {
                        "enabled": True,
                        "auto_apply": False
                    }
                },
                "plugins": {
                    "enabled": True,
                    "auto_update": True
                },
                "notifications": {
                    "enabled": True,
                    "sound": True
                }
            }
        elif scope_value == ConfigScope.PROJECT.value:
            return {
                "analysis": {
                    "include_patterns": ["**/*.py", "**/*.js", "**/*.ts"],
                    "exclude_patterns": ["**/node_modules/**", "**/__pycache__/**", "**/venv/**"],
                    "max_file_size": 1048576  # 1 MB
                },
                "agents": {
                    "code_review": {
                        "enabled": True,
                        "rules": ["all"]
                    },
                    "refactoring": {
                        "enabled": True,
                        "patterns": ["all"]
                    }
                },
                "plugins": {
                    "enabled": ["all"]
                }
            }
        elif scope_value == ConfigScope.SESSION.value:
            return {}
        else:
            logger.error(f"Invalid configuration scope: {scope_value}")
            return {}
    
    def create_default_config(self, scope: Union[ConfigScope, str]) -> bool:
        """Create default configuration for a scope.
        
        Args:
            scope: Configuration scope
            
        Returns:
            True if successful, False otherwise
        """
        scope_value = scope.value if isinstance(scope, ConfigScope) else scope
        
        if scope_value not in self._config:
            logger.error(f"Invalid configuration scope: {scope_value}")
            return False
        
        # Get default configuration
        default_config = self.get_default_config(scope_value)
        
        # Update configuration
        self._config[scope_value] = default_config
        
        # Save configuration
        if scope_value != ConfigScope.SESSION.value:
            return self._save_scope(scope_value)
        
        return True
    
    def validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate configuration against a schema.
        
        Args:
            config: Configuration to validate
            schema: Schema to validate against
            
        Returns:
            List of validation errors (empty if valid)
        """
        # Simple schema validation implementation
        # In a real implementation, you might want to use a library like jsonschema
        errors = []
        
        for key, value_schema in schema.items():
            if key not in config:
                if value_schema.get("required", False):
                    errors.append(f"Missing required key: {key}")
                continue
            
            value = config[key]
            
            # Check type
            expected_type = value_schema.get("type")
            if expected_type:
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Key {key} should be a string")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Key {key} should be a number")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Key {key} should be a boolean")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Key {key} should be an array")
                elif expected_type == "object" and not isinstance(value, dict):
                    errors.append(f"Key {key} should be an object")
            
            # Check nested objects
            if isinstance(value, dict) and "properties" in value_schema:
                nested_errors = self.validate_config(value, value_schema["properties"])
                errors.extend([f"{key}.{e}" for e in nested_errors])
        
        return errors