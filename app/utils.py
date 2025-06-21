from types import SimpleNamespace
import logging
import builtins # To access the standard __builtins__

utils_logger = logging.getLogger('photo_album_manager.utils')
if not utils_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - UTILS - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    utils_logger.addHandler(handler)
    utils_logger.setLevel(logging.DEBUG)
    utils_logger.propagate = False

def execute_user_filter_function(media_item_dict, filter_function_str):
    # If filter string is empty or only whitespace, consider it a pass for all items.
    if not filter_function_str or not filter_function_str.strip():
        return True

    media_proxy = SimpleNamespace(**media_item_dict)

    # Prepare a limited global scope for exec.
    # We provide standard builtins and the media_proxy object.
    # User's code can also define other helper functions if they wish,
    # they will be defined in local_namespace.
    exec_globals = {
        '__builtins__': builtins, # Provide standard Python builtins
        'media': media_proxy
    }
    local_namespace = {}

    filename = media_item_dict.get('filename', media_item_dict.get('filepath', 'N/A'))
    utils_logger.debug(f"Executing filter for media: {filename}")

    try:
        # Execute the user-provided Python code string.
        # This will define the api_select function within local_namespace.
        exec(filter_function_str, exec_globals, local_namespace)

        api_select_func = local_namespace.get('api_select')

        if not callable(api_select_func):
            utils_logger.error(f"User filter code for {filename} did not define a callable 'api_select' function.")
            return True # Permissive: if api_select isn't defined, treat as pass

        # Call the user's api_select function
        result = api_select_func(media_proxy)
        final_outcome = bool(result)
        utils_logger.debug(f"Filter outcome for {filename}: {final_outcome}")

    except SyntaxError as se:
        utils_logger.error(f"Syntax error in user filter function for {filename}: {se}")
        utils_logger.error(f"Problematic filter code:\n{filter_function_str}")
        final_outcome = True # Permissive on syntax error
    except Exception as e:
        utils_logger.error(f"Error executing user filter function for {filename}: {e}", exc_info=True)
        utils_logger.error(f"Problematic filter code:\n{filter_function_str}")
        final_outcome = True # Permissive on runtime error in user function

    return final_outcome
