from pytest import fixture


@fixture(scope="module")
def vcr_config():
    return {"filter_query_parameters": ["api_key"]}


@fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
