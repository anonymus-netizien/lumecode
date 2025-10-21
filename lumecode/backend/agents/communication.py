import logging
import asyncio
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
from dataclasses import dataclass

from ..plugins.interface import PluginInterface, PluginType, PluginResult

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be exchanged between agents and plugins."""
    REQUEST = "request"           # Request from agent to plugin
    RESPONSE = "response"         # Response from plugin to agent
    EVENT = "event"               # Event notification
    COMMAND = "command"           # Command to execute
    STATUS = "status"             # Status update
    ERROR = "error"               # Error notification


class MessagePriority(Enum):
    """Priority levels for messages."""
    HIGH = "high"                 # High priority message
    NORMAL = "normal"             # Normal priority message
    LOW = "low"                   # Low priority message


@dataclass
class Message:
    """Message exchanged between agents and plugins."""
    id: str                                      # Unique message ID
    type: MessageType                            # Message type
    source: str                                  # Source of the message (agent or plugin ID)
    target: Optional[str] = None                 # Target of the message (agent or plugin ID, None for broadcast)
    content: Dict[str, Any] = None               # Message content
    priority: MessagePriority = MessagePriority.NORMAL  # Message priority
    correlation_id: Optional[str] = None         # ID of related message (for responses)
    timestamp: float = None                      # Message timestamp
    
    def __post_init__(self):
        """Initialize default values."""
        import time
        
        if self.content is None:
            self.content = {}
            
        if self.timestamp is None:
            self.timestamp = time.time()
    
    @classmethod
    def create_request(cls, source: str, target: str, content: Dict[str, Any], 
                      priority: MessagePriority = MessagePriority.NORMAL) -> 'Message':
        """Create a request message.
        
        Args:
            source: Source of the message
            target: Target of the message
            content: Message content
            priority: Message priority
            
        Returns:
            Request message
        """
        return cls(
            id=str(uuid.uuid4()),
            type=MessageType.REQUEST,
            source=source,
            target=target,
            content=content,
            priority=priority
        )
    
    @classmethod
    def create_response(cls, request: 'Message', source: str, content: Dict[str, Any],
                       priority: Optional[MessagePriority] = None) -> 'Message':
        """Create a response message.
        
        Args:
            request: Request message to respond to
            source: Source of the response
            content: Response content
            priority: Response priority (defaults to request priority)
            
        Returns:
            Response message
        """
        return cls(
            id=str(uuid.uuid4()),
            type=MessageType.RESPONSE,
            source=source,
            target=request.source,
            content=content,
            priority=priority or request.priority,
            correlation_id=request.id
        )
    
    @classmethod
    def create_error(cls, request: 'Message', source: str, error: str,
                    details: Optional[Dict[str, Any]] = None) -> 'Message':
        """Create an error message.
        
        Args:
            request: Request message that caused the error
            source: Source of the error
            error: Error message
            details: Error details
            
        Returns:
            Error message
        """
        content = {"error": error}
        if details:
            content["details"] = details
            
        return cls(
            id=str(uuid.uuid4()),
            type=MessageType.ERROR,
            source=source,
            target=request.source,
            content=content,
            priority=MessagePriority.HIGH,
            correlation_id=request.id
        )
    
    @classmethod
    def create_event(cls, source: str, event_type: str, content: Dict[str, Any],
                    target: Optional[str] = None,
                    priority: MessagePriority = MessagePriority.NORMAL) -> 'Message':
        """Create an event message.
        
        Args:
            source: Source of the event
            event_type: Type of event
            content: Event content
            target: Target of the event (None for broadcast)
            priority: Event priority
            
        Returns:
            Event message
        """
        event_content = {"event_type": event_type}
        event_content.update(content)
        
        return cls(
            id=str(uuid.uuid4()),
            type=MessageType.EVENT,
            source=source,
            target=target,
            content=event_content,
            priority=priority
        )
    
    @classmethod
    def create_command(cls, source: str, target: str, command: str, 
                      params: Optional[Dict[str, Any]] = None,
                      priority: MessagePriority = MessagePriority.NORMAL) -> 'Message':
        """Create a command message.
        
        Args:
            source: Source of the command
            target: Target of the command
            command: Command to execute
            params: Command parameters
            priority: Command priority
            
        Returns:
            Command message
        """
        content = {"command": command}
        if params:
            content["params"] = params
            
        return cls(
            id=str(uuid.uuid4()),
            type=MessageType.COMMAND,
            source=source,
            target=target,
            content=content,
            priority=priority
        )
    
    @classmethod
    def create_status(cls, source: str, status: str, details: Optional[Dict[str, Any]] = None,
                     target: Optional[str] = None,
                     priority: MessagePriority = MessagePriority.LOW) -> 'Message':
        """Create a status message.
        
        Args:
            source: Source of the status
            status: Status value
            details: Status details
            target: Target of the status (None for broadcast)
            priority: Status priority
            
        Returns:
            Status message
        """
        content = {"status": status}
        if details:
            content["details"] = details
            
        return cls(
            id=str(uuid.uuid4()),
            type=MessageType.STATUS,
            source=source,
            target=target,
            content=content,
            priority=priority
        )


class MessageBus:
    """Message bus for agent-to-plugin communication.
    
    Provides a publish-subscribe mechanism for agents and plugins to communicate.
    """
    
    def __init__(self):
        """Initialize the message bus."""
        self._subscribers: Dict[str, List[Callable[[Message], Awaitable[None]]]] = {}
        self._response_handlers: Dict[str, asyncio.Future] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task = None
    
    async def start(self):
        """Start the message bus."""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Message bus started")
    
    async def stop(self):
        """Stop the message bus."""
        if not self._running:
            return
            
        self._running = False
        
        # Cancel all pending response handlers
        for future in self._response_handlers.values():
            if not future.done():
                future.cancel()
        
        # Wait for the worker task to complete
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            
        logger.info("Message bus stopped")
    
    async def _process_queue(self):
        """Process messages from the queue."""
        while self._running:
            try:
                message = await self._queue.get()
                await self._dispatch_message(message)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _dispatch_message(self, message: Message):
        """Dispatch a message to subscribers.
        
        Args:
            message: Message to dispatch
        """
        # Handle responses to requests
        if message.type == MessageType.RESPONSE and message.correlation_id:
            if message.correlation_id in self._response_handlers:
                future = self._response_handlers.pop(message.correlation_id)
                if not future.done():
                    future.set_result(message)
                return
        
        # Handle errors for requests
        if message.type == MessageType.ERROR and message.correlation_id:
            if message.correlation_id in self._response_handlers:
                future = self._response_handlers.pop(message.correlation_id)
                if not future.done():
                    future.set_exception(Exception(message.content.get("error", "Unknown error")))
                return
        
        # Dispatch to target subscriber
        if message.target and message.target in self._subscribers:
            for callback in self._subscribers[message.target]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
        
        # Dispatch to broadcast subscribers if no target or target not found
        if not message.target or message.target not in self._subscribers:
            if "*" in self._subscribers:
                for callback in self._subscribers["*"]:
                    try:
                        await callback(message)
                    except Exception as e:
                        logger.error(f"Error in broadcast subscriber callback: {e}")
    
    def subscribe(self, subscriber_id: str, callback: Callable[[Message], Awaitable[None]]):
        """Subscribe to messages.
        
        Args:
            subscriber_id: Subscriber ID
            callback: Callback function to handle messages
        """
        if subscriber_id not in self._subscribers:
            self._subscribers[subscriber_id] = []
        self._subscribers[subscriber_id].append(callback)
        logger.debug(f"Subscriber {subscriber_id} registered")
    
    def unsubscribe(self, subscriber_id: str, callback: Optional[Callable[[Message], Awaitable[None]]] = None):
        """Unsubscribe from messages.
        
        Args:
            subscriber_id: Subscriber ID
            callback: Callback function to unsubscribe (None to unsubscribe all)
        """
        if subscriber_id not in self._subscribers:
            return
            
        if callback is None:
            del self._subscribers[subscriber_id]
            logger.debug(f"Subscriber {subscriber_id} unregistered")
        else:
            self._subscribers[subscriber_id] = [
                cb for cb in self._subscribers[subscriber_id] if cb != callback
            ]
            if not self._subscribers[subscriber_id]:
                del self._subscribers[subscriber_id]
            logger.debug(f"Callback unregistered for subscriber {subscriber_id}")
    
    async def publish(self, message: Message):
        """Publish a message.
        
        Args:
            message: Message to publish
        """
        await self._queue.put(message)
    
    async def request(self, message: Message, timeout: float = 5.0) -> Message:
        """Send a request and wait for a response.
        
        Args:
            message: Request message
            timeout: Timeout in seconds
            
        Returns:
            Response message
            
        Raises:
            asyncio.TimeoutError: If no response is received within the timeout
            Exception: If an error response is received
        """
        if message.type != MessageType.REQUEST:
            raise ValueError("Message must be a request")
            
        # Create a future to receive the response
        future = asyncio.Future()
        self._response_handlers[message.id] = future
        
        # Publish the request
        await self.publish(message)
        
        try:
            # Wait for the response
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            # Remove the response handler on timeout
            self._response_handlers.pop(message.id, None)
            raise
        except Exception:
            # Remove the response handler on error
            self._response_handlers.pop(message.id, None)
            raise


class PluginCommunicator:
    """Facilitates communication between agents and plugins.
    
    Provides a high-level interface for agents to interact with plugins.
    """
    
    def __init__(self, message_bus: MessageBus, agent_id: str):
        """Initialize the plugin communicator.
        
        Args:
            message_bus: Message bus for communication
            agent_id: ID of the agent using this communicator
        """
        self.message_bus = message_bus
        self.agent_id = agent_id
        
        # Register to receive messages
        self.message_bus.subscribe(agent_id, self._handle_message)
    
    async def _handle_message(self, message: Message):
        """Handle incoming messages.
        
        Args:
            message: Incoming message
        """
        # Default implementation does nothing
        # Subclasses can override this method to handle messages
        pass
    
    async def request_plugin(self, plugin_id: str, action: str, 
                           params: Dict[str, Any] = None,
                           timeout: float = 5.0) -> Dict[str, Any]:
        """Send a request to a plugin and wait for a response.
        
        Args:
            plugin_id: ID of the plugin
            action: Action to request
            params: Parameters for the action
            timeout: Timeout in seconds
            
        Returns:
            Response content
            
        Raises:
            asyncio.TimeoutError: If no response is received within the timeout
            Exception: If an error response is received
        """
        content = {"action": action}
        if params:
            content["params"] = params
            
        request = Message.create_request(
            source=self.agent_id,
            target=plugin_id,
            content=content
        )
        
        response = await self.message_bus.request(request, timeout)
        return response.content
    
    async def execute_plugin(self, plugin: PluginInterface, method_name: str, 
                           params: Dict[str, Any] = None) -> PluginResult:
        """Execute a plugin method directly.
        
        Args:
            plugin: Plugin instance
            method_name: Method to execute
            params: Parameters for the method
            
        Returns:
            Plugin result
            
        Raises:
            AttributeError: If the plugin doesn't have the specified method
            Exception: If the plugin method raises an exception
        """
        if not hasattr(plugin, method_name):
            raise AttributeError(f"Plugin {plugin.metadata.id} doesn't have method {method_name}")
            
        method = getattr(plugin, method_name)
        if not callable(method):
            raise AttributeError(f"{method_name} is not a callable method")
            
        if params is None:
            params = {}
            
        try:
            if asyncio.iscoroutinefunction(method):
                return await method(**params)
            else:
                return method(**params)
        except Exception as e:
            logger.error(f"Error executing plugin method {method_name}: {e}")
            raise
    
    async def broadcast_event(self, event_type: str, content: Dict[str, Any] = None,
                            priority: MessagePriority = MessagePriority.NORMAL):
        """Broadcast an event to all subscribers.
        
        Args:
            event_type: Type of event
            content: Event content
            priority: Event priority
        """
        event = Message.create_event(
            source=self.agent_id,
            event_type=event_type,
            content=content or {},
            priority=priority
        )
        
        await self.message_bus.publish(event)
    
    async def send_command(self, target_id: str, command: str, 
                         params: Dict[str, Any] = None,
                         priority: MessagePriority = MessagePriority.NORMAL,
                         timeout: Optional[float] = None) -> Optional[Message]:
        """Send a command to a target.
        
        Args:
            target_id: ID of the target
            command: Command to execute
            params: Command parameters
            priority: Command priority
            timeout: Timeout in seconds (None for no response)
            
        Returns:
            Response message if timeout is specified, None otherwise
            
        Raises:
            asyncio.TimeoutError: If no response is received within the timeout
            Exception: If an error response is received
        """
        command_msg = Message.create_command(
            source=self.agent_id,
            target=target_id,
            command=command,
            params=params,
            priority=priority
        )
        
        if timeout is not None:
            # Convert to request/response pattern
            request = Message(
                id=command_msg.id,
                type=MessageType.REQUEST,
                source=command_msg.source,
                target=command_msg.target,
                content=command_msg.content,
                priority=command_msg.priority
            )
            
            return await self.message_bus.request(request, timeout)
        else:
            # Fire and forget
            await self.message_bus.publish(command_msg)
            return None
    
    async def send_status(self, status: str, details: Dict[str, Any] = None,
                        target_id: Optional[str] = None,
                        priority: MessagePriority = MessagePriority.LOW):
        """Send a status update.
        
        Args:
            status: Status value
            details: Status details
            target_id: Target ID (None for broadcast)
            priority: Status priority
        """
        status_msg = Message.create_status(
            source=self.agent_id,
            status=status,
            details=details,
            target=target_id,
            priority=priority
        )
        
        await self.message_bus.publish(status_msg)
    
    def close(self):
        """Close the communicator and unsubscribe from messages."""
        self.message_bus.unsubscribe(self.agent_id)