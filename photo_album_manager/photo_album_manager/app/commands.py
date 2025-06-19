import click
from flask.cli import with_appcontext
from .scanner import scan_libraries

def init_app(app):
    @app.cli.command('scan')
    @click.option('--force-rescan', is_flag=True, help="Force re-check of all media files even if modification time and size haven't changed.")
    # Add more options if needed, e.g., specific paths to scan
    @with_appcontext
    def scan_command(force_rescan):
        """Scans media libraries specified in config.py."""
        click.echo('Starting library scan...')
        # scan_libraries(force_rescan=force_rescan) # If scan_libraries is updated to accept it
        scan_libraries()
        click.echo('Library scan finished.')

    # Add other CLI commands here if needed
