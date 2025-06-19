from flask import current_app, jsonify, request, send_from_directory, abort, render_template, session
from .models import db, Media, Tag
from app.tag_manager import get_all_global_tags, add_global_tag, delete_global_tag, add_tags_to_media, set_tags_for_media # Import set_tags_for_media
from app.image_utils import generate_thumbnail, get_thumbnail_path
from app.utils import execute_user_filter_function
from app.scanner import scan_libraries
import os, logging, traceback

# Ensure logger is configured once
routes_logger = logging.getLogger('photo_album_manager.routes') # Use fixed name
if not routes_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - ROUTES - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    routes_logger.addHandler(handler)
    routes_logger.setLevel(logging.DEBUG)
    routes_logger.propagate = False


@current_app.route('/')
def index_page(): return render_template('index.html')

@current_app.route('/api/scan/trigger', methods=['POST'])
def trigger_scan_endpoint():
    routes_logger.info("POST /api/scan/trigger called.")
    try: scan_libraries(); return jsonify({'message': 'Scan completed successfully.'}), 200
    except Exception as e: routes_logger.error(f'Scan error: {e}', exc_info=True); return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@current_app.route('/api/media/filter_config', methods=['POST', 'DELETE'])
def media_filter_config():
    if request.method == 'POST':
        data = request.get_json();
        if not data or 'filter_code' not in data: return jsonify({'error': 'Missing filter_code'}), 400
        if 'def api_select(media):' not in data['filter_code']: return jsonify({'error': 'Filter code must contain "def api_select(media):"'}), 400
        session['media_filter_code'] = data['filter_code'];
        routes_logger.info(f"Filter config saved. Starts: {data['filter_code'][:100]}...");
        return jsonify({'message': 'Filter configuration saved.'})
    elif request.method == 'DELETE':
        session.pop('media_filter_code', None);
        routes_logger.info("Filter config cleared.");
        return jsonify({'message': 'Filter configuration cleared.'})

@current_app.route('/api/media', methods=['GET'])
def list_media():
    page=request.args.get('page',1,type=int); per_page_arg=request.args.get('per_page',20,type=int)
    sort_by=request.args.get('sort_by','capture_time',type=str); sort_order=request.args.get('sort_order','desc',type=str)
    routes_logger.debug(f"GET /api/media: page={page}, per_page={per_page_arg}, sort_by='{sort_by}', sort_order='{sort_order}'")
    q=Media.query
    om={'capture_time':Media.capture_time,'modification_time':Media.modification_time,'filepath':Media.filepath,'filename':Media.filename,'filesize':Media.filesize}
    oc=om.get(sort_by,Media.capture_time); q=q.order_by(oc.asc() if sort_order.lower()=='asc' else oc.desc())
    ufc=session.get('media_filter_code'); db_items=q.all(); fi=[]
    if ufc:
        routes_logger.info(f"Applying user filter. Starts: {ufc[:100]}..."); routes_logger.debug(f"Items before filter: {len(db_items)}")
        for i in db_items:
            md={'tag':[t.name for t in i.tags],'org_PATH':i.org_path,'filename':i.filename,'filepath':i.filepath,'capture_time':i.capture_time.isoformat() if i.capture_time else None,'modification_time':i.modification_time.isoformat() if i.modification_time else None,'filesize':i.filesize,'media_type':i.media_type,'id':i.id}
            if execute_user_filter_function(md,ufc): fi.append(i)
        routes_logger.info(f"Items after filter: {len(fi)}")
    else: routes_logger.debug("No user filter."); fi=db_items
    ti=len(fi);si=(page-1)*per_page_arg;ei=si+per_page_arg;ps=fi[si:ei];tp=(ti+per_page_arg-1)//per_page_arg if per_page_arg>0 else 0
    if ti==0: tp=0
    routes_logger.debug(f"Pagination: total_items={ti}, page={page}, per_page={per_page_arg}, returning {len(ps)} items.")
    mlr=[{'id':s.id,'filepath':s.filepath,'filename':s.filename,'org_path':s.org_path,'capture_time':s.capture_time.isoformat() if s.capture_time else None,'modification_time':s.modification_time.isoformat() if s.modification_time else None,'filesize':s.filesize,'media_type':s.media_type,'tags':[t.name for t in s.tags]} for s in ps]
    return jsonify({'media':mlr,'total_pages':tp,'current_page':page,'total_items':ti})

@current_app.route('/api/tags', methods=['GET', 'POST'])
def manage_tags_endpoint():
    if request.method == 'GET':
        routes_logger.debug("GET /api/tags")
        return jsonify([{'id': t.id, 'name': t.name} for t in get_all_global_tags()])
    if request.method == 'POST':
        routes_logger.debug("POST /api/tags")
        d=request.get_json(); n=d.get('name','').strip()
        if not n: routes_logger.warning("Empty tag name on POST /api/tags"); return jsonify({'error': 'Tag name required.'}), 400
        to=add_global_tag(n);
        if to: routes_logger.info(f"Tag '{to.name}' processed via POST /api/tags."); return jsonify({'id':to.id,'name':to.name})
        else: routes_logger.error(f"Failed to add tag '{n}' via POST /api/tags."); return jsonify({'error':'Failed to add tag.'}),500

@current_app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag_endpoint(tag_id):
    routes_logger.info(f"DELETE /api/tags/{tag_id}")
    t=Tag.query.get(tag_id)
    if not t: routes_logger.warning(f"Tag ID {tag_id} not found for DELETE."); return jsonify({'error': 'Tag not found.'}), 404
    tag_name_cache = t.name # Cache name for logging, as 't' will be invalid after successful delete
    if delete_global_tag(t.name): routes_logger.info(f"Tag '{tag_name_cache}' (ID: {tag_id}) deleted."); return jsonify({'message':f"Tag '{tag_name_cache}' deleted."})
    else: routes_logger.error(f"Failed to delete tag '{tag_name_cache}' (ID: {tag_id})."); return jsonify({'error':'Failed to delete.'}),500

@current_app.route('/api/media/<int:media_id>/tags', methods=['POST', 'PUT'])
def manage_media_item_tags_endpoint(media_id):
    media_item = Media.query.get(media_id)
    if not media_item:
        routes_logger.warning(f"Media item ID {media_id} not found for tag management.")
        return jsonify({'error': 'Media item not found.'}), 404

    data = request.get_json()
    if not data or 'tag_names' not in data or not isinstance(data['tag_names'], list):
        routes_logger.warning(f"Invalid payload for media ID {media_id}: 'tag_names' list required.")
        return jsonify({'error': "Invalid payload. 'tag_names' must be a list."}), 400

    # Clean tag names: convert to string, strip whitespace, filter out empty strings
    tag_names = [str(name).strip() for name in data['tag_names'] if str(name).strip()]

    if request.method == 'POST': # Add tags (cumulative)
        routes_logger.info(f"POST /api/media/{media_id}/tags - Adding tags: {tag_names}")
        if not tag_names and data['tag_names']: # Original list was non-empty but all stripped to empty
             return jsonify({'error': 'Tag names cannot be empty or just whitespace.'}), 400
        if not add_tags_to_media(media_id, tag_names): # Handles empty tag_names list gracefully now
            routes_logger.error(f"Failed to add tags {tag_names} to media ID {media_id}.")
            return jsonify({'error': 'Failed to add tags.'}), 500
        action_message = 'Tags added successfully.'
    elif request.method == 'PUT': # Set tags (replace all)
        routes_logger.info(f"PUT /api/media/{media_id}/tags - Setting tags to: {tag_names}")
        if not set_tags_for_media(media_id, tag_names): # Handles empty tag_names list by clearing tags
            routes_logger.error(f"Failed to set tags for media ID {media_id} to {tag_names}.")
            return jsonify({'error': 'Failed to set tags.'}), 500
        action_message = 'Tags set successfully (replaced existing).'

    db.session.refresh(media_item) # Ensure media_item.tags is up-to-date before creating response
    updated_tags = [tag.name for tag in media_item.tags]
    routes_logger.info(f"Successfully processed tags for media ID {media_id}. Current tags: {updated_tags}")
    return jsonify({'message': action_message, 'media_id': media_id, 'tags': updated_tags}), 200

@current_app.route('/api/org_paths', methods=['GET'])
def list_org_paths(): return jsonify(current_app.config.get('ORG_PATHS',[]))

@current_app.route('/api/media/file/<int:media_id>')
def get_media_file(media_id):
    m=Media.query.get_or_404(media_id);
    if not any(os.path.abspath(m.filepath).startswith(os.path.abspath(p)) for p in current_app.config.get('ORG_PATHS',[])): abort(403)
    if not os.path.exists(m.filepath): abort(404)
    return send_from_directory(os.path.dirname(m.filepath),os.path.basename(m.filepath))

@current_app.route('/api/media/thumbnail/<int:media_id>')
def get_media_thumbnail(media_id):
    m=Media.query.get_or_404(media_id);
    if m.media_type!='image': return jsonify({'message':'Thumbnails for images only.'}),404
    tp,td,tf=get_thumbnail_path(m.id);
    if not os.path.exists(tp):
        gp=generate_thumbnail(m);
        if not gp: return jsonify({'message':'Thumbnail generation failed.'}),500
    etb=os.path.join(current_app.config.get('BASE_DIR',''),'data','thumbnails');
    if not os.path.abspath(td).startswith(os.path.abspath(etb)): routes_logger.error(f"Thumbnail path {td} outside base {etb}."); abort(403)
    return send_from_directory(td,tf)
