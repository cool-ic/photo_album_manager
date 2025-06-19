from flask import Flask
import os
from .models import db, init_db as init_models_db
from .scanner import scan_libraries # Import the scanner function
import click # For Flask CLI commands

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    config_path = os.path.join(app.root_path, '..', 'config.py')
    if os.path.exists(config_path):
        app.config.from_pyfile(config_path)
        print(f"Loaded configuration from: {config_path}")
    else:
        print(f"Warning: Configuration file not found at {config_path}")
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', f"sqlite:///{os.path.join(app.root_path, '..', 'data', 'photo_album.sqlite')}")
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        base_dir_for_fallback = os.path.join(app.root_path, '..')
        app.config.setdefault('ORG_PATHS', [
            os.path.join(base_dir_for_fallback, 'sample_media_fallback', 'library1'),
        ])
        app.config.setdefault('ARCHIVE_PATH', os.path.join(base_dir_for_fallback, 'sample_media_fallback', 'archive'))
        app.config.setdefault('SUPPORTED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg'])
        app.config.setdefault('SUPPORTED_VIDEO_EXTENSIONS', ['.mp4', '.mov'])

    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
        print(f"Created instance folder at {app.instance_path}")

    init_models_db(app)

    @app.cli.command('scan')
    def scan_command():
        """Scans media libraries."""
        with app.app_context():
            scan_libraries()
        click.echo('Scan complete.')

    with app.app_context():
        from . import routes
        pass

    return app
