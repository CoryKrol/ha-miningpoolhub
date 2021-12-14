from pytest import fixture


@fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@fixture
def mock_miningpoolhub_dashboard_response() -> dict:
    return {
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
