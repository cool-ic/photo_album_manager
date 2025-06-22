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

    # Phase 1: Mark all items as potentially inaccessible
    # We commit this separately to ensure this state is captured before further processing
    # if the scan is interrupted.
    # However, for a single transaction, we might defer commit until the end.
    # For simplicity and clarity of this step, let's make it part of the main transaction.
    # If performance becomes an issue on very large DBs, this could be optimized.
    scanner_logger.info("Marking all existing database media as potentially inaccessible before scan verification...")
    all_db_media_count = Media.query.update({Media.is_accessible: False})
    db.session.commit() # Commit this initial marking to ensure it's visible to subsequent queries
    scanner_logger.info(f"Marked {all_db_media_count} items and committed. Note: is_accessible will be set to True for found/updated items.")


    existing_media_in_db = {media.filepath: media for media in Media.query.all()} # Re-fetch to ensure objects reflect committed state
    scanner_logger.debug(f"Found {len(existing_media_in_db)} media items currently in database (after initial marking).")

    processed_paths_in_fs = set() # Keep track of paths found in this scan run
    items_added_count = 0
    items_updated_count = 0
    # items_removed_count = 0 # Will be items_marked_inaccessible_or_retained_as_inaccessible
    items_made_accessible_count = 0
    items_newly_marked_inaccessible_fs = 0 # Files that disappeared from an active ORG_PATH

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
                media_item.org_path != media_data["org_path"] or
                media_item.filename != media_data["filename"] or
                media_item.is_accessible is not True): # Also update if it was marked inaccessible

                scanner_logger.debug(f"UPDATING metadata (and/or marking accessible) for: {filepath}")
                media_item.modification_time = modification_time
                media_item.filesize = filesize
                media_item.capture_time = effective_capture_time
                media_item.media_type = media_data["media_type"]
                media_item.org_path = media_data["org_path"]
                media_item.filename = media_data["filename"]
                media_item.is_accessible = True # Mark as accessible
                items_updated_count += 1
            elif media_item.is_accessible is not True: # No metadata change, but was marked inaccessible
                scanner_logger.debug(f"Marking item as accessible (no other metadata changes): {filepath}")
                media_item.is_accessible = True
                items_made_accessible_count +=1 # Count this separately
            # else:
                # scanner_logger.debug(f"No changes detected for existing item: {filepath}, already accessible.")
        else:
            scanner_logger.debug(f"ADDING new media: {filepath}")
            media_item = Media(
                filepath=filepath, org_path=media_data["org_path"],
                filename=media_data["filename"], capture_time=effective_capture_time,
                modification_time=modification_time, filesize=filesize,
                media_type=media_data["media_type"],
                is_accessible=True # New items are accessible
            )
            db.session.add(media_item)
            items_added_count += 1

    # Phase 3: Identify items in DB that are part of an active ORG_PATH but were not found in FS.
    # These are files that were deleted from the disk from a still-configured library.
    # Instead of deleting them from DB, mark them as is_accessible = False.
    # Items from ORG_PATHS that are no longer in config.py will remain is_accessible=False
    # from the initial marking phase and won't be touched here.

    current_configured_org_paths = set(ORG_PATHS)
    for db_media_item in existing_media_in_db.values(): # Iterate through all items fetched at start of scan
        if db_media_item.org_path in current_configured_org_paths: # If its library is still configured
            if db_media_item.filepath not in processed_paths_in_fs: # But the file itself is no longer on disk
                if db_media_item.is_accessible is True: # And it was previously accessible
                    scanner_logger.info(f"Marking as inaccessible (file deleted from disk): {db_media_item.filepath}")
                    db_media_item.is_accessible = False
                    items_newly_marked_inaccessible_fs += 1
        # else: item's org_path is not in current ORG_PATHS, it remains is_accessible=False from initial step.

    try:
        db.session.commit()
        scanner_logger.info("Database changes committed successfully.")
    except Exception as e:
        db.session.rollback()
        scanner_logger.error(f"Error committing changes to database: {e}", exc_info=True)

    total_accessible_in_db = Media.query.filter_by(is_accessible=True).count()
    scanner_logger.info(f"Library scan finished. Added: {items_added_count}, Updated: {items_updated_count}, Newly Inaccessible (FS delete): {items_newly_marked_inaccessible_fs}. Total accessible in DB: {total_accessible_in_db} (Total in DB: {Media.query.count()}).")
