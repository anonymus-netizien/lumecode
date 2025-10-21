"""
Configuration Management System
Store and manage user preferences and settings
"""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Config:
    """User configuration settings"""

    # LLM Settings
    default_provider: str = "groq"
    default_model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000

    # Cache Settings
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    cache_dir: Optional[str] = None

    # UI Settings
    streaming_enabled: bool = True
    show_provider_info: bool = False
    color_theme: str = "default"

    # Git Settings
    conventional_commits: bool = True
    auto_stage: bool = False
    sign_commits: bool = False

    # Test Settings
    default_test_framework: str = "pytest"
    test_coverage_threshold: int = 80

    # Advanced Settings
    verbose_logging: bool = False
    telemetry_enabled: bool = False
    check_for_updates: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary"""
        # Filter out unknown keys
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class ConfigManager:
    """Manage user configuration"""

    DEFAULT_CONFIG_PATH = Path.home() / ".lumecode" / "config.json"

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager.

        Args:
            config_path: Path to config file (default: ~/.lumecode/config.json)
        """
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config = Config()
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Config:
        """
        Load configuration from file.

        Returns:
            Config object
        """
        if not self.config_path.exists():
            # Create default config
            self.save()
            return self.config

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)

            self.config = Config.from_dict(data)
            return self.config

        except (json.JSONDecodeError, IOError) as e:
            # If config is corrupted, create new one
            print(f"Warning: Could not load config ({e}), using defaults")
            self.save()
            return self.config

    def save(self):
        """Save configuration to file"""
        self._ensure_config_dir()

        with open(self.config_path, "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any):
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: New value
        """
        if not hasattr(self.config, key):
            raise ValueError(f"Unknown configuration key: {key}")

        setattr(self.config, key, value)
        self.save()

    def reset(self):
        """Reset configuration to defaults"""
        self.config = Config()
        self.save()

    def show(self) -> Dict[str, Any]:
        """Show current configuration"""
        return self.config.to_dict()

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if valid, raises ValueError if invalid
        """
        # Validate provider
        valid_providers = ["groq", "openrouter", "mock"]
        if self.config.default_provider not in valid_providers:
            raise ValueError(f"Invalid provider: {self.config.default_provider}")

        # Validate temperature
        if not 0.0 <= self.config.temperature <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0")

        # Validate max_tokens
        if self.config.max_tokens < 1:
            raise ValueError(f"max_tokens must be positive")

        # Validate cache_ttl_hours
        if self.config.cache_ttl_hours < 1:
            raise ValueError(f"cache_ttl_hours must be positive")

        # Validate test framework
        valid_frameworks = ["pytest", "unittest"]
        if self.config.default_test_framework not in valid_frameworks:
            raise ValueError(f"Invalid test framework: {self.config.default_test_framework}")

        # Validate coverage threshold
        if not 0 <= self.config.test_coverage_threshold <= 100:
            raise ValueError(f"Coverage threshold must be between 0 and 100")

        return True


# Global config instance
_config_manager = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get global config manager instance"""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
        _config_manager.load()

    return _config_manager


def get_config() -> Config:
    """Get current configuration"""
    manager = get_config_manager()
    return manager.config


def set_config(key: str, value: any) -> None:
    """
    Set a configuration value and save it.

    Args:
        key: Configuration key (can use dot notation like 'providers.groq.api_key')
        value: Configuration value

    Example:
        set_config('default_provider', 'groq')
        set_config('providers.groq.api_key', 'gsk_...')
    """
    manager = get_config_manager()

    # Parse key path
    parts = key.split(".")
    config_dict = manager.config.dict()

    # Navigate to the right place in the config
    current = config_dict
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value

    # Update config object
    manager.config = Config(**config_dict)

    # Save to file
    manager.save()
