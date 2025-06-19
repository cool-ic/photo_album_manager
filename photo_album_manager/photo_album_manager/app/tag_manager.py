from .models import db, Media, Tag
from sqlalchemy.exc import IntegrityError
import logging

tag_manager_logger = logging.getLogger('photo_album_manager.tag_manager') # Use fixed name
if not tag_manager_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - TAG_MANAGER - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    tag_manager_logger.addHandler(handler)
    tag_manager_logger.setLevel(logging.DEBUG)
    tag_manager_logger.propagate = False

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
        tag_id_cache = tag_to_delete.id # Cache for logging
        tag_manager_logger.info(f"Deleting global tag '{tag_name}' (ID: {tag_id_cache}). This will remove it from all associated media.")
        db.session.delete(tag_to_delete)
        db.session.commit()
        tag_manager_logger.info(f"Global tag '{tag_name}' (ID: {tag_id_cache}) deleted successfully.")
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
        tag_manager_logger.warning(f"add_tags_to_media: tag_names_list was not a list for media ID {media_id}.")
        return False

    added_any_new_association = False
    for tag_name_raw in tag_names_list:
        tag_name = str(tag_name_raw).strip()
        if not tag_name:
            tag_manager_logger.debug(f"Skipping empty tag name in list for media ID {media_id}.")
            continue

        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag_manager_logger.info(f"Tag '{tag_name}' not found globally, attempting to create it while adding to media ID {media_id}.")
            tag = add_global_tag(tag_name)
            if not tag:
                tag_manager_logger.warning(f"Could not find or create global tag '{tag_name}' for media ID {media_id}. Skipping this tag for this media item.")
                continue # Skip this tag if it couldn't be created

        if tag not in media_item.tags:
            media_item.tags.append(tag)
            added_any_new_association = True
            tag_manager_logger.debug(f"Associated tag '{tag_name}' (ID: {tag.id}) with media ID {media_id}.")
        else:
            tag_manager_logger.debug(f"Media ID {media_id} already has tag '{tag_name}' (ID: {tag.id}). No new association needed for this tag-media pair.")

    if added_any_new_association:
        try:
            db.session.commit()
            tag_manager_logger.info(f"Successfully committed new tag associations for media ID {media_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            tag_manager_logger.error(f"Error committing new tag associations for media ID {media_id}: {e}", exc_info=True)
            return False

    tag_manager_logger.info(f"No new tag associations were needed or made for media ID {media_id} with tags {tag_names_list} (all might have existed already).")
    return True

# Removed set_tags_for_media function as per subtask instruction

def remove_tags_from_media(media_id, tag_names_list_to_remove):
    media_item = Media.query.get(media_id)
    if not media_item:
        tag_manager_logger.warning(f"remove_tags_from_media: Media item ID {media_id} not found.")
        return False
    if not isinstance(tag_names_list_to_remove, list):
        tag_manager_logger.warning(f"remove_tags_from_media: tag_names_list_to_remove was not a list for media ID {media_id}.")
        return False

    removed_any = False
    for tag_name_raw in tag_names_list_to_remove:
        tag_name = str(tag_name_raw).strip()
        if not tag_name:
            tag_manager_logger.debug(f"Skipping empty tag name in removal list for media ID {media_id}.")
            continue

        tag_to_remove = Tag.query.filter_by(name=tag_name).first()
        if tag_to_remove and tag_to_remove in media_item.tags:
            media_item.tags.remove(tag_to_remove)
            removed_any = True
            tag_manager_logger.debug(f"Disassociated tag '{tag_name}' (ID: {tag_to_remove.id}) from media ID {media_id}.")
        elif not tag_to_remove:
            tag_manager_logger.debug(f"Tag '{tag_name}' not found globally, so cannot remove from media ID {media_id}.")
        else: # Tag exists globally but not on item
            tag_manager_logger.debug(f"Media ID {media_id} does not have tag '{tag_name}'. No removal needed for this tag-media pair.")

    if removed_any:
        try:
            db.session.commit()
            tag_manager_logger.info(f"Successfully committed tag removals for media ID {media_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            tag_manager_logger.error(f'Error committing tag removals for media ID {media_id}: {e}', exc_info=True)
            return False

    tag_manager_logger.info(f"No tags needed to be removed from media ID {media_id} for list {tag_names_list_to_remove} (none might have been present).")
    return True

def get_tags_for_media(media_id):
    media_item = Media.query.get(media_id)
    if not media_item:
        tag_manager_logger.warning(f"get_tags_for_media: Media item ID {media_id} not found.")
        return []
    return list(media_item.tags)

def get_media_for_tag(tag_name):
    tag_name_stripped = str(tag_name).strip()
    if not tag_name_stripped:
        tag_manager_logger.warning("get_media_for_tag: Called with an empty tag name.")
        return []
    tag = Tag.query.filter_by(name=tag_name_stripped).first()
    if not tag:
        tag_manager_logger.debug(f"get_media_for_tag: Tag '{tag_name_stripped}' not found.")
        return []
    return list(tag.media_items)

def get_all_global_tags():
    return Tag.query.all()
