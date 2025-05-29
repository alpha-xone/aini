import os
import sys
import pytest
import tempfile
import shutil
import yaml

# Add parent directory to path to import aini modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aini.listing import alist


class TestAlist:
    """Test the alist function in aini.listing module."""

    @pytest.fixture
    def temp_dir_structure(self):
        """Create a temporary directory with test YAML files."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        try:
            # Create subdirectories
            models_dir = os.path.join(temp_dir, "models")
            agents_dir = os.path.join(temp_dir, "agents")
            hidden_dir = os.path.join(temp_dir, ".hidden")
            os.makedirs(models_dir)
            os.makedirs(agents_dir)
            os.makedirs(hidden_dir)

            # Create test YAML files
            # Root directory YAML
            with open(os.path.join(temp_dir, "config.yaml"), "w") as f:
                yaml.dump({"global": "settings", "defaults": "should_be_excluded"}, f)

            # Models directory YAMLs
            with open(os.path.join(models_dir, "gpt4.yaml"), "w") as f:
                yaml.dump({"model": "gpt-4", "defaults": {"temp": 0.7}}, f)

            with open(os.path.join(models_dir, "claude.yml"), "w") as f:
                yaml.dump({"model": "claude-3", "provider": "anthropic"}, f)

            # Agents directory YAMLs
            with open(os.path.join(agents_dir, "assistant.yaml"), "w") as f:
                yaml.dump({"agent": "assistant", "model": "gpt-4"}, f)

            # Hidden directory YAML (should be excluded by default)
            with open(os.path.join(hidden_dir, "hidden.yaml"), "w") as f:
                yaml.dump({"hidden": "config"}, f)

            # Non-YAML file (should be excluded)
            with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
                f.write("This is not a YAML file")

            yield temp_dir

        finally:
            # Clean up the temporary directory
            shutil.rmtree(temp_dir)

    def test_alist_basic_functionality(self, temp_dir_structure, monkeypatch):
        """Test that alist finds and categorizes YAML files correctly."""
        # Change working directory to the temp directory
        monkeypatch.chdir(temp_dir_structure)

        # Call alist with print_results=False to get the dictionary
        result = alist(print_results=False, verbose=False)

        # Check that we found the expected number of files
        assert len(result) == 4  # 3 visible YAML files + root config

        # Check specific files
        assert "config.yaml" in result
        assert "models/gpt4.yaml" in result
        assert "models/claude.yml" in result
        assert "agents/assistant.yaml" in result

        # Check that hidden files are excluded
        assert not any(".hidden" in key for key in result.keys())

        # Check that the keys are correct
        assert "global" in result["config.yaml"]
        assert "defaults" not in result["config.yaml"]  # Should be excluded
        assert "model" in result["models/gpt4.yaml"]
        assert "model" in result["models/claude.yml"]
        assert "provider" in result["models/claude.yml"]
        assert "agent" in result["agents/assistant.yaml"]

    def test_alist_key_filter(self, temp_dir_structure, monkeypatch):
        """Test that alist filters subdirectories by key correctly."""
        monkeypatch.chdir(temp_dir_structure)

        # Filter for "model" subdirectory
        result = alist(key="model", print_results=False)

        # Should only include files from the models directory
        assert len(result) == 2
        assert all("models/" in key for key in result.keys())

        # Check that we found the right files
        assert "models/gpt4.yaml" in result
        assert "models/claude.yml" in result

        # Filter for "agent" subdirectory
        result = alist(key="agent", print_results=False)

        # Should only include files from the agents directory
        assert len(result) == 1
        assert "agents/assistant.yaml" in result

    def test_alist_exclude_patterns(self, temp_dir_structure, monkeypatch):
        """Test that alist excludes files based on patterns."""
        monkeypatch.chdir(temp_dir_structure)

        # Exclude all files with "gpt" in the name
        result = alist(exclude_patterns=["*gpt*.yaml"], print_results=False)

        # Check that gpt4.yaml is excluded
        assert "models/gpt4.yaml" not in result

        # But other files are still included
        assert "models/claude.yml" in result
        assert "agents/assistant.yaml" in result

    def test_alist_include_hidden(self, temp_dir_structure, monkeypatch):
        """Test that alist can include hidden directories when asked."""
        monkeypatch.chdir(temp_dir_structure)

        # Include hidden directories
        result = alist(exclude_hidden=False, print_results=False)

        # Check that the hidden file is included
        assert any(".hidden" in key for key in result.keys())

        # Specifically check for the hidden.yaml file
        assert ".hidden/hidden.yaml" in result

    def test_alist_custom_base_path(self, temp_dir_structure):
        """Test that alist works with a custom base path."""
        # Use the temp directory as the base path without changing working directory
        result = alist(base_path=temp_dir_structure, print_results=False)

        # Check that we found the expected files
        assert len(result) == 4
        assert "config.yaml" in result
        assert "models/gpt4.yaml" in result

    def test_alist_exclude_keys(self, temp_dir_structure, monkeypatch):
        """Test that alist excludes specified top-level keys."""
        monkeypatch.chdir(temp_dir_structure)

        # Exclude both "defaults" and "model" keys
        result = alist(exclude_keys=["defaults", "model"], print_results=False)

        # Check that "model" is excluded from results
        assert "model" not in result["models/gpt4.yaml"]
        assert "model" not in result["models/claude.yml"]

        # But other keys should still be there
        assert "provider" in result["models/claude.yml"]
        assert "agent" in result["agents/assistant.yaml"]
