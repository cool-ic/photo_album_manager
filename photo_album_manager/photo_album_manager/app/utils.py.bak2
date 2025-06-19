import RestrictedPython
from RestrictedPython import compile_restricted, safe_builtins, limited_builtins, utility_builtins
from RestrictedPython.PrintCollector import PrintCollector
import logging

# Use a fixed name for the logger
utils_logger = logging.getLogger('photo_album_manager.utils')
if not utils_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - UTILS - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    utils_logger.addHandler(handler)
    utils_logger.setLevel(logging.DEBUG) # Or logging.INFO for less verbosity
    utils_logger.propagate = False # Avoid duplicate logs if root logger also has stream handler

def execute_user_filter_function(media_item_dict, filter_function_str):
    if not filter_function_str or not filter_function_str.strip():
        return True

    allowed_builtins = safe_builtins.copy()
    # Add commonly used builtins for simple logic, like 'in', len(), etc.
    allowed_builtins.update(limited_builtins)
    allowed_builtins.update(utility_builtins)

    _print_collector = PrintCollector()
    restricted_globals = {
        '__builtins__': allowed_builtins,
        '_print_': _print_collector, # Allows user filter to use print() for debugging
        '_getattr_': RestrictedPython.Guards.safer_getattr,
        '_getitem_': RestrictedPython.Guards.safely_get_item,
        '_iter_unpack_sequence_': RestrictedPython.Guards.guarded_iter_unpack_sequence,
        'media': media_item_dict # The media item itself
    }

    media_identifier = media_item_dict.get('filename', media_item_dict.get('filepath', 'N/A'))
    utils_logger.debug(f"Executing filter for media: {media_identifier}")
    # utils_logger.debug(f"Filter function string for {media_identifier}:\n{filter_function_str}") # Can be very verbose

    # User's function is named 'api_select'. It should return True or False.
    # We wrap it to ensure it's called and its result is captured.
    code_to_execute = (
        f"{filter_function_str}\n"
        "api_select_result = True\n"  # Default if function doesn't set it or errors before explicit return
        "try:\n"
        "    api_select_result = api_select(media)\n"
        "except Exception as e:\n"
        # This print goes to _print_collector if user code has error *inside* api_select
        "    _print_('Error inside api_select: %s' % str(e))\n"
        "    api_select_result = True\n" # Permissive default on error within user function
    )

    results_dict_after_exec = {} # To capture 'api_select_result'
    final_outcome = True # Default to permissive if execution fails catastrophically

    try:
        byte_code = compile_restricted(code_to_execute, filename='<user_filter_string>', mode='exec')
        exec(byte_code, restricted_globals, results_dict_after_exec) # results_dict_after_exec gets populated

        final_outcome = bool(results_dict_after_exec.get('api_select_result', True))
        utils_logger.debug(f"Filter outcome for {media_identifier}: {final_outcome}")

        collected_prints = _print_collector.printed_text
        if collected_prints:
            utils_logger.info(f"Prints from user filter for {media_identifier}:\n{collected_prints.strip()}")

    except SyntaxError as se:
        utils_logger.error(f"Syntax error in user filter function (compilation stage): {se}")
        # Also log the problematic code for easier debugging by the user
        utils_logger.error(f"Problematic filter code (structure):\n{filter_function_str}")
        final_outcome = True # Permissive on syntax error
    except Exception as e:
        utils_logger.error(f"Error executing user filter function wrapper for {media_identifier}: {e}", exc_info=True)
        final_outcome = True # Permissive on other errors during exec

    return final_outcome
