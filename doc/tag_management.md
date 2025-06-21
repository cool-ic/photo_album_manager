# Tag Management System Documentation

This document details the underlying code principles and implementation of the tag management features (Feature 2.x) in the Photo Album Manager application.
It covers both backend and frontend aspects, providing references to relevant code snippets.

## 1. Introduction and Overview

The tag management system allows users to organize and categorize their media (photos and videos) using descriptive tags. Users can:

*   Maintain a global list of available tags.
*   Add new tags to this global list.
*   Delete tags from the global list (which also removes them from all associated media).
*   Apply one or more tags to individual media items.
*   Apply tags to a batch of selected media items.

Tags are stored persistently in a database. A many-to-many relationship is established between media items and tags, meaning a single media item can have multiple tags, and a single tag can be associated with multiple media items.

The system is designed with distinct backend logic for data management and API provision, and a frontend interface for user interaction.

## 2. Backend Implementation

The backend, built with Flask and SQLAlchemy, handles the persistent storage of tags, the association of tags with media files, and provides API endpoints for the frontend to consume.

### 2.1. Data Models (`app/models.py`)

The core data structures for tag management are defined in `app/models.py` using SQLAlchemy.

#### 2.1.1. `Tag` Model

The `Tag` model represents an individual tag in the system.

```python
# app/models.py

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'
```

*   **`id`**: An integer serving as the primary key for the `Tag` table.
*   **`name`**: A string (up to 100 characters) storing the actual tag text (e.g., "travel", "family"). This field is unique and cannot be null, ensuring that each tag name exists only once in the global list.

#### 2.1.2. `Media` Model and Relationship with `Tag`

The `Media` model represents a photo or video file. It has a many-to-many relationship with the `Tag` model, defined as follows:

```python
# app/models.py

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filepath = db.Column(db.String(1024), unique=True, nullable=False)
    # ... other fields like org_path, filename, capture_time, etc. ...

    tags = db.relationship('Tag', secondary='media_tag', backref=db.backref('media_items', lazy='dynamic'))

# Association table for Many-to-Many relationship between Media and Tag
media_tag = db.Table('media_tag',
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)
```

*   **`tags` attribute in `Media`**: This is a SQLAlchemy relationship attribute.
    *   `db.relationship('Tag', ...)`: Specifies that this field will hold related `Tag` objects.
    *   `secondary='media_tag'`: This crucial parameter tells SQLAlchemy to use the `media_tag` table as the association table (also known as a join table) to manage this many-to-many relationship.
    *   `backref=db.backref('media_items', lazy='dynamic')`: This creates a `media_items` attribute on the `Tag` model. This allows easy retrieval of all `Media` items associated with a particular `Tag`. The `lazy='dynamic'` setting means that `tag.media_items` will return a query object that can be further refined before fetching data, which is efficient.
*   **`media_tag` Association Table**:
    *   This table is not a model class but is defined directly using `db.Table`.
    *   It has two columns: `media_id` (a foreign key to `media.id`) and `tag_id` (a foreign key to `tag.id`).
    *   Together, `media_id` and `tag_id` form a composite primary key for this table. Each row in this table represents a single association between one media item and one tag.

#### 2.1.3. Database Initialization

The database (SQLite by default) and its tables are initialized by the `init_db(app)` function in `app/models.py`.

```python
# app/models.py

def init_db(app):
    # ... configuration for database URI ...
    db_path = os.path.join(app.instance_path, '..', 'data', 'photo_album.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    # ...
    db.init_app(app)
    with app.app_context():
        db.create_all() # This line creates the tables based on model definitions
    print("Database initialized and tables created.")
```
*   `db.create_all()`: This SQLAlchemy command inspects all classes that inherit from `db.Model` and creates the corresponding tables in the database if they don't already exist. This includes the `tag` table, the `media` table, and the `media_tag` association table.

### 2.2. Core Tag Logic (`app/tag_manager.py`)

The `app/tag_manager.py` module contains the business logic for all tag-related operations. It interacts directly with the database models. A dedicated logger, `tag_manager_logger`, is used for detailed logging within this module.

```python
# app/tag_manager.py
import logging
# ... other imports ...

tag_manager_logger = logging.getLogger('photo_album_manager.tag_manager')
# ... logger configuration ...
```

#### 2.2.1. `add_global_tag(tag_name)`

This function is responsible for adding a new tag to the global list of tags (`Tag` table).

```python
# app/tag_manager.py

def add_global_tag(tag_name):
    tag_name = str(tag_name).strip() # Ensure it's a string before stripping
    if not tag_name:
        tag_manager_logger.warning("Attempted to add an empty or non-string global tag.")
        return None

    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if existing_tag:
        tag_manager_logger.debug(f"Global tag '{tag_name}' already exists with ID {existing_tag.id}, returning existing.")
        return existing_tag

    new_tag = Tag(name=tag_name)
    try:
        db.session.add(new_tag)
        db.session.commit()
        tag_manager_logger.info(f"Global tag '{tag_name}' added with ID {new_tag.id}.")
        return new_tag
    except IntegrityError:
        db.session.rollback()
        tag_manager_logger.warning(f"IntegrityError adding global tag '{tag_name}', likely added concurrently. Querying again.", exc_info=True)
        return Tag.query.filter_by(name=tag_name).first() # Attempt to fetch the concurrently added tag
    except Exception as e:
        db.session.rollback()
        tag_manager_logger.error(f"Error adding global tag '{tag_name}': {e}", exc_info=True)
        return None
```

*   **Parameters**:
    *   `tag_name`: The string name of the tag to be added.
*   **Functionality**:
    1.  The input `tag_name` is stripped of leading/trailing whitespace and checked for emptiness.
    2.  It queries the `Tag` table to see if a tag with the given name already exists. If so, the existing tag object is returned.
    3.  If the tag does not exist, a new `Tag` instance is created.
    4.  The new tag is added to the database session and committed.
    5.  **Concurrency Handling**: It includes an `except IntegrityError` block. This can occur if two processes try to add the same tag simultaneously (due to the `unique=True` constraint on `Tag.name`). In this case, it rolls back the session and attempts to fetch the tag again, assuming it was added by the other process.
*   **Returns**: The `Tag` object (either newly created or existing), or `None` if an error occurs or the input is invalid.

#### 2.2.2. `delete_global_tag(tag_name)`

This function removes a tag from the global list. Due to database foreign key constraints and SQLAlchemy's relationship management, deleting a `Tag` object will also lead to the removal of its associations in the `media_tag` table.

```python
# app/tag_manager.py

def delete_global_tag(tag_name):
    tag_name = str(tag_name).strip()
    if not tag_name:
        tag_manager_logger.warning("Attempted to delete global tag with empty name.")
        return False

    tag_to_delete = Tag.query.filter_by(name=tag_name).first()
    if not tag_to_delete:
        tag_manager_logger.warning(f"Attempted to delete non-existent global tag: '{tag_name}'")
        return False
    try:
        # ... logging ...
        db.session.delete(tag_to_delete)
        db.session.commit()
        # ... logging ...
        return True
    except Exception as e:
        db.session.rollback()
        tag_manager_logger.error(f"Error deleting global tag '{tag_name}': {e}", exc_info=True)
        return False
```

*   **Parameters**:
    *   `tag_name`: The name of the tag to delete.
*   **Functionality**:
    1.  Finds the `Tag` object by its name.
    2.  If found, it's deleted from the database session and the session is committed.
    3.  SQLAlchemy, through the defined relationships, handles the removal of corresponding entries from the `media_tag` association table. This effectively removes the tag from all media items it was associated with.
*   **Returns**: `True` if deletion was successful, `False` otherwise.

#### 2.2.3. `add_tags_to_media(media_id, tag_names_list)`

This function associates one or more tags with a specific media item.

```python
# app/tag_manager.py

def add_tags_to_media(media_id, tag_names_list):
    media_item = Media.query.get(media_id)
    if not media_item:
        # ... logging ...
        return False
    # ... input validation for tag_names_list ...

    added_any_new_association = False
    for tag_name_raw in tag_names_list:
        tag_name = str(tag_name_raw).strip()
        if not tag_name: continue

        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            # If tag doesn't exist globally, try to create it.
            tag = add_global_tag(tag_name)
            if not tag:
                # ... logging ...
                continue

        if tag not in media_item.tags:
            media_item.tags.append(tag) # This appends to the SQLAlchemy relationship
            added_any_new_association = True
            # ... logging ...
        # ... else logging ...

    if added_any_new_association:
        try:
            db.session.commit() # Commit changes to the association table
            # ... logging ...
            return True
        except Exception as e:
            db.session.rollback()
            # ... logging ...
            return False
    # ... logging ...
    return True
```

*   **Parameters**:
    *   `media_id`: The ID of the `Media` item.
    *   `tag_names_list`: A list of strings, where each string is a tag name.
*   **Functionality**:
    1.  Retrieves the `Media` item by its ID.
    2.  Iterates through each `tag_name` in the provided list.
    3.  For each `tag_name`:
        *   It attempts to find the corresponding `Tag` object.
        *   If the tag doesn't exist globally, it calls `add_global_tag(tag_name)` to create it. If creation fails, this tag is skipped.
        *   It then checks if the `Tag` object is already present in the `media_item.tags` collection (which represents the media's current tags).
        *   If not already associated, the `tag` is appended to `media_item.tags`. SQLAlchemy handles the necessary insertion into the `media_tag` association table when the session is committed.
    4.  If any new associations were made, `db.session.commit()` is called.
*   **Returns**: `True` if the operation (including potential commits) was successful or if no new tags needed to be added. `False` if a critical error occurs (e.g., media item not found, database commit error).

#### 2.2.4. `remove_tags_from_media(media_id, tag_names_list_to_remove)`

This function disassociates specified tags from a media item.

```python
# app/tag_manager.py

def remove_tags_from_media(media_id, tag_names_list_to_remove):
    media_item = Media.query.get(media_id)
    if not media_item:
        # ... logging ...
        return False
    # ... input validation ...

    removed_any = False
    for tag_name_raw in tag_names_list_to_remove:
        tag_name = str(tag_name_raw).strip()
        if not tag_name: continue

        tag_to_remove = Tag.query.filter_by(name=tag_name).first()
        if tag_to_remove and tag_to_remove in media_item.tags:
            media_item.tags.remove(tag_to_remove) # Remove from SQLAlchemy relationship
            removed_any = True
            # ... logging ...
        # ... else logging for tag not found or not on item ...

    if removed_any:
        try:
            db.session.commit() # Commit changes to the association table
            # ... logging ...
            return True
        except Exception as e:
            db.session.rollback()
            # ... logging ...
            return False
    # ... logging ...
    return True
```

*   **Parameters**:
    *   `media_id`: The ID of the `Media` item.
    *   `tag_names_list_to_remove`: A list of tag names to remove from the media item.
*   **Functionality**:
    1.  Retrieves the `Media` item.
    2.  For each `tag_name` in the list:
        *   Finds the `Tag` object.
        *   If the tag exists globally and is currently associated with `media_item.tags`, it is removed using `media_item.tags.remove(tag_to_remove)`. SQLAlchemy handles the deletion from the `media_tag` association table upon commit.
    3.  If any tags were removed, `db.session.commit()` is called.
*   **Returns**: `True` if successful or no tags needed to be removed, `False` on critical error.

#### 2.2.5. Getter Functions

*   **`get_tags_for_media(media_id)`**:
    *   Retrieves a `Media` item by its ID.
    *   Returns a list of `Tag` objects associated with it (e.g., `list(media_item.tags)`).
    *   Returns an empty list if the media item is not found.
    ```python
    # app/tag_manager.py
    def get_tags_for_media(media_id):
        media_item = Media.query.get(media_id)
        if not media_item:
            tag_manager_logger.warning(f"get_tags_for_media: Media item ID {media_id} not found.")
            return []
        return list(media_item.tags)
    ```

*   **`get_media_for_tag(tag_name)`**:
    *   Finds a `Tag` object by its name.
    *   Returns a list of `Media` items associated with that tag (e.g., `list(tag.media_items)`).
    *   Returns an empty list if the tag is not found.
    ```python
    # app/tag_manager.py
    def get_media_for_tag(tag_name):
        tag_name_stripped = str(tag_name).strip()
        if not tag_name_stripped: # ... logging ...
            return []
        tag = Tag.query.filter_by(name=tag_name_stripped).first()
        if not tag: # ... logging ...
            return []
        return list(tag.media_items) # Accesses the backref
    ```

*   **`get_all_global_tags()`**:
    *   Queries and returns all `Tag` objects from the `Tag` table.
    ```python
    # app/tag_manager.py
    def get_all_global_tags():
        return Tag.query.all()
    ```

### 2.3. API Endpoints (`app/routes.py`)

The `app/routes.py` file defines the HTTP API endpoints that the frontend uses to interact with the tag management system. These routes call functions from `app.tag_manager` to perform the actual logic.

Relevant imports for tag management in `app/routes.py`:
```python
# app/routes.py
from flask import current_app, jsonify, request # ... other Flask imports
from .models import db, Media, Tag
from app.tag_manager import get_all_global_tags, add_global_tag, delete_global_tag, add_tags_to_media
# ... other imports ...
```

#### 2.3.1. `GET /api/tags`

*   **Purpose**: Fetches a list of all globally defined tags.
*   **Method**: `GET`
*   **Backend Logic**: Calls `get_all_global_tags()` from `app.tag_manager`.
*   **Response**: A JSON array of tag objects, where each object has `id` and `name`.
    ```json
    [
      {"id": 1, "name": "travel"},
      {"id": 2, "name": "family"}
    ]
    ```
*   **Code Snippet**:
    ```python
    # app/routes.py
    @current_app.route('/api/tags', methods=['GET', 'POST'])
    def manage_tags_endpoint():
        if request.method == 'GET':
            routes_logger.debug("GET /api/tags")
            tags_list = get_all_global_tags()
            return jsonify([{'id': t.id, 'name': t.name} for t in tags_list])
        # ... POST logic ...
    ```

#### 2.3.2. `POST /api/tags`

*   **Purpose**: Creates a new global tag.
*   **Method**: `POST`
*   **Request Payload**: A JSON object with a `name` key.
    ```json
    {"name": "new_tag_name"}
    ```
*   **Backend Logic**:
    1.  Retrieves the `name` from the JSON payload.
    2.  Calls `add_global_tag(tag_name)` from `app.tag_manager`.
*   **Response**:
    *   On success: A JSON object of the created (or existing if it was a duplicate attempt handled by `add_global_tag`) tag with `id` and `name`. HTTP status 200.
    *   On failure (e.g., empty name, error in `add_global_tag`): JSON error message. HTTP status 400 or 500.
*   **Code Snippet**:
    ```python
    # app/routes.py
    @current_app.route('/api/tags', methods=['GET', 'POST'])
    def manage_tags_endpoint():
        # ... GET logic ...
        if request.method == 'POST':
            routes_logger.debug("POST /api/tags")
            data = request.get_json()
            if not data or not data.get('name'):
                # ... error handling ...
                return jsonify({'error': 'Tag name required.'}), 400
            tag_name = data.get('name','').strip()
            if not tag_name:
                # ... error handling ...
                return jsonify({'error': 'Tag name cannot be empty.'}), 400
            tag_object = add_global_tag(tag_name)
            if tag_object:
                # ... logging ...
                return jsonify({'id':tag_object.id,'name':tag_object.name})
            else:
                # ... error handling ...
                return jsonify({'error':'Failed to add tag.'}),500
    ```

#### 2.3.3. `DELETE /api/tags/<int:tag_id>`

*   **Purpose**: Deletes a global tag by its ID. This also removes its associations from all media items.
*   **Method**: `DELETE`
*   **URL Parameter**: `tag_id` - The integer ID of the tag to delete.
*   **Backend Logic**:
    1.  Fetches the `Tag` object by `tag_id` using `Tag.query.get(tag_id)`.
    2.  If found, calls `delete_global_tag(tag.name)` from `app.tag_manager`.
*   **Response**:
    *   On success: JSON message confirming deletion. HTTP status 200.
    *   If tag not found: JSON error message. HTTP status 404.
    *   On deletion failure: JSON error message. HTTP status 500.
*   **Code Snippet**:
    ```python
    # app/routes.py
    @current_app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
    def delete_tag_endpoint(tag_id):
        routes_logger.info(f"DELETE /api/tags/{tag_id}")
        tag = Tag.query.get(tag_id)
        if not tag:
            # ... error handling ...
            return jsonify({'error': 'Tag not found.'}), 404
        tag_name = tag.name
        if delete_global_tag(tag_name):
            # ... logging ...
            return jsonify({'message':f"Tag '{tag_name}' deleted."})
        else:
            # ... error handling ...
            return jsonify({'error':'Failed to delete.'}),500
    ```

#### 2.3.4. `POST /api/media/<int:media_id>/tags`

*   **Purpose**: Adds one or more tags to a specific media item.
*   **Method**: `POST`
*   **URL Parameter**: `media_id` - The integer ID of the media item to tag.
*   **Request Payload**: A JSON object with a `tag_names` key, which is a list of tag name strings.
    ```json
    {"tag_names": ["tag1", "tag2", "existing_or_new_tag"]}
    ```
*   **Backend Logic**:
    1.  Validates the payload.
    2.  Calls `add_tags_to_media(media_id, tag_names)` from `app.tag_manager`.
    3.  Refreshes the media item from the database to get the updated list of tags.
*   **Response**:
    *   On success: JSON message confirming addition, the `media_id`, and the updated list of `tags` for that media item. HTTP status 200.
    *   If media not found: JSON error. HTTP status 404.
    *   Invalid payload: JSON error. HTTP status 400.
    *   On failure to add tags: JSON error. HTTP status 500.
*   **Code Snippet**:
    ```python
    # app/routes.py
    @current_app.route('/api/media/<int:media_id>/tags', methods=['POST'])
    def add_media_item_tags_endpoint(media_id):
        media_item = Media.query.get(media_id)
        if not media_item:
            # ... error handling ...
            return jsonify({'error':'Media not found.'}),404

        data = request.get_json()
        if not data or 'tag_names' not in data or not isinstance(data['tag_names'], list):
            # ... error handling ...
            return jsonify({'error':"Invalid payload. 'tag_names' list required."}),400

        tag_names = [str(name).strip() for name in data['tag_names'] if str(name).strip()]
        # ... validation for empty tags after strip ...

        routes_logger.info(f"Adding tags {tag_names} to media {media_id}")
        if not add_tags_to_media(media_id, tag_names):
            # ... error handling ...
            return jsonify({'error':'Failed to add tags.'}),500

        db.session.refresh(media_item) # Ensure the session has the latest data for media_item.tags
        updated_tags = [t.name for t in media_item.tags]
        # ... logging ...
        return jsonify({'message':'Tags added.','media_id':media_id,'tags':updated_tags}),200
    ```

## 3. Frontend Implementation (`static/js/main.js`)

The frontend JavaScript file (`static/js/main.js`) handles user interactions for tag management, makes API calls to the backend, and updates the UI dynamically.

### 3.1. State Variables

Several JavaScript variables are used to maintain the state related to tags:

*   **`activeTagNamesForOperations`**:
    *   **Definition**: `const activeTagNamesForOperations = new Set();`
    *   **Purpose**: This `Set` stores the names (strings) of tags that are currently "active" or "selected" by the user in the global tag list displayed in the sidebar (part of feature 1.2). These active tags are then used for "Quick Tagging" (T + Left Click) and "Batch Tag Selected" operations.
    *   **Updated by**: Clicking on tags in the `globalTagsListUl` (populated by `fetchGlobalTags()`).

*   **`selectedMediaIds`**:
    *   **Definition**: `const selectedMediaIds = new Set();`
    *   **Purpose**: This `Set` stores the integer IDs of media items that have been selected by a simple left-click on their thumbnails in the photo wall.
    *   **Interaction with Tagging**: Used by the "Batch Tag Selected" feature (`batchTagBtn`) to determine which media items should receive the tags currently in `activeTagNamesForOperations`.
    *   **Updated by**: The `toggleSelection()` function, called when a thumbnail is clicked without modifier keys.

*   **`currentMediaItems`**:
    *   **Definition**: `let currentMediaItems = [];`
    *   **Purpose**: An array that holds the full data (including `id`, `filename`, `tags`, etc.) for all media items currently displayed in the photo wall (i.e., the current page of results after filtering and sorting).
    *   **Interaction with Tagging**: After successful tagging operations (quick or batch), the `tags` array within the corresponding media item objects in `currentMediaItems` is updated with the response from the server. The `renderPhotoWall()` function is then called with this updated `currentMediaItems` to refresh the display, showing the new tags on thumbnails.
    *   **Updated by**: Primarily by `fetchMedia()`, and modified by tagging success callbacks.

### 3.2. Key Functions and UI Interactions

#### 3.2.1. Global Tag List (Sidebar - Feature 1.2 related)

The sidebar displays a list of all available global tags, allowing users to select tags for subsequent operations.

*   **DOM Element**: `const globalTagsListUl = document.getElementById('global-tags-list');`
*   **Function: `fetchGlobalTags()`**:
    ```javascript
    // static/js/main.js
    async function fetchGlobalTags() {
        if(!globalTagsListUl)return;
        try{
            const r=await fetch('/api/tags'); // GET /api/tags
            const d=await r.json();
            globalTagsListUl.innerHTML='';
            if(d.length===0)globalTagsListUl.innerHTML='<li>No tags.</li>';
            d.forEach(t=>{
                const l=document.createElement('li');
                l.textContent=t.name;
                l.dataset.tagId=t.id;
                l.dataset.tagName=t.name;
                // Highlight if tag is in activeTagNamesForOperations
                if(activeTagNamesForOperations.has(t.name)) l.classList.add('active-for-tagging');
                l.addEventListener('click',()=>{
                    if(activeTagNamesForOperations.has(t.name)){
                        activeTagNamesForOperations.delete(t.name);
                        l.classList.remove('active-for-tagging');
                    }else{
                        activeTagNamesForOperations.add(t.name);
                        l.classList.add('active-for-tagging');
                    }
                });
                globalTagsListUl.appendChild(l);
            })
        }catch(e){globalTagsListUl.innerHTML='<li>Error tags.</li>'}
    }
    ```
    *   **Purpose**: Fetches all global tags from the `/api/tags` backend endpoint.
    *   **Functionality**:
        1.  Makes a `GET` request to `/api/tags`.
        2.  Clears the existing list in `globalTagsListUl`.
        3.  For each tag received:
            *   Creates an `<li>` element.
            *   Sets its text content to the tag's name.
            *   Stores `tag.id` and `tag.name` in `dataset` attributes.
            *   Checks if the tag name is in `activeTagNamesForOperations`; if so, adds the class `active-for-tagging` for visual styling.
            *   Adds a click event listener to the `<li>`:
                *   Toggles the presence of the tag's name in the `activeTagNamesForOperations` Set.
                *   Toggles the `active-for-tagging` class on the `<li>` element.
    *   **Called**: During initial page load and after operations that might change the global tag list (e.g., adding/deleting a tag via the management modal, or after a full refresh).

#### 3.2.2. Tag Management Modal (Feature 2.1)

This modal allows users to add new global tags and delete existing ones.

*   **Trigger**: `const tagManagementBtn = document.getElementById('tag-management-btn');`
    *   Clicking this button opens the `tagManagementModal`.
    *   `if(tagManagementBtn) tagManagementBtn.onclick=()=>{ ... openModal('tag-management-modal'); if(populateManageTagsList)populateManageTagsList()};`
*   **Modal DOM Elements**:
    *   `const tagManagementModal = document.getElementById('tag-management-modal');`
    *   `const newTagInput = document.getElementById('new-tag-input');` (for typing new tag name)
    *   `const addNewTagBtn = document.getElementById('add-new-tag-btn');` (button to submit new tag)
    *   `const manageTagsListUl = document.getElementById('manage-tags-list');` (ul to list tags with delete buttons)

*   **Function: `populateManageTagsList()`**:
    ```javascript
    // static/js/main.js
    async function populateManageTagsList() {
        if(!manageTagsListUl)return;
        try{
            const r=await fetch('/api/tags'); // GET /api/tags
            const d=await r.json();
            manageTagsListUl.innerHTML='';
            if(d.length===0)manageTagsListUl.innerHTML='<li>No tags.</li>';
            d.forEach(t=>{
                const li=document.createElement('li');
                const s=document.createElement('span');
                s.textContent=t.name;
                li.appendChild(s);
                li.dataset.tagId=t.id; // Store tag ID
                const b=document.createElement('button'); // Delete button
                b.textContent='Delete';
                // ... styling for delete button ...
                b.onclick=(e)=>{e.stopPropagation();handleDeleteTag(t.id,t.name)}; // Attach delete handler
                li.appendChild(b);
                manageTagsListUl.appendChild(li);
            })
        }catch(e){manageTagsListUl.innerHTML='<li>Error tags.</li>'}
    }
    ```
    *   **Purpose**: Fetches all global tags and displays them within the management modal, each with a "Delete" button.
    *   **Functionality**: Similar to `fetchGlobalTags()`, but populates `manageTagsListUl` and adds a "Delete" button next to each tag. The delete button's click event is wired to `handleDeleteTag()`.
    *   **Called**: When the tag management modal is opened.

*   **Adding a New Tag (`addNewTagBtn` event listener)**:
    ```javascript
    // static/js/main.js
    if(addNewTagBtn) addNewTagBtn.addEventListener('click', async () => {
        const tn=newTagInput.value.trim();
        if(!tn){alert('Empty tag.');return}
        try{
            const r=await fetch('/api/tags',{ // POST /api/tags
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({name:tn})
            });
            const rs=await r.json();
            if(r.ok){
                newTagInput.value=''; // Clear input
                populateManageTagsList(); // Refresh list in modal
                fetchGlobalTags();      // Refresh global list in sidebar
            }else{
                alert(`Error: ${rs.error||'Unknown'}`)
            }
        }catch(e){alert('Network error.')}
    });
    ```
    *   **Purpose**: Handles the creation of a new global tag.
    *   **Functionality**:
        1.  Gets the trimmed tag name from `newTagInput`.
        2.  Makes a `POST` request to `/api/tags` with the tag name.
        3.  On success:
            *   Clears the input field.
            *   Calls `populateManageTagsList()` to refresh the list within the modal.
            *   Calls `fetchGlobalTags()` to refresh the global tag list in the sidebar.
        4.  On failure, shows an alert.

*   **Function: `handleDeleteTag(tagId, tagName)`**:
    ```javascript
    // static/js/main.js
    async function handleDeleteTag(tagId, tagName) {
        if(!confirm(`Delete '${tagName}'?`))return; // User confirmation (Note 3)
        try{
            const r=await fetch(`/api/tags/${tagId}`,{method:'DELETE'}); // DELETE /api/tags/<tag_id>
            const rs=await r.json();
            if(r.ok){
                if(populateManageTagsList)populateManageTagsList(); // Refresh list in modal
                fetchGlobalTags(); // Refresh global list in sidebar
                // Potentially refresh photo wall if tags were removed from displayed items
                if(window.appContext)window.appContext.refreshPhotoWall();
            }else{
                alert(`Error: ${rs.error||'Unknown'}`)
            }
        }catch(e){alert('Network error.')}
    }
    ```
    *   **Purpose**: Handles the deletion of a global tag.
    *   **Functionality**:
        1.  Shows a confirmation dialog (`confirm()`) as per Note 3.
        2.  If confirmed, makes a `DELETE` request to `/api/tags/<tagId>`.
        3.  On success:
            *   Calls `populateManageTagsList()` to refresh the list in the modal.
            *   Calls `fetchGlobalTags()` to refresh the global tag list in the sidebar.
            *   Calls `window.appContext.refreshPhotoWall()` to re-fetch and render media, as the deleted tag might have been displayed on some thumbnails.
        4.  On failure, shows an alert.

#### 3.2.3. Quick Tagging (Feature 2.2 - T + Left Click)

This feature allows users to quickly apply the currently active tags (selected in the sidebar) to a single media item by holding the 'T' key and left-clicking on its thumbnail.

*   **Key Press Detection**:
    ```javascript
    // static/js/main.js
    let isTKeyPressed = false;
    // ...
    document.addEventListener('keydown', (event) => { /* ... */ if(event.key==='t'||event.key==='T')isTKeyPressed=true; });
    document.addEventListener('keyup', (event) => { /* ... */ if(event.key==='t'||event.key==='T')isTKeyPressed=false; });
    ```
    *   The `isTKeyPressed` boolean variable tracks whether the 'T' key is currently pressed.

*   **Thumbnail Click Handler Integration**:
    *   Inside `renderPhotoWall(mediaItems)`, the event listener for each thumbnail item (`ti`) checks `isTKeyPressed`:
    ```javascript
    // static/js/main.js (within renderPhotoWall)
    ti.addEventListener('click',(e)=>{
        e.preventDefault();
        const mId=parseInt(item.id);
        if(isTKeyPressed){ // Check for 'T' key
            handleQuickTagging(mId,ti); // Call quick tagging function
        }else if(isXKeyPressed){
            openImageViewer(mId);
        }else{
            toggleSelection(ti,mId);
        }
    });
    ```

*   **Function: `handleQuickTagging(mediaId, thumbItem)`**:
    ```javascript
    // static/js/main.js
    async function handleQuickTagging(mediaId, thumbItem) {
        const aT=Array.from(activeTagNamesForOperations); // Get active tags
        if(aT.length===0){
            console.warn('[QuickTag] No active tags.');
            return;
        }
        try{
            const r=await fetch(`/api/media/${mediaId}/tags`,{ // POST /api/media/<media_id>/tags
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({tag_names:aT})
            });
            const rs=await r.json();
            if(r.ok){
                // Update currentMediaItems with new tags
                const idx=currentMediaItems.findIndex(m=>m.id===mediaId);
                if(idx>-1)currentMediaItems[idx].tags=rs.tags;
                renderPhotoWall(currentMediaItems); // Re-render to show new tags on thumbnail
                if(thumbItem)thumbItem.style.outline='2px solid green'; // Visual feedback
                setTimeout(()=>{if(thumbItem)thumbItem.style.outline=''},1000);
            }else{
                alert(`Error: ${rs.error||'Unknown'}`)
            }
        }catch(e){alert('Network error.')}
    }
    ```
    *   **Parameters**:
        *   `mediaId`: The ID of the media item that was T-clicked.
        *   `thumbItem`: The DOM element of the thumbnail (for visual feedback).
    *   **Functionality**:
        1.  Retrieves the list of tag names from `activeTagNamesForOperations`.
        2.  If no tags are active, it does nothing.
        3.  Makes a `POST` request to `/api/media/<mediaId>/tags` with the `tag_names` payload containing the active tags.
        4.  On success:
            *   Finds the corresponding media item in the `currentMediaItems` array and updates its `tags` property with the tags returned from the server (which now includes the newly added ones).
            *   Calls `renderPhotoWall(currentMediaItems)` to refresh the display. The `renderPhotoWall` function includes logic to display tags on thumbnails.
            *   Provides brief visual feedback (green outline) on the clicked thumbnail.
        5.  On failure, shows an alert.
        6.  This operation does not require user confirmation, as per Note 3.

#### 3.2.4. Batch Tagging (Feature 2.3 - "Batch Tag Selected" button)

This feature allows users to apply the currently active tags (selected in the sidebar) to all currently selected media items (those selected by left-click).

*   **Trigger**: `const batchTagBtn = document.getElementById('batch-tag-btn');`
*   **Event Listener (`batchTagBtn` click)**:
    ```javascript
    // static/js/main.js
    if(batchTagBtn) batchTagBtn.addEventListener('click', async () => {
        const mIds=Array.from(selectedMediaIds); // Get IDs of selected media
        const tApply=Array.from(activeTagNamesForOperations); // Get active tags
        if(mIds.length===0||tApply.length===0){
            alert('Select photos & active tags.');
            return;
        }
        const o=batchTagBtn.textContent;
        batchTagBtn.textContent='Tagging...';
        batchTagBtn.disabled=true;
        let sC=0,eC=0; // Success and error counters

        for(const mId of mIds){ // Loop through each selected media ID
            try{
                const idx=currentMediaItems.findIndex(m=>m.id===mId);
                const r=await fetch(`/api/media/${mId}/tags`,{ // POST /api/media/<media_id>/tags
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({tag_names:tApply})
                });
                const rs=await r.json();
                if(r.ok){
                    sC++;
                    // Update currentMediaItems with new tags for this item
                    if(idx>-1)currentMediaItems[idx].tags=rs.tags;
                }else{
                    eC++;
                }
            }catch(e){eC++}
        }
        batchTagBtn.textContent=o; // Restore button text
        batchTagBtn.disabled=false;
        alert(`Batch: ${sC} success, ${eC} failed.`);
        if(sC>0){
            renderPhotoWall(currentMediaItems); // Re-render to show new tags
        }
    });
    ```
    *   **Functionality**:
        1.  Retrieves media IDs from `selectedMediaIds` and tag names from `activeTagNamesForOperations`.
        2.  If either set is empty, it alerts the user and exits.
        3.  Disables the button and changes its text to "Tagging..." for user feedback.
        4.  Iterates over each `mediaId` in `mIds`:
            *   Makes a `POST` request to `/api/media/<mediaId>/tags` with the `tag_names` payload containing the `tApply` tags.
            *   If successful, increments `sC` (success count) and updates the `tags` for the corresponding item in `currentMediaItems`.
            *   If failed, increments `eC` (error count).
        5.  After processing all selected media items:
            *   Restores the button's text and enabled state.
            *   Shows an alert summarizing the number of successes and failures.
            *   If at least one tagging operation was successful (`sC > 0`), it calls `renderPhotoWall(currentMediaItems)` to refresh the display.
        6.  This operation does not require user confirmation, as per Note 3.

#### 3.2.5. Thumbnail Tag Display (within `renderPhotoWall`)

The `renderPhotoWall` function is responsible for displaying thumbnails. It also includes logic to show a few tags directly on the thumbnail if the media item has tags.

```javascript
// static/js/main.js (within renderPhotoWall)
// ...
if(item.tags&&item.tags.length>0){
    const o=document.createElement('div');
    o.className='thumbnail-tags-overlay';
    item.tags.slice(0,3).forEach(tn=>{ // Show up to 3 tags
        const s=document.createElement('span');
        s.className='thumbnail-tag';
        s.textContent=tn;
        o.appendChild(s)
    });
    if(item.tags.length>3){ // Add "..." if more than 3 tags
        const m=document.createElement('span');
        m.className='thumbnail-tag-more';
        m.textContent='...';
        o.appendChild(m)
    }
    ti.appendChild(o); // Add overlay to thumbnail item
}
// ...
```
*   This snippet checks if `item.tags` exists and has entries.
*   It creates a `div` for the tags overlay.
*   It displays up to the first 3 tags.
*   If there are more than 3 tags, it adds a "..." indicator.
*   This overlay is appended to the thumbnail item (`ti`).
This ensures that when `currentMediaItems` is updated after a tagging operation and `renderPhotoWall` is called, the new tags are visually reflected on the thumbnails.

### 3.3. Compliance with Notes

The frontend implementation, in conjunction with the backend, adheres to the specific notes regarding tag management:

*   **Note 1: Duplicate tag on a photo is a no-op.**
    *   The backend's `add_tags_to_media` function (in `app/tag_manager.py`) checks `if tag not in media_item.tags:` before appending. If a tag is already present on a photo, attempting to add it again via any frontend mechanism (Quick Tagging or Batch Tagging) results in no change for that specific tag-photo association, and no error is reported to the user for this specific case.

*   **Note 3: Confirmation for destructive operations.**
    *   **Deleting a global tag**: The `handleDeleteTag(tagId, tagName)` function in `static/js/main.js` uses a JavaScript `confirm()` dialog:
        ```javascript
        if(!confirm(`Delete '${tagName}'?`))return;
        ```
        This prompts the user before proceeding with the deletion of a global tag from the Tag Management modal.
    *   **Quick Tagging and Batch Tagging**: As specified, these operations (`handleQuickTagging` and the `batchTagBtn` event listener) do *not* implement a user confirmation dialog before applying tags to photos. They proceed immediately upon user action (T+click or button press).
