import os
import shutil
import logging
from datetime import datetime

file_utils_logger = logging.getLogger('photo_album_manager.file_utils')
if not file_utils_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - FILE_UTILS - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    file_utils_logger.addHandler(handler)
    file_utils_logger.setLevel(logging.DEBUG)
    file_utils_logger.propagate = False

def move_media_to_archive(media_filepath, archive_base_path):
    """Moves a media file to the archive directory, handling filename conflicts.
    Args:
        media_filepath (str): Absolute path to the media file to move.
        archive_base_path (str): Absolute path to the base archive directory.
    Returns:
        str: The new full path of the moved file if successful, None otherwise.
    """
    if not os.path.isabs(media_filepath):
        file_utils_logger.error(f"Source path is not absolute: {media_filepath}")
        return None
    if not os.path.isabs(archive_base_path):
        file_utils_logger.error(f"Archive path is not absolute: {archive_base_path}")
        return None

    if not os.path.exists(media_filepath):
        file_utils_logger.error(f"File to move does not exist: {media_filepath}")
        return None

    if not os.path.isdir(archive_base_path): # Ensure archive_base_path is a directory
        try:
            # exist_ok=True means it won't raise an error if the directory already exists.
            # It will raise an OSError if the path exists but is not a directory.
            os.makedirs(archive_base_path, exist_ok=True)
            file_utils_logger.info(f"Created archive directory: {archive_base_path}")
        except OSError as e:
            file_utils_logger.error(f"Failed to create archive directory {archive_base_path} (it might exist as a file): {e}", exc_info=True)
            return None

    original_filename = os.path.basename(media_filepath)
    filename_root, filename_ext = os.path.splitext(original_filename)

    destination_filepath = os.path.join(archive_base_path, original_filename)
    counter = 1
    while os.path.exists(destination_filepath):
        # Filename conflict: try appending _1, _2, etc.
        new_filename = f"{filename_root}_{counter}{filename_ext}"
        destination_filepath = os.path.join(archive_base_path, new_filename)
        if not os.path.exists(destination_filepath):
            break # Found a unique name with counter
        counter += 1
        if counter > 99: # Safety break for counter, try timestamp
            timestamp_suffix = datetime.now().strftime("%Y%m%d%H%M%S%f") # Added microseconds for more uniqueness
            new_filename = f"{filename_root}_{timestamp_suffix}{filename_ext}"
            destination_filepath = os.path.join(archive_base_path, new_filename)
            if not os.path.exists(destination_filepath):
                file_utils_logger.info(f"Used timestamp suffix for {original_filename} due to multiple conflicts. New name: {new_filename}")
                break # Found a unique name with timestamp
            else:
                 # Extremely unlikely to happen if microseconds are used.
                 file_utils_logger.error(f"Timestamped file {destination_filepath} also exists. Cannot resolve conflict automatically for {original_filename}.")
                 return None
    try:
        file_utils_logger.info(f"Attempting to move '{media_filepath}' to '{destination_filepath}'")
        shutil.move(media_filepath, destination_filepath)
        file_utils_logger.info(f"Successfully moved '{media_filepath}' to '{destination_filepath}'")
        return destination_filepath
    except Exception as e:
        file_utils_logger.error(f"Error moving file '{media_filepath}' to '{destination_filepath}': {e}", exc_info=True)
        return None
