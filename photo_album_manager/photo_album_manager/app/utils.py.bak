import RestrictedPython
from RestrictedPython import compile_restricted, safe_builtins, limited_builtins, utility_builtins
from RestrictedPython.PrintCollector import PrintCollector

def execute_user_filter_function(media_item_dict, filter_function_str):
    """
    Safely executes a user-defined Python function string to filter a media item.
    media_item_dict should be a dictionary with 'tag' (list of strings) and 'org_PATH' (string).
    Returns True if the media item should be included, False otherwise.
    Returns True by default if the function is invalid or causes an error, to be permissive.
    """
    if not filter_function_str or not filter_function_str.strip():
        return True # No filter, include item

    allowed_builtins = safe_builtins.copy()
    allowed_builtins.update(limited_builtins)
    allowed_builtins.update(utility_builtins)

    additional_globals = {'media': media_item_dict}

    code_to_execute = (
        f"{filter_function_str}\n"
        "api_select_result = True\n"
        "try:\n"
        "    api_select_result = api_select(media)\n"
        "except Exception as e:\n"
        "    print(f'Error in user-defined api_select function: {e}')\n"
        "    api_select_result = True \n" # Default to True on error
    )

    results = {}
    restricted_globals = {
        '__builtins__': allowed_builtins,
        '_print_': PrintCollector,
        '_getattr_': RestrictedPython.Guards.safer_getattr,
        '_getitem_': RestrictedPython.Guards.safely_get_item,
        '_iter_unpack_sequence_': RestrictedPython.Guards.guarded_iter_unpack_sequence,
    }
    restricted_globals.update(additional_globals)

    try:
        byte_code = compile_restricted(
            code_to_execute,
            filename='<user_filter_string>',
            mode='exec'
        )
        exec(byte_code, restricted_globals, results)
        return bool(results.get('api_select_result', True))
    except SyntaxError as se:
        print(f"Syntax error in user filter function: {se}")
        return True
    except Exception as e:
        print(f"Error executing user filter function: {e}")
        return True
