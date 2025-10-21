"""
Streaming UI Display
Handles real-time rendering of AI responses with Rich UI
"""

from typing import Iterator, Optional
from rich.live import Live
from rich.markdown import Markdown
from rich.console import Console
from rich.panel import Panel


class StreamingDisplay:
    """Handle streaming AI responses with Rich UI."""

    def __init__(self, console: Console = None):
        """
        Initialize streaming display.

        Args:
            console: Rich console instance (creates new if None)
        """
        self.console = console or Console()

    def stream_markdown(
        self, chunks: Iterator[str], title: Optional[str] = None, show_panel: bool = False
    ) -> str:
        """
        Stream and render markdown in real-time.

        Args:
            chunks: Iterator of text chunks from LLM
            title: Optional title for the response
            show_panel: Whether to wrap in a panel

        Returns:
            Complete response text
        """
        buffer = ""

        try:
            with Live(console=self.console, refresh_per_second=10, transient=False) as live:
                for chunk in chunks:
                    buffer += chunk

                    # Create markdown content
                    if title:
                        content = f"# {title}\n\n{buffer}"
                    else:
                        content = buffer

                    # Render with or without panel
                    if show_panel:
                        display = Panel(
                            Markdown(content), title=title or "Response", border_style="cyan"
                        )
                    else:
                        display = Markdown(content)

                    live.update(display)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")

        return buffer

    def stream_text(self, chunks: Iterator[str], style: str = "cyan") -> str:
        """
        Stream plain text (for logs/debugging).

        Args:
            chunks: Iterator of text chunks
            style: Rich style to apply

        Returns:
            Complete response text
        """
        buffer = ""

        try:
            for chunk in chunks:
                self.console.print(chunk, end="", style=style)
                buffer += chunk

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")

        # New line at end
        self.console.print()
        return buffer

    def stream_with_status(
        self,
        chunks: Iterator[str],
        status_text: str = "Generating response...",
        title: Optional[str] = None,
    ) -> str:
        """
        Stream with a status indicator before starting.

        Args:
            chunks: Iterator of text chunks
            status_text: Status message to show before streaming
            title: Optional title for response

        Returns:
            Complete response text
        """
        # Show status briefly
        with self.console.status(f"[cyan]{status_text}", spinner="dots"):
            # Get first chunk to confirm connection
            try:
                first_chunk = next(chunks)
                buffer = first_chunk
            except StopIteration:
                return ""

        # Now stream the rest
        self.console.print()  # Add spacing

        try:
            with Live(console=self.console, refresh_per_second=10, transient=False) as live:
                # Render first chunk
                content = f"# {title}\n\n{buffer}" if title else buffer
                live.update(Markdown(content))

                # Stream remaining chunks
                for chunk in chunks:
                    buffer += chunk
                    content = f"# {title}\n\n{buffer}" if title else buffer
                    live.update(Markdown(content))

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")

        return buffer
