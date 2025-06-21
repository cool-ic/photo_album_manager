from flask import current_app, jsonify, request, send_from_directory, abort, render_template, session
from .models import db, Media, Tag
from app.tag_manager import get_all_global_tags, add_global_tag, delete_global_tag, add_tags_to_media, remove_tags_from_media
from app.image_utils import generate_thumbnail, get_thumbnail_path
from app.utils import execute_user_filter_function
from app.scanner import scan_libraries
from app.file_utils import move_media_to_archive
import os, logging, traceback

routes_logger = logging.getLogger('photo_album_manager.routes')
if not routes_logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('%(asctime)s - ROUTES - %(levelname)s - %(message)s'))
    routes_logger.addHandler(h)
    routes_logger.setLevel(logging.DEBUG)
    routes_logger.propagate = False

@current_app.route('/')
def index_page():
    return render_template('index.html')

@current_app.route('/api/scan/trigger', methods=['POST'])
def trigger_scan_endpoint():
    routes_logger.info("POST /api/scan/trigger called.")
    try:
        scan_libraries()
        routes_logger.info("API: Scan completed successfully.")
        return jsonify({'message': 'Scan completed.'}), 200
    except Exception as e:
        detailed_error = traceback.format_exc()
        routes_logger.error(f'API Scan error: {e}\n{detailed_error}', exc_info=False)
        return jsonify({'error': str(e), 'trace': detailed_error}), 500

@current_app.route('/api/media/delete_selected', methods=['POST'])
def delete_selected_media_endpoint():
    data = request.get_json()
    if not data or 'media_ids' not in data or not isinstance(data['media_ids'], list):
        routes_logger.warning("POST /api/media/delete_selected: Invalid payload. 'media_ids' list is required.")
        return jsonify({'error': "Invalid payload. 'media_ids' must be a list."}), 400

    media_ids_to_delete = data['media_ids']
    if not media_ids_to_delete:
        routes_logger.info("POST /api/media/delete_selected: No media IDs provided.")
        return jsonify({'message': 'No media IDs provided for deletion.'}), 200

    routes_logger.info(f"Attempting to delete media items with IDs: {media_ids_to_delete}")
    archive_base_path = current_app.config.get('ARCHIVE_PATH')
    if not archive_base_path or not os.path.isabs(archive_base_path):
        routes_logger.error(f"ARCHIVE_PATH not configured or not absolute: {archive_base_path}")
        return jsonify({'error': 'Archive path not configured correctly.'}), 500

    success_count = 0
    failed_items_info = []
    db_items_to_remove_from_db = []

    for media_id_raw in media_ids_to_delete:
        try:
            media_id = int(media_id_raw)
            media_item = Media.query.get(media_id)
            if not media_item:
                routes_logger.warning(f"Media item with ID {media_id} not found for deletion.")
                failed_items_info.append({'id': media_id, 'reason': 'Not found in DB'})
                continue

            if not os.path.isabs(media_item.filepath):
                routes_logger.error(f"Media item ID {media_id} has a non-absolute filepath: {media_item.filepath}. Skipping.")
                failed_items_info.append({'id': media_id, 'reason': 'Invalid (non-absolute) filepath in DB'})
                continue

            new_path = move_media_to_archive(media_item.filepath, archive_base_path)
            if new_path:
                routes_logger.info(f"Successfully moved file for media ID {media_id} to archive: {new_path}")
                db_items_to_remove_from_db.append(media_item)
            else:
                routes_logger.error(f"Failed to move file for media ID {media_id} (path: {media_item.filepath}) to archive.")
                failed_items_info.append({'id': media_id, 'reason': 'File move failed'})
        except ValueError:
            routes_logger.warning(f"Invalid media ID format received: {media_id_raw}")
            failed_items_info.append({'id': media_id_raw, 'reason': 'Invalid ID format'})
        except Exception as e:
            routes_logger.error(f"Unexpected error processing media ID {media_id_raw} for deletion: {e}", exc_info=True)
            failed_items_info.append({'id': media_id_raw, 'reason': f'Unexpected error: {str(e)}'})

    if db_items_to_remove_from_db:
        try:
            for item_to_remove in db_items_to_remove_from_db:
                db.session.delete(item_to_remove)
            db.session.commit()
            success_count = len(db_items_to_remove_from_db)
            routes_logger.info(f"Successfully deleted {success_count} items from database.")
        except Exception as e:
            db.session.rollback()
            routes_logger.error(f"Error committing deletions to database: {e}", exc_info=True)
            for item_to_remove in db_items_to_remove_from_db:
                if not any(f_info['id'] == item_to_remove.id for f_info in failed_items_info):
                    failed_items_info.append({'id': item_to_remove.id, 'reason': 'DB commit failed after move'})
            success_count = 0

    summary_message = f"Delete complete. Success: {success_count}. Fail: {len(failed_items_info)}."
    routes_logger.info(summary_message)
    if failed_items_info:
        routes_logger.warning(f"Failed deletion details: {failed_items_info}")

    status_code = 200
    if failed_items_info and success_count > 0:
        status_code = 207 # Multi-Status
    elif failed_items_info and success_count == 0:
        status_code = 500
        # Refine status code based on failure reasons if all failed
        all_not_found = all(f['reason'] == 'Not found in DB' for f in failed_items_info)
        all_invalid_id = any('Invalid ID format' in f['reason'] for f in failed_items_info) # if any invalid id, it's a client error

        if all_not_found and len(failed_items_info) == len(media_ids_to_delete):
            status_code = 404 # All specified IDs were not found
        elif all_invalid_id:
             status_code = 400 # At least one ID was invalid format

    return jsonify({'message': summary_message, 'success_count': success_count, 'failures': failed_items_info}), status_code

@current_app.route('/api/media/filter_config', methods=['POST', 'DELETE'])
def media_filter_config():
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'filter_code' not in data:
            routes_logger.warning("Filter config POST missing 'filter_code'.")
            return jsonify({'error': 'Missing filter_code in request body'}), 400
        filter_code_str = data.get('filter_code', '')
        if 'def api_select(media):' not in filter_code_str:
            routes_logger.warning("Filter config POST: 'def api_select(media):' not found in filter_code.")
            return jsonify({'error': 'Filter code must contain "def api_select(media):"'}), 400
        session['media_filter_code'] = filter_code_str
        routes_logger.info(f"Filter code updated in session (len: {len(filter_code_str)}).")
        return jsonify({'message': 'Filter saved.'})
    elif request.method == 'DELETE':
        session.pop('media_filter_code', None)
        routes_logger.info("Filter code cleared from session.")
        return jsonify({'message': 'Filter cleared.'})

@current_app.route('/api/media', methods=['GET'])
def list_media():
    page = request.args.get('page', 1, type=int)
    per_page_arg = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'capture_time', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    routes_logger.debug(f"GET /api/media: p={page},pp={per_page_arg},sb='{sort_by}',so='{sort_order}'")

    query = Media.query
    order_column_map = {
        'capture_time': Media.capture_time,
        'modification_time': Media.modification_time,
        'filepath': Media.filepath,
        'filename': Media.filename,
        'filesize': Media.filesize
    }
    order_column = order_column_map.get(sort_by, Media.capture_time)
    query = query.order_by(order_column.asc() if sort_order.lower() == 'asc' else order_column.desc())

    user_filter_code = session.get('media_filter_code')
    db_items = query.all() # Fetch all after sorting
    filtered_items = []

    if user_filter_code:
        routes_logger.info(f"Filtering {len(db_items)} items. Filter: {user_filter_code[:70]}...")
        for item_from_db in db_items: # Use a more descriptive variable name
            media_dict = {
                'tag': [t.name for t in (item_from_db.tags or [])], # Ensure 'tag' is always a list for the filter
                'org_PATH': item_from_db.org_path,
                'filename': item_from_db.filename,
                'filepath': item_from_db.filepath,
                'capture_time': item_from_db.capture_time.isoformat() if item_from_db.capture_time else None,
                'modification_time': item_from_db.modification_time.isoformat() if item_from_db.modification_time else None,
                'filesize': item_from_db.filesize,
                'media_type': item_from_db.media_type,
                'id': item_from_db.id
            }
            if execute_user_filter_function(media_dict, user_filter_code):
                filtered_items.append(item_from_db)
        routes_logger.info(f"Filter result: {len(filtered_items)} items.")
    else:
        routes_logger.debug("No user filter.")
        filtered_items = db_items

    total_items = len(filtered_items)
    start_index = (page - 1) * per_page_arg
    end_index = start_index + per_page_arg
    paginated_slice = filtered_items[start_index:end_index]
    total_pages = (total_items + per_page_arg - 1) // per_page_arg if per_page_arg > 0 else 0
    if total_items == 0: total_pages = 0

    routes_logger.debug(f"Paginate: total={total_items},page={page},per_page={per_page_arg},slice_len={len(paginated_slice)}")
    media_list_response = [
        {
            'id': s.id, 'filepath': s.filepath, 'filename': s.filename, 'org_path': s.org_path,
            'capture_time': s.capture_time.isoformat() if s.capture_time else None,
            'modification_time': s.modification_time.isoformat() if s.modification_time else None,
            'filesize': s.filesize, 'media_type': s.media_type, 'tags': [t.name for t in (s.tags or [])]
        } for s in paginated_slice
    ]
    return jsonify({'media': media_list_response, 'total_pages': total_pages, 'current_page': page, 'total_items': total_items})

@current_app.route('/api/tags', methods=['GET', 'POST'])
def manage_tags_endpoint():
    if request.method == 'GET':
        routes_logger.debug("GET /api/tags")
        tags_list = get_all_global_tags()
        return jsonify([{'id': t.id, 'name': t.name} for t in tags_list])
    if request.method == 'POST':
        routes_logger.debug("POST /api/tags")
        data = request.get_json()
        if not data or not data.get('name'):
            routes_logger.warning("POST /api/tags: Missing 'name'.")
            return jsonify({'error': 'Tag name required.'}), 400
        tag_name = data.get('name','').strip()
        if not tag_name:
            routes_logger.warning("POST /api/tags: Empty tag name.")
            return jsonify({'error': 'Tag name cannot be empty.'}), 400
        tag_object = add_global_tag(tag_name)
        if tag_object:
            routes_logger.info(f"Tag '{tag_object.name}' (ID:{tag_object.id}) processed.")
            return jsonify({'id':tag_object.id,'name':tag_object.name})
        else:
            routes_logger.error(f"Failed to add tag '{tag_name}'.")
            return jsonify({'error':'Failed to add tag.'}),500

@current_app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag_endpoint(tag_id):
    routes_logger.info(f"DELETE /api/tags/{tag_id}")
    tag = Tag.query.get(tag_id)
    if not tag:
        routes_logger.warning(f"Tag ID {tag_id} not found for DELETE.")
        return jsonify({'error': 'Tag not found.'}), 404
    tag_name = tag.name
    if delete_global_tag(tag_name):
        routes_logger.info(f"Tag '{tag_name}' deleted.")
        return jsonify({'message':f"Tag '{tag_name}' deleted."})
    else:
        routes_logger.error(f"Failed to delete tag '{tag_name}'.")
        return jsonify({'error':'Failed to delete.'}),500

@current_app.route('/api/media/<int:media_id>/tags', methods=['POST'])
def add_media_item_tags_endpoint(media_id):
    media_item = Media.query.get(media_id) # Ensure Media object is fetched
    if not media_item:
        routes_logger.warning(f"Media {media_id} not found for POST tags.")
        return jsonify({'error':'Media not found.'}),404

    data = request.get_json()
    if not data or 'tag_names' not in data or not isinstance(data['tag_names'], list):
        routes_logger.warning(f"Invalid payload for POST /api/media/{media_id}/tags.")
        return jsonify({'error':"Invalid payload. 'tag_names' list required."}),400

    tag_names = [str(name).strip() for name in data['tag_names'] if str(name).strip()]
    if not tag_names and data['tag_names']: # List was not empty but all tags were whitespace
        routes_logger.warning(f"Empty tags after strip for media {media_id}. Original: {data['tag_names']}")
        return jsonify({'error': 'Tags cannot be empty/whitespace only.'}), 400

    routes_logger.info(f"Adding tags {tag_names} to media {media_id}")
    if not add_tags_to_media(media_id, tag_names):
        routes_logger.error(f"Failed to add tags {tag_names} to media {media_id} via tag_manager.")
        return jsonify({'error':'Failed to add tags.'}),500

    db.session.refresh(media_item)
    updated_tags = [t.name for t in media_item.tags]
    routes_logger.info(f"Tags for media ID {media_id} are now: {updated_tags}")
    return jsonify({'message':'Tags added.','media_id':media_id,'tags':updated_tags}),200

@current_app.route('/api/media/<int:media_id>/tags/<tag_name>', methods=['DELETE'])
def remove_specific_tag_from_media_endpoint(media_id, tag_name):
    routes_logger.info(f"DELETE /api/media/{media_id}/tags/{tag_name} called.")
    media_item = Media.query.get(media_id)
    if not media_item:
        routes_logger.warning(f"Media item with ID {media_id} not found for tag removal.")
        return jsonify({'error': 'Media not found.'}), 404

    tag_to_remove = Tag.query.filter_by(name=tag_name).first()
    if not tag_to_remove:
        routes_logger.warning(f"Tag '{tag_name}' not found globally, cannot remove from media ID {media_id}.")
        return jsonify({'error': f"Tag '{tag_name}' not found globally."}), 404

    # Check if the tag is actually associated with the media item
    if tag_to_remove not in media_item.tags:
        routes_logger.info(f"Tag '{tag_name}' is not associated with media ID {media_id}. No action needed.")
        # Return current tags as if successful, as the state is already achieved
        updated_tags = [t.name for t in media_item.tags]
        return jsonify({'message': f"Tag '{tag_name}' was not associated with media item {media_id}.", 'media_id': media_id, 'tags': updated_tags}), 200

    if remove_tags_from_media(media_id, [tag_name]):
        db.session.refresh(media_item) # Refresh to get the updated tags list
        updated_tags = [t.name for t in media_item.tags]
        routes_logger.info(f"Tag '{tag_name}' removed from media ID {media_id}. Current tags: {updated_tags}")
        return jsonify({'message': f"Tag '{tag_name}' removed from media item {media_id}.", 'media_id': media_id, 'tags': updated_tags}), 200
    else:
        # This case should ideally be rare if checks above are done,
        # but could happen if remove_tags_from_media has an internal issue (e.g. DB commit error)
        routes_logger.error(f"Failed to remove tag '{tag_name}' from media ID {media_id} using tag_manager.")
        return jsonify({'error': f"Failed to remove tag '{tag_name}' from media item {media_id}."}), 500

@current_app.route('/api/org_paths', methods=['GET'])
def list_org_paths():
    return jsonify(current_app.config.get('ORG_PATHS',[]))

@current_app.route('/api/media/file/<int:media_id>')
def get_media_file(media_id):
    media_item = Media.query.get_or_404(media_id)
    # Path safety check
    if not any(os.path.abspath(media_item.filepath).startswith(os.path.abspath(p))
               for p in current_app.config.get('ORG_PATHS', [])):
        abort(403)
    # File existence check
    if not os.path.exists(media_item.filepath):
        abort(404)
    return send_from_directory(os.path.dirname(media_item.filepath), os.path.basename(media_item.filepath))

@current_app.route('/api/media/thumbnail/<int:media_id>')
def get_media_thumbnail(media_id):
    media_item = Media.query.get_or_404(media_id)
    if media_item.media_type != 'image':
        return jsonify({'message':'Thumbs for images only.'}),404

    thumb_path, thumb_dir, thumb_filename = get_thumbnail_path(media_item.id)
    if not os.path.exists(thumb_path):
        generated_path = generate_thumbnail(media_item)
        if not generated_path:
            return jsonify({'message':'Thumb gen failed.'}),500

    expected_thumb_base = os.path.join(current_app.config.get('BASE_DIR',''),'data','thumbnails')
    if not os.path.abspath(thumb_dir).startswith(os.path.abspath(expected_thumb_base)):
        routes_logger.error(f"Thumb path {thumb_dir} outside base {expected_thumb_base}. Aborting.")
        abort(403)
    return send_from_directory(thumb_dir, thumb_filename)
