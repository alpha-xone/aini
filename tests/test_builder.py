import os
import pytest
from unittest.mock import patch

# Import the functions to test
from aini.builder import (
    resolve_vars,
    build_from_config,
    track_used_variables
)


# Simple test classes to use in our tests
class SimpleClass:
    def __init__(self, name=None, value=None, **kwargs):
        self.name = name
        self.value = value
        # Store any extra kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def from_config(cls, **kwargs):
        """Custom initialization method for testing"""
        instance = cls()
        for k, v in kwargs.items():
            setattr(instance, k, v)
        return instance


class RecursiveClass:
    def __init__(self, child=None, **kwargs):
        self.child = child
        # Store any extra kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestResolveVars:
    """Test the variable resolution functionality."""

    def test_simple_string_resolution(self):
        """Test resolving simple string variables."""
        # Test with input variables
        template = "Hello ${name}!"
        variables = {"name": "World"}
        result = resolve_vars(template, variables, {})
        assert result == "Hello World!"

        # Test with default variables
        template = "Hello ${name}!"
        result = resolve_vars(template, {}, {"name": "Default"})
        assert result == "Hello Default!"

        # Test with environment variables
        with patch.dict(os.environ, {"NAME": "Environment"}):
            template = "Hello ${NAME}!"
            result = resolve_vars(template, {}, {})
            assert result == "Hello Environment!"

    def test_alternative_variables(self):
        """Test variable resolution with alternatives."""
        template = "Value: ${var1|var2|'default'}"

        # Test first alternative
        result = resolve_vars(template, {"var1": "first"}, {})
        assert result == "Value: first"

        # Test second alternative
        result = resolve_vars(template, {"var2": "second"}, {})
        assert result == "Value: second"

        # Test literal default
        result = resolve_vars(template, {}, {})
        assert result == "Value: default"

    def test_object_injection(self):
        """Test that object references are preserved when entire string is a variable."""
        obj = {"key": "value", "nested": [1, 2, 3]}
        template = "${object_var}"

        # When a string is just a variable reference, it injects the object directly
        result = resolve_vars(template, {"object_var": obj}, {})
        assert result is obj  # Same object reference
        assert result["key"] == "value"
        assert result["nested"] == [1, 2, 3]

    def test_numeric_and_boolean_literals(self):
        """Test handling of numeric and boolean literals."""
        # Integer literal
        assert resolve_vars("${var|42}", {}, {}) == 42

        # Float literal
        assert resolve_vars("${var|3.14}", {}, {}) == 3.14

        # Boolean literals
        assert resolve_vars("${var|true}", {}, {}) is True
        assert resolve_vars("${var|false}", {}, {}) is False

        # Embedded in string
        assert resolve_vars("Pi: ${pi|3.14}", {}, {}) == "Pi: 3.14"
        assert resolve_vars("Truth: ${truth|true}", {}, {}) == "Truth: True"

    def test_nested_structure_resolution(self):
        """Test resolving variables in nested structures."""
        template = {
            "name": "${user_name|'default_user'}",
            "config": {
                "api_key": "${api_key}",
                "settings": {
                    "timeout": "${timeout|30}",
                    "retry": "${retry|false}"
                }
            },
            "items": ["${item1}", "${item2|'default_item'}", "static"]
        }

        variables = {
            "user_name": "test_user",
            "api_key": "secret_key",
            "item1": "first_item"
        }

        expected = {
            "name": "test_user",
            "config": {
                "api_key": "secret_key",
                "settings": {
                    "timeout": 30,
                    "retry": False
                }
            },
            "items": ["first_item", "default_item", "static"]
        }

        result = resolve_vars(template, variables, {})
        assert result == expected


class TestBuildFromConfig:
    """Test the config building functionality."""

    def test_simple_class_instantiation(self):
        """Test building a simple class from config."""
        config = {
            "class": "SimpleClass",
            "params": {
                "name": "test_name",
                "value": "test_value"
            }
        }

        # Use a mock for import_class to avoid actual imports
        with patch("aini.builder.import_class", return_value=SimpleClass):
            result = build_from_config(config)

            assert isinstance(result, SimpleClass)
            assert result.name == "test_name"
            assert result.value == "test_value"

    def test_custom_init_method(self):
        """Test using a custom initialization method."""
        config = {
            "class": "SimpleClass",
            "init": "from_config",
            "params": {
                "name": "test_name",
                "custom_param": "custom_value"
            }
        }

        # Use a mock for import_class to avoid actual imports
        with patch("aini.builder.import_class", return_value=SimpleClass):
            result = build_from_config(config)

            assert isinstance(result, SimpleClass)
            assert result.name == "test_name"
            assert result.custom_param == "custom_value"

    def test_nested_class_instantiation(self):
        """Test building nested class structures."""
        config = {
            "class": "SimpleClass",
            "params": {
                "name": "parent",
                "value": {
                    "class": "SimpleClass",
                    "params": {
                        "name": "child",
                        "value": 42
                    }
                }
            }
        }

        # Use a mock for import_class to avoid actual imports
        with patch("aini.builder.import_class", return_value=SimpleClass):
            result = build_from_config(config)

            assert isinstance(result, SimpleClass)
            assert result.name == "parent"
            assert isinstance(result.value, SimpleClass)
            assert result.value.name == "child"
            assert result.value.value == 42

    def test_list_of_objects(self):
        """Test building a list of objects."""
        config = [
            {
                "class": "SimpleClass",
                "params": {"name": "item1"}
            },
            {
                "class": "SimpleClass",
                "params": {"name": "item2"}
            }
        ]

        # Use a mock for import_class to avoid actual imports
        with patch("aini.builder.import_class", return_value=SimpleClass):
            result = build_from_config(config)

            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(item, SimpleClass) for item in result)
            assert result[0].name == "item1"
            assert result[1].name == "item2"

    def test_dict_without_class(self):
        """Test building a dictionary without a class key."""
        config = {
            "key1": "value1",
            "key2": {
                "class": "SimpleClass",
                "params": {"name": "nested"}
            },
            "key3": ["item1", "item2"]
        }

        # Use a mock for import_class to avoid actual imports
        with patch("aini.builder.import_class", return_value=SimpleClass):
            result = build_from_config(config)

            assert isinstance(result, dict)
            assert result["key1"] == "value1"
            assert isinstance(result["key2"], SimpleClass)
            assert result["key2"].name == "nested"
            assert result["key3"] == ["item1", "item2"]


class TestTrackUsedVariables:
    """Test the tracking of used variables."""

    def test_simple_variable_tracking(self):
        """Test tracking of simple variables."""
        template = "Hello ${name}!"
        variables = {"name": "World", "unused": "value"}

        used_vars = track_used_variables(template, variables)
        assert "name" in used_vars
        assert "unused" not in used_vars

    def test_nested_variable_tracking(self):
        """Test tracking variables in nested structures."""
        template = {
            "name": "${user}",
            "config": {
                "setting1": "${setting1}",
                "setting2": "static"
            },
            "items": ["${item1}", "static", "${item2}"]
        }

        variables = {
            "user": "test",
            "setting1": "value1",
            "item1": "first",
            "item2": "second",
            "unused": "not_used"
        }

        used_vars = track_used_variables(template, variables)
        assert "user" in used_vars
        assert "setting1" in used_vars
        assert "item1" in used_vars
        assert "item2" in used_vars
        assert "unused" not in used_vars

    def test_alternative_variable_tracking(self):
        """Test tracking of variables in alternatives."""
        template = "${var1|var2|var3|'default'}"
        variables = {
            "var1": "value1",
            "var2": "value2",
            "var3": "value3",
            "unused": "not_used"
        }

        used_vars = track_used_variables(template, variables)
        assert "var1" in used_vars
        assert "var2" in used_vars
        assert "var3" in used_vars
        assert "unused" not in used_vars

    def test_literals_not_tracked(self):
        """Test that literals are not tracked as variables."""
        template = "${var1|'literal'|42|true}"
        variables = {"var1": "value1", "literal": "value2", "42": "value3", "true": "value4"}

        used_vars = track_used_variables(template, variables)
        assert "var1" in used_vars
        assert "literal" not in used_vars
        assert "42" not in used_vars
        assert "true" not in used_vars


# Example configurations based on your YAML files

def test_langchain_message_example():
    """Test example configuration based on LangChain message format."""
    # This mimics a structure like what might be in lang/msg.yml
    config = {
        "invoke": {
            "messages": [
                {
                    "class": "SimpleClass",  # Stand-in for HumanMessage
                    "params": {
                        "content": "${query}",
                        "config": {
                            "configurable": {
                                "thread_id": "${thread_id}"
                            }
                        }
                    }
                }
            ]
        }
    }

    variables = {
        "query": "What is the meaning of life?",
        "thread_id": "conversation_123",
        "unused": "should_not_be_used"
    }

    # Track which variables are used
    used_vars = track_used_variables(config, variables)
    assert "query" in used_vars
    assert "thread_id" in used_vars
    assert "unused" not in used_vars

    # Resolve variables
    resolved = resolve_vars(config, variables, {})

    # Check that the variables were properly resolved
    message_config = resolved["invoke"]["messages"][0]
    assert message_config["params"]["content"] == "What is the meaning of life?"
    assert message_config["params"]["config"]["configurable"]["thread_id"] == "conversation_123"

    # Build from config (with mocked import)
    with patch("aini.builder.import_class", return_value=SimpleClass):
        built = build_from_config(resolved)

        assert isinstance(built, dict)
        assert "invoke" in built
        assert isinstance(built["invoke"], dict)
        assert "messages" in built["invoke"]
        assert isinstance(built["invoke"]["messages"], list)
        assert isinstance(built["invoke"]["messages"][0], SimpleClass)
        assert built["invoke"]["messages"][0].content == "What is the meaning of life?"
        assert built["invoke"]["messages"][0].config["configurable"]["thread_id"] == "conversation_123"


def test_autogen_agent_example():
    """Test example configuration based on AutoGen agent format."""
    # This mimics a structure like what might be in autogen/assistant.yml
    config = {
        "assistant": {
            "class": "SimpleClass",  # Stand-in for AssistantAgent
            "params": {
                "name": "assistant",
                "system_message": "${system_prompt|'You are a helpful AI assistant.'}",
                "llm_config": {
                    "config_list": "${config_list}",
                    "temperature": "${temperature|0.7}"
                }
            }
        }
    }

    variables = {
        "system_prompt": "You are an expert programmer.",
        "config_list": [{"model": "gpt-4"}, {"model": "gpt-3.5-turbo"}],
        "temperature": 0.5
    }

    # Track which variables are used
    used_vars = track_used_variables(config, variables)
    assert "system_prompt" in used_vars
    assert "config_list" in used_vars
    assert "temperature" in used_vars

    # Resolve variables
    resolved = resolve_vars(config, variables, {})

    # Check that the variables were properly resolved
    agent_config = resolved["assistant"]
    assert agent_config["params"]["system_message"] == "You are an expert programmer."
    assert agent_config["params"]["llm_config"]["config_list"] == [
        {"model": "gpt-4"}, {"model": "gpt-3.5-turbo"}
    ]
    assert agent_config["params"]["llm_config"]["temperature"] == 0.5

    # Build from config (with mocked import)
    with patch("aini.builder.import_class", return_value=SimpleClass):
        built = build_from_config(resolved)

        assert isinstance(built, dict)
        assert "assistant" in built
        assert isinstance(built["assistant"], SimpleClass)
        assert built["assistant"].name == "assistant"
        assert built["assistant"].system_message == "You are an expert programmer."
        assert built["assistant"].llm_config["temperature"] == 0.5


if __name__ == "__main__":
    # Run the tests directly if this file is executed
    pytest.main(["-v", __file__])
