import json
from datetime import datetime
from typing import List, Optional, Any

import yaml
from rich import print
from rich.console import Console
from rich.pretty import Pretty


def ameth(instance: Any) -> List[str]:
    """
    Get the methods of the input instance

    Returns:
        A list of method names available in the instance
    """
    return [
        attr for attr in dir(instance)
        if not attr.startswith('_')
        and callable(getattr(instance, attr))
    ]


def custom_serializer(obj: Any) -> str:
    """
    Custom serializer for non-serializable objects.
    Converts objects with a __dict__ attribute to their dictionary representation.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()  # Format datetime objects
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')  # Try to decode bytes to string
        except UnicodeDecodeError:
            return str(obj)  # Fallback if it's not valid UTF-8
    return str(obj)  # Fallback: Convert the object to a string


def is_empty(obj):
    """
    Check if an object is considered "empty" (None, 0, '', empty collection, etc.).
    Safely handles objects that might override comparison operators.

    Args:
        obj: The object to check for emptiness

    Returns:
        bool: True if the object is considered empty, False otherwise
    """
    try:
        # None is always considered empty
        if obj is None:
            return True

        # Numbers: 0, 0.0 are considered empty
        if isinstance(obj, (int, float)) and obj == 0:
            return True

        # Empty strings are considered empty
        if isinstance(obj, str) and obj == '':
            return True

        # Empty collections are considered empty
        if isinstance(obj, (list, tuple, dict, set)) and len(obj) == 0:
            return True

        # Not empty
        return False
    except Exception:
        # If we can't check (e.g., object has custom __eq__ that fails),
        # we assume it's not empty to be safe
        return False


def filter_instance_dict(
    instance,
    exc_keys: Optional[List[str]] = None,
    inc_: bool = False,
    depth_: int = 0,
    max_depth_: int = 3,
):
    """
    Recursively filter the __dict__ of a class instance, ignoring empty values.
    If an element is a list, apply the filter to each element recursively.

    Args:
        instance: The class instance or value to be filtered.
        exc_keys: Optional list of keys to exclude from the output.
        inc_: Whether to include attributes starting with a single underscore.
        depth_: Current recursion depth.
        max_depth_: Maximum recursion depth, especially for private attributes.

    Returns:
        dict or list or value: A filtered dictionary, list, or value with non-empty elements.
    """
    # Stop recursion if we've reached max depth for private attributes
    if inc_ and depth_ > max_depth_:
        if hasattr(instance, '__class__'):
            return f"<{instance.__class__.__module__}.{instance.__class__.__name__}> (max depth reached)"
        return str(instance)

    # Handle None explicitly
    if instance is None:
        return None

    # Handle basic types that aren't iterable
    if isinstance(instance, (int, float, bool, str)):
        return instance

    # Handle bytes
    if isinstance(instance, bytes):
        try:
            return instance.decode('utf-8')
        except UnicodeDecodeError:
            return str(instance)

    if isinstance(instance, (list, tuple)):
        # Recursively filter each element in the list
        filtered_list = [
            filter_instance_dict(item, exc_keys, inc_, depth_ + 1, max_depth_)
            for item in instance
            if not is_empty(item)
        ]
        # Remove the list if all elements are empty
        return filtered_list if filtered_list else None

    if hasattr(instance, '__dict__') and not isinstance(instance, dict):
        if isinstance(instance.__dict__, dict):
            return filter_instance_dict(instance.__dict__, exc_keys, inc_, depth_ + 1, max_depth_)
        elif callable(instance.__dict__):
            try:
                dict_result = instance.__dict__()
                if isinstance(dict_result, dict):
                    return filter_instance_dict(dict_result, exc_keys, inc_, depth_ + 1, max_depth_)
                return dict_result  # Return as is if not a dict
            except Exception:
                return str(instance)  # Fallback: just show the string representation

    if isinstance(instance, dict):
        # Recursively filter the __dict__ of the instance
        filtered_dict = {}
        for key, value in instance.items():
            # Skip keys starting with double underscore regardless of inc_ setting
            if key.startswith('__'):
                continue

            # Skip keys starting with single underscore unless inc_ is True
            if key.startswith('_') and not inc_:
                continue

            # Skip api_keys and keys in exclude keys
            if 'api_key' in key or key in (exc_keys or []):
                continue

            # Skip empty values
            if is_empty(value):
                continue

            # For private attributes, respect depth limit more strictly
            next_depth = depth_ + 1 if key.startswith('_') else depth_

            sub = filter_instance_dict(value, exc_keys, inc_, next_depth, max_depth_)

            # Skip if the filtered result is empty
            if is_empty(sub):
                continue

            # Only add class info to key if it's an object
            if hasattr(value, '__class__') and value.__class__.__module__ != 'builtins':
                key = f'{key} <{value.__class__.__module__}.{value.__class__.__name__}>'

            filtered_dict[key] = sub

        # Remove the dictionary if all elements are empty
        return filtered_dict if filtered_dict else None

    # Default case: return string representation
    return str(instance)


def aview(
    instance,
    to_file: Optional[str] = None,
    exc_keys: Optional[List[str]] = None,
    inc_: bool = False,
    max_depth_: int = 3,
):
    """
    Display elements of a class instance using rich.pprint, ignoring empty values.

    Args:
        instance: The class instance whose __dict__ is to be displayed.
        to_file: Optional file path to save the filtered dictionary in JSON format.
        exc_keys: Optional list of keys to exclude from the output.
        inc_: Whether to include attributes starting with a single underscore (_),
                         but still exclude double underscore attributes (__).
        max_depth_: Maximum recursion depth for private attributes (default: 3).
    """
    if not (hasattr(instance, '__dict__') or isinstance(instance, dict) or isinstance(instance, list)):
        raise ValueError('The provided object is not a class instance or a dictionary.')

    # Recursively filter the instance's __dict__
    filtered_dict = filter_instance_dict(instance, exc_keys, inc_, depth_=0, max_depth_=max_depth_)

    title = f'<{instance.__class__.__module__}.{instance.__class__.__name__}>'
    if to_file:
        ext = to_file.lower().split('.')[-1]
        if ext == 'json':
            # Write the filtered dictionary to a file in JSON format
            with open(to_file, 'w', encoding='utf-8') as f:
                json.dump(
                    obj=filtered_dict,
                    fp=f,
                    indent=2,
                    ensure_ascii=False,
                    default=custom_serializer,
                )
        elif ext in ['yaml', 'yml']:
            # Write the filtered dictionary to a file in YAML format
            with open(to_file, 'w', encoding='utf-8') as f:
                f.write(f'# {title}\n')
                yaml.dump(
                    data=filtered_dict,
                    stream=f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        else:
            raise ValueError('Unsupported file format. Use `json` or `yml`.')
    else:
        # Display class name and filtered dictionary
        console = Console()
        print(f'[bold cyan]{title}[/bold cyan]')
        console.print(Pretty(filtered_dict, indent_size=2))
