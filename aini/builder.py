import re
import importlib
import json
import os
from typing import Any, Dict, List, Literal, Optional, Union, Match

import yaml


def import_class(full_class_path: str, base_module: Optional[str] = None) -> Any:
    """
    Dynamically import a class given its full or relative module path.
    """
    if '.' not in full_class_path:
        raise ValueError(f'Invalid class path: {full_class_path}')

    if full_class_path.startswith('.'):
        if not base_module:
            raise ValueError('Relative class path requires base_module to be set.')
        # Separate relative module and class name
        module_path, class_name = full_class_path.rsplit('.', 1)
        module = importlib.import_module(module_path, package=base_module)
    else:
        module_path, class_name = full_class_path.rsplit('.', 1)
        module = importlib.import_module(module_path)

    return getattr(module, class_name)


def resolve_variable(
    var_name: str,
    is_full_match: bool,
    input_vars: Dict[str, Any],
    default_vars: Dict[str, Any],
) -> Optional[Any]:
    """
    Resolve a single variable or literal value by name.
    Handles variable lookups, literals, and special values.
    Priority: literals > input_vars > os.environ > default_vars > None.

    Args:
        var_name: The name of the variable or literal to resolve
        is_full_match: Whether this variable is the entire string (affects type preservation)
        input_vars: User-provided variables
        default_vars: Default variables from configuration

    Returns:
        The resolved value, or None if not found
    """
    # Handle boolean literals
    if var_name.lower() == 'true':
        return True if is_full_match else 'True'
    elif var_name.lower() == 'false':
        return False if is_full_match else 'False'

    # Handle numeric literals
    if var_name.isdigit():
        return int(var_name) if is_full_match else var_name
    elif var_name.replace('.', '', 1).isdigit() and var_name.count('.') == 1:
        return float(var_name) if is_full_match else var_name

    # Handle quoted literals
    if (var_name.startswith('"') and var_name.endswith('"')) \
            or (var_name.startswith("'") and var_name.endswith("'")):
        return var_name[1:-1]  # Return the literal without quotes

    # Try variables in priority order
    if var_name in input_vars:
        value = input_vars[var_name]
        return value if is_full_match else str(value)
    elif var_name in os.environ:
        env_val = os.environ[var_name]
        # Handle boolean environment variables
        if env_val.lower() == 'true':
            return True if is_full_match else 'True'
        elif env_val.lower() == 'false':
            return False if is_full_match else 'False'
        return env_val
    elif var_name in default_vars:
        value = default_vars[var_name]
        return value if is_full_match else str(value)

    # Variable not found
    return None if is_full_match else 'None'


def resolve_var_match(
    match: Match,
    input_vars: Dict[str, Any],
    default_vars: Dict[str, Any],
) -> Any:
    """
    Resolve a single variable match, handling alternatives with | operator.
    Returns the resolved value with appropriate type.
    """
    var_expr = match.group(1)
    is_full_match = match.group(0) == match.string

    # Process alternatives (using | operator)
    if '|' in var_expr:
        alternatives = var_expr.split('|')
        for alt in alternatives:
            alt = alt.strip()

            # Try to resolve the variable or literal
            result = resolve_variable(alt, is_full_match, input_vars, default_vars)
            if result is not None and (is_full_match or result != 'None'):
                return result

        # No alternatives resolved
        return None if is_full_match else 'None'

    # Handle single variable (no | operator)
    return resolve_variable(var_expr, is_full_match, input_vars, default_vars)


def resolve_vars(
    cfg: Union[Dict[str, Any], List[Any], Any],
    input_vars: Dict[str, Any],
    default_vars: Dict[str, Any],
) -> Union[Dict[str, Any], List[Any], Any]:
    """
    Recursively resolve ${VAR} placeholders in strings using input_vars, OS environment, and default_vars.
    Priority: input_vars > os.environ > default_vars > None.

    Supports OR operations with pipe symbol: ${VAR1|VAR2|"default_value"}
    - Each alternative is tried in order until one resolves successfully
    - Literal values can be included with quotes: ${VAR|"default"}
    - Lists and objects can be referenced by variable name: ${tools|empty_tools}
    - Boolean literals "true" and "false" are converted to Python bool values
    - Numeric literals are converted to int or float as appropriate

    If the entire string is ${VAR}, the resolved value is injected as-is (can be object, list, etc.).
    """
    if isinstance(cfg, dict):
        return {key: resolve_vars(val, input_vars, default_vars) for key, val in cfg.items()}

    if isinstance(cfg, list):
        return [resolve_vars(item, input_vars, default_vars) for item in cfg]

    if not isinstance(cfg, str):
        return cfg

    # Pattern to match ${var} or ${var|alt1|alt2}
    pattern = r'\${([^}]+)}'

    # Check if the entire string is a variable reference
    match = re.match(f'^{pattern}$', cfg)
    if match:
        # Return the resolved value with its original type
        return resolve_var_match(match, input_vars, default_vars)

    # Handle embedded variables by replacing them with string representations
    def replace_func(match):
        resolved = resolve_var_match(match, input_vars, default_vars)
        return str(resolved) if resolved is not None else "None"

    return re.sub(pattern, replace_func, cfg)


def build_from_config(
    cfg: Union[Dict[str, Any], List[Any], Any],
    base_module: Optional[str] = None,
) -> Union[Any, List[Any], Any]:
    """
    Recursively construct objects from a configuration structure.

    - If cfg is a dict with a 'class' key, import and instantiate it.
    - If cfg also has an 'init' key, behavior depends on the value:
      - If init is False or 'false', return the class itself without instantiation
      - If init is a string, use that method to instantiate instead of constructor
    - If cfg is a list, apply build_from_config on each element.
    - If cfg is a dict without 'class' key, recursively process its values.
    - Otherwise, return cfg as a literal.
    """
    if isinstance(cfg, list):
        return [build_from_config(item, base_module) for item in cfg]

    if isinstance(cfg, dict):
        if 'class' in cfg:
            class_path = cfg['class']
            params = cfg.get('params', {})
            init_method = cfg.get('init', None)  # Get initialization method name if specified

            # Import the class
            cls = import_class(class_path, base_module)

            # Special case: init=false means return the class itself, not an instance
            if init_method is False or init_method == 'false':
                return cls

            # Recursively build nested parameters
            built_params = {
                key: build_from_config(val, base_module) for key, val in params.items()
            }

            # Use initialization method if specified, otherwise use constructor
            if init_method and init_method is not False and init_method != 'false':
                if not hasattr(cls, init_method):
                    raise AttributeError(f"Class {class_path} has no method '{init_method}'")
                init_func = getattr(cls, init_method)
                return init_func(**built_params)
            else:
                # Default behavior: use constructor
                return cls(**built_params)
        else:
            # Process dict values recursively even if it doesn't have a 'class' key
            return {key: build_from_config(val, base_module) for key, val in cfg.items()}

    # Base literal case
    return cfg


def analyze_variables(
    template: Any,
    input_vars: Dict[str, Any],
    os_environ: Dict[str, str] = None,
    default_vars: Dict[str, Any] = None,
    track_mode: bool = True
) -> Union[set, bool]:
    """
    Analyze variables in a template structure.
    Can be used in two modes:
    1. Track used variables (track_mode=True): Returns a set of variable names used in the template
    2. Check for variable injections (track_mode=False): Returns a boolean indicating if any variables
       would be injected or if any non-empty values exist

    Args:
        template: The configuration template to analyze
        input_vars: User-provided variables
        os_environ: Environment variables (defaults to os.environ if None)
        default_vars: Default variables from configuration
        track_mode: If True, tracks variables and returns a set of names
                    If False, checks for injections and returns a boolean

    Returns:
        set: A set of variable names that were used (when track_mode=True)
        bool: True if the branch contains injections or values (when track_mode=False)
    """
    if os_environ is None:
        os_environ = os.environ
    if default_vars is None:
        default_vars = {}

    pattern = r'\${([^}]+)}'

    # Initialize result based on mode
    result = set() if track_mode else False

    # Special case: if this is a class with init=false, always keep it in injection check mode
    if not track_mode and isinstance(template, dict) and 'class' in template:
        init_method = template.get('init', None)
        if init_method is False or init_method == 'false':
            return True

    # Handle dictionaries
    if isinstance(template, dict):
        if track_mode:
            # In tracking mode, combine sets from all values
            for _, value in template.items():
                result.update(analyze_variables(value, input_vars, os_environ, default_vars, True))
        else:
            # In injection check mode, return True if any value has injections
            for key, value in template.items():
                if analyze_variables(value, input_vars, os_environ, default_vars, False):
                    return True
            return False

    # Handle lists
    elif isinstance(template, list):
        if track_mode:
            # In tracking mode, combine sets from all items
            for item in template:
                result.update(analyze_variables(item, input_vars, os_environ, default_vars, True))
        else:
            # In injection check mode, return True if any item has injections
            for item in template:
                if analyze_variables(item, input_vars, os_environ, default_vars, False):
                    return True
            return False

    # Handle strings with variable references
    elif isinstance(template, str):
        # Find all variable references
        matches = re.finditer(pattern, template)
        for match in matches:
            var_expr = match.group(1)
            # Handle alternatives (using | operator)
            if '|' in var_expr:
                alternatives = [alt.strip() for alt in var_expr.split('|')]
                for alt in alternatives:
                    # Skip literals in quotes or numeric/boolean literals
                    if (
                        (alt.startswith('"') and alt.endswith('"')) or
                        (alt.startswith("'") and alt.endswith("'")) or
                        alt.lower() in ('true', 'false') or
                        alt.isdigit() or
                        (alt.replace('.', '', 1).isdigit() and alt.count('.') == 1)
                    ):
                        if not track_mode:
                            return True  # Literal values count as "having values" in injection mode
                        continue

                    # In tracking mode, add variable to result if it exists in input_vars
                    if track_mode:
                        if alt in input_vars:
                            result.add(alt)
                    # In injection check mode, return True if the variable would be resolved
                    else:
                        if alt in input_vars or alt in os_environ or alt in default_vars:
                            return True
            else:
                # Single variable case
                if track_mode:
                    if var_expr in input_vars:
                        result.add(var_expr)
                else:
                    if var_expr in input_vars or var_expr in os_environ or var_expr in default_vars:
                        return True

        # In injection check mode, non-empty primitive strings count as "having values"
        if not track_mode:
            return template != ""

    # In injection check mode, non-empty primitives count as "having values"
    elif not track_mode:
        return bool(template)

    return result


# Replace existing functions with the new unified function
def track_used_variables(template, variables):
    """
    Track which variables from the input are used in the template.

    Args:
        template: The configuration template
        variables: The variables to check for usage

    Returns:
        set: A set of variable names that were used in the template
    """
    return analyze_variables(template, variables, track_mode=True)


def has_variable_injections_or_values(cfg, input_vars, os_environ, default_vars):
    """
    Check if a branch or any of its sub-branches contain variable injections or values.

    Args:
        cfg: The configuration branch to check
        input_vars: User-provided variables
        os_environ: Environment variables
        default_vars: Default variables from configuration

    Returns:
        bool: True if the branch contains injections or values, False otherwise
    """
    return analyze_variables(cfg, input_vars, os_environ, default_vars, track_mode=False)


def filter_branches_with_injections(
    config_item: Dict[str, Any],
    base_module: Optional[str],
    original_kwargs: Dict[str, Any],
    remaining_kwargs: Dict[str, Any],
    default_vars: Dict[str, Any]
) -> Any:
    """
    Filter branches at the second level, keeping only those with variable injections or values.
    Also handle special cases like init=false.
    Top-level kwargs are always preserved regardless of their values.

    Args:
        config_item: The configuration item to filter
        base_module: The base module for class imports
        original_kwargs: Original kwargs passed to aini
        remaining_kwargs: Kwargs not used in variable resolution
        default_vars: Default variables from configuration

    Returns:
        The filtered configuration item or direct class instance
    """
    # If not a dictionary, no filtering needed
    if not isinstance(config_item, dict):
        return build_from_config(config_item, base_module)

    # For class definitions, filter the params at the second level
    if 'class' in config_item:
        # Special case: init=false means return the class itself, not an instance
        init_method = config_item.get('init', None)
        if init_method is False or init_method == 'false':
            return import_class(config_item['class'], base_module)

        # Get the params dictionary
        params = config_item.get('params', {})

        # Filter params to keep only branches with injections or values
        filtered_params = {}
        for param_key, param_val in params.items():
            # Always keep top-level kwargs, even if empty
            if param_key in original_kwargs:
                filtered_params[param_key] = param_val
            # For other params, only keep if they have injections or values
            elif has_variable_injections_or_values(param_val, original_kwargs, os.environ, default_vars):
                filtered_params[param_key] = param_val

        # Only inject remaining kwargs to top-level class
        merged_params = {**filtered_params, **remaining_kwargs}
        filtered_item = {**config_item, 'params': merged_params}

        return build_from_config(filtered_item, base_module)
    else:
        # For regular dictionaries, filter at the second level
        filtered_dict = {}
        for key, val in config_item.items():
            # Always keep top-level kwargs, even if empty
            if key in original_kwargs:
                filtered_dict[key] = val
            # For other keys, only keep if they have injections or values
            elif has_variable_injections_or_values(val, original_kwargs, os.environ, default_vars):
                filtered_dict[key] = val

        return build_from_config(filtered_dict, base_module)


def aini(
    file_path: str,
    akey: Optional[str] = None,
    base_module: Optional[str] = None,
    file_type: Literal['yaml', 'json'] = 'yaml',
    araw: bool = False,
    **kwargs,
) -> Union[Any, Dict[str, Any]]:
    """
    Load YAML / JSON from a file, resolve input/env/default variables, and return built class instances.
    Supports a special top-level 'defaults' block to define fallback variable values.
    Priority: input variables (kwargs) > os.environ > 'defaults' block in input file > None.
    Branches at the second level with no variable injections or values are excluded.

    Args:
        file_path: Path to the YAML file. Relative path is working against current folder.
                  You can specify an akey using the format 'path/to/file:key_name'.
        akey: Optional key to select one instance of the YAML structure.
              If both 'file_path:key' syntax and akey parameter are provided, the parameter takes precedence.
        base_module: Base module for resolving relative imports.
            If not provided, derived from the parent folder of this builder file.
        file_type: Format of the configuration file ('yaml' or 'json').
        araw: If True, returns the resolved configuration without building objects,
               allowing inspection of the data with variables substituted.
        **kwargs: Variables for ${VAR} substitution. When returning a single instance,
                 these are also passed to the builder for parameter overrides.

    Returns:
        - If araw=True: Returns the resolved configuration with variables substituted.
        - If akey is provided: Returns the instance at config[akey] with kwargs applied.
        - If YAML has exactly one top-level key (and akey is None): Returns its instance with kwargs applied.
        - If YAML has multiple top-level keys (and akey is None): Returns a dict mapping each key to its instance.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_module = os.path.basename(os.path.dirname(script_dir))

    # Parse file_path for colon syntax (file_path:akey), considering Windows drive letters
    if ':' in file_path and akey is None:
        # Check if the colon is part of a Windows drive letter (e.g., C:)
        parts = file_path.split(':')
        if len(parts) > 2 or (len(parts) == 2 and len(parts[0]) > 1):
            # This is likely a path:key format, not just a drive letter
            # Find the last colon which is not part of a drive letter
            last_colon_idx = file_path.rfind(':')

            # Check if this colon might be part of a drive letter (e.g., C:)
            if last_colon_idx > 1 or (last_colon_idx == 1 and not file_path[0].isalpha()):
                # Not a drive letter colon, so this is our key separator
                extracted_path = file_path[:last_colon_idx]
                extracted_key = file_path[last_colon_idx + 1:]
                file_path = extracted_path
                akey = extracted_key

    if base_module is None:
        base_module = default_module

    ext = ['yml', 'yaml'] if file_type == 'yaml' else ['json']
    if file_path.rsplit('.')[-1].lower() not in ext:
        file_path += f'.{ext[0]}'

    # File existence checks
    if not os.path.exists(file_path):
        # Try the current working directory
        cwd_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(cwd_path):
            file_path = cwd_path
        else:
            # Try relative to the script directory
            script_relative_path = os.path.join(script_dir, file_path)
            if os.path.exists(script_relative_path):
                file_path = script_relative_path
            else:
                # As a last resort, try the original behavior (parent directory)
                parent_path = os.path.join(os.path.dirname(script_dir), file_path)
                if os.path.exists(parent_path):
                    file_path = parent_path
                else:
                    raise FileNotFoundError(f'File not found: {file_path}')

    with open(file_path, 'r', encoding='utf-8') as f:
        if file_type == 'yaml':
            raw_config = yaml.safe_load(f)
        elif file_type == 'json':
            raw_config = json.load(f)
        else:
            raise ValueError(f'Unsupported file type: {file_type}')

    if not isinstance(raw_config, dict):
        raise ValueError(f'Invalid {file_type} structure: {file_path} - required dict at top level')

    # Save original kwargs for later use
    original_kwargs = kwargs.copy()

    # Prepare default variables
    default_vars = raw_config.pop('defaults', {}) if 'defaults' in raw_config else {}

    # Track which variables are used in the config template
    used_vars = track_used_variables(raw_config, kwargs)

    # Resolve variables in the configuration
    _config_ = resolve_vars(raw_config, kwargs, default_vars)

    # Calculate which kwargs were NOT used in variable resolution
    remaining_kwargs = {k: v for k, v in original_kwargs.items() if k not in used_vars}

    # If araw is enabled, return the resolved configuration without building
    if araw:
        if akey:
            if akey not in _config_:
                raise KeyError(f"akey '{akey}' not found in configuration")
            return _config_[akey]
        return _config_

    # Handle the returned object(s)
    if isinstance(_config_, dict):
        # Case 1: akey is provided - return a single instance
        if akey:
            if akey not in _config_:
                raise KeyError(f"akey '{akey}' not found in configuration")
            return filter_branches_with_injections(
                _config_[akey], base_module, original_kwargs, remaining_kwargs, default_vars
            )

        # Case 2: Single top-level key (no akey) - return the single instance
        if len(_config_) == 1:
            key, val = next(iter(_config_.items()))
            return filter_branches_with_injections(
                val, base_module, original_kwargs, remaining_kwargs, default_vars
            )

        # Case 3: Multiple top-level keys - return a dictionary of instances
        instances: Dict[str, Any] = {}
        for key, val in _config_.items():
            instances[key] = filter_branches_with_injections(
                val, base_module, original_kwargs, remaining_kwargs, default_vars
            )
        return instances

    # Case 4: Not a dictionary (unlikely but handled for completeness)
    else:
        return build_from_config(_config_, base_module)
