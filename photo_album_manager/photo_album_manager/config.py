import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

ORG_PATHS = [
    os.path.join(BASE_DIR, 'sample_media', 'library1'),
    os.path.join(BASE_DIR, 'sample_media', 'library2')
]
ARCHIVE_PATH = os.path.join(BASE_DIR, 'sample_media', 'archive')

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']

# Create dummy directories for testing if they don't exist
for p in ORG_PATHS:
    if not os.path.exists(p):
        os.makedirs(p)
        # Create a tiny dummy file, ensuring it's a .jpg for scanner testing
        with open(os.path.join(p, f"sample_image_{os.path.basename(p)}.jpg"), "w") as f:
            f.write("dummy")
if not os.path.exists(ARCHIVE_PATH):
    os.makedirs(ARCHIVE_PATH)

SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'photo_album.sqlite')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False
