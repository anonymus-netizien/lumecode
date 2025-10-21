import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch

from backend.agents.communication import (
    Message, MessageType, MessagePriority, MessageBus, PluginCommunicator
)
from backend.plugins.interface import PluginInterface, PluginType, PluginResult, PluginMetadata


class TestMessage:
    """Tests for the Message class."""
    
    def test_init(self):
        """Test message initialization."""
        msg = Message(
            id="test-id",
            type=MessageType.REQUEST,
            source="agent-1",
            target="plugin-1",
            content={"action": "analyze"},
            priority=MessagePriority.HIGH
        )
        
        assert msg.id == "test-id"
        assert msg.type == MessageType.REQUEST
        assert msg.source == "agent-1"
        assert msg.target == "plugin-1"
        assert msg.content == {"action": "analyze"}
        assert msg.priority == MessagePriority.HIGH
        assert msg.correlation_id is None
        assert msg.timestamp is not None
    
    def test_post_init_defaults(self):
        """Test post-init default values."""
        msg = Message(
            id="test-id",
            type=MessageType.REQUEST,
            source="agent-1"
        )
        
        assert msg.content == {}
        assert msg.timestamp is not None
    
    def test_create_request(self):
        """Test create_request factory method."""
        msg = Message.create_request(
            source="agent-1",
            target="plugin-1",
            content={"action": "analyze"},
            priority=MessagePriority.HIGH
        )
        
        assert msg.type == MessageType.REQUEST
        assert msg.source == "agent-1"
        assert msg.target == "plugin-1"
        assert msg.content == {"action": "analyze"}
        assert msg.priority == MessagePriority.HIGH
        assert msg.correlation_id is None
    
    def test_create_response(self):
        """Test create_response factory method."""
        request = Message.create_request(
            source="agent-1",
            target="plugin-1",
            content={"action": "analyze"},
            priority=MessagePriority.HIGH
        )
        
        response = Message.create_response(
            request=request,
            source="plugin-1",
            content={"result": "success"}
        )
        
        assert response.type == MessageType.RESPONSE
        assert response.source == "plugin-1"
        assert response.target == "agent-1"
        assert response.content == {"result": "success"}
        assert response.priority == MessagePriority.HIGH  # Inherits from request
        assert response.correlation_id == request.id
    
    def test_create_error(self):
        """Test create_error factory method."""
        request = Message.create_request(
            source="agent-1",
            target="plugin-1",
            content={"action": "analyze"}
        )
        
        error = Message.create_error(
            request=request,
            source="plugin-1",
            error="Invalid action",
            details={"code": 400}
        )
        
        assert error.type == MessageType.ERROR
        assert error.source == "plugin-1"
        assert error.target == "agent-1"
        assert error.content == {"error": "Invalid action", "details": {"code": 400}}
        assert error.priority == MessagePriority.HIGH
        assert error.correlation_id == request.id
    
    def test_create_event(self):
        """Test create_event factory method."""
        event = Message.create_event(
            source="agent-1",
            event_type="analysis_complete",
            content={"file": "main.py"},
            priority=MessagePriority.LOW
        )
        
        assert event.type == MessageType.EVENT
        assert event.source == "agent-1"
        assert event.target is None  # Broadcast
        assert event.content == {"event_type": "analysis_complete", "file": "main.py"}
        assert event.priority == MessagePriority.LOW
    
    def test_create_command(self):
        """Test create_command factory method."""
        command = Message.create_command(
            source="agent-1",
            target="plugin-1",
            command="restart",
            params={"force": True}
        )
        
        assert command.type == MessageType.COMMAND
        assert command.source == "agent-1"
        assert command.target == "plugin-1"
        assert command.content == {"command": "restart", "params": {"force": True}}
        assert command.priority == MessagePriority.NORMAL
    
    def test_create_status(self):
        """Test create_status factory method."""
        status = Message.create_status(
            source="agent-1",
            status="running",
            details={"progress": 50}
        )
        
        assert status.type == MessageType.STATUS
        assert status.source == "agent-1"
        assert status.target is None  # Broadcast
        assert status.content == {"status": "running", "details": {"progress": 50}}
        assert status.priority == MessagePriority.LOW


@pytest.fixture
async def message_bus():
    """Fixture for MessageBus."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()


class TestMessageBus:
    """Tests for the MessageBus class."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the message bus."""
        bus = MessageBus()
        
        # Start
        await bus.start()
        assert bus._running is True
        assert bus._worker_task is not None
        
        # Start again (should be idempotent)
        await bus.start()
        assert bus._running is True
        
        # Stop
        await bus.stop()
        assert bus._running is False
        assert bus._worker_task is None or bus._worker_task.done()
        
        # Stop again (should be idempotent)
        await bus.stop()
        assert bus._running is False
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, message_bus):
        """Test subscribing and unsubscribing from the message bus."""
        callback = MagicMock()
        
        # Subscribe
        message_bus.subscribe("test-subscriber", callback)
        assert "test-subscriber" in message_bus._subscribers
        assert callback in message_bus._subscribers["test-subscriber"]
        
        # Unsubscribe specific callback
        message_bus.unsubscribe("test-subscriber", callback)
        assert "test-subscriber" not in message_bus._subscribers
        
        # Subscribe multiple callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()
        message_bus.subscribe("test-subscriber", callback1)
        message_bus.subscribe("test-subscriber", callback2)
        assert len(message_bus._subscribers["test-subscriber"]) == 2
        
        # Unsubscribe specific callback
        message_bus.unsubscribe("test-subscriber", callback1)
        assert "test-subscriber" in message_bus._subscribers
        assert len(message_bus._subscribers["test-subscriber"]) == 1
        
        # Unsubscribe all callbacks
        message_bus.unsubscribe("test-subscriber")
        assert "test-subscriber" not in message_bus._subscribers
    
    @pytest.mark.asyncio
    async def test_publish_targeted(self, message_bus):
        """Test publishing a targeted message."""
        received_messages = []
        
        async def callback(message):
            received_messages.append(message)
        
        # Subscribe
        message_bus.subscribe("target-1", callback)
        
        # Publish
        message = Message.create_request(
            source="source-1",
            target="target-1",
            content={"action": "test"}
        )
        await message_bus.publish(message)
        
        # Allow time for message processing
        await asyncio.sleep(0.1)
        
        # Check
        assert len(received_messages) == 1
        assert received_messages[0].id == message.id
    
    @pytest.mark.asyncio
    async def test_publish_broadcast(self, message_bus):
        """Test publishing a broadcast message."""
        received_messages = []
        
        async def callback(message):
            received_messages.append(message)
        
        # Subscribe to broadcast
        message_bus.subscribe("*", callback)
        
        # Publish broadcast
        message = Message.create_event(
            source="source-1",
            event_type="test_event",
            content={"data": "test"}
        )
        await message_bus.publish(message)
        
        # Allow time for message processing
        await asyncio.sleep(0.1)
        
        # Check
        assert len(received_messages) == 1
        assert received_messages[0].id == message.id
    
    @pytest.mark.asyncio
    async def test_request_response(self, message_bus):
        """Test request-response pattern."""
        async def responder(message):
            if message.type == MessageType.REQUEST:
                response = Message.create_response(
                    request=message,
                    source="responder",
                    content={"result": "success"}
                )
                await message_bus.publish(response)
        
        # Subscribe responder
        message_bus.subscribe("responder", responder)
        
        # Send request
        request = Message.create_request(
            source="requester",
            target="responder",
            content={"action": "test"}
        )
        
        response = await message_bus.request(request, timeout=1.0)
        
        # Check response
        assert response.type == MessageType.RESPONSE
        assert response.source == "responder"
        assert response.target == "requester"
        assert response.content == {"result": "success"}
        assert response.correlation_id == request.id
    
    @pytest.mark.asyncio
    async def test_request_timeout(self, message_bus):
        """Test request timeout."""
        # Send request to non-existent target
        request = Message.create_request(
            source="requester",
            target="non-existent",
            content={"action": "test"}
        )
        
        with pytest.raises(asyncio.TimeoutError):
            await message_bus.request(request, timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_request_error(self, message_bus):
        """Test request error response."""
        async def error_responder(message):
            if message.type == MessageType.REQUEST:
                error = Message.create_error(
                    request=message,
                    source="responder",
                    error="Test error"
                )
                await message_bus.publish(error)
        
        # Subscribe responder
        message_bus.subscribe("responder", error_responder)
        
        # Send request
        request = Message.create_request(
            source="requester",
            target="responder",
            content={"action": "test"}
        )
        
        with pytest.raises(Exception) as exc_info:
            await message_bus.request(request, timeout=1.0)
        
        assert "Test error" in str(exc_info.value)


class MockPlugin(PluginInterface):
    """Mock plugin for testing."""
    
    def __init__(self, plugin_id="mock-plugin"):
        self.metadata = PluginMetadata(
            id=plugin_id,
            name="Mock Plugin",
            version="1.0.0",
            description="Mock plugin for testing",
            type=PluginType.ANALYZER
        )
        self.called_with = None
    
    def analyze(self, **params):
        """Mock analyze method."""
        self.called_with = params
        return PluginResult(
            success=True,
            data={"result": "mock-result"}
        )
    
    async def analyze_async(self, **params):
        """Mock async analyze method."""
        self.called_with = params
        return PluginResult(
            success=True,
            data={"result": "mock-async-result"}
        )


@pytest.fixture
async def plugin_communicator(message_bus):
    """Fixture for PluginCommunicator."""
    communicator = PluginCommunicator(message_bus, "test-agent")
    yield communicator
    communicator.close()


class TestPluginCommunicator:
    """Tests for the PluginCommunicator class."""
    
    @pytest.mark.asyncio
    async def test_request_plugin(self, message_bus, plugin_communicator):
        """Test requesting a plugin."""
        async def plugin_handler(message):
            if message.type == MessageType.REQUEST:
                response = Message.create_response(
                    request=message,
                    source="test-plugin",
                    content={"result": "plugin-result"}
                )
                await message_bus.publish(response)
        
        # Subscribe mock plugin
        message_bus.subscribe("test-plugin", plugin_handler)
        
        # Request plugin
        result = await plugin_communicator.request_plugin(
            plugin_id="test-plugin",
            action="analyze",
            params={"file": "test.py"}
        )
        
        # Check result
        assert result == {"result": "plugin-result"}
    
    @pytest.mark.asyncio
    async def test_execute_plugin_sync(self, plugin_communicator):
        """Test executing a plugin synchronously."""
        plugin = MockPlugin()
        
        result = await plugin_communicator.execute_plugin(
            plugin=plugin,
            method_name="analyze",
            params={"file": "test.py"}
        )
        
        # Check result
        assert result.success is True
        assert result.data == {"result": "mock-result"}
        assert plugin.called_with == {"file": "test.py"}
    
    @pytest.mark.asyncio
    async def test_execute_plugin_async(self, plugin_communicator):
        """Test executing a plugin asynchronously."""
        plugin = MockPlugin()
        
        result = await plugin_communicator.execute_plugin(
            plugin=plugin,
            method_name="analyze_async",
            params={"file": "test.py"}
        )
        
        # Check result
        assert result.success is True
        assert result.data == {"result": "mock-async-result"}
        assert plugin.called_with == {"file": "test.py"}
    
    @pytest.mark.asyncio
    async def test_execute_plugin_method_not_found(self, plugin_communicator):
        """Test executing a non-existent plugin method."""
        plugin = MockPlugin()
        
        with pytest.raises(AttributeError):
            await plugin_communicator.execute_plugin(
                plugin=plugin,
                method_name="non_existent_method"
            )
    
    @pytest.mark.asyncio
    async def test_broadcast_event(self, message_bus, plugin_communicator):
        """Test broadcasting an event."""
        received_events = []
        
        async def event_handler(message):
            if message.type == MessageType.EVENT:
                received_events.append(message)
        
        # Subscribe to broadcast
        message_bus.subscribe("*", event_handler)
        
        # Broadcast event
        await plugin_communicator.broadcast_event(
            event_type="test_event",
            content={"data": "test"}
        )
        
        # Allow time for message processing
        await asyncio.sleep(0.1)
        
        # Check
        assert len(received_events) == 1
        assert received_events[0].type == MessageType.EVENT
        assert received_events[0].source == "test-agent"
        assert received_events[0].content == {"event_type": "test_event", "data": "test"}
    
    @pytest.mark.asyncio
    async def test_send_command_with_response(self, message_bus, plugin_communicator):
        """Test sending a command and waiting for response."""
        async def command_handler(message):
            if message.type == MessageType.REQUEST and message.content.get("command") == "test_command":
                response = Message.create_response(
                    request=message,
                    source="target",
                    content={"status": "executed"}
                )
                await message_bus.publish(response)
        
        # Subscribe target
        message_bus.subscribe("target", command_handler)
        
        # Send command
        response = await plugin_communicator.send_command(
            target_id="target",
            command="test_command",
            params={"param": "value"},
            timeout=1.0
        )
        
        # Check response
        assert response.type == MessageType.RESPONSE
        assert response.source == "target"
        assert response.content == {"status": "executed"}
    
    @pytest.mark.asyncio
    async def test_send_command_without_response(self, message_bus, plugin_communicator):
        """Test sending a command without waiting for response."""
        received_commands = []
        
        async def command_handler(message):
            if message.type == MessageType.COMMAND:
                received_commands.append(message)
        
        # Subscribe target
        message_bus.subscribe("target", command_handler)
        
        # Send command
        result = await plugin_communicator.send_command(
            target_id="target",
            command="test_command",
            params={"param": "value"},
            timeout=None
        )
        
        # Allow time for message processing
        await asyncio.sleep(0.1)
        
        # Check
        assert result is None
        assert len(received_commands) == 1
        assert received_commands[0].type == MessageType.COMMAND
        assert received_commands[0].source == "test-agent"
        assert received_commands[0].target == "target"
        assert received_commands[0].content == {"command": "test_command", "params": {"param": "value"}}
    
    @pytest.mark.asyncio
    async def test_send_status(self, message_bus, plugin_communicator):
        """Test sending a status update."""
        received_statuses = []
        
        async def status_handler(message):
            if message.type == MessageType.STATUS:
                received_statuses.append(message)
        
        # Subscribe to broadcast
        message_bus.subscribe("*", status_handler)
        
        # Send status
        await plugin_communicator.send_status(
            status="running",
            details={"progress": 50}
        )
        
        # Allow time for message processing
        await asyncio.sleep(0.1)
        
        # Check
        assert len(received_statuses) == 1
        assert received_statuses[0].type == MessageType.STATUS
        assert received_statuses[0].source == "test-agent"
        assert received_statuses[0].content == {"status": "running", "details": {"progress": 50}}
    
    def test_close(self, message_bus):
        """Test closing the communicator."""
        communicator = PluginCommunicator(message_bus, "test-agent")
        
        # Check subscription
        assert "test-agent" in message_bus._subscribers
        
        # Close
        communicator.close()
        
        # Check unsubscription
        assert "test-agent" not in message_bus._subscribers