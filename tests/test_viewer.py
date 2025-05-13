import os
import json
import yaml
import pytest
from datetime import datetime
import tempfile

from aini.viewer import is_empty, filter_instance_dict, aview, custom_serializer, ameth


class SimpleClass:
    def __init__(self, name="test", value=None):
        self.name = name
        self.value = value
        self._private = "private_value"
        self.__double_private = "super_private"
        self.empty_list = []
        self.empty_dict = {}
        self.zero = 0
        self.empty_str = ""

    def method(self):
        return self.name

    def another_method(self):
        pass


class ComplexClass:
    def __init__(self):
        self.nested = SimpleClass()
        self.list_of_objects = [SimpleClass("obj1"), SimpleClass("obj2")]
        self.dict_of_objects = {
            "key1": SimpleClass("dict_obj1"),
            "key2": SimpleClass("dict_obj2")
        }
        self.bytes_data = b"Hello World"
        self.date = datetime.now()
        self._private_nested = {
            "_level1": {
                "_level2": {
                    "_level3": "deep_value"
                }
            }
        }

    def __eq__(self, other):
        # Intentionally broken comparison for testing
        raise ValueError("Comparison not allowed")


class BrokenClass:
    def __init__(self):
        self.normal_attr = "ok"

    @property
    def __dict__(self):
        # Return a callable that returns a dictionary
        return lambda: {"dynamic": "content"}


class RecursiveClass:
    def __init__(self):
        self.name = "recursive"
        self._child = None

    def create_recursive(self):
        # Create a recursive reference
        child = RecursiveClass()
        self._child = child
        child._parent = self
        return self


# Tests for afunc function
class TestAfunc:
    def test_list_methods(self):
        obj = SimpleClass()
        methods = ameth(obj)
        assert "method" in methods
        assert "another_method" in methods
        assert "__init__" not in methods  # Should exclude private methods

    def test_empty_methods(self):
        # Test with an object that has no methods
        class EmptyClass:
            x = 1

        obj = EmptyClass()
        methods = ameth(obj)
        assert methods == []


# Tests for is_empty function
class TestIsEmpty:
    def test_none_is_empty(self):
        assert is_empty(None) is True

    def test_zero_is_empty(self):
        assert is_empty(0) is True
        assert is_empty(0.0) is True

    def test_empty_string_is_empty(self):
        assert is_empty("") is True

    def test_empty_collections_are_empty(self):
        assert is_empty([]) is True
        assert is_empty({}) is True
        assert is_empty(set()) is True
        assert is_empty(()) is True

    def test_non_empty_values(self):
        assert is_empty(1) is False
        assert is_empty("text") is False
        assert is_empty([1, 2, 3]) is False
        assert is_empty({"key": "value"}) is False

    def test_custom_objects(self):
        obj = SimpleClass()
        assert is_empty(obj) is False

    def test_broken_comparison(self):
        # Test with an object that raises an exception during comparison
        obj = ComplexClass()
        assert is_empty(obj) is False  # Should handle exception and return False


# Tests for filter_instance_dict function
class TestFilterInstanceDict:
    def test_basic_types(self):
        assert filter_instance_dict(None) is None
        assert filter_instance_dict(42) == 42
        assert filter_instance_dict("text") == "text"
        assert filter_instance_dict(True) is True

    def test_empty_collections_filtered_out(self):
        assert filter_instance_dict([]) is None
        assert filter_instance_dict({}) is None

    def test_non_empty_collections(self):
        assert filter_instance_dict([1, 2, 3]) == [1, 2, 3]
        assert filter_instance_dict({"key": "value"}) == {"key": "value"}

    def test_nested_collections(self):
        data = {
            "level1": {
                "level2": [1, 2, {"level3": "value"}]
            }
        }
        filtered = filter_instance_dict(data)
        assert filtered["level1"]["level2"][2]["level3"] == "value"

    def test_class_instance(self):
        obj = SimpleClass("test_name", "test_value")
        filtered = filter_instance_dict(obj)
        assert filtered["name"] == "test_name"
        assert filtered["value"] == "test_value"
        # Private attributes should be excluded
        assert "_private" not in filtered
        assert "__double_private" not in filtered

    def test_include_private(self):
        obj = SimpleClass()
        filtered = filter_instance_dict(obj, inc_=True)
        # Single underscore private should be included
        assert "_private" in filtered
        # Double underscore private should still be excluded
        assert "__double_private" not in filtered

    def test_exclude_keys(self):
        obj = SimpleClass("test_name", "test_value")
        filtered = filter_instance_dict(obj, exc_keys=["name"])
        assert "name" not in filtered
        assert "value" in filtered

    def test_api_key_filtering(self):
        data = {
            "api_key": "secret",
            "openai_api_key": "secret",
            "normal_key": "visible"
        }
        filtered = filter_instance_dict(data)
        assert "api_key" not in filtered
        assert "openai_api_key" not in filtered
        assert "normal_key" in filtered

    def test_complex_object(self):
        obj = ComplexClass()
        filtered = filter_instance_dict(obj)
        # Check nested objects
        assert "nested <test_viewer.SimpleClass>" in filtered
        assert filtered["nested <test_viewer.SimpleClass>"]["name"] == "test"
        # Check lists of objects
        assert len(filtered["list_of_objects"]) == 2
        assert filtered["list_of_objects"][0]["name"] == "obj1"
        # Check bytes conversion
        assert isinstance(filtered["bytes_data"], str)
        assert "Hello World" in filtered["bytes_data"]

    def test_callable_dict(self):
        obj = BrokenClass()
        filtered = filter_instance_dict(obj)
        assert "dynamic" in filtered
        assert filtered["dynamic"] == "content"

    def test_empty_filtering(self):
        obj = SimpleClass()
        filtered = filter_instance_dict(obj)
        # These should be filtered out as they're empty
        assert "empty_list" not in filtered
        assert "empty_dict" not in filtered
        assert "zero" not in filtered
        assert "empty_str" not in filtered

    def test_depth_limiting(self):
        obj = ComplexClass()
        # Test with depth limiting on private attributes
        filtered = filter_instance_dict(obj, inc_=True, max_depth_=2)
        # Should include private attributes but stop at level 2
        assert "_private_nested" in filtered
        assert "_level1" in filtered["_private_nested"]
        # todo: test more levels

    def test_recursive_structure(self):
        # Test handling of recursive structures
        obj = RecursiveClass().create_recursive()
        filtered = filter_instance_dict(obj, inc_=True)
        # Should handle the recursion without infinite loop
        assert filtered["name"] == "recursive"
        assert "_child <test_viewer.RecursiveClass>" in filtered
        # The recursive parent reference should be handled via max depth
        assert "_parent <test_viewer.RecursiveClass>" in filtered["_child <test_viewer.RecursiveClass>"]
        # Should truncate the recursion at some point
        assert isinstance(filtered["_child <test_viewer.RecursiveClass>"]["_parent <test_viewer.RecursiveClass>"], str)


# Tests for bytes handling
class TestBytesHandling:
    def test_bytes_in_dict(self):
        data = {
            "text": b"Hello World",
            "binary": b"\x00\x01\x02\x03\xff"
        }
        filtered = filter_instance_dict(data)
        assert filtered["text"] == "Hello World"
        assert isinstance(filtered["binary"], str)

    def test_bytes_in_custom_serializer(self):
        # Test bytes handling in custom_serializer
        assert custom_serializer(b"Hello") == "Hello"
        binary = b"\x00\x01\x02\x03\xff"
        # Should still return a string representation for non-UTF8 bytes
        assert isinstance(custom_serializer(binary), str)


# Tests for aview function
class TestAview:
    @pytest.fixture
    def temp_json_file(self):
        """Create a temporary JSON file for testing."""
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp_path = tmp.name
        tmp.close()  # Close the file immediately

        # Return the path and ensure it gets cleaned up after the test
        yield tmp_path

        # Clean up after test
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    @pytest.fixture
    def temp_yaml_file(self):
        """Create a temporary YAML file for testing."""
        tmp = tempfile.NamedTemporaryFile(suffix='.yml', delete=False)
        tmp_path = tmp.name
        tmp.close()  # Close the file immediately

        # Return the path and ensure it gets cleaned up after the test
        yield tmp_path

        # Clean up after test
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    def test_aview_console_output(self, capsys):
        obj = SimpleClass("console_test")
        aview(obj)
        captured = capsys.readouterr()
        # Check that the output contains the class name and attribute
        assert "SimpleClass" in captured.out
        assert "console_test" in captured.out

    def test_aview_json_file_output(self, temp_json_file):
        obj = SimpleClass("json_test")
        aview(obj, to_file=temp_json_file)

        # Verify the file was created and contains expected content
        assert os.path.exists(temp_json_file)
        with open(temp_json_file, 'r') as f:
            data = json.load(f)
        assert data["name"] == "json_test"

    def test_aview_yaml_file_output(self, temp_yaml_file):
        obj = SimpleClass("yaml_test")
        aview(obj, to_file=temp_yaml_file)

        # Verify the file was created and contains expected content
        assert os.path.exists(temp_yaml_file)
        with open(temp_yaml_file, 'r') as f:
            content = f.read()
            # Check for the title comment
            assert "SimpleClass" in content
            data = yaml.safe_load(content.split('\n', 1)[1])  # Skip first line (title)
        assert data["name"] == "yaml_test"

    def test_aview_invalid_file_format(self):
        obj = SimpleClass()
        with pytest.raises(ValueError, match="Unsupported file format"):
            aview(obj, to_file="output.txt")

    def test_aview_nondict_object(self):
        # Test with an object that doesn't have __dict__
        with pytest.raises(ValueError, match="not a class instance or a dictionary."):
            aview(42)

    def test_aview_with_exclusions(self, temp_json_file):
        obj = ComplexClass()
        aview(obj, to_file=temp_json_file, exc_keys=["nested"])

        with open(temp_json_file, 'r') as f:
            data = json.load(f)
        assert "nested" not in data
        assert "list_of_objects" in data

    def test_aview_with_private(self, temp_json_file):
        obj = SimpleClass()
        aview(obj, to_file=temp_json_file, inc_=True)

        with open(temp_json_file, 'r') as f:
            data = json.load(f)
        assert "_private" in data
        assert "__double_private" not in data  # Should still be excluded

    def test_aview_with_custom_depth(self, temp_json_file):
        obj = ComplexClass()
        # Test with a custom max_depth
        aview(obj, to_file=temp_json_file, inc_=True, max_depth_=1)

        with open(temp_json_file, 'r') as f:
            data = json.load(f)
        # Private nested structure should be truncated earlier
        assert "_private_nested" in data
        assert isinstance(data["_private_nested"], str)
        assert "max depth reached" in data["_private_nested"]


# Tests for custom_serializer function
class TestCustomSerializer:
    def test_datetime_serialization(self):
        now = datetime.now()
        serialized = custom_serializer(now)
        assert isinstance(serialized, str)
        assert serialized == now.isoformat()

    def test_bytes_serialization(self):
        bytes_data = b"Test bytes data"
        serialized = custom_serializer(bytes_data)
        assert isinstance(serialized, str)
        assert "Test bytes data" in serialized

        # Test binary data
        binary_bytes = b"\x00\x01\x02\x03\xff"
        serialized = custom_serializer(binary_bytes)
        assert isinstance(serialized, str)

    def test_object_serialization(self):
        obj = SimpleClass()
        serialized = custom_serializer(obj)
        assert isinstance(serialized, str)
        # Should include the class name in string representation
        assert "SimpleClass" in serialized


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
