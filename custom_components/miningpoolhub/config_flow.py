import logging
from typing import Any, Dict, Optional

from miningpoolhub_py.exceptions import InvalidCoinError, UnauthorizedError
from miningpoolhub_py.miningpoolhubapi import MiningPoolHubAPI
from homeassistant import config_entries, core
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import CONF_CURRENCY_NAMES, CONF_FIAT_CURRENCY, DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {vol.Required(CONF_API_KEY): cv.string, vol.Optional(CONF_FIAT_CURRENCY): cv.string}
)
CURRENCY_NAME_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional("add_another"): cv.boolean,
    }
)

OPTIONS_SCHEMA = vol.Schema({vol.Optional(CONF_NAME, default="foo"): cv.string})


async def validate_coin(coin: str, api_key: str, hass: core.HomeAssistant) -> None:
    """Validates a coin.
    Raises a ValueError if the coin is invalid.
    """
    session = async_get_clientsession(hass)
    miningpoolhubapi = MiningPoolHubAPI(session, api_key=api_key)
    try:
        await miningpoolhubapi.async_get_dashboard(coin_name=coin)
    except InvalidCoinError:
        raise ValueError


async def validate_auth(api_key: str, hass: core.HomeAssistant) -> None:
    """Validates a Mining Pool Hub API key.
    Raises a ValueError if the API key is invalid.
    """
    session = async_get_clientsession(hass)
    miningpoolhubapi = MiningPoolHubAPI(session, api_key=api_key)
    try:
        await miningpoolhubapi.async_get_user_all_balances()
    except UnauthorizedError:
        raise ValueError


class MiningPoolHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Mining Pool Hub config flow."""

    data: Optional[Dict[str, Any]] = {"api_key": "default"}

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
        """Second step in config flow to add a repo to watch."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate the coin.
            try:
                await validate_coin(
                    user_input[CONF_NAME], self.data[CONF_API_KEY], self.hass
                )
            except ValueError:
                errors["base"] = "invalid_path"

            if not errors:
                # Input is valid, set data.
                self.data[CONF_CURRENCY_NAMES].append(user_input[CONF_NAME])
                # If user ticked the box show this form again so they can add an
                # additional coins.
                if user_input.get("add_another", False):
                    return await self.async_step_coin()

                # User is done adding coins, create the config entry.
                return self.async_create_entry(title="MiningPoolHub", data=self.data)

        return self.async_show_form(
            step_id="coin", data_schema=CURRENCY_NAME_SCHEMA, errors=errors
        )
