"""Tests for the sensor module."""
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.entity_platform import DATA_ENTITY_PLATFORM
from miningpoolhub_py.exceptions import APIError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockPlatform,
    MockEntityPlatform,
    patch,
)

from custom_components.miningpoolhub.const import (
    CONF_CURRENCY_NAMES,
    DOMAIN,
    CONF_FIAT_CURRENCY,
)
from custom_components.miningpoolhub.sensor import (
    MiningPoolHubSensor,
    PLATFORM_SCHEMA,
    SCAN_INTERVAL,
    async_setup_platform,
)


@patch("custom_components.miningpoolhub.sensor.async_get_clientsession")
async def test_async_setup_entry(m_async_get_clientsession, hass, aioclient_mock):
    assert SCAN_INTERVAL == timedelta(minutes=1)
    assert PLATFORM_SCHEMA is not None

    m_async_get_clientsession.return_value = aioclient_mock

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
    assert hass.data[DOMAIN].get(config_entry.entry_id) is not None
    assert config_entry.state == ConfigEntryState.LOADED
    m_async_get_clientsession.assert_called_once()
    assert (
        hass.data[DATA_ENTITY_PLATFORM][DOMAIN][0]
        .entities.get("sensor.miningpoolhub_ethereum")
        .miningpoolhub_api
    )


@patch("custom_components.miningpoolhub.sensor.async_get_clientsession")
async def test_async_setup_platform(m_async_get_clientsession, hass, aioclient_mock):
    assert SCAN_INTERVAL == timedelta(minutes=1)
    assert PLATFORM_SCHEMA is not None

    m_async_get_clientsession.return_value = aioclient_mock

    mock_platform = MockPlatform(
        platform_schema=PLATFORM_SCHEMA,
        scan_interval=SCAN_INTERVAL,
        async_setup_platform=async_setup_platform,
    )
    # noinspection PyTypeChecker
    mock_entity_platform = MockEntityPlatform(
        hass=hass, domain="sensor", platform=mock_platform, platform_name=DOMAIN
    )
    await mock_entity_platform.async_setup(
        {
            CONF_API_KEY: "api_key",
            CONF_CURRENCY_NAMES: ["ethereum"],
            CONF_FIAT_CURRENCY: "USD",
        }
    )

    await hass.async_block_till_done()

    m_async_get_clientsession.assert_called_once()
    assert (
        hass.data[DATA_ENTITY_PLATFORM][DOMAIN][0]
        .entities.get("sensor.miningpoolhub_ethereum")
        .miningpoolhub_api
    )


async def test_async_update_success(
    hass, aioclient_mock, mock_miningpoolhub_dashboard_response
):
    """Tests a fully successful async_update."""
    miningpoolhub = MagicMock()
    miningpoolhub.async_get_dashboard = AsyncMock(
        side_effect=[mock_miningpoolhub_dashboard_response]
    )
    sensor = MiningPoolHubSensor(miningpoolhub, "ethereum", "USD")
    await sensor.async_update()

    expected = {
        "balance_auto_exchange_confirmed": 5.287e-05,
        "balance_auto_exchange_unconfirmed": 0.0,
        "balance_confirmed": 0.05458251,
        "balance_on_exchange": 0.0,
        "balance_unconfirmed": 6.64e-05,
        "currency": "ETH",
        "current_hashrate": 143.165577,
        "invalid_shares": 0,
        "name": "Ethereum (ETH) Mining Pool Hub",
        "recent_credits_24_hours": 0.0032644192,
        "valid_shares": 13056,
    }

    assert sensor.attrs == expected
    assert sensor.device_state_attributes == expected
    assert sensor.available is True


async def test_async_update_failed():
    """Tests a failed async_update."""
    miningpoolhub = MagicMock()
    miningpoolhub.async_get_dashboard = AsyncMock(side_effect=APIError)
    sensor = MiningPoolHubSensor(miningpoolhub, "ethereum", "USD")

    await sensor.async_update()

    assert sensor.available is False
    assert sensor.attrs == {}
