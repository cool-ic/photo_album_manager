import os
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from .models import db, Media
from flask import current_app

def get_capture_time_from_exif(filepath):
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'DateTimeOriginal' or tag_name == 'DateTimeDigitized':
                    # Ensure the value is a string before parsing
                    if isinstance(value, str):
                        return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                    elif isinstance(value, bytes): # Sometimes EXIF strings are bytes
                        return datetime.strptime(value.decode('utf-8', errors='ignore'), '%Y:%m:%d %H:%M:%S')
    except Exception: # Broad exception to catch various PIL/OS errors
        pass # Optionally log the error: print(f"Error reading EXIF for {filepath}: {e}")
    return None

def scan_libraries():
    print("Starting library scan...")
    ORG_PATHS = current_app.config.get('ORG_PATHS', [])
    SUPPORTED_IMAGE_EXTENSIONS = current_app.config.get('SUPPORTED_IMAGE_EXTENSIONS', [])
    SUPPORTED_VIDEO_EXTENSIONS = current_app.config.get('SUPPORTED_VIDEO_EXTENSIONS', [])

    if not ORG_PATHS:
        print("No ORG_PATHS configured. Aborting scan.")
        return

    all_media_files_in_fs = []
    for org_path_root in ORG_PATHS:
        if not os.path.exists(org_path_root):
            print(f"Warning: Library path {org_path_root} does not exist. Skipping.")
            continue

        print(f"Scanning library: {org_path_root}")
        for root, _, files in os.walk(org_path_root):
            for filename in files:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                media_type = None
                if ext in SUPPORTED_IMAGE_EXTENSIONS:
                    media_type = 'image'
                elif ext in SUPPORTED_VIDEO_EXTENSIONS:
                    media_type = 'video'

                if media_type:
                    all_media_files_in_fs.append({
                        "filepath": filepath,
                        "org_path": org_path_root, # Store the specific org_path root for this item
                        "filename": filename,
                        "media_type": media_type
                    })

    existing_media_in_db = {media.filepath: media for media in Media.query.all()}
    processed_paths_in_fs = set()

    for media_data in all_media_files_in_fs:
        filepath = media_data["filepath"]
        processed_paths_in_fs.add(filepath) # Track processed file paths

        try:
            stat_info = os.stat(filepath)
        except FileNotFoundError:
            print(f"Warning: File {filepath} not found during stat. Skipping.")
            continue

        modification_time = datetime.fromtimestamp(stat_info.st_mtime)
        filesize = stat_info.st_size
        capture_time = None

        if media_data["media_type"] == 'image':
            capture_time = get_capture_time_from_exif(filepath)

        # Use a consistent default for comparison and storage if EXIF data is missing
        effective_capture_time = capture_time if capture_time else datetime(1999, 1, 1, 0, 0, 0)

        if filepath in existing_media_in_db:
            media_item = existing_media_in_db[filepath]
            # Check for changes
            if (media_item.modification_time != modification_time or
                media_item.filesize != filesize or
                media_item.capture_time != effective_capture_time or
                media_item.media_type != media_data["media_type"] or
                media_item.org_path != media_data["org_path"]): # Check if org_path changed (e.g. moved between libraries)

                media_item.modification_time = modification_time
                media_item.filesize = filesize
                media_item.capture_time = effective_capture_time
                media_item.media_type = media_data["media_type"]
                media_item.org_path = media_data["org_path"]
                media_item.filename = media_data["filename"] # Update filename in case it changed (though filepath is key)
                print(f"Updating metadata for: {filepath}")
        else:
            media_item = Media(
                filepath=filepath,
                org_path=media_data["org_path"],
                filename=media_data["filename"],
                capture_time=effective_capture_time,
                modification_time=modification_time,
                filesize=filesize,
                media_type=media_data["media_type"]
            )
            db.session.add(media_item)
            print(f"Adding new media: {filepath}")

    # Remove items from DB that are in a scanned org_path but no longer exist in the filesystem
    scanned_org_path_roots = set(ORG_PATHS)
    for path_in_db, media_item_in_db in existing_media_in_db.items():
        if media_item_in_db.org_path in scanned_org_path_roots and path_in_db not in processed_paths_in_fs:
            print(f"Removing media no longer found (from a scanned org_path): {path_in_db}")
            db.session.delete(media_item_in_db)

    try:
        db.session.commit()
        print("Database updated successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error committing changes to database: {e}")

    print("Library scan finished.")
