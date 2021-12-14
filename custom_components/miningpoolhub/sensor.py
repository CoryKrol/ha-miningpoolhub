"""MiningPoolHub sensor platform."""
import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import miningpoolhub_py.exceptions
import voluptuous as vol
from aiohttp import ClientError
from aiohttp import ClientResponseError
from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_NAME, CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from miningpoolhub_py import MiningPoolHubAPI

from .const import (
    ATTR_BALANCE_AUTO_EXCHANGE_CONFIRMED,
    ATTR_BALANCE_AUTO_EXCHANGE_UNCONFIRMED,
    ATTR_BALANCE_CONFIRMED,
    ATTR_BALANCE_ON_EXCHANGE,
    ATTR_BALANCE_UNCONFIRMED,
    ATTR_CURRENT_HASHRATE,
    ATTR_CURRENCY,
    ATTR_INVALID_SHARES,
    ATTR_VALID_SHARES,
    ATTR_RECENT_CREDITS_24_HOURS,
    CONF_CURRENCY_NAMES,
    CONF_FIAT_CURRENCY,
    SENSOR_PREFIX,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
# Time between updating data from MiningPoolHub
SCAN_INTERVAL = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_CURRENCY_NAMES): vol.All(cv.ensure_list, [cv.string]),
        vol.Required(CONF_FIAT_CURRENCY): cv.string,
    }
)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: Callable,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    # Update our config to include new coins and remove those that have been removed.
    if config_entry.options:
        config.update(config_entry.options)
    session = async_get_clientsession(hass)
    miningpoolhub_api = MiningPoolHubAPI(session, api_key=config[CONF_API_KEY])
    sensors = [
        MiningPoolHubSensor(miningpoolhub_api, coin, config[CONF_FIAT_CURRENCY])
        for coin in config[CONF_CURRENCY_NAMES]
    ]

    # Remove update_before_add
    # See: https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity_platform.py#L344
    return await async_add_entities(sensors)


# noinspection PyUnusedLocal
async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    miningpoolhub_api = MiningPoolHubAPI(session, api_key=config[CONF_API_KEY])
    fiat_currency = config[CONF_FIAT_CURRENCY]
    sensors = [
        MiningPoolHubSensor(miningpoolhub_api, coin, fiat_currency)
        for coin in config[CONF_CURRENCY_NAMES]
    ]
    return await async_add_entities(sensors)


class MiningPoolHubSensor(Entity):
    """Representation of a Mining Pool Hub Coin sensor."""

    def __init__(
        self, miningpoolhub_api: MiningPoolHubAPI, coin_name: str, fiat_currency: str
    ):
        super().__init__()
        self.miningpoolhub_api = miningpoolhub_api
        self.coin_name = coin_name
        self.fiat_currency = fiat_currency
        self.attrs: Dict[str, Any] = {}
        self._icon = "mdi:ethereum" if coin_name == "ethereum" else None
        self._name = SENSOR_PREFIX + self.coin_name.title()
        self._state = None
        self._unit_of_measurement = "\u200b"
        self._available = True

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self):
        return self._icon

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.coin_name

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self):
        try:
            dashboard_data = await self.miningpoolhub_api.async_get_dashboard(
                self.coin_name
            )
            self.attrs[ATTR_NAME] = dashboard_data["pool"]["info"]["name"]
            self.attrs[ATTR_CURRENCY] = dashboard_data["pool"]["info"]["currency"]
            self.attrs[ATTR_CURRENT_HASHRATE] = float(
                dashboard_data["personal"]["hashrate"]
            )

            self.attrs[ATTR_VALID_SHARES] = int(
                dashboard_data["personal"]["shares"]["valid"]
            )

            self.attrs[ATTR_INVALID_SHARES] = int(
                dashboard_data["personal"]["shares"]["invalid"]
            )

            self.attrs[ATTR_BALANCE_CONFIRMED] = float(
                dashboard_data["balance"]["confirmed"]
            )
            self.attrs[ATTR_BALANCE_UNCONFIRMED] = float(
                dashboard_data["balance"]["unconfirmed"]
            )
            self.attrs[ATTR_BALANCE_AUTO_EXCHANGE_CONFIRMED] = float(
                dashboard_data["balance_for_auto_exchange"]["confirmed"]
            )
            self.attrs[ATTR_BALANCE_AUTO_EXCHANGE_UNCONFIRMED] = float(
                dashboard_data["balance_for_auto_exchange"]["unconfirmed"]
            )

            self.attrs[ATTR_BALANCE_ON_EXCHANGE] = float(
                dashboard_data["balance_on_exchange"]
            )

            self.attrs[ATTR_RECENT_CREDITS_24_HOURS] = float(
                dashboard_data["recent_credits_24hours"]["amount"]
            )

            self._state = self.attrs[ATTR_CURRENT_HASHRATE]
            self._available = True
        except (ClientError, miningpoolhub_py.exceptions.APIError, ClientResponseError):
            self._available = False
            _LOGGER.exception(
                "Error retrieving data from MiningPoolHub for sensor %s.", self.name
            )
