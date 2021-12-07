"""Tests for the miningpoolhub custom component."""
from unittest.mock import call
from custom_components import miningpoolhub
from homeassistant.const import CONF_API_KEY
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry, patch
from custom_components.miningpoolhub.const import (
    CONF_CURRENCY_NAMES,
    DOMAIN,
    CONF_FIAT_CURRENCY,
)


def test_init():
    """Should initialize all members correctly"""
    assert miningpoolhub._LOGGER is not None


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_async_setup_entry(m_miningpoolhubapi, hass):
    assert "miningpoolhub" == DOMAIN

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="miningpoolhub_ethereum",
        data={
            CONF_API_KEY: "api-key",
            CONF_FIAT_CURRENCY: "USD",
            CONF_CURRENCY_NAMES: ["ethereum"],
        },
    )

    # await miningpoolhub.async_setup_entry(hass, config_entry)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN].get(config_entry.entry_id) is not None
    assert (
        hass.data[DOMAIN][config_entry.entry_id]["unsub_options_update_listener"]
        is not None
    )
    assert ConfigEntryState.LOADED == config_entry.state


@patch("custom_components.miningpoolhub.config_flow.MiningPoolHubAPI")
async def test_async_unload_entry(m_miningpoolhubapi, hass):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="miningpoolhub_ethereum",
        data={
            CONF_API_KEY: "api-key",
            CONF_FIAT_CURRENCY: "USD",
            CONF_CURRENCY_NAMES: ["ethereum"],
        },
    )

    with patch.object(
        MockConfigEntry, "async_unload", wraps=config_entry.async_unload
    ) as mock_unload:
        # Add config to ha
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Unload config from ha
        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
        assert hass.data[DOMAIN].get(config_entry.entry_id) is None
        assert not hass.components._hass.data["miningpoolhub"]
        assert ConfigEntryState.NOT_LOADED == config_entry.state
        mock_unload.assert_has_calls(
            [call(hass), call(hass, integration=hass.data["integrations"]["sensor"])]
        )
