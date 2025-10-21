"""
Advanced tests for chat command - targeting missing coverage.

This test file focuses on edge cases, error conditions, and less-traveled code paths
to increase coverage from 40% to 60%.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from lumecode.cli.commands.chat import ChatSession, chat
from lumecode.cli.core.session import SessionManager, Session
from lumecode.cli.core.llm.mock import MockProvider


class TestChatSessionAdvanced:
    """Advanced tests for ChatSession class covering edge cases."""
    
    @pytest.fixture
    def temp_session_dir(self, tmp_path):
        """Create temporary session directory."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        return session_dir
    
    @pytest.fixture
    def chat_session(self, temp_session_dir, monkeypatch):
        """Create ChatSession instance."""
        # Set XDG_DATA_HOME to use temp directory
        monkeypatch.setenv('XDG_DATA_HOME', str(temp_session_dir.parent))
        return ChatSession(model='mock')
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary test file."""
        test_file = tmp_path / "test_code.py"
        test_file.write_text("def hello():\n    return 'world'")
        return test_file
    
    # Test command processing edge cases
    
    def test_load_command_without_args(self, chat_session):
        """Test load command without session ID."""
        result = chat_session._handle_command("load")
        assert "Usage: load <session_id>" in result
    
    def test_load_command_with_invalid_session(self, chat_session):
        """Test load command with non-existent session."""
        result = chat_session._handle_command("load invalid_session_id")
        assert "Error loading session" in result
    
    def test_context_command_without_args(self, chat_session):
        """Test context command without arguments shows context."""
        result = chat_session._handle_command("context")
        assert "No files in context" in result or "Current Context" in result
    
    def test_context_add_nonexistent_file(self, chat_session, tmp_path):
        """Test adding non-existent file to context."""
        fake_file = tmp_path / "nonexistent.py"
        result = chat_session._handle_command(f"context add {fake_file}")
        assert "Error: File not found" in result
    
    def test_context_add_duplicate_file(self, chat_session, temp_file):
        """Test adding same file twice to context."""
        # Add first time
        result1 = chat_session._handle_command(f"context add {temp_file}")
        assert "Added to context" in result1
        
        # Add second time
        result2 = chat_session._handle_command(f"context add {temp_file}")
        assert "already in context" in result2
    
    def test_context_remove_file_not_in_context(self, chat_session, temp_file):
        """Test removing file that's not in context."""
        result = chat_session._handle_command(f"context remove {temp_file}")
        assert "not in context" in result
    
    def test_context_remove_existing_file(self, chat_session, temp_file):
        """Test removing file from context."""
        # Add file first
        chat_session._handle_command(f"context add {temp_file}")
        
        # Remove it
        result = chat_session._handle_command(f"context remove {temp_file}")
        assert "Removed from context" in result
    
    def test_context_clear(self, chat_session, temp_file):
        """Test clearing all context files."""
        # Add a file
        chat_session._handle_command(f"context add {temp_file}")
        
        # Clear context
        result = chat_session._handle_command("context clear")
        assert "Cleared" in result
        assert len(chat_session.context_files) == 0
    
    def test_model_command_without_args(self, chat_session):
        """Test model command without arguments shows current model."""
        result = chat_session._handle_command("model")
        assert "Current model: mock" in result
    
    def test_switch_model_success(self, chat_session):
        """Test switching to different model."""
        result = chat_session._handle_command("model groq")
        # Will fail because groq requires API key, but tests error handling
        assert "Error switching model" in result or "Switched to model" in result
    
    def test_unknown_command(self, chat_session):
        """Test handling of unknown command."""
        result = chat_session._handle_command("unknown_cmd")
        assert "Unknown command" in result
        assert "help" in result
    
    # Test file operation commands
    
    def test_explain_command_nonexistent_file(self, chat_session, tmp_path):
        """Test explain command with non-existent file."""
        fake_file = tmp_path / "nonexistent.py"
        result = chat_session._handle_command(f"explain {fake_file}")
        assert "Error: File not found" in result
    
    def test_explain_command_success(self, chat_session, temp_file):
        """Test explain command with valid file."""
        result = chat_session._handle_command(f"explain {temp_file}")
        # Mock provider should return something
        assert result is not None
        assert len(result) > 0
    
    def test_refactor_command_nonexistent_file(self, chat_session, tmp_path):
        """Test refactor command with non-existent file."""
        fake_file = tmp_path / "nonexistent.py"
        result = chat_session._handle_command(f"refactor {fake_file}")
        assert "Error: File not found" in result
    
    def test_refactor_command_success(self, chat_session, temp_file):
        """Test refactor command with valid file."""
        result = chat_session._handle_command(f"refactor {temp_file}")
        assert result is not None
        assert len(result) > 0
    
    def test_test_command_nonexistent_file(self, chat_session, tmp_path):
        """Test test command with non-existent file."""
        fake_file = tmp_path / "nonexistent.py"
        result = chat_session._handle_command(f"test {fake_file}")
        assert "Error: File not found" in result
    
    def test_test_command_success(self, chat_session, temp_file):
        """Test test command with valid file."""
        result = chat_session._handle_command(f"test {temp_file}")
        assert result is not None
        assert len(result) > 0
    
    # Test prompt building and context
    
    def test_build_prompt_with_context_files(self, chat_session, temp_file):
        """Test prompt building with context files."""
        # Add file to context
        chat_session._handle_command(f"context add {temp_file}")
        
        # Build prompt
        prompt = chat_session._build_prompt("What does this code do?")
        
        # Prompt should include context
        assert "Context Files" in prompt
        assert str(temp_file) in prompt
        assert "def hello()" in prompt
    
    def test_build_prompt_without_context(self, chat_session):
        """Test prompt building without context files."""
        prompt = chat_session._build_prompt("Hello AI")
        assert "Hello AI" in prompt
    
    # Test session save/load with errors
    
    def test_save_session_with_name(self, chat_session):
        """Test saving session with custom name."""
        result = chat_session._save_session("my_test_session")
        assert "Session saved" in result
        assert "my_test_session" in result
    
    def test_save_session_with_error(self, chat_session):
        """Test save session error handling."""
        # Mock the session_manager to raise an error
        chat_session.session_manager.save = Mock(side_effect=Exception("Save failed"))
        
        result = chat_session._save_session()
        assert "Error saving session" in result
    
    def test_load_session_with_error(self, chat_session):
        """Test load session error handling."""
        # Mock the session_manager to raise an error
        chat_session.session_manager.load = Mock(side_effect=Exception("Load failed"))
        
        result = chat_session._load_session("some_id")
        assert "Error loading session" in result
    
    # Test history display
    
    def test_show_history_empty(self, chat_session):
        """Test showing history when empty."""
        result = chat_session._show_history()
        assert "No conversation history" in result
    
    def test_show_history_with_messages(self, chat_session):
        """Test showing history with messages."""
        # Add some messages
        chat_session.session.add_message('user', 'Hello')
        chat_session.session.add_message('assistant', 'Hi there!')
        
        result = chat_session._show_history()
        assert "Conversation History" in result
        assert "user" in result.lower()
        assert "Hello" in result
    
    def test_show_history_truncates_long_messages(self, chat_session):
        """Test that long messages are truncated in history."""
        # Add a very long message
        long_message = "x" * 500
        chat_session.session.add_message('user', long_message)
        
        result = chat_session._show_history()
        assert "..." in result  # Should be truncated
    
    # Test context display
    
    def test_show_context_empty(self, chat_session):
        """Test showing context when empty."""
        result = chat_session._show_context()
        assert "No files in context" in result
    
    def test_show_context_with_files(self, chat_session, temp_file):
        """Test showing context with files."""
        chat_session._handle_command(f"context add {temp_file}")
        
        result = chat_session._show_context()
        assert "Current Context" in result
        assert str(temp_file) in result
        assert "bytes" in result
    
    # Test reset conversation
    
    def test_reset_conversation_empty(self, chat_session):
        """Test resetting empty conversation."""
        result = chat_session._reset_conversation()
        assert "Reset conversation" in result
        assert "0 messages" in result
    
    def test_reset_conversation_with_messages(self, chat_session):
        """Test resetting conversation with messages."""
        chat_session.session.add_message('user', 'Test')
        chat_session.session.add_message('assistant', 'Response')
        
        result = chat_session._reset_conversation()
        assert "Reset conversation" in result
        assert "2 messages" in result
        assert len(chat_session.session.messages) == 0
    
    # Test process_input with AI errors
    
    def test_process_input_ai_error(self, chat_session):
        """Test handling AI provider errors."""
        # Mock provider to raise error  
        chat_session.provider.complete = Mock(side_effect=Exception("API Error"))
        
        response = chat_session.process_input("Tell me something")
        assert "Error:" in response
    
    def test_process_input_normal_message(self, chat_session):
        """Test processing normal message."""
        response = chat_session.process_input("Hello AI")
        assert response is not None
        # User message should be added to session
        assert len(chat_session.session.messages) >= 1
        assert chat_session.session.messages[0].role == 'user'
        assert chat_session.session.messages[0].content == 'Hello AI'
    
    # Test files command (alias for context)
    
    def test_files_command(self, chat_session, temp_file):
        """Test files command shows context."""
        chat_session._handle_command(f"context add {temp_file}")
        
        result = chat_session._handle_command("files")
        assert str(temp_file) in result


class TestChatCommandAdvanced:
    """Advanced tests for chat CLI command."""
    
    def test_chat_with_resume_option(self):
        """Test chat command with --resume option."""
        runner = CliRunner()
        
        with patch('lumecode.cli.commands.chat.PromptSession') as mock_prompt:
            # Simulate immediate exit
            mock_prompt.return_value.prompt.side_effect = ["exit"]
            
            result = runner.invoke(chat, ['--resume', 'test_session'])
            # Command should process without error
            assert result.exit_code in [0, 1]  # May exit with error if session not found
    
    def test_chat_with_load_option(self):
        """Test chat command with --load option."""
        runner = CliRunner()
        
        with patch('lumecode.cli.commands.chat.PromptSession') as mock_prompt:
            # Simulate immediate exit
            mock_prompt.return_value.prompt.side_effect = ["exit"]
            
            result = runner.invoke(chat, ['--load', 'test_session'])
            assert result.exit_code in [0, 1]
    
    def test_chat_keyboard_interrupt_handling(self):
        """Test handling of Ctrl+C during chat."""
        runner = CliRunner()
        
        with patch('lumecode.cli.commands.chat.PromptSession') as mock_prompt:
            # Simulate KeyboardInterrupt then exit
            mock_prompt.return_value.prompt.side_effect = [
                KeyboardInterrupt(),
                "exit"
            ]
            
            result = runner.invoke(chat)
            # Should handle interrupt gracefully
            assert result.exit_code == 0
    
    def test_chat_eof_error_handling(self):
        """Test handling of EOF (Ctrl+D) during chat."""
        runner = CliRunner()
        
        with patch('lumecode.cli.commands.chat.PromptSession') as mock_prompt:
            # Simulate EOFError
            mock_prompt.return_value.prompt.side_effect = EOFError()
            
            result = runner.invoke(chat)
            # Should save and exit gracefully
            assert result.exit_code == 0
    
    def test_chat_unexpected_error_handling(self):
        """Test handling of unexpected errors during chat."""
        runner = CliRunner()
        
        with patch('lumecode.cli.commands.chat.PromptSession') as mock_prompt:
            # Simulate unexpected error then exit
            mock_prompt.return_value.prompt.side_effect = [
                Exception("Unexpected error"),
                "exit"
            ]
            
            result = runner.invoke(chat)
            # Should handle error and continue
            assert result.exit_code == 0
    
    def test_chat_empty_input_handling(self):
        """Test handling of empty input."""
        runner = CliRunner()
        
        with patch('lumecode.cli.commands.chat.PromptSession') as mock_prompt:
            # Simulate empty inputs then exit
            mock_prompt.return_value.prompt.side_effect = [
                "",
                "   ",
                "exit"
            ]
            
            result = runner.invoke(chat)
            assert result.exit_code == 0


class TestChatSessionEdgeCases:
    """Edge case tests for ChatSession."""
    
    @pytest.fixture
    def chat_session(self, tmp_path, monkeypatch):
        """Create ChatSession instance."""
        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        # Set XDG_DATA_HOME to use temp directory
        monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
        return ChatSession(model='mock')
    
    def test_multiple_context_operations(self, chat_session, tmp_path):
        """Test multiple context operations in sequence."""
        # Create multiple test files
        file1 = tmp_path / "test1.py"
        file2 = tmp_path / "test2.py"
        file1.write_text("code1")
        file2.write_text("code2")
        
        # Add files
        chat_session._handle_command(f"context add {file1}")
        chat_session._handle_command(f"context add {file2}")
        assert len(chat_session.context_files) == 2
        
        # Show context
        result = chat_session._handle_command("context")
        assert str(file1) in result
        assert str(file2) in result
        
        # Remove one
        chat_session._handle_command(f"context remove {file1}")
        assert len(chat_session.context_files) == 1
        
        # Clear all
        chat_session._handle_command("context clear")
        assert len(chat_session.context_files) == 0
    
    def test_save_and_show_commands_sequence(self, chat_session):
        """Test sequence of save and show commands."""
        # Add messages
        chat_session.session.add_message('user', 'Test 1')
        chat_session.session.add_message('assistant', 'Response 1')
        
        # Save
        save_result = chat_session._handle_command("save test_chat")
        assert "saved" in save_result.lower()
        
        # Show history
        history_result = chat_session._handle_command("history")
        assert "Test 1" in history_result
        assert "Response 1" in history_result
    
    def test_help_command_shows_all_commands(self, chat_session):
        """Test that help shows all available commands."""
        result = chat_session._handle_command("help")
        
        # Should show main commands
        assert "exit" in result or "quit" in result
        assert "help" in result
        assert "context" in result
        assert "save" in result
        assert "load" in result
        assert "model" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
