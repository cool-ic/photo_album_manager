import click
from flask.cli import AppGroup, with_appcontext
from .scanner import scan_libraries

# Create an AppGroup for 'scan' commands
scan_cli = AppGroup('scan', help='Media scanning commands.')

@scan_cli.command('libraries', help='Scans media libraries specified in config.py.')
@click.option('--force-rescan', is_flag=True, help="Force re-check of all media files even if modification time and size haven't changed.")
@with_appcontext
def scan_libraries_command(force_rescan):
    """Command to scan media libraries."""
    click.echo('Starting library scan via Flask CLI...')
    # Pass force_rescan to scan_libraries if it's updated to handle it
    # For now, scan_libraries doesn't take arguments, but this structure allows it.
    if force_rescan:
        click.echo('Force rescan option is set (currently illustrative).')
        # scan_libraries(force_rescan=True) # Example if scan_libraries supported it
        scan_libraries()
    else:
        scan_libraries()
    click.echo('Library scan finished.')

def init_app(app):
    """Registers the scan_cli blueprint with the Flask app."""
    app.cli.add_command(scan_cli)
    # Add other command groups or commands to app.cli here
