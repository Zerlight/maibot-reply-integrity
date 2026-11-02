import pytest

from plugin import create_plugin


@pytest.fixture
def plugin():
    instance = create_plugin()
    instance.set_plugin_config(instance.get_default_config())
    return instance
