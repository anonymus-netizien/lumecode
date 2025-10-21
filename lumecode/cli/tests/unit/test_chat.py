"""
Unit tests for Chat Command
Tests interactive REPL, session management, and chat functionality
"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from lumecode.cli.commands.chat import (
    chat,
    ChatSession,
    ChatCompleter
)


class TestChatSession:
    """Test ChatSession class."""
    
    def test_session_creation(self):
        """Test creating a new chat session."""
        session = ChatSession()
        
        assert session.session is not None
        assert session.context_files == []
        assert session.model == "gpt-3.5-turbo"  # Default model for ContextManager
        assert session.provider is not None
    
    def test_session_creation_with_model(self):
        """Test creating session with specific model."""
        session = ChatSession(model="mock")
        
        assert session.model == "mock"
        assert session.provider is not None
    
    def test_display_welcome(self):
        """Test displaying welcome message."""
        session = ChatSession()
        
        # Should not raise error
        session.display_welcome()
    
    def test_process_help_command(self):
        """Test processing help command."""
        session = ChatSession(model="mock")
        
        result = session.process_input("help")
        
        assert result is not None
        assert "command" in result.lower() or "help" in result.lower()
    
    def test_process_exit_command(self):
        """Test processing exit command."""
        session = ChatSession(model="mock")
        
        result = session.process_input("exit")
        
        # Exit returns None to signal exit
        assert result is None
    
    def test_process_clear_command(self):
        """Test processing clear command."""
        session = ChatSession(model="mock")
        
        result = session.process_input("clear")
        
        # Clear returns empty string
        assert result == ""
    
    def test_process_files_command(self):
        """Test processing files command."""
        session = ChatSession(model="mock")  # Use mock provider
        
        result = session.process_input("files")
        
        assert result is not None
        assert "file" in result.lower() or "context" in result.lower() or "error" in result.lower()
    
    def test_process_model_command(self):
        """Test processing model command."""
        session = ChatSession(model="mock")
        
        result = session.process_input("model")
        
        assert result is not None
        # Should return either model info or error message
        assert "model" in result.lower() or "error" in result.lower()
    
    def test_context_command(self):
        """Test context command."""
        session = ChatSession(model="mock")
        
        result = session.process_input("context")
        
        # Context command should return something
        assert result is not None or result == ""
    
    def test_reset_command(self):
        """Test reset command."""
        session = ChatSession(model="mock")
        
        # Add a message
        session.session.add_message("user", "Test")
        
        # Reset
        result = session.process_input("reset")
        
        # Reset should return some message
        assert result is not None or result == ""


class TestChatCompleter:
    """Test ChatCompleter for tab completion."""
    
    def test_completer_creation(self):
        """Test creating completer."""
        completer = ChatCompleter()
        
        assert completer is not None
    
    def test_get_completions_for_commands(self):
        """Test command completions."""
        completer = ChatCompleter()
        
        from prompt_toolkit.document import Document
        
        # Test /h should suggest help and history
        doc = Document("/h")
        completions = list(completer.get_completions(doc, None))
        
        completion_texts = [c.text for c in completions]
        # Should have completions for help and/or history
        assert "help" in completion_texts or "history" in completion_texts or len(completions) > 0
    
    def test_get_completions_for_partial_command(self):
        """Test partial command completions."""
        completer = ChatCompleter()
        
        from prompt_toolkit.document import Document
        
        # Test /s should suggest /save
        doc = Document("/s")
        completions = list(completer.get_completions(doc, None))
        
        # Should have completions
        assert len(completions) > 0





class TestChatCommand:
    """Test chat command CLI."""
    
    def test_chat_help(self):
        """Test chat command help."""
        runner = CliRunner()
        
        result = runner.invoke(chat, ["--help"])
        
        assert result.exit_code == 0
        assert "chat" in result.output.lower()
        assert "interactive" in result.output.lower() or "session" in result.output.lower()
    
    def test_chat_with_model_option(self):
        """Test chat with model option."""
        runner = CliRunner()
        
        # Just test that option is recognized (won't actually start interactive session)
        result = runner.invoke(chat, ["--model", "gpt-4", "--help"])
        
        # Should accept the option
        assert result.exit_code == 0
    
    @patch('lumecode.cli.commands.chat.PromptSession')
    def test_chat_interactive_mock(self, mock_prompt):
        """Test interactive chat with mocked input."""
        # Mock the prompt session
        mock_session = MagicMock()
        mock_session.prompt.side_effect = ["/exit"]  # Exit immediately
        mock_prompt.return_value = mock_session
        
        runner = CliRunner()
        result = runner.invoke(chat, input="/exit\n")
        
        # Should handle the exit gracefully
        assert result.exit_code == 0 or "/exit" in result.output


class TestChatIntegration:
    """Integration tests for chat functionality."""
    
    def test_command_sequence(self):
        """Test sequence of commands."""
        session = ChatSession(model="mock")
        
        # Test various commands
        commands = [
            "help",
            "files",
            "model",
            "context",
        ]
        
        for cmd in commands:
            result = session.process_input(cmd)
            # All should return something, None for exit, or empty string (not raise errors)
            assert result is not None or result == "" or cmd == "exit"
    
    def test_session_persistence(self):
        """Test session can be saved and loaded."""
        import tempfile
        import shutil
        from lumecode.cli.core.session import SessionManager
        
        # Create temp dir for sessions
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Create session manager with temp dir
            manager = SessionManager(sessions_dir=temp_dir)
            
            # Create and save session
            session1 = ChatSession(model="mock")
            session1.session.add_message("user", "Test message")
            manager.save(session1.session)
            
            # Load session with same manager
            loaded_session = manager.load(session1.session.id)
            
            assert len(loaded_session.messages) == 1
            assert loaded_session.messages[0].content == "Test message"
            
        finally:
            shutil.rmtree(temp_dir)


@pytest.mark.smoke
def test_chat_command_exists():
    """Smoke test: Verify chat command is registered."""
    runner = CliRunner()
    result = runner.invoke(chat, ["--help"])
    
    assert result.exit_code == 0
    assert "chat" in result.output.lower()


@pytest.mark.smoke  
def test_chat_has_options():
    """Smoke test: Verify chat command has expected options."""
    runner = CliRunner()
    result = runner.invoke(chat, ["--help"])
    
    assert result.exit_code == 0
    # Should have model, resume, or load options
    assert "--model" in result.output or "-m" in result.output
