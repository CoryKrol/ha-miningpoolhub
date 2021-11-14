"""Tests for the config flow."""
from unittest import mock
from unittest.mock import AsyncMock

from miningpoolhub_py.exceptions import InvalidCoinError, UnauthorizedError
from homeassistant.const import CONF_API_KEY, CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch
from custom_components.miningpoolhub import config_flow
from custom_components.miningpoolhub.const import (
    CONF_CURRENCY_NAMES,
    DOMAIN,
    CONF_FIAT_CURRENCY,
)

API_KEY = "key"


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_validate_coin_valid(m_miningpoolhubapi, hass):
    """Test no exception is raised for a valid coin."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock()
    m_miningpoolhubapi.return_value = m_instance
    await config_flow.validate_coin("ethereum", API_KEY, hass)


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_validate_coin_invalid(m_miningpoolhubapi, hass):
    """Test a ValueError is raised when the coin is not valid."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock(
        side_effect=InvalidCoinError(AsyncMock())
    )
    m_miningpoolhubapi.return_value = m_instance
    for bad_coin in ("dollarcoin", "bitdollar"):
        with pytest.raises(ValueError):
            await config_flow.validate_coin(bad_coin, API_KEY, hass)


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_validate_auth_valid(m_miningpoolhubapi, hass):
    """Test no exception is raised for valid API key."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock()
    m_miningpoolhubapi.return_value = m_instance
    await config_flow.validate_auth(API_KEY, hass)


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_validate_auth_invalid(m_miningpoolhubapi, hass):
    """Test ValueError is raised when API key is invalid."""
    m_instance = AsyncMock()
    m_instance.async_get_user_all_balances = AsyncMock(
        side_effect=UnauthorizedError(AsyncMock())
    )
    m_miningpoolhubapi.return_value = m_instance
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
    assert result["errors"] == {"base": "auth"}


@patch("custom_components.miningpoolhub.config_flow.validate_auth")
async def test_flow_user_init_data_valid(m_validate_auth, hass):
    """Test we advance to the next step when data is valid."""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_API_KEY: "good"}
    )
    assert result["step_id"] == "coin"
    assert result["type"] == "form"


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
    assert result == expected


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
    assert result["errors"] == {"base": "invalid_coin"}


@patch("custom_components.miningpoolhub.config_flow.validate_coin")
async def test_flow_coin_add_another(m_validate_coin, hass):
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
    assert result["step_id"] == "coin"
    assert result["type"] == "form"


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
    assert result == expected


@patch("custom_components.miningpoolhub.sensor.MiningPoolHubAPI")
async def test_options_flow_init(m_miningpoolhub, hass):
    """Test config flow options."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock()
    m_miningpoolhub.return_value = m_instance

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="miningpoolhub_ethereum",
        data={
            CONF_API_KEY: "api-key",
            CONF_FIAT_CURRENCY: "USD",
            CONF_CURRENCY_NAMES: ["ethereum"],
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"
    assert result["errors"] == {}
    # Verify multi-select options populated with configured coins.
    assert result["data_schema"].schema["coins"].options == {
        "sensor.miningpoolhub_ethereum": "ethereum"
    }


@patch("custom_components.miningpoolhub.sensor.MiningPoolHubAPI")
async def test_options_flow_remove_coin(m_miningpoolhub, hass):
    """Test config flow options."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock()
    m_miningpoolhub.return_value = m_instance

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="miningpoolhub_ethereum",
        data={
            CONF_API_KEY: "api-key",
            CONF_FIAT_CURRENCY: "USD",
            CONF_CURRENCY_NAMES: ["ethereum"],
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    # submit form with options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"coins": []}
    )
    assert result["type"] == "create_entry"
    assert result["title"] == ""
    assert result["result"] is True
    assert result["data"] == {CONF_CURRENCY_NAMES: []}


@patch("custom_components.miningpoolhub.sensor.MiningPoolHubAPI")
@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_options_flow_add_coin(m_miningpoolhub, m_miningpoolhub_cf, hass):
    """Test config flow options."""
    m_instance = AsyncMock()
    m_instance.async_get_dashboard = AsyncMock()
    m_miningpoolhub.return_value = m_instance
    m_miningpoolhub_cf.return_value = m_instance

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="miningpoolhub_ethereum",
        data={
            CONF_API_KEY: "api-key",
            CONF_FIAT_CURRENCY: "USD",
            CONF_CURRENCY_NAMES: ["ethereum"],
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    # submit form with options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"coins": ["sensor.miningpoolhub_ethereum"], "name": "doge"},
    )
    assert result["type"] == "create_entry"
    assert result["title"] == ""
    assert result["result"] is True
    expected_coins = [
        "ethereum",
        "doge",
    ]
    assert result["data"] == {CONF_CURRENCY_NAMES: expected_coins}
