from .models import db, Media, Tag
from sqlalchemy.exc import IntegrityError

def add_global_tag(tag_name):
    """Adds a new tag to the global list. Returns the Tag object or None if error."""
    if not tag_name.strip():
        print("Error: Tag name cannot be empty.")
        return None
    existing_tag = Tag.query.filter_by(name=tag_name.strip()).first()
    if existing_tag:
        # print(f"Tag '{tag_name}' already exists.")
        return existing_tag

    new_tag = Tag(name=tag_name.strip())
    try:
        db.session.add(new_tag)
        db.session.commit()
        print(f"Global tag '{tag_name}' added.")
        return new_tag
    except IntegrityError:
        db.session.rollback()
        print(f"Error: Tag '{tag_name}' might already exist (concurrent add?).")
        return Tag.query.filter_by(name=tag_name.strip()).first()
    except Exception as e:
        db.session.rollback()
        print(f"Error adding global tag '{tag_name}': {e}")
        return None

def delete_global_tag(tag_name):
    """Deletes a tag from the global list and removes it from all associated media. Returns True if successful."""
    tag_to_delete = Tag.query.filter_by(name=tag_name).first()
    if not tag_to_delete:
        print(f"Tag '{tag_name}' not found.")
        return False

    try:
        # The association  with  or similar on relationship
        # might handle disassociation automatically. However, explicit removal from media_tag is safer
        # if cascade rules are not perfectly set for this specific many-to-many scenario.
        # Here, we are deleting the Tag object, and SQLAlchemy should handle removing entries
        # from the 'media_tag' association table due to the ForeignKey constraints or relationship settings.

        db.session.delete(tag_to_delete)
        db.session.commit()
        print(f"Global tag '{tag_name}' deleted and disassociated from all media.")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting global tag '{tag_name}': {e}")
        return False

def add_tags_to_media(media_id, tag_names_list):
    """Adds a list of tags (by name) to a specific media item. Creates global tags if they don't exist. Returns True if successful."""
    media_item = Media.query.get(media_id)
    if not media_item:
        print(f"Media item with ID {media_id} not found.")
        return False

    if not isinstance(tag_names_list, list):
        print("Error: tag_names_list must be a list of strings.")
        return False

    added_any = False
    for tag_name in tag_names_list:
        if not tag_name.strip(): continue # Skip empty tag names

        tag = Tag.query.filter_by(name=tag_name.strip()).first()
        if not tag:
            tag = add_global_tag(tag_name.strip()) # Create it if it doesn't exist
            if not tag:
                print(f"Could not create or find tag: {tag_name}")
                continue # Skip this tag if creation failed

        if tag not in media_item.tags:
            media_item.tags.append(tag)
            added_any = True
        # else:
        #     print(f"Media {media_id} already has tag '{tag_name}'.")

    if added_any:
        try:
            db.session.commit()
            print(f"Tags {tag_names_list} processed for media ID {media_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error adding tags to media ID {media_id}: {e}")
            return False
    return True # No changes needed or made, still counts as success

def remove_tags_from_media(media_id, tag_names_list):
    """Removes a list of tags (by name) from a specific media item. Returns True if successful."""
    media_item = Media.query.get(media_id)
    if not media_item:
        print(f"Media item with ID {media_id} not found.")
        return False

    if not isinstance(tag_names_list, list):
        print("Error: tag_names_list must be a list of strings.")
        return False

    removed_any = False
    for tag_name in tag_names_list:
        tag = Tag.query.filter_by(name=tag_name.strip()).first()
        if tag and tag in media_item.tags:
            media_item.tags.remove(tag)
            removed_any = True
        # elif not tag:
        #     print(f"Tag '{tag_name}' not found in global list, cannot remove from media.")
        # else:
        #     print(f"Media {media_id} does not have tag '{tag_name}'.")

    if removed_any:
        try:
            db.session.commit()
            print(f"Tags {tag_names_list} removed from media ID {media_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error removing tags from media ID {media_id}: {e}")
            return False
    return True # No changes needed or made

def get_tags_for_media(media_id):
    """Returns a list of Tag objects for a given media_id."""
    media_item = Media.query.get(media_id)
    if not media_item:
        print(f"Media item with ID {media_id} not found.")
        return []
    return list(media_item.tags) # Convert SQLAlchemy collection to list

def get_media_for_tag(tag_name):
    """Returns a list of Media objects associated with a given tag_name."""
    tag = Tag.query.filter_by(name=tag_name.strip()).first()
    if not tag:
        print(f"Tag '{tag_name}' not found.")
        return []
    return list(tag.media_items) # Convert SQLAlchemy collection to list

def get_all_global_tags():
    """Returns a list of all Tag objects in the system."""
    return Tag.query.all()
