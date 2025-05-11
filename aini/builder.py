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


def resolve_var_match(match: Match, input_vars: Dict[str, Any], default_vars: Dict[str, Any]) -> Any:
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

            # Handle boolean literals
            if alt.lower() == 'true':
                return True if is_full_match else 'True'
            elif alt.lower() == 'false':
                return False if is_full_match else 'False'

            # Handle numeric literals
            if alt.isdigit():
                return int(alt) if is_full_match else alt
            elif alt.replace('.', '', 1).isdigit() and alt.count('.') == 1:
                return float(alt) if is_full_match else alt

            # Handle quoted literals
            if (alt.startswith('"') and alt.endswith('"')) or (alt.startswith("'") and alt.endswith("'")):
                return alt[1:-1]  # Return the literal without quotes

            # Try variables in priority order
            if alt in input_vars:
                value = input_vars[alt]
                return value if is_full_match else str(value)
            elif alt in os.environ:
                env_val = os.environ[alt]
                # Handle boolean environment variables
                if env_val.lower() == 'true':
                    return True if is_full_match else 'True'
                elif env_val.lower() == 'false':
                    return False if is_full_match else 'False'
                return env_val
            elif alt in default_vars:
                value = default_vars[alt]
                return value if is_full_match else str(value)

        # No alternatives resolved
        return None if is_full_match else 'None'

    # Handle single variable (no | operator)
    var_name = var_expr
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
    - If cfg also has an 'init' key, use that method to instantiate instead of constructor.
    - If cfg is a list, apply build_from_config on each element.
    - Otherwise, return cfg as a literal.
    """
    if isinstance(cfg, list):
        return [build_from_config(item, base_module) for item in cfg]

    if isinstance(cfg, dict) and 'class' in cfg:
        class_path = cfg['class']
        params = cfg.get('params', {})
        init_method = cfg.get('init', None)  # Get initialization method name if specified

        # Recursively build nested parameters
        built_params = {
            key: build_from_config(val, base_module) for key, val in params.items()
        }

        # Import the class
        cls = import_class(class_path, base_module)

        # Use initialization method if specified, otherwise use constructor
        if init_method:
            if not hasattr(cls, init_method):
                raise AttributeError(f"Class {class_path} has no method '{init_method}'")
            init_func = getattr(cls, init_method)
            return init_func(**built_params)
        else:
            # Default behavior: use constructor
            return cls(**built_params)

    # Base literal case
    return cfg


def aini(
    file_path: str,
    akey: Optional[str] = None,
    base_module: Optional[str] = None,
    file_type: Literal['yaml', 'json'] = 'yaml',
    **kwargs,
) -> Union[Any, Dict[str, Any]]:
    """
    Load YAML / JSON from a file, resolve input/env/default variables, and return built class instances.
    Supports a special top-level 'defaults' block to define fallback variable values.
    Priority: input varriables (kwargs) > os.environ > 'defaults' block in input file > None.

    Args:
        file_path: Path to the YAML file. Relative path is working against current folder.
        akey: Optional key to select one instance of the YAML structure.
        base_module: Base module for resolving relative imports.
            If not provided, derived from the parent folder of this builder file.
        kwargs: Variables for ${VAR} substitution.

    Returns:
        - If akey is provided, returns the instance at config[akey].
        - If YAML has exactly one top-level key (and akey is None), returns its instance.
        - If YAML has multiple top-level keys (and akey is None), returns a dict mapping each key to its instance.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_module = os.path.basename(os.path.dirname(script_dir))

    if base_module is None:
        base_module = default_module

    ext = ['yml', 'yaml'] if file_type == 'yaml' else ['json']
    if file_path.rsplit('.')[-1].lower() not in ext:
        file_path += f'.{ext[0]}'

    # First check if file exists at specified path (absolute or relative to current working directory)
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

    # Prepare and resolve variables
    default_vars = raw_config.pop('defaults', {})
    _config_ = resolve_vars(raw_config, kwargs, default_vars)

    if isinstance(_config_, dict):
        # Select subset if akey given
        if akey:
            if akey not in _config_:
                raise KeyError(f"akey '{akey}' not found in YAML file")
            return build_from_config(_config_[akey], base_module)

        # No akey: handle single or multiple
        if len(_config_) == 1:
            _, val = next(iter(_config_.items()))
            return build_from_config(val, base_module)

        instances: Dict[str, Any] = {}
        for key, val in _config_.items():
            instances[key] = build_from_config(val, base_module)

        return instances

    else:
        return build_from_config(_config_)
