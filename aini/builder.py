import importlib
import json
import os
from typing import Any, Dict, List, Literal, Optional, Union

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


def resolve_vars(
    cfg: Union[Dict[str, Any], List[Any], Any],
    input_vars: Dict[str, Any],
    default_vars: Dict[str, Any],
) -> Union[Dict[str, Any], List[Any], Any]:
    """
    Recursively resolve ${VAR} placeholders in strings using input_vars, OS environment, and default_vars.
    Priority: input_vars > os.environ > default_vars > None.

    If the entire string is ${VAR}, the resolved value is injected as-is (can be object, list, etc.).
    """
    if isinstance(cfg, dict):
        return {
            key: resolve_vars(val, input_vars, default_vars) for key, val in cfg.items()
        }
    if isinstance(cfg, list):
        return [resolve_vars(item, input_vars, default_vars) for item in cfg]
    if isinstance(cfg, str):
        if cfg.startswith('${') and cfg.endswith('}') and cfg.count('${') == 1:
            var_name = cfg[2:-1]
            if var_name in input_vars:
                return input_vars[var_name]
            elif var_name in os.environ:
                return os.environ[var_name]
            return default_vars.get(var_name, None)

        parts = []
        while '${' in cfg:
            before, _, rest = cfg.partition('${')
            var_name, sep, after = rest.partition('}')
            if not sep:
                parts.append(before + '${' + rest)
                break
            parts.append(before)
            if var_name in input_vars:
                parts.append(str(input_vars[var_name]))
            elif var_name in os.environ:
                parts.append(str(os.environ[var_name]))
            elif var_name in default_vars:
                parts.append(str(default_vars[var_name]))
            else:
                parts.append('None')
            cfg = after
        parts.append(cfg)
        return ''.join(parts)
    return cfg


def build_from_config(
    cfg: Union[Dict[str, Any], List[Any], Any],
    base_module: Optional[str] = None,
) -> Union[Any, List[Any], Any]:
    """
    Recursively construct objects from a configuration structure.

    - If cfg is a dict with a 'class' key, import and instantiate it.
    - If cfg is a list, apply build_from_config on each element.
    - Otherwise, return cfg as a literal.
    """
    if isinstance(cfg, list):
        return [build_from_config(item, base_module) for item in cfg]

    if isinstance(cfg, dict) and 'class' in cfg:
        class_path = cfg['class']
        params = cfg.get('params', {})

        # Recursively build nested parameters
        built_params = {
            key: build_from_config(val, base_module) for key, val in params.items()
        }

        # Instantiate the class
        cls = import_class(class_path, base_module)
        return cls(**built_params)

    # Base literal case
    return cfg


def aini(
    file_path: str,
    root_key: Optional[str] = None,
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
        root_key: Optional key to select one instance of the YAML structure.
        base_module: Base module for resolving relative imports.
            If not provided, derived from the parent folder of this builder file.
        kwargs: Variables for ${VAR} substitution.

    Returns:
        - If root_key is provided, returns the instance at config[root_key].
        - If YAML has exactly one top-level key (and root_key is None), returns its instance.
        - If YAML has multiple top-level keys (and root_key is None), returns a dict mapping each key to its instance.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_module = os.path.basename(os.path.dirname(script_dir))

    if base_module is None:
        base_module = default_module

    ext = ['yml', 'yaml'] if file_type == 'yaml' else ['json']
    if file_path.rsplit('.')[-1].lower() not in ext:
        file_path += f'.{ext[0]}'
    if not os.path.exists(file_path):
        inferred_path = os.path.join(os.path.dirname(script_dir), file_path)
        if os.path.exists(inferred_path):
            file_path = inferred_path
        else:
            raise FileNotFoundError(f'YAML file not found: {file_path}')

    with open(file_path, 'r', encoding='utf-8') as f:
        if file_type == 'yaml':
            raw_config = yaml.safe_load(f)
        elif file_type == 'json':
            raw_config = json.load(f)
        else:
            raise ValueError(f'Unsupported file type: {file_type}')

    if not isinstance(raw_config, dict):
        raise ValueError(
            f'Invalid {file_type} structure: {file_path} - required dict at top level'
        )

    # Prepare and resolve variables
    default_vars = raw_config.pop('defaults', {})
    _config_ = resolve_vars(raw_config, kwargs, default_vars)

    if isinstance(_config_, dict):
        # Select subset if root_key given
        if root_key:
            if root_key not in _config_:
                raise KeyError(f"root_key '{root_key}' not found in YAML file")
            return build_from_config(_config_[root_key], base_module)

        # No root_key: handle single or multiple
        if len(_config_) == 1:
            _, val = next(iter(_config_.items()))
            return build_from_config(val, base_module)

        instances: Dict[str, Any] = {}
        for key, val in _config_.items():
            instances[key] = build_from_config(val, base_module)

        return instances

    else:
        return build_from_config(_config_)
