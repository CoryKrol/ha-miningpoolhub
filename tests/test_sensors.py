"""Tests for the sensor module."""
from miningpoolhub_py.miningpoolhubapi import MiningPoolHubAPI
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant.async_mock import AsyncMock, MagicMock, Mock

from custom_components.miningpoolhub.sensor import MiningPoolHubSensor