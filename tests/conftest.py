from pytest import fixture


@fixture(scope="module")
def vcr_config():
    return {"filter_query_parameters": ["api_key"]}
