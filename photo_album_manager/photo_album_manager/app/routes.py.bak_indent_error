from flask import current_app, jsonify, request, send_from_directory, abort, render_template, session
from .models import db, Media, Tag
from app.tag_manager import get_all_global_tags, add_global_tag, delete_global_tag, add_tags_to_media
from app.image_utils import generate_thumbnail, get_thumbnail_path
from app.utils import execute_user_filter_function
from app.scanner import scan_libraries
from app.file_utils import move_media_to_archive # Import the new utility
import os, logging, traceback

routes_logger = logging.getLogger('photo_album_manager.routes')
if not routes_logger.handlers:
    h = logging.StreamHandler();
    h.setFormatter(logging.Formatter('%(asctime)s - ROUTES - %(levelname)s - %(message)s'));
    routes_logger.addHandler(h);
    routes_logger.setLevel(logging.DEBUG)
    routes_logger.propagate = False

@current_app.route('/')
def index_page(): return render_template('index.html')

@current_app.route('/api/scan/trigger', methods=['POST'])
def trigger_scan_endpoint():
    routes_logger.info("POST /api/scan/trigger called.")
    try:
        scan_libraries();
        routes_logger.info("API: Scan completed successfully.")
        return jsonify({'message': 'Scan completed.'}), 200
    except Exception as e:
        detailed_error = traceback.format_exc()
        routes_logger.error(f'API Scan error: {e}\n{detailed_error}', exc_info=False); # exc_info=False as we have detailed_error
        return jsonify({'error': str(e), 'trace': detailed_error}), 500

@current_app.route('/api/media/delete_selected', methods=['POST'])
def delete_selected_media_endpoint():
    data = request.get_json()
    if not data or 'media_ids' not in data or not isinstance(data['media_ids'], list):
        routes_logger.warning("POST /api/media/delete_selected: Invalid payload. 'media_ids' list is required.")
        return jsonify({'error': "Invalid payload. 'media_ids' must be a list."}), 400

    media_ids_to_delete = data['media_ids']
    if not media_ids_to_delete:
        routes_logger.info("POST /api/media/delete_selected: No media IDs provided for deletion.")
        return jsonify({'message': 'No media IDs provided for deletion.'}), 200 # Not an error, just no-op

    routes_logger.info(f"Attempting to delete media items with IDs: {media_ids_to_delete}")
    archive_base_path = current_app.config.get('ARCHIVE_PATH')
    if not archive_base_path or not os.path.isabs(archive_base_path): # Also check if it's an absolute path
        routes_logger.error(f"ARCHIVE_PATH is not configured or is not an absolute path: {archive_base_path}")
        return jsonify({'error': 'Archive path is not configured correctly on the server.'}), 500

    success_count = 0
    failed_items_info = [] # Store info about failures
    db_items_to_remove_from_db = []

    for media_id_raw in media_ids_to_delete:
        try:
            media_id = int(media_id_raw)
            media_item = Media.query.get(media_id)
            if not media_item:
                routes_logger.warning(f"Media item with ID {media_id} not found for deletion.")
                failed_items_info.append({'id': media_id, 'reason': 'Not found in DB'})
                continue

            routes_logger.debug(f"Processing deletion for media ID {media_id}, path: {media_item.filepath}")

            # Ensure media_item.filepath is absolute before passing to move_media_to_archive
            if not os.path.isabs(media_item.filepath):
                # This case should ideally not happen if scanner stores absolute paths
                routes_logger.error(f"Media item ID {media_id} has a non-absolute filepath: {media_item.filepath}. Skipping.")
                failed_items_info.append({'id': media_id, 'reason': 'Invalid (non-absolute) filepath in DB'})
                continue

            new_path = move_media_to_archive(media_item.filepath, archive_base_path)
            if new_path:
                routes_logger.info(f"Successfully moved file for media ID {media_id} to archive: {new_path}")
                db_items_to_remove_from_db.append(media_item) # Add to list for DB deletion
                # success_count will be based on successful DB deletion later
            else:
                routes_logger.error(f"Failed to move file for media ID {media_id} (path: {media_item.filepath}) to archive.")
                failed_items_info.append({'id': media_id, 'reason': 'Failed to move file to archive'})
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
            success_count = len(db_items_to_remove_from_db) # Count successful DB deletions
            routes_logger.info(f"Successfully deleted {success_count} items from database.")
        except Exception as e:
            db.session.rollback()
            routes_logger.error(f"Error committing deletions to database: {e}", exc_info=True)
            # Files were moved but DB entries not deleted. Add these to failed_items_info.
            for item_to_remove in db_items_to_remove_from_db:
                # Avoid adding duplicates if already in failed_items_info for file move failure (though logic should prevent this path)
                if not any(f_info['id'] == item_to_remove.id for f_info in failed_items_info):
                    failed_items_info.append({'id': item_to_remove.id, 'reason': 'DB commit failed after successful file move'})
            success_count = 0 # None were fully successful if DB commit failed for all

    summary_message = f"Deletion process complete. Successfully archived and removed from DB: {success_count} item(s). Failed: {len(failed_items_info)} item(s)."
    routes_logger.info(summary_message)
    if failed_items_info:
        routes_logger.warning(f"Failed deletion details: {failed_items_info}")

    status_code = 200
    if failed_items_info and success_count > 0:
        status_code = 207 # Multi-Status
    elif failed_items_info and success_count == 0:
        status_code = 500 # If all specified items failed, treat as a server-side issue or major failure
        if all(f['reason'] == 'Not found in DB' for f in failed_items_info) and len(failed_items_info) == len(media_ids_to_delete):
            status_code = 404 # If all specified IDs were not found
        elif any('Invalid ID format' in f['reason'] for f in failed_items_info):
             status_code = 400 # If any ID was invalid format

    return jsonify({'message': summary_message, 'success_count': success_count, 'failures': failed_items_info}), status_code


@current_app.route('/api/media/filter_config', methods=['POST', 'DELETE'])
def media_filter_config(): # Condensed
    if request.method == 'POST': d=request.get_json();
        if not d or 'filter_code' not in d: routes_logger.warning("Filter POST missing 'filter_code'."); return jsonify({'error': 'Missing filter_code'}), 400
        if 'def api_select(media):' not in d['filter_code']: routes_logger.warning("Filter POST missing 'def api_select(media):'."); return jsonify({'error': 'Filter code must contain "def api_select(media):"'}), 400
        session['media_filter_code']=d['filter_code']; routes_logger.info(f"Filter saved (len:{len(d['filter_code'])})."); return jsonify({'message': 'Filter saved.'})
    elif request.method == 'DELETE': session.pop('media_filter_code',None); routes_logger.info("Filter cleared."); return jsonify({'message': 'Filter cleared.'})

@current_app.route('/api/media', methods=['GET'])
def list_media(): # Condensed
    page=request.args.get('page',1,type=int);per_page_arg=request.args.get('per_page',20,type=int);sort_by=request.args.get('sort_by','capture_time',type=str);sort_order=request.args.get('sort_order','desc',type=str);routes_logger.debug(f"GET /api/media: p={page},pp={per_page_arg},sb='{sort_by}',so='{sort_order}'");q=Media.query;om={'capture_time':Media.capture_time,'modification_time':Media.modification_time,'filepath':Media.filepath,'filename':Media.filename,'filesize':Media.filesize};oc=om.get(sort_by,Media.capture_time);q=q.order_by(oc.asc() if sort_order.lower()=='asc' else oc.desc());ufc=session.get('media_filter_code');db_items=q.all();fi=[];
    if ufc:
        routes_logger.info(f"Filtering {len(db_items)} items. Filter: {ufc[:70]}...");
        for i in db_items: md={'tag':[t.name for t in i.tags],'org_PATH':i.org_path,'filename':i.filename,'filepath':i.filepath,'capture_time':i.capture_time.isoformat() if i.capture_time else None,'modification_time':i.modification_time.isoformat() if i.modification_time else None,'filesize':i.filesize,'media_type':i.media_type,'id':i.id};
        if execute_user_filter_function(md,ufc): fi.append(i)
        routes_logger.info(f"Filter result: {len(fi)} items.")
    else: routes_logger.debug("No user filter."); fi=db_items
    ti=len(fi);si=(page-1)*per_page_arg;ei=si+per_page_arg;ps=fi[si:ei];tp=(ti+per_page_arg-1)//per_page_arg if per_page_arg>0 else 0;
    if ti==0:tp=0;
    routes_logger.debug(f"Paginate: total={ti},page={page},per_page={per_page_arg},slice_len={len(ps)}");
    mlr=[{'id':s.id,'filepath':s.filepath,'filename':s.filename,'org_path':s.org_path,'capture_time':s.capture_time.isoformat() if s.capture_time else None,'modification_time':s.modification_time.isoformat() if s.modification_time else None,'filesize':s.filesize,'media_type':s.media_type,'tags':[t.name for t in s.tags]} for s in ps];
    return jsonify({'media':mlr,'total_pages':tp,'current_page':page,'total_items':ti})

@current_app.route('/api/tags', methods=['GET', 'POST'])
def manage_tags_endpoint(): # Condensed
    if request.method == 'GET': routes_logger.debug("GET /api/tags"); return jsonify([{'id': t.id, 'name': t.name} for t in get_all_global_tags()])
    if request.method == 'POST': routes_logger.debug("POST /api/tags");d=request.get_json();
        if not d or not d.get('name'): routes_logger.warning("POST /api/tags: Missing 'name'."); return jsonify({'error': 'Tag name required.'}), 400
        n=d.get('name','').strip();
        if not n: routes_logger.warning("POST /api/tags: Empty tag name."); return jsonify({'error': 'Tag name cannot be empty.'}), 400
        to=add_global_tag(n);
        if to: routes_logger.info(f"Tag '{to.name}' (ID:{to.id}) processed."); return jsonify({'id':to.id,'name':to.name})
        else: routes_logger.error(f"Failed to add tag '{n}'."); return jsonify({'error':'Failed to add tag.'}),500

@current_app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag_endpoint(tag_id): # Condensed
    routes_logger.info(f"DELETE /api/tags/{tag_id}");t=Tag.query.get(tag_id);
    if not t: routes_logger.warning(f"Tag ID {tag_id} not found for DELETE."); return jsonify({'error': 'Tag not found.'}), 404
    n=t.name;
    if delete_global_tag(n): routes_logger.info(f"Tag '{n}' deleted."); return jsonify({'message':f"Tag '{n}' deleted."})
    else: routes_logger.error(f"Failed to delete tag '{n}'."); return jsonify({'error':'Failed to delete.'}),500

@current_app.route('/api/media/<int:media_id>/tags', methods=['POST'])
def add_media_item_tags_endpoint(media_id): # Condensed
    m=Media.query.get(media_id);if not m: routes_logger.warning(f"Media {media_id} not found for POST tags."); return jsonify({'error':'Media not found.'}),404;
    d=request.get_json();if not d or'tag_names'not in d or not isinstance(d['tag_names'],list): routes_logger.warning(f"Invalid payload for POST /api/media/{media_id}/tags."); return jsonify({'error':"Invalid payload."}),400;
    tn=[str(n).strip() for n in d['tag_names'] if str(n).strip()];routes_logger.info(f"Adding tags {tn} to media {media_id}");
    if not tn and d['tag_names']: routes_logger.warning(f"Empty tags after strip for media {media_id}."); return jsonify({'error': 'Tags cannot be empty/whitespace.'}), 400
    if not add_tags_to_media(media_id,tn): routes_logger.error(f"Failed to add tags {tn} to media {media_id}."); return jsonify({'error':'Failed to add tags.'}),500;
    ut=[t.name for t in m.tags];routes_logger.info(f"Tags for media {media_id} now: {ut}");return jsonify({'message':'Tags added.','media_id':media_id,'tags':ut}),200

@current_app.route('/api/org_paths', methods=['GET'])
def list_org_paths(): return jsonify(current_app.config.get('ORG_PATHS',[]))

@current_app.route('/api/media/file/<int:media_id>')
def get_media_file(media_id): # Condensed
    m=Media.query.get_or_404(media_id);
    if not any(os.path.abspath(m.filepath).startswith(os.path.abspath(p)) for p in current_app.config.get('ORG_PATHS',[])): abort(403)
    if not os.path.exists(m.filepath): abort(404)
    return send_from_directory(os.path.dirname(m.filepath),os.path.basename(m.filepath))

@current_app.route('/api/media/thumbnail/<int:media_id>')
def get_media_thumbnail(media_id): # Condensed
    m=Media.query.get_or_404(media_id);if m.media_type!='image':return jsonify({'message':'Thumbs for images only.'}),404
    tp,td,tf=get_thumbnail_path(m.id);if not os.path.exists(tp):gp=generate_thumbnail(m);if not gp:return jsonify({'message':'Thumb gen failed.'}),500
    etb=os.path.join(current_app.config.get('BASE_DIR',''),'data','thumbnails');if not os.path.abspath(td).startswith(os.path.abspath(etb)):routes_logger.error(f"Thumb path {td} outside base {etb}.");abort(403);return send_from_directory(td,tf)
