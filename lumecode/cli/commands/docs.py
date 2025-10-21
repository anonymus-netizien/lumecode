import os
import click
import logging
from pathlib import Path

from lumecode.backend.docs import DocManager, DocFormat

# Provide get_provider for tests that patch this symbol at module level
try:
    from lumecode.cli.core.llm import get_provider  # noqa: F401
except Exception:
    # Backend docs don't use providers; ignore if unavailable
    get_provider = None  # type: ignore

logger = logging.getLogger(__name__)


@click.group(name="docs", help="Documentation generation commands")
def docs_group():
    """Documentation generation command group."""
    pass


@docs_group.command("generate", help="Generate documentation for the project")
@click.option(
    "--output", "-o", type=click.Path(), help="Output directory for generated documentation"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice([fmt.value for fmt in DocFormat]),
    default="markdown",
    help="Documentation format",
)
@click.option("--serve", "-s", is_flag=True, help="Serve the documentation after generation")
@click.option(
    "--port",
    "-p",
    type=int,
    default=8080,
    help="Port to serve documentation on (if --serve is specified)",
)
@click.option(
    "--type",
    "-t",
    type=click.Choice(["api", "overview", "all"]),
    default="all",
    help="Type of documentation to generate",
)
@click.pass_context
def generate_docs(ctx, output, format, serve, port, type):
    """Generate documentation for the project.

    This command analyzes the project codebase and generates documentation
    based on the specified options. It can generate API documentation,
    project overview, or both, and can optionally serve the documentation
    via a local web server.
    """
    from lumecode.backend.config import ConfigManager

    # Get project root from config
    config = ConfigManager()
    project_root = config.get_value("project.directory")

    if not project_root:
        project_root = os.getcwd()
        logger.warning(f"Project directory not configured, using current directory: {project_root}")

    # Set output directory
    if output:
        output_dir = os.path.abspath(output)
    else:
        output_dir = os.path.join(project_root, "docs", "generated")

    click.echo(f"Generating documentation in {output_dir}...")

    # Create doc manager
    doc_manager = DocManager(project_root, output_dir)

    # Generate documentation
    if type == "api" or type == "all":
        api_path = doc_manager.generate_api_docs()
        click.echo(f"Generated API documentation: {api_path}")

    if type == "overview" or type == "all":
        overview_path = doc_manager.generate_overview_docs()
        click.echo(f"Generated overview documentation: {overview_path}")

    # Serve documentation if requested
    if serve:
        url = doc_manager.serve_docs(port=port)
        click.echo(f"Documentation server started at {url}")
        click.echo("Press Ctrl+C to stop the server")

        try:
            # Keep the process running
            import time

            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            doc_manager.stop_server()
            click.echo("Documentation server stopped")


@docs_group.command("serve", help="Serve existing documentation")
@click.option(
    "--directory",
    "-d",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Directory containing documentation to serve",
)
@click.option("--port", "-p", type=int, default=8080, help="Port to serve documentation on")
@click.pass_context
def serve_docs(ctx, directory, port):
    """Serve existing documentation.

    This command starts a local web server to serve existing documentation.
    If no directory is specified, it will look for documentation in the
    default location (docs/generated).
    """
    from lumecode.backend.config import ConfigManager
    from lumecode.backend.docs import DocServer

    # Get project root from config
    config = ConfigManager()
    project_root = config.get_value("project.directory")

    if not project_root:
        project_root = os.getcwd()
        logger.warning(f"Project directory not configured, using current directory: {project_root}")

    # Set documentation directory
    if directory:
        doc_dir = os.path.abspath(directory)
    else:
        doc_dir = os.path.join(project_root, "docs", "generated")

    if not os.path.exists(doc_dir):
        click.echo(f"Documentation directory not found: {doc_dir}")
        click.echo("Generate documentation first with 'lumecode docs generate'")
        ctx.exit(1)

    click.echo(f"Serving documentation from {doc_dir}...")

    # Create and start server
    server = DocServer(doc_dir, port=port)
    url = server.start()

    click.echo(f"Documentation server started at {url}")
    click.echo("Press Ctrl+C to stop the server")

    try:
        # Keep the process running
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        click.echo("Documentation server stopped")
