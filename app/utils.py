import RestrictedPython
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.PrintCollector import PrintCollector
from RestrictedPython import Guards # Make sure Guards itself is imported directly
import logging

utils_logger = logging.getLogger('photo_album_manager.utils') # Use fixed name
if not utils_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - UTILS - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    utils_logger.addHandler(handler)
    utils_logger.setLevel(logging.DEBUG)
    utils_logger.propagate = False

def execute_user_filter_function(media_item_dict, filter_function_str):
    if not filter_function_str or not filter_function_str.strip():
        return True

    allowed_builtins = safe_builtins.copy()
    # If specific additional builtins like 'len', 'any', 'all', 'in' (via _iter_ and _getitem_) are needed
    # they must be explicitly added or Guards must be configured to allow them.
    # For now, safe_builtins is quite restrictive. User code like "if 'tagname' in media.tag:"
    # relies on _getitem_ and _iter_ being available and working for the 'media' object's 'tag' attribute.
    _print_collector = PrintCollector()

    restricted_globals = {
        '__builtins__': allowed_builtins,
        'sandbox_print': _print_collector, # Allows user's print() to be captured, renamed from _print_
        '_getattr_': Guards.safer_getattr,
        # '_getitem_': Guards.guarded_getitem, # Removed: This caused AttributeError. Standard dict access should work via safe_builtins.
        # '_iter_': Guards.guarded_iter, # Usually provided by safe_builtins for basic iteration like "for t in media.tag:"
        # Sequence operations for assignments like "a,b = my_list_or_tuple" might need:
        # '_unpack_sequence_': Guards.guarded_unpack_sequence, # If user code uses tuple/list unpacking
        'media': media_item_dict # The media item dictionary itself is a global
    }

    utils_logger.debug(f"Executing filter for media: {media_item_dict.get('filename', media_item_dict.get('filepath', 'N/A'))}")
    # utils_logger.debug(f"Filter function string for debugging:\n{filter_function_str}")

    # User's function is named 'api_select'. It should be defined in filter_function_str.
    # The wrapper calls it and handles result/errors.
    code_to_execute = (
        f"{filter_function_str}\n" # User's code defining api_select(media)
        "api_select_result = True\n"  # Default result if function doesn't run or finish
        "try:\n"
        "    api_select_result = api_select(media)\n" # Call the user's function
        "except Exception as e:\n"
        # This print goes to _print_collector if user code has error *inside* api_select
        "    sandbox_print('Error inside user-defined api_select function: %s' % str(e))\n"
        "    api_select_result = True\n" # Permissive default on error within user function
    )

    results_dict_after_exec = {} # This will be populated by exec with api_select_result
    final_outcome = True # Default to permissive if overall execution fails

    try:
        byte_code = compile_restricted(code_to_execute, filename='<user_filter_string>', mode='exec')
        exec(byte_code, restricted_globals, results_dict_after_exec) # Pass restricted_globals and local dict for results

        final_outcome = bool(results_dict_after_exec.get('api_select_result', True))
        utils_logger.debug(f"Filter outcome for {media_item_dict.get('filename', 'N/A')}: {final_outcome}")

        collected_prints = _print_collector.printed_text
        if collected_prints:
            utils_logger.info(f"Prints from user filter for {media_item_dict.get('filename', 'N/A')}:\n{collected_prints.strip()}")

    except SyntaxError as se:
        utils_logger.error(f"Syntax error in user filter function (compilation stage): {se}")
        utils_logger.error(f"Problematic filter code (structure):\n{filter_function_str}") # Log the code for debugging
        final_outcome = True
    except Exception as e:
        utils_logger.error(f"Error executing user filter function wrapper for {media_item_dict.get('filename', 'N/A')}: {e}", exc_info=True)
        final_outcome = True

    return final_outcome
