"""
Unit tests for Session Management
Tests session creation, save/load, and message handling
"""

import pytest
from datetime import datetime
from pathlib import Path
import json
import tempfile
import shutil

from lumecode.cli.core.session import Session, SessionManager, Message


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            role="user", content="Hello AI!", timestamp=datetime.now(), metadata={"source": "test"}
        )

        assert msg.role == "user"
        assert msg.content == "Hello AI!"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata["source"] == "test"

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        now = datetime.now()
        msg = Message(role="assistant", content="Hello human!", timestamp=now, metadata={})

        msg_dict = msg.to_dict()

        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "Hello human!"
        assert msg_dict["timestamp"] == now.isoformat()
        assert "metadata" in msg_dict

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        now = datetime.now()
        msg_dict = {
            "role": "user",
            "content": "Test content",
            "timestamp": now.isoformat(),
            "metadata": {"test": "value"},
        }

        msg = Message.from_dict(msg_dict)

        assert msg.role == "user"
        assert msg.content == "Test content"
        assert msg.metadata["test"] == "value"


class TestSession:
    """Test Session class."""

    def test_session_creation(self):
        """Test creating a new session."""
        session = Session.create_new("Test Session")

        assert session.name == "Test Session"
        assert len(session.id) == 8  # UUID first 8 chars
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert len(session.messages) == 0
        assert len(session.context) == 0

    def test_add_message(self):
        """Test adding messages to session."""
        session = Session.create_new()

        session.add_message("user", "What is Python?")
        session.add_message("assistant", "Python is a programming language.")

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"
        assert session.messages[0].content == "What is Python?"

    def test_add_message_with_metadata(self):
        """Test adding message with metadata."""
        session = Session.create_new()

        session.add_message("user", "Test message", file_path="/test/file.py", line_number=42)

        assert len(session.messages) == 1
        assert session.messages[0].metadata["file_path"] == "/test/file.py"
        assert session.messages[0].metadata["line_number"] == 42

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        session = Session.create_new()

        # Add 15 messages
        for i in range(15):
            session.add_message("user", f"Message {i}")

        # Get last 10
        recent = session.get_recent_messages(10)

        assert len(recent) == 10
        assert recent[0].content == "Message 5"
        assert recent[-1].content == "Message 14"

    def test_get_context_summary(self):
        """Test getting session summary."""
        session = Session.create_new("My Session")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        summary = session.get_context_summary()

        assert "My Session" in summary
        assert "Messages: 2" in summary
        assert session.id in summary

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        session = Session.create_new("Test")
        session.add_message("user", "Hello")

        session_dict = session.to_dict()

        assert session_dict["name"] == "Test"
        assert session_dict["id"] == session.id
        assert len(session_dict["messages"]) == 1
        assert "created_at" in session_dict
        assert "updated_at" in session_dict

    def test_session_from_dict(self):
        """Test creating session from dictionary."""
        now = datetime.now()
        session_dict = {
            "id": "test123",
            "name": "Test Session",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "messages": [
                {"role": "user", "content": "Hello", "timestamp": now.isoformat(), "metadata": {}}
            ],
            "context": {"file": "test.py"},
            "metadata": {"test": "value"},
        }

        session = Session.from_dict(session_dict)

        assert session.id == "test123"
        assert session.name == "Test Session"
        assert len(session.messages) == 1
        assert session.context["file"] == "test.py"
        assert session.metadata["test"] == "value"


class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create SessionManager with temporary directory."""
        return SessionManager(sessions_dir=temp_dir)

    def test_manager_creation(self, temp_dir):
        """Test creating session manager."""
        manager = SessionManager(sessions_dir=temp_dir)

        assert manager.sessions_dir == temp_dir
        assert manager.sessions_dir.exists()

    def test_save_session(self, manager):
        """Test saving session to disk."""
        session = Session.create_new("Save Test")
        session.add_message("user", "Test message")

        saved_path = manager.save(session)

        assert saved_path.exists()
        assert saved_path.name == f"{session.id}.json"

        # Verify file contents
        with open(saved_path) as f:
            data = json.load(f)

        assert data["name"] == "Save Test"
        assert len(data["messages"]) == 1

    def test_load_session(self, manager):
        """Test loading session from disk."""
        # Create and save session
        session = Session.create_new("Load Test")
        session.add_message("user", "Original message")
        session.context["test_key"] = "test_value"
        manager.save(session)

        # Load session
        loaded = manager.load(session.id)

        assert loaded.id == session.id
        assert loaded.name == "Load Test"
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Original message"
        assert loaded.context["test_key"] == "test_value"

    def test_load_nonexistent_session(self, manager):
        """Test loading session that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            manager.load("nonexistent123")

    def test_list_sessions(self, manager):
        """Test listing all sessions."""
        # Create multiple sessions
        session1 = Session.create_new("Session 1")
        session1.add_message("user", "Message 1")
        manager.save(session1)

        session2 = Session.create_new("Session 2")
        session2.add_message("user", "Message 2")
        session2.add_message("assistant", "Response 2")
        manager.save(session2)

        # List sessions
        sessions = manager.list_sessions()

        assert len(sessions) == 2

        # Check session info
        session_names = [s["name"] for s in sessions]
        assert "Session 1" in session_names
        assert "Session 2" in session_names

        # Check message counts
        for s in sessions:
            if s["name"] == "Session 1":
                assert s["message_count"] == 1
            elif s["name"] == "Session 2":
                assert s["message_count"] == 2

    def test_list_sessions_limit(self, manager):
        """Test listing sessions with limit."""
        # Create many sessions
        for i in range(25):
            session = Session.create_new(f"Session {i}")
            manager.save(session)

        # List with limit
        sessions = manager.list_sessions(limit=10)

        assert len(sessions) == 10

    def test_delete_session(self, manager):
        """Test deleting a session."""
        session = Session.create_new("Delete Test")
        manager.save(session)

        # Verify exists
        session_file = manager.sessions_dir / f"{session.id}.json"
        assert session_file.exists()

        # Delete
        manager.delete(session.id)

        # Verify deleted
        assert not session_file.exists()

    def test_export_markdown(self, manager):
        """Test exporting session as Markdown."""
        session = Session.create_new("Export Test")
        session.add_message("user", "What is Python?")
        session.add_message("assistant", "Python is a programming language.")
        session.add_message("user", "Tell me more.")
        manager.save(session)

        # Export
        markdown = manager.export(session.id, format="markdown")

        assert "# Export Test" in markdown
        assert "What is Python?" in markdown
        assert "Python is a programming language." in markdown
        assert "user" in markdown.lower()
        assert "assistant" in markdown.lower()

    def test_export_json(self, manager):
        """Test exporting session as JSON."""
        session = Session.create_new("JSON Test")
        session.add_message("user", "Test")
        manager.save(session)

        # Export
        json_str = manager.export(session.id, format="json")

        # Verify valid JSON
        data = json.loads(json_str)
        assert data["name"] == "JSON Test"
        assert len(data["messages"]) == 1

    def test_export_invalid_format(self, manager):
        """Test export with invalid format."""
        session = Session.create_new("Test")
        manager.save(session)

        with pytest.raises(ValueError):
            manager.export(session.id, format="invalid")


class TestSessionIntegration:
    """Integration tests for session management."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)

    def test_full_session_workflow(self, temp_dir):
        """Test complete session workflow."""
        manager = SessionManager(sessions_dir=temp_dir)

        # Create session
        session = Session.create_new("Workflow Test")

        # Add conversation
        session.add_message("user", "Explain decorators")
        session.add_message("assistant", "Decorators modify function behavior...")
        session.add_message("user", "Give me an example")
        session.add_message("assistant", "Here's an example...")

        # Add context
        session.context["file"] = "test.py"
        session.context["line"] = 42

        # Save
        manager.save(session)

        # List and verify
        sessions = manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["message_count"] == 4

        # Load and verify
        loaded = manager.load(session.id)
        assert len(loaded.messages) == 4
        assert loaded.context["file"] == "test.py"

        # Export
        markdown = manager.export(session.id, format="markdown")
        assert "Workflow Test" in markdown
        assert "decorators" in markdown.lower()

        # Add more messages
        loaded.add_message("user", "Thanks!")
        manager.save(loaded)

        # Reload and verify
        reloaded = manager.load(session.id)
        assert len(reloaded.messages) == 5
        assert reloaded.messages[-1].content == "Thanks!"

    def test_multiple_sessions_concurrent(self, temp_dir):
        """Test managing multiple sessions."""
        manager = SessionManager(sessions_dir=temp_dir)

        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = Session.create_new(f"Session {i}")
            session.add_message("user", f"Message in session {i}")
            manager.save(session)
            sessions.append(session)

        # List all
        all_sessions = manager.list_sessions()
        assert len(all_sessions) == 5

        # Load each and verify
        for i, orig_session in enumerate(sessions):
            loaded = manager.load(orig_session.id)
            assert loaded.name == f"Session {i}"
            assert len(loaded.messages) == 1
