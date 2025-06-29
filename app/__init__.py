from flask import Flask
from flask_session import Session # Import Session
import os

from .models import db, init_db as init_models_db
import logging # For HEIC registration logging

# Attempt to register HEIC opener from pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    logging.info("Successfully registered HEIF opener with Pillow.")
except ImportError:
    logging.warning("pillow-heif not found or could not be imported. HEIC/HEIF support will be disabled.")
except Exception as e:
    logging.error(f"An error occurred during HEIF opener registration: {e}", exc_info=True)


def create_app(config_pyfile_path=None):
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static',
                instance_relative_config=False)

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    if not config_pyfile_path:
        config_pyfile_path = os.path.join(project_root, 'config.py')

    if os.path.exists(config_pyfile_path):
        app.config.from_pyfile(config_pyfile_path)
        print(f"Loaded configuration from: {config_pyfile_path}")
    else:
        print(f"Warning: Configuration file not found at {config_pyfile_path}. Using defaults.")
        app.config.setdefault('BASE_DIR', project_root)
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', f"sqlite:///{os.path.join(project_root, 'data', 'default_photo_album.sqlite')}")
        app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
        app.config.setdefault('ORG_PATHS', [os.path.join(project_root, 'sample_media_fallback', 'library1')])
        app.config.setdefault('ARCHIVE_PATH', os.path.join(project_root, 'sample_media_fallback', 'archive'))
        app.config.setdefault('SUPPORTED_IMAGE_EXTENSIONS', ['.jpg', '.jpeg'])
        app.config.setdefault('SUPPORTED_VIDEO_EXTENSIONS', ['.mp4', '.mov'])
        # Ensure sample dirs for fallback are created
        fallback_org_path = app.config['ORG_PATHS'][0]
        fallback_archive_path = app.config['ARCHIVE_PATH']
        if not os.path.exists(fallback_org_path): os.makedirs(fallback_org_path, exist_ok=True)
        if not os.path.exists(fallback_archive_path): os.makedirs(fallback_archive_path, exist_ok=True)

    app.config.setdefault('SESSION_TYPE', 'filesystem')
    # Use BASE_DIR from app.config if available (set by config.py), else use project_root
    # This ensures SESSION_FILE_DIR is relative to the actual project base.
    effective_base_dir = app.config.get('BASE_DIR', project_root)
    app.config.setdefault('SESSION_FILE_DIR', os.path.join(effective_base_dir, 'data', 'flask_session'))
    app.config.setdefault('SESSION_PERMANENT', False)
    app.config.setdefault('SESSION_USE_SIGNER', True)

    if 'SECRET_KEY' not in app.config:
        print("Warning: SECRET_KEY not found in config. Generating a temporary one. Set a fixed SECRET_KEY in config.py for production.")
        app.config['SECRET_KEY'] = os.urandom(32)

    session_file_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_file_dir):
        try:
            os.makedirs(session_file_dir)
            print(f"Created SESSION_FILE_DIR at {session_file_dir}")
        except OSError as e:
            print(f"Error creating SESSION_FILE_DIR {session_file_dir}: {e}")

    Session(app)

    if not os.path.exists(app.instance_path):
        try:
            os.makedirs(app.instance_path)
        except OSError as e:
            print(f"Error creating instance folder {app.instance_path}: {e}")

    init_models_db(app)

    from . import commands
    commands.init_app(app)

    with app.app_context():
        from . import routes
        pass

    return app
