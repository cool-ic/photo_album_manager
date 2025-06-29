import os

# Absolute path to the directory where this config.py file is located.
# This is used to set up default sample paths and the database path.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- User Configuration: Media Library Paths ---
# IMPORTANT: Define the *absolute* paths to your photo and video libraries.
# These are the directories the application will scan for media.
#
# Example for Linux/macOS:
# ORG_PATHS = [
#     '/mnt/photos/family_albums',
#     '/home/user/my_videos',
# ]
#
# Example for Windows (use raw strings r'...' or double backslashes '\\'):
# ORG_PATHS = [
#     r'D:\Photos\Holidays',
#     r'C:\Users\YourName\Videos\Projects',
# ]
#
# **NOTE:** You MUST create these directories on your filesystem if they do not already exist.
# The application will NOT create these custom paths for you.
ORG_PATHS = [
    # Default sample path (relative to this project's location for easy demo)
    '/mnt/c/Users/root/Desktop/请柬'
]

# --- User Configuration: Archive Path ---
# IMPORTANT: Define the *absolute* path where 'deleted' media will be moved.
# This feature is planned but not fully implemented in the UI yet.
#
# **NOTE:** You MUST create this directory on your filesystem if it does not already exist.
ARCHIVE_PATH = '/mnt/c/Users/root/Desktop/ac' # Default sample path


# --- Supported File Extensions (lowercase) ---
# You can extend these lists if you have other common media file types.
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']


# --- Automatic Sample Directory Creation (for demo purposes) ---
# If you are using the default ORG_PATHS and ARCHIVE_PATH as defined above
# (pointing to 'sample_media' within this project), this code will create them
# and add a few dummy files to help you get started quickly.
# If you define your own custom paths above, this section will likely not affect them
# unless your custom paths happen to be the same as these defaults.
def create_sample_dirs_and_files():
    default_sample_org_paths = [
        os.path.join(BASE_DIR, 'sample_media', 'library1'),
        os.path.join(BASE_DIR, 'sample_media', 'library2')
    ]
    default_sample_archive_path = os.path.join(BASE_DIR, 'sample_media', 'archive')

    # Check if current ORG_PATHS are the default sample ones
    if sorted(ORG_PATHS) == sorted(default_sample_org_paths):
        print("Using default sample ORG_PATHS. Checking/creating sample directories...")
        for p in ORG_PATHS:
            if not os.path.exists(p):
                try:
                    os.makedirs(p)
                    print(f"Created sample library directory: {p}")
                    # Add a dummy file for testing
                    with open(os.path.join(p, f"sample_image_{os.path.basename(p)}.jpg"), "w") as f:
                        f.write("dummy image content")
                    with open(os.path.join(p, f"sample_video_{os.path.basename(p)}.mp4"), "w") as f:
                        f.write("dummy video content")
                except OSError as e:
                    print(f"Error creating sample directory {p}: {e}. Please check permissions.")
            # else:
                # print(f"Sample library directory already exists: {p}")

    # Check if current ARCHIVE_PATH is the default sample one
    if ARCHIVE_PATH == default_sample_archive_path:
        print("Using default sample ARCHIVE_PATH. Checking/creating sample archive directory...")
        if not os.path.exists(ARCHIVE_PATH):
            try:
                os.makedirs(ARCHIVE_PATH)
                print(f"Created sample archive directory: {ARCHIVE_PATH}")
            except OSError as e:
                print(f"Error creating sample archive directory {ARCHIVE_PATH}: {e}. Please check permissions.")
        # else:
            # print(f"Sample archive directory already exists: {ARCHIVE_PATH}")

create_sample_dirs_and_files() # Call the function to set up sample dirs if applicable


# --- Database Configuration ---
# The SQLite database file will be created in the 'data' directory,
# relative to this project's root (BASE_DIR).
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'photo_album.sqlite')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

print(f"Config loaded. ORG_PATHS set to: {ORG_PATHS}")
print(f"ARCHIVE_PATH set to: {ARCHIVE_PATH}")
print(f"Database URI set to: {SQLALCHEMY_DATABASE_URI}")

# --- Flask Session Configuration ---
# IMPORTANT: This is a RANDOMLY GENERATED key for development/testing.
# For production, REPLACE this with a strong, unique, and static secret value.
# Keep this key confidential. It's used to sign session cookies.
SECRET_KEY = 'cb74945de63c9bc727ebeef452a8d3f741149305e4c2483503b5c45aae0ac946'
