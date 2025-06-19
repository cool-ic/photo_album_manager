from flask import current_app, jsonify, request, send_from_directory, abort
from .models import Media, Tag
from app.tag_manager import get_all_global_tags
from app.image_utils import generate_thumbnail, get_thumbnail_path # Import thumbnail functions
import os

# Helper to get db session (not strictly needed if using models directly)
# def get_db():
#     return current_app.extensions['sqlalchemy'].db

@current_app.route('/')
def index():
    return "Hello, Photo Album Manager! API is under /api"

@current_app.route('/api/media', methods=['GET'])
def list_media():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
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
    paginated_media = query.paginate(page=page, per_page=per_page, error_out=False)
    media_list = []
    for item in paginated_media.items:
        media_list.append({
            'id': item.id,
            'filepath': item.filepath,
            'filename': item.filename,
            'org_path': item.org_path,
            'capture_time': item.capture_time.isoformat() if item.capture_time else None,
            'modification_time': item.modification_time.isoformat() if item.modification_time else None,
            'filesize': item.filesize,
            'media_type': item.media_type,
            'tags': [tag.name for tag in item.tags]
        })
    return jsonify({
        'media': media_list,
        'total_pages': paginated_media.pages,
        'current_page': paginated_media.page,
        'total_items': paginated_media.total
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
            is_safe_path = True
            break
    if not is_safe_path:
        abort(403)
    if not os.path.exists(media_item.filepath):
        abort(404)
    return send_from_directory(os.path.dirname(media_item.filepath), os.path.basename(media_item.filepath))

@current_app.route('/api/media/thumbnail/<int:media_id>', methods=['GET'])
def get_media_thumbnail(media_id):
    media_item = Media.query.get_or_404(media_id)
    if media_item.media_type != 'image':
        return jsonify({'message': 'Thumbnails only available for images.'}), 404

    # Check if thumbnail exists, if not, try to generate it
    thumb_full_path, thumb_dir, thumb_filename = get_thumbnail_path(media_item.id)

    if not os.path.exists(thumb_full_path):
        generated_path = generate_thumbnail(media_item) # This will save the thumbnail
        if not generated_path:
            # Fallback: if thumbnail generation failed, serve original if it's an image (already checked)
            # Or, more strictly, return a specific error that thumbnail couldn't be made.
            # For robustness, let's try to serve original if thumb fails, but log error server-side.
            print(f"Thumbnail generation failed for {media_item.id}, attempting to serve original.")
            # return get_media_file(media_id) # This could be large!
            return jsonify({'message': 'Thumbnail generation failed.'}), 500

    # Security check for thumbnail path (it should be within our data/thumbnails dir)
    # The get_thumbnail_path function constructs this, so it should be safe.
    # However, an explicit check against an allowed base thumbnail directory is good practice.
    base_dir_check = current_app.config.get('BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    expected_thumb_base = os.path.join(base_dir_check, 'data', 'thumbnails')
    if not os.path.abspath(thumb_dir).startswith(os.path.abspath(expected_thumb_base)):
        print(f"Security alert: Thumbnail path '{thumb_dir}' seems outside of expected base '{expected_thumb_base}'.")
        abort(403)

    return send_from_directory(thumb_dir, thumb_filename)
