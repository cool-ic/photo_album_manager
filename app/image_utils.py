import os
from PIL import Image, ImageOps
from flask import current_app

DEFAULT_THUMBNAIL_SIZE = (256, 256) # Width, Height

def get_thumbnail_path(media_id, filename_prefix="thumb"):
    """Constructs the path for a thumbnail based on media_id."""
    # Thumbnails will be stored as JPEG for consistency
    thumbnail_filename = f"{media_id}_{filename_prefix}.jpg"
    # Get BASE_DIR from config to construct path to 'data/thumbnails'
    # current_app.config['BASE_DIR'] should be the project root: photo_album_manager/photo_album_manager
    base_dir = current_app.config.get('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    thumbnail_dir = os.path.join(base_dir, 'data', 'thumbnails')
    return os.path.join(thumbnail_dir, thumbnail_filename), thumbnail_dir, thumbnail_filename

def generate_thumbnail(media_item, size=DEFAULT_THUMBNAIL_SIZE, force_generate=False):
    """Generates a square cropped thumbnail for the given media_item (if it's an image).
       Saves it to the thumbnails directory and returns the path to the thumbnail.
       Returns None if media is not an image or if generation fails.
    """
    if media_item.media_type != 'image':
        return None

    thumb_path, thumb_dir, _ = get_thumbnail_path(media_item.id)

    if not os.path.exists(thumb_dir):
        try:
            os.makedirs(thumb_dir)
        except OSError as e:
            print(f"Error creating thumbnail directory {thumb_dir}: {e}")
            return None

    if os.path.exists(thumb_path) and not force_generate:
        return thumb_path # Thumbnail already exists

    if not os.path.exists(media_item.filepath):
        print(f"Original media file not found: {media_item.filepath}")
        return None

    try:
        img = Image.open(media_item.filepath)

        # Apply EXIF orientation correction before any other processing
        img = ImageOps.exif_transpose(img)

        # Convert to RGB if it's a palette-based image (e.g., some PNGs) or has alpha, to ensure JPEG saving works.
        if img.mode == 'P' or img.mode == 'RGBA' or img.mode == 'LA':
            img = img.convert('RGB')

        # Use ImageOps.fit to resize and crop to a square of the given size
        # This method ensures the image fits within the dimensions and crops excess.
        # It maintains aspect ratio before cropping.
        thumb = ImageOps.fit(img, size, Image.Resampling.LANCZOS) # High quality downsampling

        thumb.save(thumb_path, 'JPEG', quality=90)
        print(f"Thumbnail generated for {media_item.filename} at {thumb_path}")
        return thumb_path
    except FileNotFoundError:
        print(f"Error: Original file not found during thumbnail generation for {media_item.filepath}")
        return None
    except Exception as e:
        print(f"Error generating thumbnail for {media_item.filepath}: {e}")
        # Attempt to remove partially created thumbnail if save failed mid-way
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass # Can't remove, just log the main error
        return None
