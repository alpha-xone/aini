import os
import tempfile
import pytest
from pathlib import Path
import yaml
import json
from unittest.mock import patch

# Import builder functions - make sure these paths match your actual module structure
from aini.builder import resolve_vars, build_from_config


class SimpleClass:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    @classmethod
    def from_dict(cls, name, config=None):
        """Alternative initialization method for testing 'init' functionality"""
        instance = cls(name)
        if config:
            instance.config = config
        return instance


# Test resolve_vars function
class TestResolveVars:
    def test_basic_variable_resolution(self):
        # Test simple variable substitution
        template = "${var1}"
        input_vars = {"var1": "value1"}
        result = resolve_vars(template, input_vars, {})
        assert result == "value1"

    def test_nested_variable_resolution(self):
        # Test variables in nested structures
        template = {"key1": "${var1}", "key2": ["${var2}", {"nested": "${var3}"}]}
        input_vars = {"var1": "value1", "var2": "value2", "var3": "value3"}
        result = resolve_vars(template, input_vars, {})
        assert result == {"key1": "value1", "key2": ["value2", {"nested": "value3"}]}

    def test_alternative_variables(self):
        # Test OR syntax with pipe operator
        template = "${var1|var2|'default'}"

        # First variable exists
        result1 = resolve_vars(template, {"var1": "value1", "var2": "value2"}, {})
        assert result1 == "value1"

        # Second variable exists, first doesn't
        result2 = resolve_vars(template, {"var2": "value2"}, {})
        assert result2 == "value2"

        # No variables exist, use default
        result3 = resolve_vars(template, {}, {})
        assert result3 == "default"

    def test_environment_variables(self):
        # Test environment variable substitution
        with patch.dict(os.environ, {"ENV_VAR": "env_value"}):
            template = "${ENV_VAR}"
            result = resolve_vars(template, {}, {})
            assert result == "env_value"

    def test_default_variables(self):
        # Test default variables
        template = "${var1}"
        default_vars = {"var1": "default_value"}
        result = resolve_vars(template, {}, default_vars)
        assert result == "default_value"

        # Input variables override defaults
        result2 = resolve_vars(template, {"var1": "input_value"}, default_vars)
        assert result2 == "input_value"

    def test_boolean_values(self):
        # Test boolean value conversion
        template1 = "${var1|true}"
        template2 = "${var2|false}"

        # From literal
        result1 = resolve_vars(template1, {}, {})
        assert result1 is True

        result2 = resolve_vars(template2, {}, {})
        assert result2 is False

        # From environment variable
        with patch.dict(os.environ, {"BOOL_TRUE": "true", "BOOL_FALSE": "false"}):
            result3 = resolve_vars("${BOOL_TRUE}", {}, {})
            assert result3 is True

            result4 = resolve_vars("${BOOL_FALSE}", {}, {})
            assert result4 is False

    def test_numeric_values(self):
        # Test numeric value conversion
        template1 = "${var1|42}"
        template2 = "${var2|3.14}"

        result1 = resolve_vars(template1, {}, {})
        assert result1 == 42
        assert isinstance(result1, int)

        result2 = resolve_vars(template2, {}, {})
        assert result2 == 3.14
        assert isinstance(result2, float)

    def test_embedded_variables(self):
        # Test variables embedded in strings
        template = "prefix-${var1}-middle-${var2}-suffix"
        input_vars = {"var1": "value1", "var2": "value2"}
        result = resolve_vars(template, input_vars, {})
        assert result == "prefix-value1-middle-value2-suffix"


# Test build_from_config function
class TestBuildFromConfig:
    def test_basic_class_instantiation(self):
        # Test basic class instantiation
        config = {
            "class": "test_builder.SimpleClass",
            "params": {
                "name": "test_instance",
                "value": 42
            }
        }
        result = build_from_config(config)
        assert isinstance(result, SimpleClass)
        assert result.name == "test_instance"
        assert result.value == 42

    def test_custom_init_method(self):
        # Test using a custom initialization method
        config = {
            "class": "test_builder.SimpleClass",
            "init": "from_dict",
            "params": {
                "name": "test_instance",
                "config": {"setting": "value"}
            }
        }
        result = build_from_config(config)
        assert isinstance(result, SimpleClass)
        assert result.name == "test_instance"
        assert result.config == {"setting": "value"}

    def test_recursive_config_building(self):
        # Test nested configuration objects
        config = {
            "class": "test_builder.SimpleClass",
            "params": {
                "name": "parent",
                "value": {
                    "class": "test_builder.SimpleClass",
                    "params": {
                        "name": "child"
                    }
                }
            }
        }
        result = build_from_config(config)
        assert isinstance(result, SimpleClass)
        assert isinstance(result.value, SimpleClass)
        assert result.name == "parent"
        assert result.value.name == "child"

    def test_list_handling(self):
        # Test list handling
        config = [
            {
                "class": "test_builder.SimpleClass",
                "params": {"name": "item1"}
            },
            {
                "class": "test_builder.SimpleClass",
                "params": {"name": "item2"}
            }
        ]
        result = build_from_config(config)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, SimpleClass) for item in result)
        assert result[0].name == "item1"
        assert result[1].name == "item2"


# Test aini function
class TestAini:
    @pytest.fixture(scope="function")
    def temp_yaml_file(request):  # Use request parameter for pytest fixture
        # Create a temporary YAML file for testing
        config = {
            "defaults": {
                "default_val": "default_value"
            },
            "test_instance": {
                "class": "tests.test_builder.SimpleClass",
                "params": {
                    "name": "${name|'default_name'}",
                    "value": "${value|default_val}"
                }
            },
            "another_instance": {
                "class": "tests.test_builder.SimpleClass",
                "params": {
                    "name": "fixed_name"
                }
            }
        }

        with tempfile.NamedTemporaryFile(suffix='.yml', delete=False, mode='w', encoding='utf-8') as tmp:
            yaml.dump(config, tmp)
            tmp_path = tmp.name

        # Return the path to the file
        yield tmp_path

        # Clean up
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    @pytest.fixture(scope="function")
    def temp_json_file(request):  # Use request parameter for pytest fixture
        # Create a temporary JSON file for testing
        config = {
            "defaults": {
                "default_val": "default_value"
            },
            "test_instance": {
                "class": "tests.test_builder.SimpleClass",
                "params": {
                    "name": "${name|'default_name'}",
                    "value": "${value|default_val}"
                }
            }
        }

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w', encoding='utf-8') as tmp:
            json.dump(config, tmp)
            tmp_path = tmp.name

        # Return the path to the file
        yield tmp_path

        # Clean up
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    def teardown_method(self, method):
        # Clean up temporary files after tests
        for fixture_name in ["temp_yaml_file", "temp_json_file"]:
            fixture_value = getattr(self, fixture_name, None)
            if fixture_value and Path(fixture_value).exists():
                Path(fixture_value).unlink()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
