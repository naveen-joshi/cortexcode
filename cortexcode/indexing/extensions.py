def get_all_extensions(supported_extensions: set[str], registered_extensions: set[str]) -> set[str]:
    return supported_extensions | registered_extensions
