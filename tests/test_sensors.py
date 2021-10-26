"""Tests for the sensor module."""
import os
from dotenv import load_dotenv

import aiohttp

from miningpoolhub_py import MiningPoolHubAPI
from custom_components.miningpoolhub.sensor import MiningPoolHubSensor
import pytest

load_dotenv()
API_KEY = os.environ.get("MPH_API_KEY", None)


@pytest.mark.asyncio
@pytest.mark.vcr
async def test_async_update_success(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    async with aiohttp.ClientSession() as session:
        miningpoolhub = MiningPoolHubAPI(session, api_key=API_KEY)

        sensor = MiningPoolHubSensor(miningpoolhub, "ethereum", "USD")
        await sensor.async_update()

    expected = {
        "balance_auto_exchange_confirmed": 5.287e-05,
        "balance_auto_exchange_unconfirmed": 0.0,
        "balance_confirmed": 0.04767677,
        "balance_on_exchange": 0.0,
        "balance_unconfirmed": 6.279e-05,
        "current_hashrate": 128.849019,
        "currency": "ETH",
        "name": "Ethereum (ETH) Mining Pool Hub",
        "invalid_shares": 0,
        "valid_shares": 6912,
        "recent_credits_24_hours": 0.0025891894,
    }
    assert expected == sensor.attrs
    assert expected == sensor.device_state_attributes
    assert sensor.available is True


async def test_async_update_failed():
    """Tests a failed async_update."""
    async with aiohttp.ClientSession() as session:
        miningpoolhub = MiningPoolHubAPI(session, api_key="bad api_key")

        sensor = MiningPoolHubSensor(miningpoolhub, "ethereum", "USD")
        await sensor.async_update()

        assert sensor.available is False
        assert {} == sensor.attrs
