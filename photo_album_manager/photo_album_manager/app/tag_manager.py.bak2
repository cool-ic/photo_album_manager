from .models import db, Media, Tag
from sqlalchemy.exc import IntegrityError
import logging

tag_manager_logger = logging.getLogger('photo_album_manager.tag_manager') # Fixed logger name
if not tag_manager_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - TAG_MANAGER - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    tag_manager_logger.addHandler(handler)
    tag_manager_logger.setLevel(logging.DEBUG)
    tag_manager_logger.propagate = False


def add_global_tag(tag_name):
    tag_name = tag_name.strip()
    if not tag_name:
        tag_manager_logger.warning("Attempted to add an empty global tag.")
        return None
    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if existing_tag:
        tag_manager_logger.debug(f"Global tag '{tag_name}' already exists, returning existing.")
        return existing_tag

    new_tag = Tag(name=tag_name)
    try:
        db.session.add(new_tag)
        db.session.commit()
        tag_manager_logger.info(f"Global tag '{tag_name}' added with ID {new_tag.id}.")
        return new_tag
    except IntegrityError: # Handles race condition if tag was added between query and commit
        db.session.rollback()
        tag_manager_logger.warning(f"IntegrityError adding global tag '{tag_name}', likely added concurrently. Fetching again.")
        return Tag.query.filter_by(name=tag_name).first()
    except Exception as e:
        db.session.rollback()
        tag_manager_logger.error(f"Error adding global tag '{tag_name}': {e}", exc_info=True)
        return None

def delete_global_tag(tag_name):
    tag_name = str(tag_name).strip()
    if not tag_name:
        tag_manager_logger.warning("Attempted to delete a global tag with an empty name.")
        return False

    tag_to_delete = Tag.query.filter_by(name=tag_name).first()
    if not tag_to_delete:
        tag_manager_logger.warning(f"Attempted to delete non-existent global tag: '{tag_name}'")
        return False # Or indicate 'not found' specifically
    try:
        # Associations in media_tag table should be handled by cascade delete if set up in models.py
        # or by SQLAlchemy's ORM relationship management when the Tag object is deleted.
        tag_manager_logger.info(f"Deleting global tag '{tag_name}' (ID: {tag_to_delete.id}).")
        db.session.delete(tag_to_delete)
        db.session.commit()
        tag_manager_logger.info(f"Global tag '{tag_name}' deleted successfully.")
        return True
    except Exception as e:
        db.session.rollback()
        tag_manager_logger.error(f"Error deleting global tag '{tag_name}': {e}", exc_info=True)
        return False

def add_tags_to_media(media_id, tag_names_list):
    media_item = Media.query.get(media_id)
    if not media_item:
        tag_manager_logger.warning(f"add_tags_to_media: Media item ID {media_id} not found.")
        return False
    if not isinstance(tag_names_list, list):
        tag_manager_logger.error(f"add_tags_to_media: tag_names_list must be a list for media ID {media_id}.")
        return False

    added_any_new_association = False
    for tag_name_raw in tag_names_list:
        tag_name = str(tag_name_raw).strip()
        if not tag_name:
            tag_manager_logger.debug(f"Skipping empty tag name for media ID {media_id}.")
            continue

        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag_manager_logger.info(f"Tag '{tag_name}' not found globally, attempting to create it for media ID {media_id}.")
            tag = add_global_tag(tag_name) # This will create if not exists

        if tag:
            if tag not in media_item.tags:
                media_item.tags.append(tag)
                added_any_new_association = True
                tag_manager_logger.debug(f"Associated tag '{tag_name}' with media ID {media_id}.")
            else:
                tag_manager_logger.debug(f"Media ID {media_id} already has tag '{tag_name}'. No new association needed.")
        else:
            tag_manager_logger.warning(f"Could not find or create tag '{tag_name}' to associate with media ID {media_id}.")
            # Depending on desired behavior, this could be a partial failure.
            # For now, we continue trying to add other tags.

    if added_any_new_association:
        try:
            db.session.commit()
            tag_manager_logger.info(f"Successfully committed new tag associations for media ID {media_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            tag_manager_logger.error(f"Error committing new tag associations for media ID {media_id}: {e}", exc_info=True)
            return False # Indicate that commit failed

    tag_manager_logger.info(f"No new tag associations were needed or made for media ID {media_id} with tags {tag_names_list}.")
    return True # Success, even if no *new* associations were made (e.g., all tags already existed on item)

def set_tags_for_media(media_id, new_tag_names_list):
    media_item = Media.query.get(media_id)
    if not media_item:
        tag_manager_logger.warning(f"set_tags_for_media: Media item ID {media_id} not found.")
        return False # Media item must exist
    if not isinstance(new_tag_names_list, list):
        tag_manager_logger.error(f"set_tags_for_media: new_tag_names_list must be a list for media ID {media_id}.")
        return False

    tag_manager_logger.info(f"Setting tags for media ID {media_id} to: {new_tag_names_list}")

    # Clear existing tags for the media item
    # For many-to-many, modifying `media_item.tags` directly handles the association table.
    # Setting it to an empty list effectively removes all associations for this media_item.
    media_item.tags.clear()
    tag_manager_logger.debug(f"Cleared existing tags for media ID {media_id}.")

    # Add new tags
    new_tags_to_associate = []
    for tag_name_raw in new_tag_names_list:
        tag_name = str(tag_name_raw).strip()
        if not tag_name:
            tag_manager_logger.debug(f"Skipping empty tag name in set_tags_for_media for media ID {media_id}.")
            continue

        tag_object = Tag.query.filter_by(name=tag_name).first()
        if not tag_object:
            tag_manager_logger.info(f"Tag '{tag_name}' not found globally, attempting to create it for media ID {media_id} during set_tags.")
            tag_object = add_global_tag(tag_name) # Create if it doesn't exist

        if tag_object:
            new_tags_to_associate.append(tag_object)
        else:
            tag_manager_logger.warning(f"set_tags_for_media: Could not find or create tag '{tag_name}' for media ID {media_id}. This tag will not be set.")
            # Decide if this constitutes a failure for the whole operation or just skip this tag.
            # Current: skip this tag.

    media_item.tags = new_tags_to_associate # Assign the new list of Tag objects

    try:
        db.session.commit()
        tag_manager_logger.info(f"Successfully set tags for media ID {media_id}. Current tags: {[t.name for t in media_item.tags]}")
        return True
    except Exception as e:
        db.session.rollback()
        tag_manager_logger.error(f"Error committing set_tags_for_media for media ID {media_id}: {e}", exc_info=True)
        return False

def remove_tags_from_media(media_id, tag_names_list_to_remove):
    media_item = Media.query.get(media_id)
    if not media_item:
        tag_manager_logger.warning(f"remove_tags_from_media: Media item ID {media_id} not found.")
        return False
    if not isinstance(tag_names_list_to_remove, list):
        tag_manager_logger.error(f"remove_tags_from_media: tag_names_list_to_remove must be a list for media ID {media_id}.")
        return False

    removed_any = False
    for tag_name_raw in tag_names_list_to_remove:
        tag_name = str(tag_name_raw).strip()
        if not tag_name: continue
        tag_to_remove = Tag.query.filter_by(name=tag_name).first()
        if tag_to_remove and tag_to_remove in media_item.tags:
            media_item.tags.remove(tag_to_remove)
            removed_any = True
            tag_manager_logger.debug(f"Removed tag '{tag_name}' from media ID {media_id}.")
        elif not tag_to_remove:
            tag_manager_logger.debug(f"Tag '{tag_name}' not found globally, cannot remove from media ID {media_id}.")
        else: # Tag exists globally but not on item
            tag_manager_logger.debug(f"Media ID {media_id} does not have tag '{tag_name}'. No removal needed.")

    if removed_any:
        try:
            db.session.commit()
            tag_manager_logger.info(f"Successfully committed tag removals for media ID {media_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            tag_manager_logger.error(f'Error committing tag removals for media ID {media_id}: {e}', exc_info=True)
            return False
    tag_manager_logger.info(f"No tags needed to be removed from media ID {media_id} for list {tag_names_list_to_remove}.")
    return True

def get_tags_for_media(media_id):
    media_item = Media.query.get(media_id)
    return list(media_item.tags) if media_item else []

def get_media_for_tag(tag_name):
    tag = Tag.query.filter_by(name=str(tag_name).strip()).first()
    return list(tag.media_items) if tag else []

def get_all_global_tags():
    return Tag.query.all()
