import abc
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins supported by the system."""

    ANALYZER = "analyzer"  # Code analysis plugins
    TRANSFORMER = "transformer"  # Code transformation plugins
    GENERATOR = "generator"  # Code generation plugins
    INTEGRATION = "integration"  # External tool integration plugins
    VISUALIZATION = "visualization"  # Result visualization plugins
    CUSTOM = "custom"  # Custom plugin types


class PluginStatus(Enum):
    """Status of a plugin."""

    LOADED = "loaded"  # Plugin is loaded but not initialized
    INITIALIZED = "initialized"  # Plugin is initialized and ready
    ACTIVE = "active"  # Plugin is currently active/running
    DISABLED = "disabled"  # Plugin is disabled by user or system
    ERROR = "error"  # Plugin encountered an error


class PluginMetadata:
    """Metadata for a plugin."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        plugin_type: PluginType,
        author: Optional[str] = None,
        homepage: Optional[str] = None,
        repository: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        supported_languages: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ):
        """Initialize plugin metadata.

        Args:
            name: Name of the plugin
            version: Version string (semver format)
            description: Short description of the plugin
            plugin_type: Type of the plugin
            author: Plugin author or organization
            homepage: Plugin homepage URL
            repository: Plugin source code repository URL
            dependencies: List of plugin dependencies
            supported_languages: List of programming languages supported by the plugin
            tags: List of tags for categorization
        """
        self.name = name
        self.version = version
        self.description = description
        self.plugin_type = plugin_type
        self.author = author
        self.homepage = homepage
        self.repository = repository
        self.dependencies = dependencies or []
        self.supported_languages = supported_languages or []
        self.tags = tags or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary.

        Returns:
            Dictionary representation of metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "type": self.plugin_type.value,
            "author": self.author,
            "homepage": self.homepage,
            "repository": self.repository,
            "dependencies": self.dependencies,
            "supported_languages": self.supported_languages,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginMetadata":
        """Create metadata from dictionary.

        Args:
            data: Dictionary containing metadata

        Returns:
            PluginMetadata instance
        """
        plugin_type = PluginType(data.get("type", "custom"))
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            plugin_type=plugin_type,
            author=data.get("author"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            dependencies=data.get("dependencies"),
            supported_languages=data.get("supported_languages"),
            tags=data.get("tags"),
        )


class PluginResult:
    """Result from a plugin operation."""

    def __init__(
        self,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin result.

        Args:
            success: Whether the operation was successful
            data: Result data (if successful)
            error: Error message (if unsuccessful)
            metadata: Additional metadata about the result
        """
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation of result
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def success_result(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "PluginResult":
        """Create a successful result.

        Args:
            data: Result data
            metadata: Additional metadata

        Returns:
            PluginResult instance
        """
        return cls(True, data, None, metadata)

    @classmethod
    def error_result(cls, error: str, metadata: Optional[Dict[str, Any]] = None) -> "PluginResult":
        """Create an error result.

        Args:
            error: Error message
            metadata: Additional metadata

        Returns:
            PluginResult instance
        """
        return cls(False, None, error, metadata)


class PluginInterface(abc.ABC):
    """Base interface for all plugins.

    All plugins must implement this interface to be compatible with the plugin system.
    """

    def __init__(self):
        """Initialize the plugin."""
        self.metadata = None
        self.status = PluginStatus.LOADED
        self.config = {}

    @abc.abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata.

        Returns:
            PluginMetadata instance
        """
        pass

    @abc.abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the plugin with configuration.

        Args:
            config: Plugin configuration

        Returns:
            True if initialization was successful, False otherwise
        """
        pass

    @abc.abstractmethod
    def execute(self, context: Dict[str, Any]) -> PluginResult:
        """Execute the plugin with the given context.

        Args:
            context: Execution context

        Returns:
            PluginResult containing the result of execution
        """
        pass

    def cleanup(self) -> bool:
        """Clean up plugin resources.

        Returns:
            True if cleanup was successful, False otherwise
        """
        return True

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration.

        Args:
            config: Plugin configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        return True


class AnalyzerPlugin(PluginInterface):
    """Interface for analyzer plugins.

    Analyzer plugins analyze code and provide insights, metrics, or issues.
    """

    @abc.abstractmethod
    def analyze_file(
        self, file_path: Union[str, Path], options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Analyze a single file.

        Args:
            file_path: Path to the file to analyze
            options: Analysis options

        Returns:
            PluginResult containing analysis results
        """
        pass

    @abc.abstractmethod
    def analyze_code(
        self, code: str, language: str, options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Analyze code snippet.

        Args:
            code: Code snippet to analyze
            language: Programming language of the code
            options: Analysis options

        Returns:
            PluginResult containing analysis results
        """
        pass

    def analyze_project(
        self, project_path: Union[str, Path], options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Analyze an entire project.

        Args:
            project_path: Path to the project root
            options: Analysis options

        Returns:
            PluginResult containing analysis results
        """
        # Default implementation that can be overridden by subclasses
        logger.info(f"Analyzing project at {project_path}")
        return PluginResult.error_result("analyze_project not implemented")


class TransformerPlugin(PluginInterface):
    """Interface for transformer plugins.

    Transformer plugins transform code based on specific rules or patterns.
    """

    @abc.abstractmethod
    def transform_file(
        self, file_path: Union[str, Path], options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Transform a single file.

        Args:
            file_path: Path to the file to transform
            options: Transformation options

        Returns:
            PluginResult containing transformed code or transformation results
        """
        pass

    @abc.abstractmethod
    def transform_code(
        self, code: str, language: str, options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Transform code snippet.

        Args:
            code: Code snippet to transform
            language: Programming language of the code
            options: Transformation options

        Returns:
            PluginResult containing transformed code or transformation results
        """
        pass

    def preview_transformation(
        self, code: str, language: str, options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Preview transformation without applying it.

        Args:
            code: Code snippet to transform
            language: Programming language of the code
            options: Transformation options

        Returns:
            PluginResult containing preview of transformation
        """
        # Default implementation that can be overridden by subclasses
        return PluginResult.error_result("preview_transformation not implemented")


class GeneratorPlugin(PluginInterface):
    """Interface for generator plugins.

    Generator plugins generate code based on specifications or templates.
    """

    @abc.abstractmethod
    def generate_code(
        self, specification: Dict[str, Any], language: str, options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Generate code based on specification.

        Args:
            specification: Code generation specification
            language: Target programming language
            options: Generation options

        Returns:
            PluginResult containing generated code
        """
        pass

    def generate_from_template(
        self, template_name: str, context: Dict[str, Any], options: Optional[Dict[str, Any]] = None
    ) -> PluginResult:
        """Generate code from a template.

        Args:
            template_name: Name of the template to use
            context: Template context variables
            options: Generation options

        Returns:
            PluginResult containing generated code
        """
        # Default implementation that can be overridden by subclasses
        return PluginResult.error_result("generate_from_template not implemented")


class IntegrationPlugin(PluginInterface):
    """Interface for integration plugins.

    Integration plugins integrate with external tools or services.
    """

    @abc.abstractmethod
    def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to the external service.

        Args:
            credentials: Connection credentials

        Returns:
            True if connection was successful, False otherwise
        """
        pass

    @abc.abstractmethod
    def execute_operation(self, operation: str, params: Dict[str, Any]) -> PluginResult:
        """Execute an operation on the external service.

        Args:
            operation: Operation name
            params: Operation parameters

        Returns:
            PluginResult containing operation results
        """
        pass

    def disconnect(self) -> bool:
        """Disconnect from the external service.

        Returns:
            True if disconnection was successful, False otherwise
        """
        # Default implementation that can be overridden by subclasses
        return True


class VisualizationPlugin(PluginInterface):
    """Interface for visualization plugins.

    Visualization plugins visualize data or code in various formats.
    """

    @abc.abstractmethod
    def visualize(self, data: Any, options: Optional[Dict[str, Any]] = None) -> PluginResult:
        """Visualize data.

        Args:
            data: Data to visualize
            options: Visualization options

        Returns:
            PluginResult containing visualization (e.g., HTML, SVG, or URL)
        """
        pass

    def get_supported_formats(self) -> List[str]:
        """Get supported visualization formats.

        Returns:
            List of supported format identifiers
        """
        # Default implementation that can be overridden by subclasses
        return ["html"]


class PluginManager:
    """Manager for plugin discovery, loading, and execution."""

    def __init__(self, plugin_dir: Optional[Union[str, Path]] = None):
        """Initialize plugin manager.

        Args:
            plugin_dir: Directory containing plugins
        """
        self.plugin_dir = Path(plugin_dir) if plugin_dir else None
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, List[Callable]] = {}

    def discover_plugins(self) -> List[str]:
        """Discover available plugins.

        Returns:
            List of discovered plugin identifiers
        """
        if not self.plugin_dir or not self.plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {self.plugin_dir}")
            return []

        discovered = []
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                discovered.append(item.name)
            elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                discovered.append(item.stem)

        logger.info(f"Discovered {len(discovered)} plugins: {', '.join(discovered)}")
        return discovered

    def load_plugin(self, plugin_id: str) -> bool:
        """Load a plugin by ID.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if plugin was loaded successfully, False otherwise
        """
        if plugin_id in self.plugins:
            logger.warning(f"Plugin already loaded: {plugin_id}")
            return True

        try:
            # In a real implementation, this would dynamically import the plugin module
            # and instantiate the plugin class
            logger.info(f"Loading plugin: {plugin_id}")

            # Placeholder for actual plugin loading logic
            # plugin_module = importlib.import_module(f"plugins.{plugin_id}")
            # plugin_class = getattr(plugin_module, f"{plugin_id.capitalize()}Plugin")
            # plugin = plugin_class()

            # For now, just log that we would load it
            logger.info(f"Plugin {plugin_id} would be loaded here")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return False

    def initialize_plugin(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Initialize a loaded plugin.

        Args:
            plugin_id: Plugin identifier
            config: Plugin configuration

        Returns:
            True if plugin was initialized successfully, False otherwise
        """
        if plugin_id not in self.plugins:
            logger.error(f"Plugin not loaded: {plugin_id}")
            return False

        plugin = self.plugins[plugin_id]
        try:
            if not plugin.validate_config(config):
                logger.error(f"Invalid configuration for plugin {plugin_id}")
                return False

            success = plugin.initialize(config)
            if success:
                plugin.status = PluginStatus.INITIALIZED
                logger.info(f"Plugin {plugin_id} initialized successfully")
            else:
                logger.error(f"Failed to initialize plugin {plugin_id}")

            return success

        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_id}: {e}")
            plugin.status = PluginStatus.ERROR
            return False

    def execute_plugin(self, plugin_id: str, context: Dict[str, Any]) -> PluginResult:
        """Execute a plugin.

        Args:
            plugin_id: Plugin identifier
            context: Execution context

        Returns:
            PluginResult containing execution results
        """
        if plugin_id not in self.plugins:
            return PluginResult.error_result(f"Plugin not loaded: {plugin_id}")

        plugin = self.plugins[plugin_id]
        if plugin.status != PluginStatus.INITIALIZED and plugin.status != PluginStatus.ACTIVE:
            return PluginResult.error_result(
                f"Plugin not ready: {plugin_id} (status: {plugin.status.value})"
            )

        try:
            plugin.status = PluginStatus.ACTIVE
            result = plugin.execute(context)
            plugin.status = PluginStatus.INITIALIZED
            return result

        except Exception as e:
            logger.error(f"Error executing plugin {plugin_id}: {e}")
            plugin.status = PluginStatus.ERROR
            return PluginResult.error_result(str(e))

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            True if plugin was unloaded successfully, False otherwise
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin not loaded: {plugin_id}")
            return True

        try:
            plugin = self.plugins[plugin_id]
            plugin.cleanup()
            del self.plugins[plugin_id]
            logger.info(f"Plugin {plugin_id} unloaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_id}: {e}")
            return False

    def register_hook(self, hook_name: str, callback: Callable) -> bool:
        """Register a hook callback.

        Args:
            hook_name: Name of the hook
            callback: Callback function

        Returns:
            True if hook was registered successfully, False otherwise
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []

        self.hooks[hook_name].append(callback)
        logger.debug(f"Registered hook {hook_name}")
        return True

    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Trigger a hook.

        Args:
            hook_name: Name of the hook
            *args: Positional arguments to pass to callbacks
            **kwargs: Keyword arguments to pass to callbacks

        Returns:
            List of results from callbacks
        """
        if hook_name not in self.hooks:
            return []

        results = []
        for callback in self.hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in hook {hook_name} callback: {e}")

        return results

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[str]:
        """Get plugins of a specific type.

        Args:
            plugin_type: Plugin type to filter by

        Returns:
            List of plugin identifiers
        """
        result = []
        for plugin_id, plugin in self.plugins.items():
            if plugin.get_metadata().plugin_type == plugin_type:
                result.append(plugin_id)

        return result

    def get_plugin_status(self, plugin_id: str) -> Optional[PluginStatus]:
        """Get the status of a plugin.

        Args:
            plugin_id: Plugin identifier

        Returns:
            PluginStatus or None if plugin not found
        """
        if plugin_id not in self.plugins:
            return None

        return self.plugins[plugin_id].status
