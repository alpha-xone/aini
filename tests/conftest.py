import pytest

@pytest.fixture(autouse=True)
def run_around_tests():
    yield
    # Cleanup code can be added here if necessary