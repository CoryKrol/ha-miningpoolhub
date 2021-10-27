"""Tests for the config flow."""
import os
from dotenv import load_dotenv
from unittest import mock
from unittest.mock import AsyncMock

from miningpoolhub_py.exceptions import NotFoundError
from homeassistant.const import CONF_API_KEY, CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import patch
from custom_components.miningpoolhub import config_flow
from custom_components.miningpoolhub.const import CONF_CURRENCY_NAMES

load_dotenv()
API_KEY = os.environ.get("MPH_API_KEY", None)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_validate_coin_valid(hass):
    """Test no exception is raised for a valid coin."""
    await config_flow.validate_coin("ethereum", API_KEY, hass)


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_validate_coin_invalid(m_miningpoolhubapi, hass):
    """Test a ValueError is raised when the coin is not valid."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock(side_effect=NotFoundError(AsyncMock()))
    m_miningpoolhubapi.return_value = m_instance
    for bad_path in ("dollarcoin", "bitdollar"):
        with pytest.raises(ValueError):
            await config_flow.validate_coin(bad_path, API_KEY, hass)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_validate_auth_valid(hass):
    """Test no exception is raised for valid API key."""
    await config_flow.validate_auth(API_KEY, hass)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_validate_auth_invalid(hass):
    """Test ValueError is raised when API key is invalid."""
    with pytest.raises(ValueError):
        await config_flow.validate_auth("token", hass)


async def test_flow_user_init(hass):
    """Test the initialization of the form in the first step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    expected = {
        "data_schema": config_flow.AUTH_SCHEMA,
        "description_placeholders": None,
        "errors": {},
        "flow_id": mock.ANY,
        "last_step": None,
        "handler": "miningpoolhub",
        "step_id": "user",
        "type": "form",
    }
    assert expected == result


@patch("custom_components.miningpoolhub.config_flow.validate_auth")
async def test_flow_user_init_invalid_api_key(m_validate_auth, hass):
    """Test errors populated when API key is invalid."""
    m_validate_auth.side_effect = ValueError
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_API_KEY: "bad"}
    )
    assert {"base": "auth"} == result["errors"]


@patch("custom_components.miningpoolhub.config_flow.validate_auth")
async def test_flow_user_init_data_valid(m_validate_auth, hass):
    """Test we advance to the next step when data is valid."""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_API_KEY: "good"}
    )
    assert "coin" == result["step_id"]
    assert "form" == result["type"]


async def test_flow_coin_init_form(hass):
    """Test the initialization of the form in the second step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "coin"}
    )
    expected = {
        "data_schema": config_flow.CURRENCY_NAME_SCHEMA,
        "description_placeholders": None,
        "errors": {},
        "flow_id": mock.ANY,
        "handler": "miningpoolhub",
        "last_step": None,
        "step_id": "coin",
        "type": "form",
    }
    assert expected == result


@patch("custom_components.miningpoolhub.config_flow.validate_coin")
async def test_flow_coin_path_invalid(m_validate_coin, hass):
    """Test errors populated when coin name is invalid."""
    m_validate_coin.side_effect = ValueError
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "coin"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_NAME: "bad"}
    )
    assert {"base": "invalid_path"} == result["errors"]


async def test_flow_coin_add_another(hass):
    """Test we show the coin flow again if the add_another box was checked."""
    config_flow.MiningPoolHubConfigFlow.data = {
        CONF_API_KEY: API_KEY,
        CONF_CURRENCY_NAMES: [],
    }
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "coin"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        user_input={CONF_NAME: "ethereum", "add_another": True},
    )
    print(result)
    assert "coin" == result["step_id"]
    assert "form" == result["type"]


@patch("custom_components.miningpoolhub.config_flow.validate_coin")
async def test_flow_coin_creates_config_entry(m_validate_coin, hass):
    """Test the config entry is successfully created."""
    config_flow.MiningPoolHubConfigFlow.data = {
        CONF_API_KEY: "key",
        CONF_CURRENCY_NAMES: [],
    }
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "coin"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        user_input={CONF_NAME: "ethereum"},
    )
    expected = {
        "version": 1,
        "type": "create_entry",
        "flow_id": mock.ANY,
        "handler": "miningpoolhub",
        "options": {},
        "title": "MiningPoolHub",
        "data": {
            "api_key": "key",
            "currency_names": ["ethereum"],
        },
        "description": None,
        "description_placeholders": None,
        "result": mock.ANY,
    }
    assert expected == result
