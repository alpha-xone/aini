import os
from typing import Dict, List, Optional, Union
import yaml
from pathlib import Path
import logging
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


def alist(
    key: Optional[str] = None,
    base_path: Optional[str] = None,
    include_patterns: List[str] = ["*.yaml", "*.yml"],
    exclude_patterns: List[str] = [],
    exclude_hidden: bool = True,
    verbose: bool = False,
    exclude_keys: List[str] = ["defaults"],
    print_results: bool = True,
    indent_size: int = 2
) -> Union[Dict[str, Dict[str, List[str]]], None]:
    """
    List all YAML files and their top-level keys from immediate subfolders of:
    1) The current working directory
    2) The directory containing this script

    Args:
        key: Optional keyword to filter results. Only files in subfolders
             with names containing this string will be included.
        base_path: Optional base path to search from. If not provided, searches both
                   current directory and script directory.
        include_patterns: Glob patterns for files to include (defaults to *.yaml, *.yml)
        exclude_patterns: Glob patterns for files to exclude
        exclude_hidden: Whether to exclude hidden folders (starting with .)
        verbose: Whether to print detailed information while searching
        exclude_keys: List of top-level keys to exclude from results (defaults to ["defaults"])
        print_results: Whether to print the results directly (if True, returns None)
        indent_size: Size of the indentation for printed results (default: 2)

    Returns:
        Dictionary with 'current' and 'aini' keys, each containing dictionaries mapping
        file paths to lists of their top-level keys, or None if print_results is True
    """
    if verbose:
        logger.setLevel(logging.INFO)

    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the current working directory
    cwd = os.getcwd()

    # Determine which directories to search
    search_dirs = []
    if base_path:
        search_dirs.append(Path(base_path))
    else:
        search_dirs = [Path(cwd), Path(script_dir)]
        # Avoid duplicates if cwd is the same as script_dir
        search_dirs = list(set(search_dirs))

    # Initialize result structure with 'current' and 'aini' dictionaries
    result = {
        'current': {},  # For files from current working directory or base_path
        'aini': {}      # For files from script directory
    }

    for search_dir in search_dirs:
        if verbose:
            logger.info(f"Searching in: {search_dir}")

        # Determine if this is current directory, base_path, or aini directory
        # If base_path is provided, always treat it as 'current'
        if base_path:
            is_cwd = True  # Treat as 'current' when base_path is provided
        else:
            is_cwd = str(search_dir.resolve()) == str(Path(cwd).resolve())

        target_dict = result['current'] if is_cwd else result['aini']

        # Get immediate subdirectories
        subdirs = [d for d in search_dir.iterdir() if d.is_dir()]

        # Filter out hidden directories if needed
        if exclude_hidden:
            subdirs = [d for d in subdirs if not d.name.startswith('.')]

        # Filter subdirectories by key if provided
        if key:
            subdirs = [d for d in subdirs if key.lower() in d.name.lower()]
            if verbose:
                logger.info(f"Filtered to {len(subdirs)} subdirectories matching '{key}'")
                for d in subdirs:
                    logger.info(f"  - {d.name}")

        # Include the search_dir itself as a possible location only if key is None
        all_dirs = ([search_dir] + subdirs) if key is None else subdirs

        # Search only in immediate subdirectories (and the search_dir itself if key is None)
        for dir_to_search in all_dirs:
            for pattern in include_patterns:
                # Use simple glob to find only files in this directory (not recursive)
                yaml_files = list(dir_to_search.glob(pattern))

                # Apply exclusion patterns
                for exclude in exclude_patterns:
                    excluded_files = list(dir_to_search.glob(exclude))
                    yaml_files = [f for f in yaml_files if f not in excluded_files]

                for yaml_file in yaml_files:
                    try:
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            yaml_content = yaml.safe_load(f)

                        if not isinstance(yaml_content, dict):
                            if verbose:
                                logger.info(f"Skipping {yaml_file}: Content is not a dictionary")
                            continue

                        # Get the top-level keys
                        top_level_keys = list(yaml_content.keys())

                        # Exclude specified keys
                        top_level_keys = [k for k in top_level_keys if k not in exclude_keys]

                        # Store the result with origin information
                        relative_path = os.path.relpath(yaml_file, search_dir)
                        relative_path = relative_path.replace('\\', '/')

                        # Store directly in the appropriate dictionary
                        target_dict[relative_path] = top_level_keys

                        if verbose:
                            origin_type = "current" if is_cwd else "aini"
                            logger.info(f"Found {relative_path} with keys: {top_level_keys} (origin: {origin_type})")

                    except Exception as e:
                        if verbose:
                            logger.error(f"Error processing {yaml_file}: {str(e)}")

    # Print results if requested
    if print_results:
        _print_yaml_summary(result, indent_size)
        return None
    else:
        return result


def _print_yaml_summary(
    result: Dict[str, Dict[str, List[str]]],
    indent_size: int = 2
):
    """
    Print a nicely formatted summary of YAML files and their keys using Rich.

    Args:
        result: Dictionary with 'current' and 'aini' keys, each containing dictionaries
               mapping file paths to lists of their top-level keys
        indent_size: Size of the indentation (default: 2)
    """
    # Get total number of files
    total_files = len(result.get('current', {})) + len(result.get('aini', {}))

    if total_files == 0:
        console.print("[bold red]No YAML files found.[/bold red]")
        return

    # Get the current working directory and script directory
    cwd = str(Path(os.getcwd()).resolve())
    script_dir = str(Path(os.path.dirname(os.path.abspath(__file__))).resolve())

    # Format paths with forward slashes for consistency
    cwd_formatted = cwd.replace('\\', '/')
    script_dir_formatted = script_dir.replace('\\', '/')

    # Group files by directory
    cwd_files = {}  # Structure: {dir_name: {file_name: {keys: [...]}}}
    aini_files = {}

    # Process current working directory files
    for file_path, keys in result.get('current', {}).items():
        # Split path into directory and filename parts
        path_parts = file_path.split('/')
        if len(path_parts) > 1:
            dir_name = '/'.join(path_parts[:-1])
            file_name = path_parts[-1]
        else:
            dir_name = "."  # Root directory
            file_name = file_path

        # Initialize directory dictionary if not present
        if dir_name not in cwd_files:
            cwd_files[dir_name] = {}

        # Store file with its keys
        cwd_files[dir_name][file_name] = {
            'keys': keys,
            'original_path': file_path
        }

    # Process aini directory files
    for file_path, keys in result.get('aini', {}).items():
        # Split path into directory and filename parts
        path_parts = file_path.split('/')
        if len(path_parts) > 1:
            dir_name = '/'.join(path_parts[:-1])
            file_name = path_parts[-1]
        else:
            dir_name = "."  # Root directory
            file_name = file_path

        # Initialize directory dictionary if not present
        if dir_name not in aini_files:
            aini_files[dir_name] = {}

        # Store file with its keys
        aini_files[dir_name][file_name] = {
            'keys': keys,
            'original_path': file_path
        }

    # Create a main tree
    guide_style = f"bright_black {' ' * (indent_size - 1)}"
    main_tree = Tree(
        f"[bold blue]Found {total_files} YAML file(s)[/bold blue]",
        guide_style=guide_style
    )

    # Add Current Working Directory section if there are files
    if cwd_files:
        cwd_tree = main_tree.add(f"[bold magenta]Current Working Directory[/bold magenta]: [dim]{cwd_formatted}/[/dim]")

        # Sort directories for consistent output
        for dir_name in sorted(cwd_files.keys()):
            files = cwd_files[dir_name]
            if dir_name == ".":
                dir_tree = cwd_tree  # Files in root go directly under CWD
            else:
                dir_tree = cwd_tree.add(f"[bold cyan]{dir_name}/[/bold cyan]")

            # Sort files for consistent output
            for file_name in sorted(files.keys()):
                file_info = files[file_name]
                keys = file_info['keys']
                if keys:
                    # Create a styled string with the keys
                    keys_text = ", ".join(f"[green]{key}[/green]" for key in keys)
                    dir_tree.add(f"[yellow]{file_name}[/yellow]: {keys_text}")
                else:
                    dir_tree.add(f"[yellow]{file_name}[/yellow]: [italic](no keys)[/italic]")

    # Add aini / Site-Packages section if there are files
    if aini_files:
        aini_tree = main_tree.add(f"[bold magenta]aini / Site-Packages[/bold magenta]: [dim]{script_dir_formatted}/[/dim]")

        # Sort directories for consistent output
        for dir_name in sorted(aini_files.keys()):
            files = aini_files[dir_name]
            if dir_name == ".":
                dir_tree = aini_tree  # Files in root go directly under aini
            else:
                dir_tree = aini_tree.add(f"[bold cyan]{dir_name}/[/bold cyan]")

            # Sort files for consistent output
            for file_name in sorted(files.keys()):
                file_info = files[file_name]
                keys = file_info['keys']
                if keys:
                    # Create a styled string with the keys
                    keys_text = ", ".join(f"[green]{key}[/green]" for key in keys)
                    dir_tree.add(f"[yellow]{file_name}[/yellow]: {keys_text}")
                else:
                    dir_tree.add(f"[yellow]{file_name}[/yellow]: [italic](no keys)[/italic]")

    # Print the tree with the specified indentation size
    console.print(Panel(main_tree, expand=False), justify="left")
