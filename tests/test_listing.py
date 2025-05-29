import os
import sys
import pytest
import yaml
import tempfile
import shutil
from unittest.mock import patch
from contextlib import contextmanager

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aini.listing import alist, _print_yaml_summary


@contextmanager
def temp_directory_setup():
    """Create a temporary directory structure with test YAML files."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    original_dir = os.getcwd()

    try:
        # Create subdirectories
        models_dir = os.path.join(temp_dir, "models")
        agents_dir = os.path.join(temp_dir, "agents")
        config_dir = os.path.join(temp_dir, "config")
        hidden_dir = os.path.join(temp_dir, ".hidden")

        os.makedirs(models_dir)
        os.makedirs(agents_dir)
        os.makedirs(config_dir)
        os.makedirs(hidden_dir)

        # Create test YAML files
        # Root directory YAML
        with open(os.path.join(temp_dir, "config.yaml"), "w") as f:
            yaml.dump({"global": "settings", "defaults": "should_be_excluded"}, f)

        # Models directory YAMLs
        with open(os.path.join(models_dir, "gpt4.yaml"), "w") as f:
            yaml.dump({"model": "gpt-4", "defaults": {"temp": 0.7}, "config": "model"}, f)

        with open(os.path.join(models_dir, "claude.yml"), "w") as f:
            yaml.dump({"model": "claude-3", "provider": "anthropic"}, f)

        # Agents directory YAMLs
        with open(os.path.join(agents_dir, "assistant.yaml"), "w") as f:
            yaml.dump({"agent": "assistant", "model": "gpt-4"}, f)

        # Config directory YAML
        with open(os.path.join(config_dir, "settings.yaml"), "w") as f:
            yaml.dump({"settings": {"temperature": 0.7}, "max_tokens": 4096}, f)

        # Hidden directory YAML (should be excluded by default)
        with open(os.path.join(hidden_dir, "hidden.yaml"), "w") as f:
            yaml.dump({"hidden": "config"}, f)

        # Non-YAML file (should be excluded)
        with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
            f.write("This is not a YAML file")

        # Create an invalid YAML file
        with open(os.path.join(temp_dir, "invalid.yaml"), "w") as f:
            f.write("This is not valid YAML: :")

        # Change to the temp directory
        os.chdir(temp_dir)

        yield temp_dir

    finally:
        # Restore original directory and clean up
        os.chdir(original_dir)
        shutil.rmtree(temp_dir)


class TestListing:
    """Test the alist and related functions in the listing module."""

    def test_basic_functionality(self, capsys):
        """Test basic functionality of alist with default parameters."""
        with temp_directory_setup():
            # Call alist with default parameters (print_results=True)
            result = alist()

            # Should return None when print_results is True
            assert result is None

            # Verify output contains expected sections
            captured = capsys.readouterr()
            assert "Current Working Directory" in captured.out
            assert "models/" in captured.out
            assert "agents/" in captured.out
            assert "config/" in captured.out

    def test_return_results(self):
        """Test alist returns a dictionary when print_results=False."""
        with temp_directory_setup():
            # Call alist with print_results=False
            result = alist(print_results=False)

            # Should return a dictionary with 'current' and 'aini' keys
            assert isinstance(result, dict)
            assert 'current' in result
            assert 'aini' in result

            # Check that files from current directory are found
            current_files = result['current']
            assert "config.yaml" in current_files
            assert "models/gpt4.yaml" in current_files
            assert "models/claude.yml" in current_files
            assert "agents/assistant.yaml" in current_files
            assert "config/settings.yaml" in current_files

            # Verify that hidden files are excluded
            assert not any(".hidden" in key for key in current_files.keys())

            # Verify key filtering - defaults should be excluded
            assert "defaults" not in current_files["config.yaml"]
            assert "global" in current_files["config.yaml"]

    def test_subfolder_filtering(self):
        """Test filtering by subfolder name."""
        with temp_directory_setup():
            # Filter for 'model' subfolder
            result = alist(key="model", print_results=False)

            # Should only include files from the models directory
            assert len(result['current']) > 0
            assert all("models/" in key for key in result['current'].keys())
            assert "models/gpt4.yaml" in result['current']
            assert "models/claude.yml" in result['current']

            # Filter for 'agent' subfolder
            result = alist(key="agent", print_results=False)

            # Should only include files from the agents directory
            assert len(result['current']) > 0
            assert all("agents/" in key for key in result['current'].keys())
            assert "agents/assistant.yaml" in result['current']

    def test_include_hidden(self):
        """Test including hidden directories."""
        with temp_directory_setup():
            # Include hidden directories
            result = alist(exclude_hidden=False, print_results=False)

            # Hidden files should be included
            hidden_files = [f for f in result['current'].keys() if ".hidden" in f]
            assert len(hidden_files) > 0
            assert ".hidden/hidden.yaml" in result['current']

    def test_custom_patterns(self):
        """Test custom include and exclude patterns."""
        with temp_directory_setup():
            # Only include .yml files
            result = alist(include_patterns=["*.yml"], print_results=False)

            # Should only find .yml files
            assert "models/claude.yml" in result['current']
            assert "config.yaml" not in result['current']
            assert "models/gpt4.yaml" not in result['current']

            # Exclude files with 'gpt' in the name
            result = alist(exclude_patterns=["*gpt*.yaml"], print_results=False)

            # Should exclude gpt4.yaml but include others
            assert "models/gpt4.yaml" not in result['current']
            assert "models/claude.yml" in result['current']
            assert "config.yaml" in result['current']

    def test_custom_base_path(self):
        """Test using a custom base path."""
        with temp_directory_setup() as temp_dir:
            # Create a subdirectory and add a YAML file
            sub_dir = os.path.join(temp_dir, "custom_subdir")
            os.makedirs(sub_dir)
            with open(os.path.join(sub_dir, "custom.yaml"), "w") as f:
                yaml.dump({"custom": "value"}, f)

            # Change to a different directory
            original_dir = os.getcwd()
            tmp_dir = tempfile.mkdtemp()
            try:
                os.chdir(tmp_dir)

                # Use the created directory as base_path
                result = alist(base_path=sub_dir, print_results=False)
                print(result)

                # Should find the custom file
                assert "custom.yaml" in result['current']
                assert result['current']["custom.yaml"] == ["custom"]
            finally:
                os.chdir(original_dir)
                shutil.rmtree(tmp_dir)

    def test_exclude_keys(self):
        """Test excluding specific top-level keys."""
        with temp_directory_setup():
            # Exclude both 'defaults' (default) and 'model' keys
            result = alist(exclude_keys=["defaults", "model"], print_results=False)

            # 'model' should be excluded from results
            assert "model" not in result['current']["models/gpt4.yaml"]
            assert "model" not in result['current']["models/claude.yml"]

            # But other keys should still be there
            assert "provider" in result['current']["models/claude.yml"]
            assert "config" in result['current']["models/gpt4.yaml"]
            assert "agent" in result['current']["agents/assistant.yaml"]

    def test_verbose_mode(self, caplog):
        """Test verbose logging."""
        with temp_directory_setup():
            caplog.clear()
            # Enable verbose mode
            alist(verbose=True, print_results=False)

            # Check that log messages were generated
            assert "Searching in:" in caplog.text
            assert "Found " in caplog.text

    def test_error_handling(self, caplog):
        """Test error handling for invalid YAML files."""
        with temp_directory_setup():
            caplog.clear()
            # Try to process the invalid YAML file with verbose mode
            alist(verbose=True, print_results=False)

            # Check for error message
            assert "Error processing" in caplog.text

    # def test_empty_result(self, capsys):
    #     """Test handling of empty results."""
    #     with temp_directory_setup():
    #         # Create a temporary directory with no YAML files
    #         empty_dir = tempfile.mkdtemp()
    #         original_dir = os.getcwd()

    #         try:
    #             # Change to the empty directory
    #             os.chdir(empty_dir)

    #             # Clear any previous captured output
    #             capsys.readouterr()  # This discards any previous output

    #             # Call alist in the empty directory
    #             alist()

    #             # Now capture just the output from the alist() call
    #             captured = capsys.readouterr()
    #             assert "No YAML files found" in captured.out
    #         finally:
    #             # Make sure we change back to the original directory before attempting cleanup
    #             os.chdir(original_dir)

    #             # Try to clean up with error handling
    #             try:
    #                 shutil.rmtree(empty_dir)
    #             except OSError as e:
    #                 # Just log the error instead of failing the test
    #                 print(f"Warning: Could not remove temporary directory {empty_dir}: {e}")

    def test_indent_size(self, capsys):
        """Test custom indentation size."""
        with temp_directory_setup():
            # Call alist with a custom indent size
            alist(indent_size=4)

            # We can't easily verify the exact indentation, but we can check output is generated
            captured = capsys.readouterr()
            assert "Current Working Directory" in captured.out

    @patch('aini.listing.console.print')
    def test_print_yaml_summary(self, mock_print):
        """Test the _print_yaml_summary function directly."""
        with temp_directory_setup():
            # Create a sample result dictionary
            result = {
                'current': {
                    'test.yaml': ['key1', 'key2'],
                    'dir/test2.yaml': ['key3']
                },
                'aini': {
                    'other.yaml': ['key4']
                }
            }

            # Call _print_yaml_summary directly
            _print_yaml_summary(result, indent_size=2)

            # Verify console.print was called
            mock_print.assert_called()


if __name__ == "__main__":
    pytest.main(["-v", "test_listing.py"])
