from flask import current_app, jsonify, request, send_from_directory, abort, render_template, session
from .models import db, Media, Tag
from app.tag_manager import get_all_global_tags
from app.image_utils import generate_thumbnail, get_thumbnail_path
from app.utils import execute_user_filter_function
import os

@current_app.route('/')
def index_page():
    return render_template('index.html')

@current_app.route('/api/media/filter_config', methods=['POST', 'DELETE'])
def media_filter_config():
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'filter_code' not in data:
            return jsonify({'error': 'Missing filter_code in request body'}), 400

        filter_code = data['filter_code']
        # Basic validation: check if 'def api_select(media):' is in the code.
        if 'def api_select(media):' not in filter_code:
             return jsonify({'error': 'Filter code must contain "def api_select(media):"'}), 400

        session['media_filter_code'] = filter_code
        print(f"Filter config saved to session: {filter_code[:100]}...")
        return jsonify({'message': 'Filter configuration saved.'}), 200
    elif request.method == 'DELETE':
        session.pop('media_filter_code', None)
        print("Filter config cleared from session.")
        return jsonify({'message': 'Filter configuration cleared.'}), 200

@current_app.route('/api/media', methods=['GET'])
def list_media():
    page = request.args.get('page', 1, type=int)
    per_page_arg = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'capture_time', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

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

    all_items_from_db_query = query.all()
    filtered_items_after_py_filter = []
    user_filter_code = session.get('media_filter_code')

    if user_filter_code:
        print(f"Applying user filter (first 100 chars): {user_filter_code[:100]}...")
        for item in all_items_from_db_query:
            media_dict_for_filter = {
                'tag': [tag.name for tag in item.tags],
                'org_PATH': item.org_path,
                'filename': item.filename,
                'capture_time': item.capture_time,
                'modification_time': item.modification_time,
                'filesize': item.filesize,
                'media_type': item.media_type,
            }
            if execute_user_filter_function(media_dict_for_filter, user_filter_code):
                filtered_items_after_py_filter.append(item)
        print(f"Python filter applied. {len(filtered_items_after_py_filter)} items matched out of {len(all_items_from_db_query)} from DB query.")
    else:
        filtered_items_after_py_filter = all_items_from_db_query

    total_items = len(filtered_items_after_py_filter)
    start_index = (page - 1) * per_page_arg
    end_index = start_index + per_page_arg
    paginated_slice = filtered_items_after_py_filter[start_index:end_index]

    total_pages = (total_items + per_page_arg - 1) // per_page_arg if per_page_arg > 0 else 0
    if total_items == 0: total_pages = 0

    media_list_response = []
    for item_in_slice in paginated_slice:
        media_list_response.append({
            'id': item_in_slice.id,
            'filepath': item_in_slice.filepath,
            'filename': item_in_slice.filename,
            'org_path': item_in_slice.org_path,
            'capture_time': item_in_slice.capture_time.isoformat() if item_in_slice.capture_time else None,
            'modification_time': item_in_slice.modification_time.isoformat() if item_in_slice.modification_time else None,
            'filesize': item_in_slice.filesize,
            'media_type': item_in_slice.media_type,
            'tags': [tag.name for tag in item_in_slice.tags]
        })

    return jsonify({
        'media': media_list_response,
        'total_pages': total_pages,
        'current_page': page,
        'total_items': total_items
    })

@current_app.route('/api/tags', methods=['GET'])
def list_tags():
    tags = get_all_global_tags()
    return jsonify([{'id': tag.id, 'name': tag.name} for tag in tags])

@current_app.route('/api/org_paths', methods=['GET'])
def list_org_paths():
    org_paths = current_app.config.get('ORG_PATHS', [])
    return jsonify(org_paths)

@current_app.route('/api/media/file/<int:media_id>', methods=['GET'])
def get_media_file(media_id):
    media_item = Media.query.get_or_404(media_id)
    is_safe_path = False
    abs_filepath = os.path.abspath(media_item.filepath)
    for org_path_config in current_app.config.get('ORG_PATHS', []):
        if abs_filepath.startswith(os.path.abspath(org_path_config)):
            is_safe_path = True; break
    if not is_safe_path: abort(403)
    if not os.path.exists(media_item.filepath): abort(404)
    return send_from_directory(os.path.dirname(media_item.filepath), os.path.basename(media_item.filepath))

@current_app.route('/api/media/thumbnail/<int:media_id>', methods=['GET'])
def get_media_thumbnail(media_id):
    media_item = Media.query.get_or_404(media_id)
    if media_item.media_type != 'image': return jsonify({'message': 'Thumbnails only available for images.'}), 404
    thumb_full_path, thumb_dir, thumb_filename = get_thumbnail_path(media_item.id)
    if not os.path.exists(thumb_full_path):
        generated_path = generate_thumbnail(media_item)
        if not generated_path: return jsonify({'message': 'Thumbnail generation failed.'}), 500
    return send_from_directory(thumb_dir, thumb_filename)
