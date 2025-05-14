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
    def __init__(self, name=None, value=None):
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

    def test_quoted_literals(self):
        # Test quoted string literals
        template1 = '${var1|"quoted value"}'
        template2 = "${var2|'single quoted'}"

        # When variable doesn't exist, use the quoted value
        result1 = resolve_vars(template1, {}, {})
        assert result1 == "quoted value"

        result2 = resolve_vars(template2, {}, {})
        assert result2 == "single quoted"

        # When variable exists, use it instead
        result3 = resolve_vars(template1, {"var1": "actual value"}, {})
        assert result3 == "actual value"

    def test_special_cases(self):
        # Test edge cases and special patterns

        # Empty string
        result = resolve_vars("", {}, {})
        assert result == ""

        # String with only variable that resolves to None
        result = resolve_vars("${nonexistent}", {}, {})
        assert result is None

        # Multiple variables in one string where some don't exist
        result = resolve_vars(
            "${var1}-${nonexistent}-${var2}",
            {"var1": "exists", "var2": "also exists"},
            {}
        )
        assert result == "exists-None-also exists"

        # Object in variable
        obj = {"key": "value"}
        result = resolve_vars("${obj}", {"obj": obj}, {})
        assert result == obj  # Should preserve the object reference

    def test_nested_complex_structures(self):
        # Test complex nested structures with variables
        template = {
            "list_with_vars": [
                "${var1}",
                {"nested": "${var2}", "deeper": {"evenDeeper": "${var3}"}}
            ],
            "dict_with_list": {
                "items": ["${var4}", "${var5|var6|'default'}"]
            }
        }

        variables = {
            "var1": "first",
            "var2": "second",
            "var3": "third",
            "var5": "fifth"
        }

        expected = {
            "list_with_vars": [
                "first",
                {"nested": "second", "deeper": {"evenDeeper": "third"}}
            ],
            "dict_with_list": {
                "items": [None, "fifth"]
            }
        }

        result = resolve_vars(template, variables, {})
        assert result == expected

    def test_type_preservation(self):
        # Test that the correct types are preserved
        variables = {
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "list_val": [1, 2, 3],
            "dict_val": {"key": "value"}
        }

        # Test each type in isolation (when it's the whole string)
        int_result = resolve_vars("${int_val}", variables, {})
        assert int_result == 42
        assert isinstance(int_result, int)

        float_result = resolve_vars("${float_val}", variables, {})
        assert float_result == 3.14
        assert isinstance(float_result, float)

        bool_result = resolve_vars("${bool_val}", variables, {})
        assert bool_result is True
        assert isinstance(bool_result, bool)

        list_result = resolve_vars("${list_val}", variables, {})
        assert list_result == [1, 2, 3]
        assert isinstance(list_result, list)

        dict_result = resolve_vars("${dict_val}", variables, {})
        assert dict_result == {"key": "value"}
        assert isinstance(dict_result, dict)

        # Test embedded in string (converts to string)
        embedded_int = resolve_vars("Value: ${int_val}", variables, {})
        assert embedded_int == "Value: 42"
        assert isinstance(embedded_int, str)


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

    def test_non_class_configs(self):
        # Test configs that don't include 'class' key

        # Plain dictionary
        config = {"key": "value", "number": 42}
        result = build_from_config(config)
        assert result == config

        # Nested structure without 'class'
        config = {
            "outer": {
                "inner": {
                    "value": 123
                }
            }
        }
        result = build_from_config(config)
        assert result == config

    def test_empty_params(self):
        # Test with empty params dictionary
        config = {
            "class": "test_builder.SimpleClass",
            "params": {}
        }
        result = build_from_config(config)
        assert isinstance(result, SimpleClass)
        assert result.name is None
        assert result.value is None

        # Test with no params key at all
        config = {
            "class": "test_builder.SimpleClass"
        }
        result = build_from_config(config)
        assert isinstance(result, SimpleClass)
        assert result.name is None
        assert result.value is None

    def test_mixed_list_contents(self):
        # Test list with mixed content types
        config = [
            {
                "class": "test_builder.SimpleClass",
                "params": {"name": "instance"}
            },
            "literal string",
            42,
            {"key": "value"}  # Dict without 'class'
        ]
        result = build_from_config(config)
        assert isinstance(result, list)
        assert len(result) == 4
        assert isinstance(result[0], SimpleClass)
        assert result[0].name == "instance"
        assert result[1] == "literal string"
        assert result[2] == 42
        assert result[3] == {"key": "value"}


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


# Add these tests for ImportClass function

class TestImportClass:
    def test_import_standard_library(self):
        from aini.builder import import_class

        # Import from standard library
        datetime_class = import_class("datetime.datetime")
        assert datetime_class.__name__ == "datetime"

        # Test instantiation
        now = datetime_class.now()
        assert hasattr(now, "year")

    def test_import_errors(self):
        from aini.builder import import_class

        # Test missing dot in class path
        with pytest.raises(ValueError, match="Invalid class path"):
            import_class("InvalidClassPath")

        # Test relative import without base module
        with pytest.raises(ValueError, match="Relative class path requires base_module"):
            import_class(".SimpleClass")

        # Test nonexistent module
        with pytest.raises(ModuleNotFoundError):
            import_class("nonexistent.module.Class")


# Add these tests for ResolveVarMatch function

class TestResolveVarMatch:
    def test_variable_resolution_order(self):
        from aini.builder import resolve_var_match

        # Create a mock match object
        class MockMatch:
            def __init__(self, var_expr, is_full=True):
                self.var_expr = var_expr
                self.is_full = is_full

            def group(self, idx):
                if idx == 0:
                    return f"${{{self.var_expr}}}"
                elif idx == 1:
                    return self.var_expr

            @property
            def string(self):
                if self.is_full:
                    return f"${{{self.var_expr}}}"
                else:
                    return f"prefix-${{{self.var_expr}}}-suffix"

        # Test priority: input_vars > os.environ > default_vars > None

        # Set up test variables
        input_vars = {"input_var": "input_value"}
        env_var_name = "TEST_ENV_VAR"
        default_vars = {"default_var": "default_value", env_var_name: "should_not_use_this"}

        # Try input var
        match = MockMatch("input_var")
        result = resolve_var_match(match, input_vars, default_vars)
        assert result == "input_value"

        # Try environment variable
        with patch.dict(os.environ, {env_var_name: "env_value"}):
            match = MockMatch(env_var_name)
            result = resolve_var_match(match, input_vars, default_vars)
            assert result == "env_value"

        # Try default var
        match = MockMatch("default_var")
        result = resolve_var_match(match, input_vars, default_vars)
        assert result == "default_value"

        # Try nonexistent var
        match = MockMatch("nonexistent_var")
        result = resolve_var_match(match, input_vars, default_vars)
        assert result is None

    def test_alternative_resolution(self):
        from aini.builder import resolve_var_match

        # Mock match for testing
        class MockMatch:
            def __init__(self, var_expr, is_full=True):
                self.var_expr = var_expr
                self.is_full = is_full

            def group(self, idx):
                if idx == 0:
                    return f"${{{self.var_expr}}}"
                elif idx == 1:
                    return self.var_expr

            @property
            def string(self):
                if self.is_full:
                    return f"${{{self.var_expr}}}"
                else:
                    return f"prefix-${{{self.var_expr}}}-suffix"

        # Test alternatives with | operator

        # First alternative exists
        match = MockMatch("var1|var2|var3")
        result = resolve_var_match(match, {"var1": "first"}, {})
        assert result == "first"

        # Second alternative exists
        match = MockMatch("var1|var2|var3")
        result = resolve_var_match(match, {"var2": "second"}, {})
        assert result == "second"

        # Third alternative in default_vars
        match = MockMatch("var1|var2|var3")
        result = resolve_var_match(match, {}, {"var3": "third"})
        assert result == "third"

        # No alternatives exist
        match = MockMatch("var1|var2|var3")
        result = resolve_var_match(match, {}, {})
        assert result is None

        # With quoted literal fallback
        match = MockMatch('var1|var2|"literal value"')
        result = resolve_var_match(match, {}, {})
        assert result == "literal value"


# Add tests for edge cases and special behaviors in builder.py
def test_build_from_config_edge_cases():
    # Test edge cases for build_from_config

    # None input
    result = build_from_config(None)
    assert result is None

    # Empty list
    result = build_from_config([])
    assert result == []

    # Empty dict
    result = build_from_config({})
    assert result == {}

    # Dict with class key but missing module
    config = {
        "class": "nonexistent.ClassThatDoesntExist",
        "params": {"name": "should fail"}
    }

    with pytest.raises(ModuleNotFoundError):
        build_from_config(config)


def test_nested_class_in_non_class_dict():
    """Test that classes nested in dictionaries without a class key are still instantiated."""
    # Create a config that mimics the structure in the LangChain example
    config = {
        "invoke": {  # No class key at this level
            "messages": [
                {
                    "class": "test_builder.SimpleClass",
                    "params": {
                        "name": "nested_instance",
                        "value": {
                            "configurable": {
                                "thread_id": "example_thread_id"
                            }
                        }
                    }
                }
            ]
        }
    }

    # Build from the config
    result = build_from_config(config)

    # Check the structure is preserved
    assert "invoke" in result
    assert "messages" in result["invoke"]
    assert isinstance(result["invoke"]["messages"], list)
    assert len(result["invoke"]["messages"]) == 1

    # Check that the nested class was instantiated
    assert isinstance(result["invoke"]["messages"][0], SimpleClass)
    assert result["invoke"]["messages"][0].name == "nested_instance"
    assert result["invoke"]["messages"][0].value["configurable"]["thread_id"] == "example_thread_id"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
