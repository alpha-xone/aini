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
) -> Union[Dict[str, List[str]], None]:
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
        Dictionary mapping file paths to lists of their top-level keys,
        or None if print_results is True
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

    result = {}
    result_origins = {}  # Track which search_dir each file came from

    for search_dir in search_dirs:
        if verbose:
            logger.info(f"Searching in: {search_dir}")

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
                        result[relative_path] = top_level_keys
                        result_origins[relative_path] = str(search_dir)  # Store the origin

                        if verbose:
                            logger.info(f"Found {relative_path} with keys: {top_level_keys}")

                    except Exception as e:
                        if verbose:
                            logger.error(f"Error processing {yaml_file}: {str(e)}")

    # Print results if requested
    if print_results:
        _print_yaml_summary(result, result_origins, indent_size)
        return None
    else:
        return result


def _print_yaml_summary(
    file_keys: Dict[str, List[str]],
    file_origins: Dict[str, str],
    indent_size: int = 2
):
    """
    Print a nicely formatted summary of YAML files and their keys using Rich.

    Args:
        file_keys: Dictionary mapping file paths to lists of their top-level keys
        file_origins: Dictionary mapping file paths to their origin directories
        indent_size: Size of the indentation (default: 2)
    """
    if not file_keys:
        console.print("[bold red]No YAML files found.[/bold red]")
        return

    # Get the current working directory and script directory
    cwd = str(Path(os.getcwd()).resolve())
    script_dir = str(Path(os.path.dirname(os.path.abspath(__file__))).resolve())

    # Create two dictionaries of dictionaries to prevent subfolder name collisions
    # Structure: {dir_name: {file_name: {keys: [...], path: original_path}}}
    cwd_files = {}
    aini_files = {}

    # Debug print the origins and paths
    if logger.level <= logging.INFO:
        logger.info(f"CWD: {cwd}")
        logger.info(f"Script dir: {script_dir}")
        for path, origin in file_origins.items():
            logger.info(f"File: {path}, Origin: {origin}")

    # Group files by directory and categorize them
    for file_path, keys in file_keys.items():
        # Use the origin information to determine the source
        origin = file_origins.get(file_path, "")

        # Normalize paths for comparison
        origin_path = str(Path(origin).resolve())

        # Determine which target dictionary to use by checking if origin starts with cwd
        if origin_path == cwd or origin_path.startswith(cwd + os.sep):
            target_dict = cwd_files
            if logger.level <= logging.INFO:
                logger.info(f"Categorizing {file_path} as CWD file")
        else:
            target_dict = aini_files
            if logger.level <= logging.INFO:
                logger.info(f"Categorizing {file_path} as aini file")

        # Split path into directory and filename parts
        path_parts = file_path.split('/')
        if len(path_parts) > 1:
            dir_name = '/'.join(path_parts[:-1])
            file_name = path_parts[-1]
        else:
            dir_name = "."  # Root directory
            file_name = file_path

        # Initialize directory dictionary if not present
        if dir_name not in target_dict:
            target_dict[dir_name] = {}

        # Store file with its keys and original path
        target_dict[dir_name][file_name] = {
            'keys': keys,
            'original_path': file_path
        }

    # Create a main tree
    guide_style = f"bright_black {' ' * (indent_size - 1)}"
    main_tree = Tree(
        f"[bold blue]Found {len(file_keys)} YAML file(s)[/bold blue]",
        guide_style=guide_style
    )

    # Add Current Working Directory section if there are files
    if cwd_files:
        cwd_tree = main_tree.add("[bold magenta]Current Working Directory[/bold magenta]")

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
        aini_tree = main_tree.add("[bold magenta]aini / Site-Packages[/bold magenta]")

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
