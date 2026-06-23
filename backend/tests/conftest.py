import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the cache (and thus DRF throttle history) around every test."""
    cache.clear()
    yield
    cache.clear()
