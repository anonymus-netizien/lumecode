from typing import Dict, List, Any, Optional, Callable
import logging
from abc import ABC, abstractmethod
import os
import importlib.util
import sys
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PluginInterface(ABC):
    """
    Base interface that all plugins must implement.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the plugin.
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Get the version of the plugin.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get the description of the plugin.
        """
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the plugin with the provided configuration.
        """
        pass

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plugin with the provided context.
        """
        pass


class PluginManager:
    """
    Manager for loading, registering, and executing plugins.
    """

    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_dir = plugin_dir or os.path.join(os.path.dirname(__file__), "installed")
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        logger.info(f"Initialized PluginManager with plugin directory: {self.plugin_dir}")

    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugin directory.

        Returns:
            List of plugin names found
        """
        if not os.path.exists(self.plugin_dir):
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return []

        plugin_names = []

        # Look for Python modules in the plugin directory
        for item in os.listdir(self.plugin_dir):
            if os.path.isdir(os.path.join(self.plugin_dir, item)) and os.path.exists(
                os.path.join(self.plugin_dir, item, "__init__.py")
            ):
                plugin_names.append(item)
            elif item.endswith(".py") and item != "__init__.py":
                plugin_names.append(item[:-3])

        logger.info(f"Discovered {len(plugin_names)} plugins: {', '.join(plugin_names)}")
        return plugin_names

    def load_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """
        Load a plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            Loaded plugin instance or None if loading failed
        """
        if plugin_name in self.plugins:
            logger.info(f"Plugin {plugin_name} already loaded")
            return self.plugins[plugin_name]

        # Determine the plugin path
        if os.path.exists(os.path.join(self.plugin_dir, f"{plugin_name}.py")):
            plugin_path = os.path.join(self.plugin_dir, f"{plugin_name}.py")
            module_name = plugin_name
        elif os.path.exists(os.path.join(self.plugin_dir, plugin_name, "__init__.py")):
            plugin_path = os.path.join(self.plugin_dir, plugin_name, "__init__.py")
            module_name = plugin_name
        else:
            logger.error(f"Plugin {plugin_name} not found")
            return None

        try:
            # Load the plugin module
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create spec for plugin {plugin_name}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Look for a class that implements PluginInterface
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginInterface)
                    and attr != PluginInterface
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                logger.error(f"No plugin class found in {plugin_name}")
                return None

            # Instantiate the plugin
            plugin = plugin_class()
            self.plugins[plugin_name] = plugin

            # Load plugin configuration if available
            config_path = os.path.join(os.path.dirname(plugin_path), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    self.plugin_configs[plugin_name] = json.load(f)
            else:
                self.plugin_configs[plugin_name] = {}

            # Initialize the plugin
            plugin.initialize(self.plugin_configs[plugin_name])

            logger.info(f"Successfully loaded plugin {plugin_name} v{plugin.version}")
            return plugin

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}", exc_info=True)
            return None

    def load_all_plugins(self) -> Dict[str, PluginInterface]:
        """
        Load all available plugins.

        Returns:
            Dictionary of loaded plugins
        """
        plugin_names = self.discover_plugins()

        for name in plugin_names:
            self.load_plugin(name)

        return self.plugins

    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """
        Get a loaded plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            Plugin instance or None if not loaded
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} not loaded")
            return None

        return self.plugins[plugin_name]

    async def execute_plugin(
        self, plugin_name: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a plugin by name.

        Args:
            plugin_name: Name of the plugin to execute
            context: Context data for the plugin

        Returns:
            Plugin execution results or None if execution failed
        """
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            plugin = self.load_plugin(plugin_name)

        if plugin is None:
            logger.error(f"Failed to load plugin {plugin_name} for execution")
            return None

        try:
            logger.info(f"Executing plugin {plugin_name}")
            result = await plugin.execute(context)
            logger.info(f"Plugin {plugin_name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Error executing plugin {plugin_name}: {e}", exc_info=True)
            return None


# Create a global plugin manager
plugin_manager = PluginManager()
