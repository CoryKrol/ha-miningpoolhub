from copy import deepcopy
import logging
from typing import Any, Dict, Mapping, Optional

from miningpoolhub_py.exceptions import InvalidCoinError, UnauthorizedError
from miningpoolhub_py.miningpoolhubapi import MiningPoolHubAPI
from homeassistant import config_entries, core
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get_registry,
)
import voluptuous as vol

from .const import CONF_CURRENCY_NAMES, CONF_FIAT_CURRENCY, DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_FIAT_CURRENCY, default="USD"): cv.string,
    }
)
CURRENCY_NAME_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional("add_another"): cv.boolean,
    }
)

OPTIONS_SCHEMA = vol.Schema({vol.Optional(CONF_NAME, default="foo"): cv.string})


async def validate_coin(coin: str, api_key: str, hass: core.HomeAssistant) -> None:
    """Validates a coin

    Parameters
    ----------
    coin : str
        Coin name
    api_key : str
        MiningPoolHub API key
    hass : core.HomeAssistant
        hass instance

    Raises
    ------
    ValueError
        if the coin is invalid
    """
    session = async_get_clientsession(hass)
    miningpoolhubapi = MiningPoolHubAPI(session, api_key=api_key)
    try:
        await miningpoolhubapi.async_get_dashboard(coin_name=coin)
    except InvalidCoinError:
        raise ValueError


async def validate_auth(api_key: str, hass: core.HomeAssistant) -> None:
    """Validates a Mining Pool Hub API key.

    Parameters
    ----------
    api_key : str
        MiningPoolHub API key
    hass : core.HomeAssistant
        hass instance

    Raises
    ------
    ValueError
        if the API key is invalid
    """
    session = async_get_clientsession(hass)
    miningpoolhubapi = MiningPoolHubAPI(session, api_key=api_key)
    try:
        await miningpoolhubapi.async_get_user_all_balances()
    except UnauthorizedError:
        raise ValueError


class MiningPoolHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mining Pool Hub config flow."""

    data: Mapping[str, Any] = {CONF_API_KEY: "default"}

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_auth(user_input[CONF_API_KEY], self.hass)
            except ValueError:
                errors["base"] = "auth"
            if not errors:
                # Input is valid, set data.
                self.data = user_input
                self.data[CONF_CURRENCY_NAMES] = []
                # Return the form of the next step.
                return await self.async_step_coin()

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_coin(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step in config flow to add a mining pool to watch."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate the coin.
            try:
                await validate_coin(
                    user_input[CONF_NAME], self.data[CONF_API_KEY], self.hass
                )
            except ValueError:
                errors["base"] = "invalid_coin"

            if not errors:
                # Input is valid, set data.
                self.data[CONF_CURRENCY_NAMES].append(user_input[CONF_NAME].lower())
                # If user ticked the box show this form again so they can add an
                # additional coins.
                if user_input.get("add_another", False):
                    return await self.async_step_coin()

                # User is done adding coins, create the config entry.
                return self.async_create_entry(title="MiningPoolHub", data=self.data)

        return self.async_show_form(
            step_id="coin", data_schema=CURRENCY_NAME_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] = None) -> FlowResult:
        """Manage the options for the custom component."""
        errors: Dict[str, str] = {}
        # Grab all configured pools from the entity registry so we can populate the
        # multi-select dropdown that will allow a user to remove a mining pool.
        entity_registry = await async_get_registry(self.hass)
        entries = async_entries_for_config_entry(
            entity_registry, self.config_entry.entry_id
        )
        # Default value for our multi-select.
        all_coins = {
            e.entity_id: e.original_name[14:] if e.original_name is not None else ""
            for e in entries
        }
        coin_map = {e.entity_id: e for e in entries}

        if user_input is not None:
            updated_coins = deepcopy(self.config_entry.data[CONF_CURRENCY_NAMES])

            # Remove any unchecked coins.
            removed_entities = [
                entity_id
                for entity_id in coin_map.keys()
                if entity_id not in user_input["coins"]
            ]

            for entity_id in removed_entities:
                # Unregister from HA
                entity_registry.async_remove(entity_id)

                # Remove from our configured coins.
                entry = coin_map[entity_id]
                entry_name = entry.unique_id
                updated_coins = [e for e in updated_coins if e != entry_name]

            coin_name = user_input.get(CONF_NAME)
            if coin_name:
                # Validate the coin.
                api_key = self.hass.data[DOMAIN][self.config_entry.entry_id][
                    CONF_API_KEY
                ]
                try:
                    await validate_coin(user_input[CONF_NAME], api_key, self.hass)
                except ValueError:
                    errors["base"] = "invalid_coin"

                if not errors:
                    # Add the new coin.
                    updated_coins.append(coin_name.lower())

            if not errors:
                # Value of data will be set on the options property of our config_entry instance.
                return self.async_create_entry(
                    title="",
                    data={CONF_CURRENCY_NAMES: updated_coins},
                )

        options_schema = vol.Schema(
            {
                # TODO: Modify options schema to support modifying API key
                # vol.Optional(CONF_API_KEY): cv.string,
                vol.Optional("coins", default=list(all_coins.keys())): cv.multi_select(
                    all_coins
                ),
                vol.Optional(CONF_NAME): cv.string,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
