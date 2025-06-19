import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from .models import db, Media
from flask import current_app
import logging # Using logging for better debug output control in future

# Configure a simple logger for scanner (can be enhanced later)
# Use a fixed name for the logger to ensure consistency if this module is reloaded
scanner_logger = logging.getLogger('photo_album_manager.scanner')

# Check if handlers are already added to avoid duplication if module is reloaded (e.g. in some dev environments)
if not scanner_logger.handlers:
    handler = logging.StreamHandler() # Outputs to stderr by default
    formatter = logging.Formatter('%(asctime)s - SCANNER - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    scanner_logger.addHandler(handler)
    scanner_logger.setLevel(logging.DEBUG) # Set to INFO for less verbosity, DEBUG for detailed scan process
    scanner_logger.propagate = False # Prevent Flask's root logger from duplicating messages if it's also configured for stream output

def get_capture_time_from_exif(filepath):
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'DateTimeOriginal' or tag_name == 'DateTimeDigitized':
                    if isinstance(value, str):
                        # Ensure string is not empty or just spaces before parsing
                        if value.strip():
                            return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                    elif isinstance(value, bytes):
                        decoded_value = value.decode('utf-8', errors='ignore')
                        if decoded_value.strip():
                            return datetime.strptime(decoded_value, '%Y:%m:%d %H:%M:%S')
            # scanner_logger.debug(f"EXIF: Relevant date tags not found in {filepath}")
        # else:
            # scanner_logger.debug(f"EXIF: No EXIF data found in {filepath}")
    except FileNotFoundError:
        scanner_logger.warning(f"EXIF: File not found when trying to open for EXIF: {filepath}")
    except Exception as e:
        scanner_logger.error(f"EXIF: Could not read EXIF from {filepath}: {e}", exc_info=False) # exc_info=True for full traceback
    return None

def scan_libraries():
    scanner_logger.info("Starting library scan...")
    ORG_PATHS = current_app.config.get('ORG_PATHS', [])
    SUPPORTED_IMAGE_EXTENSIONS = current_app.config.get('SUPPORTED_IMAGE_EXTENSIONS', [])
    SUPPORTED_VIDEO_EXTENSIONS = current_app.config.get('SUPPORTED_VIDEO_EXTENSIONS', [])

    if not ORG_PATHS:
        scanner_logger.warning("No ORG_PATHS configured. Aborting scan.")
        return

    all_media_files_in_fs = []
    total_files_found_in_fs = 0

    for org_path_root in ORG_PATHS:
        if not os.path.exists(org_path_root):
            scanner_logger.warning(f"Library path {org_path_root} does not exist. Skipping.")
            continue

        scanner_logger.info(f"Scanning library: {org_path_root}")
        files_in_org_path = 0
        for root, _, files in os.walk(org_path_root):
            for filename in files:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                media_type = None
                if ext in SUPPORTED_IMAGE_EXTENSIONS: media_type = 'image'
                elif ext in SUPPORTED_VIDEO_EXTENSIONS: media_type = 'video'

                if media_type:
                    files_in_org_path += 1
                    all_media_files_in_fs.append({
                        "filepath": filepath, "org_path": org_path_root,
                        "filename": filename, "media_type": media_type
                    })
        scanner_logger.info(f"Found {files_in_org_path} supported media files in {org_path_root}.")
        total_files_found_in_fs += files_in_org_path

    scanner_logger.info(f"Total supported media files found across all libraries: {total_files_found_in_fs}")

    existing_media_in_db = {media.filepath: media for media in Media.query.all()}
    scanner_logger.debug(f"Found {len(existing_media_in_db)} media items currently in database.")
    processed_paths_in_fs = set() # Keep track of paths found in this scan run
    items_added_count = 0
    items_updated_count = 0
    items_removed_count = 0

    for media_data in all_media_files_in_fs:
        filepath = media_data["filepath"]
        processed_paths_in_fs.add(filepath) # Mark this path as seen in current FS scan

        try:
            stat_info = os.stat(filepath)
        except FileNotFoundError:
            scanner_logger.warning(f"File {filepath} not found during stat (it was present during os.walk). Skipping.")
            continue

        modification_time = datetime.fromtimestamp(stat_info.st_mtime)
        filesize = stat_info.st_size
        capture_time = get_capture_time_from_exif(filepath) if media_data["media_type"] == 'image' else None
        effective_capture_time = capture_time if capture_time else datetime(1999, 1, 1, 0, 0, 0)

        if filepath in existing_media_in_db:
            media_item = existing_media_in_db[filepath]
            # Compare relevant fields to see if an update is needed
            if (media_item.modification_time != modification_time or
                media_item.filesize != filesize or
                media_item.capture_time != effective_capture_time or
                media_item.media_type != media_data["media_type"] or
                media_item.org_path != media_data["org_path"] or # If file moved between managed org_paths
                media_item.filename != media_data["filename"]): # If filename changed (though filepath is primary key)

                scanner_logger.debug(f"UPDATING metadata for: {filepath}")
                media_item.modification_time = modification_time
                media_item.filesize = filesize
                media_item.capture_time = effective_capture_time
                media_item.media_type = media_data["media_type"]
                media_item.org_path = media_data["org_path"]
                media_item.filename = media_data["filename"]
                items_updated_count += 1
            # else:
                # scanner_logger.debug(f"No changes detected for existing item: {filepath}")
        else:
            scanner_logger.debug(f"ADDING new media: {filepath}")
            media_item = Media(
                filepath=filepath, org_path=media_data["org_path"],
                filename=media_data["filename"], capture_time=effective_capture_time,
                modification_time=modification_time, filesize=filesize,
                media_type=media_data["media_type"]
            )
            db.session.add(media_item)
            items_added_count += 1

    # Identify and remove items from DB that are in a scanned org_path but no longer exist in FS
    scanned_org_path_roots_set = set(ORG_PATHS) # Ensure it's a set for efficient 'in' check
    for path_in_db, media_item_in_db in existing_media_in_db.items():
        # Only consider deleting if the item's original library path was part of this scan session
        if media_item_in_db.org_path in scanned_org_path_roots_set:
            if path_in_db not in processed_paths_in_fs: # And if it wasn't found in the FS scan
                scanner_logger.debug(f"REMOVING media no longer found in a scanned library: {path_in_db}")
                db.session.delete(media_item_in_db)
                items_removed_count += 1

    try:
        db.session.commit()
        scanner_logger.info("Database changes committed successfully.")
    except Exception as e:
        db.session.rollback()
        scanner_logger.error(f"Error committing changes to database: {e}", exc_info=True)

    scanner_logger.info(f"Library scan finished. Added: {items_added_count}, Updated: {items_updated_count}, Removed: {items_removed_count}. Total in DB now: {Media.query.count()}.")
