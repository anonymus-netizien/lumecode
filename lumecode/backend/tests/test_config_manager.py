import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from backend.config.manager import ConfigManager, ConfigScope


class TestConfigManager(unittest.TestCase):
    """Test cases for the ConfigManager class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)
        self.project_dir = self.base_dir / "project"
        self.project_dir.mkdir(exist_ok=True)
        
        # Create config manager with test directories
        self.config_manager = ConfigManager(
            base_dir=self.base_dir,
            project_dir=self.project_dir
        )
    
    def tearDown(self):
        """Clean up after each test."""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test that the config manager initializes correctly."""
        self.assertEqual(self.config_manager.base_dir, self.base_dir)
        self.assertEqual(self.config_manager.project_dir, self.project_dir)
        
        # Check that all scopes are initialized
        self.assertIn(ConfigScope.SYSTEM.value, self.config_manager._config)
        self.assertIn(ConfigScope.USER.value, self.config_manager._config)
        self.assertIn(ConfigScope.PROJECT.value, self.config_manager._config)
        self.assertIn(ConfigScope.SESSION.value, self.config_manager._config)
    
    def test_get_config_paths(self):
        """Test getting configuration file paths."""
        system_path = self.config_manager._get_system_config_path()
        self.assertEqual(system_path, self.base_dir / "system.json")
        
        user_path = self.config_manager._get_user_config_path()
        self.assertEqual(user_path, self.base_dir / "user.json")
        
        project_path = self.config_manager._get_project_config_path()
        self.assertEqual(project_path, self.project_dir / ".lumecode" / "config.json")
    
    def test_get_project_config_path_no_project_dir(self):
        """Test getting project config path with no project directory set."""
        config_manager = ConfigManager(base_dir=self.base_dir)
        with self.assertRaises(ValueError):
            config_manager._get_project_config_path()
    
    def test_load_config_file(self):
        """Test loading configuration from a file."""
        # Create a test config file
        test_config = {"test": "value"}
        test_path = self.base_dir / "test_config.json"
        with open(test_path, 'w') as f:
            json.dump(test_config, f)
        
        # Load the config
        loaded_config = self.config_manager._load_config_file(test_path)
        self.assertEqual(loaded_config, test_config)
        
        # Test loading non-existent file
        non_existent_path = self.base_dir / "non_existent.json"
        loaded_config = self.config_manager._load_config_file(non_existent_path)
        self.assertEqual(loaded_config, {})
        
        # Test loading invalid JSON
        invalid_path = self.base_dir / "invalid.json"
        with open(invalid_path, 'w') as f:
            f.write("invalid json")
        
        loaded_config = self.config_manager._load_config_file(invalid_path)
        self.assertEqual(loaded_config, {})
    
    def test_save_config_file(self):
        """Test saving configuration to a file."""
        test_config = {"test": "value"}
        test_path = self.base_dir / "test_save.json"
        
        # Save the config
        success = self.config_manager._save_config_file(test_path, test_config)
        self.assertTrue(success)
        
        # Verify the file was created with the correct content
        with open(test_path, 'r') as f:
            loaded_config = json.load(f)
        self.assertEqual(loaded_config, test_config)
        
        # Test saving to a directory that doesn't exist
        nested_path = self.base_dir / "nested" / "config.json"
        success = self.config_manager._save_config_file(nested_path, test_config)
        self.assertTrue(success)
        
        # Verify the directory was created and the file saved
        with open(nested_path, 'r') as f:
            loaded_config = json.load(f)
        self.assertEqual(loaded_config, test_config)
    
    def test_get_set_value(self):
        """Test getting and setting configuration values."""
        # Set a value in session scope
        self.config_manager.set("test.key", "value")
        
        # Get the value
        value = self.config_manager.get("test.key")
        self.assertEqual(value, "value")
        
        # Set a value in user scope
        self.config_manager.set("user.key", "user_value", ConfigScope.USER)
        
        # Get the value from user scope
        value = self.config_manager.get("user.key", scope=ConfigScope.USER)
        self.assertEqual(value, "user_value")
        
        # Get the value without specifying scope (should use override hierarchy)
        value = self.config_manager.get("user.key")
        self.assertEqual(value, "user_value")
        
        # Set the same key in session scope (should override user scope)
        self.config_manager.set("user.key", "session_value")
        value = self.config_manager.get("user.key")
        self.assertEqual(value, "session_value")
        
        # Get a non-existent key
        value = self.config_manager.get("non_existent.key", "default")
        self.assertEqual(value, "default")
    
    def test_nested_keys(self):
        """Test getting and setting nested configuration values."""
        # Set nested values
        self.config_manager.set("parent.child.grandchild", "value")
        
        # Get the nested value
        value = self.config_manager.get("parent.child.grandchild")
        self.assertEqual(value, "value")
        
        # Get the parent object
        parent = self.config_manager.get("parent")
        self.assertEqual(parent, {"child": {"grandchild": "value"}})
        
        # Get a non-existent nested key
        value = self.config_manager.get("parent.child.non_existent", "default")
        self.assertEqual(value, "default")
    
    def test_delete_value(self):
        """Test deleting configuration values."""
        # Set a value
        self.config_manager.set("test.key", "value")
        
        # Delete the value
        success = self.config_manager.delete("test.key")
        self.assertTrue(success)
        
        # Verify the value was deleted
        value = self.config_manager.get("test.key", "default")
        self.assertEqual(value, "default")
        
        # Delete a non-existent key (should succeed)
        success = self.config_manager.delete("non_existent.key")
        self.assertTrue(success)
        
        # Delete a nested key
        self.config_manager.set("parent.child.grandchild", "value")
        success = self.config_manager.delete("parent.child.grandchild")
        self.assertTrue(success)
        
        # Verify the nested key was deleted but parent still exists
        value = self.config_manager.get("parent.child.grandchild", "default")
        self.assertEqual(value, "default")
        self.assertIsNotNone(self.config_manager.get("parent.child"))
    
    def test_get_all(self):
        """Test getting all configuration values."""
        # Set values in different scopes
        self.config_manager.set("key1", "system_value", ConfigScope.SYSTEM)
        self.config_manager.set("key2", "user_value", ConfigScope.USER)
        self.config_manager.set("key3", "project_value", ConfigScope.PROJECT)
        self.config_manager.set("key4", "session_value", ConfigScope.SESSION)
        
        # Set the same key in different scopes
        self.config_manager.set("common.key", "system_value", ConfigScope.SYSTEM)
        self.config_manager.set("common.key", "user_value", ConfigScope.USER)
        self.config_manager.set("common.key", "project_value", ConfigScope.PROJECT)
        
        # Get all values from a specific scope
        system_config = self.config_manager.get_all(ConfigScope.SYSTEM)
        self.assertEqual(system_config["key1"], "system_value")
        self.assertEqual(system_config["common"]["key"], "system_value")
        
        # Get all values (merged)
        all_config = self.config_manager.get_all()
        self.assertEqual(all_config["key1"], "system_value")
        self.assertEqual(all_config["key2"], "user_value")
        self.assertEqual(all_config["key3"], "project_value")
        self.assertEqual(all_config["key4"], "session_value")
        
        # Check that the common key uses the highest priority value
        self.assertEqual(all_config["common"]["key"], "project_value")
    
    def test_reset(self):
        """Test resetting configuration scopes."""
        # Set values in different scopes
        self.config_manager.set("key1", "system_value", ConfigScope.SYSTEM)
        self.config_manager.set("key2", "user_value", ConfigScope.USER)
        
        # Reset user scope
        success = self.config_manager.reset(ConfigScope.USER)
        self.assertTrue(success)
        
        # Verify user scope was reset
        user_config = self.config_manager.get_all(ConfigScope.USER)
        self.assertEqual(user_config, {})
        
        # Verify system scope was not reset
        system_config = self.config_manager.get_all(ConfigScope.SYSTEM)
        self.assertEqual(system_config["key1"], "system_value")
    
    def test_reload(self):
        """Test reloading configuration from files."""
        # Create test config files
        system_config = {"system": "value"}
        user_config = {"user": "value"}
        project_config = {"project": "value"}
        
        system_path = self.config_manager._get_system_config_path()
        user_path = self.config_manager._get_user_config_path()
        project_path = self.config_manager._get_project_config_path()
        
        # Create parent directories
        system_path.parent.mkdir(exist_ok=True, parents=True)
        user_path.parent.mkdir(exist_ok=True, parents=True)
        project_path.parent.mkdir(exist_ok=True, parents=True)
        
        # Write config files
        with open(system_path, 'w') as f:
            json.dump(system_config, f)
        
        with open(user_path, 'w') as f:
            json.dump(user_config, f)
        
        with open(project_path, 'w') as f:
            json.dump(project_config, f)
        
        # Reload configuration
        success = self.config_manager.reload()
        self.assertTrue(success)
        
        # Verify configuration was reloaded
        self.assertEqual(self.config_manager.get("system"), "value")
        self.assertEqual(self.config_manager.get("user"), "value")
        self.assertEqual(self.config_manager.get("project"), "value")
    
    def test_set_project_dir(self):
        """Test setting the project directory."""
        # Create a new project directory
        new_project_dir = self.base_dir / "new_project"
        new_project_dir.mkdir(exist_ok=True)
        
        # Create a project config file
        project_config_dir = new_project_dir / ".lumecode"
        project_config_dir.mkdir(exist_ok=True)
        
        project_config_path = project_config_dir / "config.json"
        project_config = {"new_project": "value"}
        
        with open(project_config_path, 'w') as f:
            json.dump(project_config, f)
        
        # Set the project directory
        success = self.config_manager.set_project_dir(new_project_dir)
        self.assertTrue(success)
        
        # Verify the project directory was set
        self.assertEqual(self.config_manager.project_dir, new_project_dir)
        
        # Verify the project config was loaded
        self.assertEqual(self.config_manager.get("new_project"), "value")
    
    def test_default_config(self):
        """Test getting default configuration."""
        # Get default user config
        user_config = self.config_manager.get_default_config(ConfigScope.USER)
        
        # Verify some expected values
        self.assertEqual(user_config["editor"]["theme"], "light")
        self.assertEqual(user_config["editor"]["font_size"], 14)
        self.assertTrue(user_config["agents"]["code_review"]["enabled"])
        
        # Get default system config
        system_config = self.config_manager.get_default_config(ConfigScope.SYSTEM)
        
        # Verify some expected values
        self.assertEqual(system_config["logging"]["level"], "INFO")
        self.assertTrue(system_config["security"]["sandbox_enabled"])
        
        # Get default project config
        project_config = self.config_manager.get_default_config(ConfigScope.PROJECT)
        
        # Verify some expected values
        self.assertIn("**/*.py", project_config["analysis"]["include_patterns"])
        self.assertIn("**/node_modules/**", project_config["analysis"]["exclude_patterns"])
    
    def test_create_default_config(self):
        """Test creating default configuration."""
        # Create default user config
        success = self.config_manager.create_default_config(ConfigScope.USER)
        self.assertTrue(success)
        
        # Verify the config was created
        user_config = self.config_manager.get_all(ConfigScope.USER)
        self.assertEqual(user_config["editor"]["theme"], "light")
        self.assertEqual(user_config["editor"]["font_size"], 14)
        
        # Create default system config
        success = self.config_manager.create_default_config(ConfigScope.SYSTEM)
        self.assertTrue(success)
        
        # Verify the config was created
        system_config = self.config_manager.get_all(ConfigScope.SYSTEM)
        self.assertEqual(system_config["logging"]["level"], "INFO")
        self.assertTrue(system_config["security"]["sandbox_enabled"])
    
    def test_validate_config(self):
        """Test validating configuration against a schema."""
        # Define a schema
        schema = {
            "name": {"type": "string", "required": True},
            "age": {"type": "number"},
            "settings": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "required": True},
                    "value": {"type": "number"}
                }
            }
        }
        
        # Valid config
        valid_config = {
            "name": "test",
            "age": 30,
            "settings": {
                "enabled": True,
                "value": 42
            }
        }
        
        errors = self.config_manager.validate_config(valid_config, schema)
        self.assertEqual(errors, [])
        
        # Invalid config (missing required field)
        invalid_config1 = {
            "age": 30,
            "settings": {
                "enabled": True
            }
        }
        
        errors = self.config_manager.validate_config(invalid_config1, schema)
        self.assertIn("Missing required key: name", errors)
        
        # Invalid config (wrong type)
        invalid_config2 = {
            "name": "test",
            "age": "thirty",
            "settings": {
                "enabled": True
            }
        }
        
        errors = self.config_manager.validate_config(invalid_config2, schema)
        self.assertIn("Key age should be a number", errors)
        
        # Invalid config (nested error)
        invalid_config3 = {
            "name": "test",
            "settings": {
                "enabled": "yes"
            }
        }
        
        errors = self.config_manager.validate_config(invalid_config3, schema)
        self.assertIn("settings.Key enabled should be a boolean", errors)


if __name__ == "__main__":
    unittest.main()