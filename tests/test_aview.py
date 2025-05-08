from aini.viewer import get_methods, filter_instance_dict


class SampleClass:
    def __init__(self):
        self.attribute = "value"

    def method1(self):
        pass

    def method2(self):
        pass

    def _private_method(self):
        pass


def test_get_methods():
    sample = SampleClass()
    methods = get_methods(sample)
    assert 'method1' in methods
    assert 'method2' in methods
    assert '_private_method' not in methods


def test_filter_instance_dict():
    sample = SampleClass()
    filtered = filter_instance_dict(sample)
    assert 'attribute' in filtered
    assert filtered['attribute'] == 'value'
