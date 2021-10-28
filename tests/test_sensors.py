"""Tests for the sensor module."""

from unittest.mock import AsyncMock, MagicMock

from miningpoolhub_py.exceptions import APIError

from custom_components.miningpoolhub.sensor import MiningPoolHubSensor


async def test_async_update_success(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    miningpoolhub = MagicMock()
    miningpoolhub.async_get_dashboard = AsyncMock(
        side_effect=[
            {
                "personal": {
                    "hashrate": 143.165577,
                    "sharerate": 0,
                    "sharedifficulty": 0,
                    "shares": {
                        "valid": 13056,
                        "invalid": 0,
                        "invalid_percent": 0,
                        "unpaid": 0,
                    },
                    "estimates": {
                        "block": 1.733e-5,
                        "fee": 0,
                        "donation": 0,
                        "payout": 1.733e-5,
                    },
                },
                "balance": {"confirmed": 0.05458251, "unconfirmed": 6.64e-5},
                "balance_for_auto_exchange": {"confirmed": 5.287e-5, "unconfirmed": 0},
                "balance_on_exchange": 0,
                "recent_credits_24hours": {"amount": 0.0032644192},
                "pool": {
                    "info": {
                        "name": "Ethereum (ETH) Mining Pool Hub",
                        "currency": "ETH",
                    }
                },
            }
        ]
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

    assert expected == sensor.attrs
    assert expected == sensor.device_state_attributes
    assert sensor.available is True


async def test_async_update_failed():
    """Tests a failed async_update."""
    miningpoolhub = MagicMock()
    miningpoolhub.async_get_dashboard = AsyncMock(side_effect=APIError)
    sensor = MiningPoolHubSensor(miningpoolhub, "ethereum", "USD")

    await sensor.async_update()

    assert sensor.available is False
    assert {} == sensor.attrs
