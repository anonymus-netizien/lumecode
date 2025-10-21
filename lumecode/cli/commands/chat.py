"""
Interactive REPL Mode for Lumecode
Provides conversational AI sessions with context preservation
"""

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json

from lumecode.cli.core.llm import get_provider_with_fallback
from lumecode.cli.core.session import Session, SessionManager
from lumecode.cli.core.context import ContextManager


class ChatCompleter(Completer):
    """Custom completer for chat commands."""

    commands = [
        "help",
        "exit",
        "quit",
        "clear",
        "history",
        "save",
        "load",
        "context",
        "files",
        "model",
        "explain",
        "refactor",
        "test",
        "review",
        "commit",
        "search",
        "reset",
    ]

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()
        for cmd in self.commands:
            if cmd.startswith(word):
                yield Completion(
                    cmd,
                    start_position=-len(word),
                    display=cmd,
                    display_meta=self._get_command_help(cmd),
                )

    def _get_command_help(self, cmd: str) -> str:
        """Get help text for command."""
        help_texts = {
            "help": "Show available commands",
            "exit": "Exit chat session",
            "quit": "Exit chat session",
            "clear": "Clear screen",
            "history": "Show conversation history",
            "save": "Save current session",
            "load": "Load previous session",
            "context": "Show current context",
            "files": "List files in context",
            "model": "Switch AI model",
            "explain": "Explain code",
            "refactor": "Refactor code",
            "test": "Generate tests",
            "review": "Review code",
            "commit": "Generate commit message",
            "search": "Search codebase",
            "reset": "Reset conversation",
        }
        return help_texts.get(cmd, "")


class ChatSession:
    """Manage interactive chat session."""

    def __init__(self, model: Optional[str] = None, session_id: Optional[str] = None):
        self.console = Console()
        self.model = model or "gpt-3.5-turbo"
        self.session_manager = SessionManager()

        if session_id:
            self.session = self.session_manager.load(session_id)
        else:
            self.session = Session.create_new(name="interactive_chat")

        self.provider = get_provider_with_fallback(model)
        self.context_manager = ContextManager(model=self.model)
        # Keep context_files for backward compatibility
        self.context_files: List[Path] = []

    def display_welcome(self):
        """Display welcome message."""
        welcome_text = """
# 🤖 Lumecode Interactive Chat

**Commands:**
- `help` - Show all commands
- `explain <file>` - Explain code in file
- `refactor <file>` - Refactor code
- `test <file>` - Generate tests
- `context add <file>` - Add file to context
- `save` - Save session
- `exit` - Quit

Type your question or command...
"""
        self.console.print(Panel(Markdown(welcome_text), title="Welcome", border_style="blue"))

    def process_input(self, user_input: str) -> Optional[str]:
        """Process user input and return response."""

        # Handle commands
        if user_input.startswith("/"):
            return self._handle_command(user_input[1:])

        # Check for special keywords
        if user_input.lower().startswith(
            (
                "help",
                "exit",
                "quit",
                "clear",
                "save",
                "load",
                "files",
                "context",
                "model",
                "explain",
                "refactor",
                "test",
                "history",
                "reset",
            )
        ):
            return self._handle_command(user_input)

        # Regular AI query
        self.session.add_message("user", user_input)

        # Build context-aware prompt
        prompt = self._build_prompt(user_input)

        try:
            # Use complete() method (common to all providers)
            response = self.provider.complete(prompt, max_tokens=2000)
            self.session.add_message("assistant", response)
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def _handle_command(self, command: str) -> Optional[str]:
        """Handle special commands."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ["exit", "quit"]:
            self._save_session()
            return None  # Signal to exit

        elif cmd == "help":
            return self._show_help()

        elif cmd == "clear":
            self.console.clear()
            return ""

        elif cmd == "history":
            return self._show_history()

        elif cmd == "save":
            session_name = args[0] if args else None
            return self._save_session(session_name)

        elif cmd == "load":
            if not args:
                return "Usage: load <session_id>"
            return self._load_session(args[0])

        elif cmd == "context":
            if not args:
                return self._show_context()

            action = args[0].lower()
            if action == "add" and len(args) > 1:
                return self._add_context_file(args[1])
            elif action == "remove" and len(args) > 1:
                return self._remove_context_file(args[1])
            elif action == "clear":
                return self._clear_context()

        elif cmd == "files":
            return self._list_context_files()

        elif cmd == "model":
            if not args:
                return f"Current model: {self.model or 'default'}"
            return self._switch_model(args[0])

        elif cmd == "reset":
            return self._reset_conversation()

        elif cmd == "explain" and args:
            return self._explain_file(args[0])

        elif cmd == "refactor" and args:
            return self._refactor_file(args[0])

        elif cmd == "test" and args:
            return self._generate_tests(args[0])

        else:
            return f"Unknown command: {cmd}. Type 'help' for available commands."

    def _build_prompt(self, user_input: str) -> str:
        """Build context-aware prompt with token management."""
        prompt_parts = []

        # Add context from context manager (already token-managed)
        context = self.context_manager.get_context(format="markdown")
        if context:
            prompt_parts.append(context)

        # Add recent conversation history (last 5 messages)
        recent_messages = self.session.messages[-10:]  # Last 5 exchanges
        if recent_messages:
            prompt_parts.append("## Conversation History\n")
            for msg in recent_messages:
                prompt_parts.append(f"**{msg.role}**: {msg.content}\n")

        # Add current query
        prompt_parts.append(f"## Current Query\n{user_input}")

        return "\n\n".join(prompt_parts)

    def _show_help(self) -> str:
        """Show help message."""
        return """
**Available Commands:**

**Basic:**
- `help` - Show this help message
- `exit`, `quit` - Exit chat session
- `clear` - Clear screen
- `reset` - Reset conversation history

**Session Management:**
- `save [name]` - Save current session
- `load <id>` - Load previous session
- `history` - Show conversation history

**Context Management:**
- `context` - Show current context
- `context add <file>` - Add file to context
- `context remove <file>` - Remove file from context
- `context clear` - Clear all context
- `files` - List files in context

**AI Operations:**
- `explain <file>` - Explain code in file
- `refactor <file>` - Refactor code in file
- `test <file>` - Generate tests for file
- `review <file>` - Review code in file

**Configuration:**
- `model [name]` - Show/switch AI model

**Tip:** You can also just type naturally and the AI will respond!
"""

    def _show_history(self) -> str:
        """Show conversation history."""
        if not self.session.messages:
            return "No conversation history yet."

        history = ["## Conversation History\n"]
        for i, msg in enumerate(self.session.messages, 1):
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            history.append(f"**{i}. [{timestamp}] {msg.role}:**")
            history.append(f"{msg.content[:200]}{'...' if len(msg.content) > 200 else ''}\n")

        return "\n".join(history)

    def _save_session(self, name: Optional[str] = None) -> str:
        """Save current session."""
        if name:
            self.session.name = name

        try:
            self.session_manager.save(self.session)
            return f"✓ Session saved: {self.session.id} ({self.session.name})"
        except Exception as e:
            return f"Error saving session: {str(e)}"

    def _load_session(self, session_id: str) -> str:
        """Load previous session."""
        try:
            self.session = self.session_manager.load(session_id)
            return f"✓ Session loaded: {self.session.id} ({self.session.name})"
        except Exception as e:
            return f"Error loading session: {str(e)}"

    def _show_context(self) -> str:
        """Show current context with token usage."""
        summary = self.context_manager.get_summary()

        if summary["file_count"] == 0:
            return "No files in context. Use `context add <file>` to add files."

        context = ["## Current Context\n"]

        # Add token usage info
        usage = summary["usage_percentage"]
        tokens = summary["current_tokens"]
        max_tokens = summary["max_tokens"]
        context.append(f"**Token Usage:** {tokens}/{max_tokens} ({usage:.1f}%)\n")

        # Add file list with full paths
        for i, file_info in enumerate(summary["files"], 1):
            context.append(f"{i}. {file_info['path']} ({file_info['size']} bytes)")

        # Keep backward compat with context_files
        self.context_files = [Path(f["path"]) for f in summary["files"]]

        return "\n".join(context)

    def _add_context_file(self, file_path: str) -> str:
        """Add file to context with token management."""
        path = Path(file_path)

        if not path.exists():
            return f"Error: File not found: {file_path}"

        # Check if already in context
        if path in self.context_manager.files:
            return f"File already in context: {file_path}"

        # Check if can add
        if not self.context_manager.can_add_file(path):
            return f"⚠ Cannot add file: Would exceed token limit. Current usage: {self.context_manager.get_usage_percentage():.1f}%"

        # Add to context manager
        if self.context_manager.add_file(path):
            # Update context_files for backward compat
            if path not in self.context_files:
                self.context_files.append(path)

            usage = self.context_manager.get_usage_percentage()
            return f"✓ Added to context: {file_path} (Usage: {usage:.1f}%)"

        return f"Error: Could not add file: {file_path}"

    def _remove_context_file(self, file_path: str) -> str:
        """Remove file from context."""
        path = Path(file_path)

        if self.context_manager.remove_file(path):
            # Update context_files for backward compat
            if path in self.context_files:
                self.context_files.remove(path)
            return f"✓ Removed from context: {file_path}"

        return f"File not in context: {file_path}"

    def _clear_context(self) -> str:
        """Clear all context."""
        count = len(self.context_files)
        self.context_manager.clear()
        self.context_files.clear()
        return f"✓ Cleared {count} file(s) from context"

    def _list_context_files(self) -> str:
        """List files in context."""
        return self._show_context()

    def _switch_model(self, model_name: str) -> str:
        """Switch AI model."""
        try:
            self.provider = get_provider_with_fallback(model_name)
            self.model = model_name
            return f"✓ Switched to model: {model_name}"
        except Exception as e:
            return f"Error switching model: {str(e)}"

    def _reset_conversation(self) -> str:
        """Reset conversation history."""
        count = len(self.session.messages)
        self.session.messages.clear()
        return f"✓ Reset conversation ({count} messages cleared)"

    def _explain_file(self, file_path: str) -> str:
        """Explain code in file."""
        path = Path(file_path)

        if not path.exists():
            return f"Error: File not found: {file_path}"

        content = path.read_text()
        prompt = f"Explain this code:\n\n```\n{content}\n```"

        try:
            return self.provider.complete(prompt, max_tokens=2000)
        except Exception as e:
            return f"Error: {str(e)}"

    def _refactor_file(self, file_path: str) -> str:
        """Refactor code in file."""
        path = Path(file_path)

        if not path.exists():
            return f"Error: File not found: {file_path}"

        content = path.read_text()
        prompt = (
            f"Refactor this code for better readability and maintainability:\n\n```\n{content}\n```"
        )

        try:
            return self.provider.complete(prompt, max_tokens=2000)
        except Exception as e:
            return f"Error: {str(e)}"

    def _generate_tests(self, file_path: str) -> str:
        """Generate tests for file."""
        path = Path(file_path)

        if not path.exists():
            return f"Error: File not found: {file_path}"

        content = path.read_text()
        prompt = f"Generate comprehensive tests for this code:\n\n```\n{content}\n```"

        try:
            return self.provider.complete(prompt, max_tokens=2000)
        except Exception as e:
            return f"Error: {str(e)}"


@click.command()
@click.option("--model", "-m", help="AI model to use")
@click.option("--resume", "-r", help="Resume previous session ID")
@click.option("--load", "-l", help="Load session by ID")
def chat(model: Optional[str], resume: Optional[str], load: Optional[str]):
    """
    Start interactive chat session with AI.

    Examples:
        lumecode chat
        lumecode chat --model groq
        lumecode chat --resume abc123
    """
    console = Console()

    # Create chat session
    session_id = resume or load
    chat_session = ChatSession(model=model, session_id=session_id)

    # Display welcome
    chat_session.display_welcome()

    # Create prompt session with history and completion
    history_file = Path.home() / ".lumecode" / "chat_history.txt"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=ChatCompleter(),
        complete_while_typing=True,
    )

    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = prompt_session.prompt(HTML("<ansigreen>You:</ansigreen> ")).strip()

            if not user_input:
                continue

            # Process input
            response = chat_session.process_input(user_input)

            # Check for exit signal
            if response is None:
                console.print("\n[yellow]Session saved. Goodbye! 👋[/yellow]\n")
                break

            # Display response
            if response:
                console.print()
                console.print(Panel(Markdown(response), title="🤖 AI", border_style="blue"))
                console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit and save session[/yellow]")
            continue

        except EOFError:
            chat_session._save_session()
            console.print("\n[yellow]Session saved. Goodbye! 👋[/yellow]\n")
            break

        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]\n")
            continue


if __name__ == "__main__":
    chat()
