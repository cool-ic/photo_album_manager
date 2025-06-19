# Python Photo Album Manager

A web application for managing local photo and video libraries, built with Python (Flask) and JavaScript.

## Current Status

*   **Backend:** Complete. Includes media scanning, database management (SQLite), tagging logic, thumbnail generation, and API endpoints for all core functionalities.
*   **Frontend:** Core photo viewing features are implemented. Users can browse photos with pagination, sort them, adjust display size, and view individual images in a larger modal. Info panel displays library paths and global tags.
*   **Next Steps:** Implementation of advanced filtering, interactive tagging, media deletion, and undo functionality.

## Features Implemented

*   **Backend:**
    *   Scans specified local directories (`ORG_PATHS`) for photos and videos.
    *   Extracts metadata (capture time via EXIF, modification time, filename, etc.). Defaults to 1999-01-01 for missing capture times.
    *   Stores media information in an SQLite database (`data/photo_album.sqlite`).
    *   Manages a global list of tags.
    *   Supports associating multiple tags with each media item.
    *   Generates square, cropped JPEG thumbnails on-demand (stored in `data/thumbnails/`).
    *   Provides API endpoints for media listing (with sorting & pagination), tag listing, org path listing, and serving original/thumbnail files.
*   **Frontend (Core Viewing):**
    *   Displays media in a responsive photo wall.
    *   "Photos per Row" input controls thumbnail size and layout.
    *   Sorting by capture time, modification time, filepath, or filename.
    *   Pagination for navigating through large libraries.
    *   Left-click to select photos (visual feedback).
    *   "X + Left-click" to open original image in a modal viewer with keyboard navigation (arrows, ESC).
    *   "Refresh" button to reload media view.
    *   Information panel displaying configured library paths and all global tags.
    *   Placeholders for advanced filtering, tag management, and other features.

## Setup Instructions

1.  **Clone the Repository:** (Assuming this code is in a Git repository)
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>/photo_album_manager/photo_album_manager
    ```
    If not using Git, ensure you are in the `photo_album_manager/photo_album_manager` directory where `run.py` is located.

2.  **Create a Python Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Paths:**
    *   Open `config.py` in a text editor.
    *   Modify the `ORG_PATHS` list to include the absolute paths to your photo/video library directories. For example:
      ```python
      ORG_PATHS = [
          '/path/to/your/photos1',
          '/path/to/your/videos_and_photos2'
      ]
      ```
    *   Modify the `ARCHIVE_PATH` variable to an absolute path where you want 'deleted' media to be moved (this feature is not yet fully implemented but the path is used).
      ```python
      ARCHIVE_PATH = '/path/to/your/archive_or_trash'
      ```
    *   **Important:** Ensure the directories specified in `ORG_PATHS` and `ARCHIVE_PATH` physically exist on your system. Create them if they don't.

## Running the Application

1.  **Activate Virtual Environment** (if not already active):
    ```bash
    source venv/bin/activate # Or venv\Scripts\activate on Windows
    ```

2.  **Scan Media Libraries:**
    This command populates the database with your media. Run it initially and whenever your libraries change.
    ```bash
    flask scan libraries
    ```

3.  **Run the Flask Development Server:**
    ```bash
    python run.py
    ```
    The application will typically be available at `http://127.0.0.1:5001/` (or `http://0.0.0.0:5001/` as configured in `run.py`).

## API Endpoint Overview (Brief)

*   `GET /api/media`: Lists media items. Supports `page`, `per_page`, `sort_by`, `sort_order` query parameters.
*   `GET /api/tags`: Lists all global tags.
*   `GET /api/org_paths`: Lists configured organization paths.
*   `GET /api/media/file/<media_id>`: Serves the original media file.
*   `GET /api/media/thumbnail/<media_id>`: Serves (and generates if needed) a thumbnail for the media item.

## Project Structure

```
photo_album_manager/photo_album_manager/
├── app/                    # Main Flask application package
│   ├── __init__.py         # Application factory
│   ├── models.py           # SQLAlchemy database models
│   ├── scanner.py          # Media library scanning logic
│   ├── tag_manager.py      # Tag manipulation logic
│   ├── image_utils.py      # Thumbnail generation logic
│   └── routes.py           # API and page routes
├── static/                 # Static files (CSS, JavaScript)
│   ├── css/main.css
│   └── js/main.js
├── templates/              # HTML templates
│   └── index.html
├── data/                   # Data directory (SQLite DB, thumbnails)
│   ├── photo_album.sqlite  # (created on first run/scan)
│   └── thumbnails/         # (populated on demand)
├── sample_media/           # Sample directories created by config.py if defaults are used
│   ├── library1/
│   └── archive/
├── config.py               # Application configuration (paths, etc.)
├── run.py                  # Script to run the Flask application
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── venv/                   # Python virtual environment (if created here)
```
