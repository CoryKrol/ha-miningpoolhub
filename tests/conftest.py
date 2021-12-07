from pytest import fixture


@fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
