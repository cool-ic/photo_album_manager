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

        # Skip EXIF attempt for formats that typically don't have it or handle it differently
        if img.format in ['GIF', 'PNG', 'WEBP']:
            scanner_logger.debug(f"EXIF: Skipping EXIF read for format {img.format} on {filepath}")
            return None

        exif_data = None
        try:
            exif_data = img.getexif() # Preferred method for Pillow 7+
        except AttributeError:
            scanner_logger.debug(f"EXIF: img.getexif() failed (likely older Pillow), trying img._getexif() for {filepath}")
            try:
                exif_data = img._getexif()
            except AttributeError: # If _getexif also fails (e.g. for non-JPEG types passed mistakenly or very old Pillow)
                 scanner_logger.warning(f"EXIF: Neither getexif nor _getexif method found for image {filepath} (format: {img.format}).")
                 return None
        except Exception as e_getexif: # Catch other errors during getexif() itself
            scanner_logger.warning(f"EXIF: Error calling getexif/ _getexif on {filepath}: {e_getexif}")
            return None


        if exif_data is not None: # Check if exif_data was successfully retrieved
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name in ['DateTimeOriginal', 'DateTimeDigitized']:
                    date_str = None
                    if isinstance(value, str):
                        date_str = value.strip()
                    elif isinstance(value, bytes):
                        date_str = value.decode('utf-8', errors='ignore').strip()

                    if date_str:
                        try:
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            scanner_logger.warning(f"EXIF: Could not parse date string '{date_str}' from {tag_name} in {filepath}")
            scanner_logger.debug(f"EXIF: DateTimeOriginal/DateTimeDigitized tags not found or empty in {filepath}")
        else:
            scanner_logger.debug(f"EXIF: No EXIF data retrieved from {filepath} (format: {img.format})")

    except FileNotFoundError:
        scanner_logger.warning(f"EXIF: File not found when trying to open for EXIF: {filepath}")
    except Image.UnidentifiedImageError:
        scanner_logger.warning(f"EXIF: Cannot identify image file (Pillow UnidentifiedImageError): {filepath}")
    except Exception as e:
        # Log other, unexpected errors during EXIF processing as errors
        scanner_logger.error(f"EXIF: Unexpected error processing EXIF for {filepath}: {e}", exc_info=False)
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
        capture_time = None
        if media_data["media_type"] == 'image':
            capture_time = get_capture_time_from_exif(filepath)

        # Fallback strategy for effective_capture_time:
        # 1. EXIF capture time
        # 2. File modification time
        # 3. Hardcoded default (1999-01-01)
        if capture_time:
            effective_capture_time = capture_time
        elif modification_time: # modification_time is already a datetime object
            effective_capture_time = modification_time
            scanner_logger.debug(f"EXIF: Using file modification time {effective_capture_time} as capture time for {filepath}")
        else: # Should be very rare if os.stat worked
            effective_capture_time = datetime(1999, 1, 1, 0, 0, 0)
            scanner_logger.warning(f"EXIF: Using default 1999-01-01 capture time for {filepath} (no EXIF and no mod time).")

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
