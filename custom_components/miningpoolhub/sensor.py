"""MiningPoolHub sensor platform."""
import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional
from urllib import parse

import voluptuous as vol
from aiohttp import ClientError

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_NAME,
    CONF_ACCESS_TOKEN,
    CONF_NAME,
    CONF_PATH,
    CONF_URL,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

from .const import (
    ATTR_ACTIVE_WORKERS,
    ATTR_CURRENT_HASHRATE,
    ATTR_INVALID_SHARES,
    ATTR_LAST_UPDATE,
    ATTR_REPORTED_HASHRATE,
    ATTR_STALE_SHARES,
    ATTR_UNPAID,
    ATTR_VALID_SHARES,
    ATTR_START_BLOCK,
    ATTR_END_BLOCK,
    ATTR_AMOUNT,
    ATTR_TXHASH,
    ATTR_PAID_ON,
    ATTR_AVERAGE_HASHRATE_24h ,
    ATTR_UNCONFIRMED,
    ATTR_SINGLE_COIN_LOCAL_CURRENCY ,
    ATTR_TOTAL_UNPAID_LOCAL_CURRENCY,
    ATTR_COINS_PER_MINUTE,
    CONF_ID,
    CONF_ACCESS_TOKEN,
    CONF_CURRENCY_NAMES,
    CONF_ID,
    CONF_NAME_OVERRIDE,
    CONF_UPDATE_FREQUENCY,
    COINGECKO_API_ENDPOINT
)


_LOGGER = logging.getLogger(__name__)
# Time between updating data from MiningPoolHub
SCAN_INTERVAL = timedelta(minutes=10)

CURRENCY_SCHEMA = vol.Schema(
    {vol.Required(CONF_PATH): cv.string, vol.Optional(CONF_NAME): cv.string}
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
        vol.Required(CONF_CURRENCY_NAMES): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_URL): cv.url,
        vol.Optional(CONF_ID, default=""): cv.string,
        vol.Optional(CONF_NAME_OVERRIDE, default=""): cv.string
    }
)

async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    github = GitHubAPI(session, "requester", oauth_token=config[CONF_ACCESS_TOKEN])
    sensors = [GitHubRepoSensor(github, repo) for repo in config[CONF_REPOS]]
    async_add_entities(sensors, update_before_add=True)


class MiningPoolHubSensor(Entity):
    """Representation of a Mining Pool Hub Coin sensor."""

    def __init__(self, github: GitHubAPI, repo: Dict[str, str]):
        super().__init__()
        self.github = github
        self.repo = repo["path"]
        self.attrs: Dict[str, Any] = {ATTR_PATH: self.repo}
        self._name = repo.get("name", self.repo)
        self._state = None
        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.repo

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self):
        try:
            repo_url = f"/repos/{self.repo}"
            repo_data = await self.github.getitem(repo_url)
            self.attrs[ATTR_FORKS] = repo_data["forks_count"]
            self.attrs[ATTR_NAME] = repo_data["name"]
            self.attrs[ATTR_STARGAZERS] = repo_data["stargazers_count"]

            if repo_data["permissions"]["push"]:
                clones_url = f"{repo_url}/traffic/clones"
                clones_data = await self.github.getitem(clones_url)
                self.attrs[ATTR_CLONES] = clones_data["count"]
                self.attrs[ATTR_CLONES_UNIQUE] = clones_data["uniques"]

                views_url = f"{repo_url}/traffic/views"
                views_data = await self.github.getitem(views_url)
                self.attrs[ATTR_VIEWS] = views_data["count"]
                self.attrs[ATTR_VIEWS_UNIQUE] = views_data["uniques"]

            commits_url = f"/repos/{self.repo}/commits"
            commits_data = await self.github.getitem(commits_url)
            latest_commit = commits_data[0]
            self.attrs[ATTR_LATEST_COMMIT_MESSAGE] = latest_commit["commit"]["message"]
            self.attrs[ATTR_LATEST_COMMIT_SHA] = latest_commit["sha"]

            prs_url = f"/repos/{self.repo}/pulls"
            prs_data = await self.github.getitem(
                prs_url, {"state": "open", "sort": "created", "per_page": 1}
            )
            self.attrs[ATTR_OPEN_PULL_REQUESTS] = await self._get_total(prs_url)
            if prs_data:
                self.attrs[ATTR_LATEST_OPEN_PULL_REQUEST_URL] = prs_data[0]["html_url"]

            issues_url = f"/repos/{self.repo}/issues"
            issues_data = await self.github.getitem(
                issues_url, {"state": "open", "sort": "created", "per_page": 1}
            )
            # GitHub issues include pull requests, so to just get the number of issues,
            # we need to subtract the total number of pull requests from this total.
            total_issues = await self._get_total(issues_url)
            self.attrs[ATTR_OPEN_ISSUES] = (
                total_issues - self.attrs[ATTR_OPEN_PULL_REQUESTS]
            )
            if issues_data:
                self.attrs[ATTR_LATEST_OPEN_ISSUE_URL] = issues_data[0]["html_url"]

            releases_url = f"/repos/{self.repo}/releases"
            releases_data = await self.github.getitem(releases_url)
            if releases_data:
                self.attrs[ATTR_LATEST_RELEASE_URL] = releases_data[0]["html_url"]
                self.attrs[ATTR_LATEST_RELEASE_TAG] = releases_data[0][
                    "html_url"
                ].split("/")[-1]

            # Set state to short commit sha.
            self._state = latest_commit["sha"][:7]
            self._available = True
        except (ClientError, gidgethub.GitHubException):
            self._available = False
            _LOGGER.exception("Error retrieving data from GitHub.")

    async def _get_total(self, url: str) -> int:
        """Get the total number of results for a GitHub resource URL.
        GitHub's API doesn't provide a total count for paginated resources.  To get
        around that and to not have to request every page, we do a single request
        requesting 1 item per page.  Then we get the url for the last page in the
        response headers and parse the page number from there.  This page number is
        the total number of results.
        """
        api_url = f"{BASE_API_URL}{url}"
        params = {"per_page": 1, "state": "open"}
        headers = {"Authorization": self.github.oauth_token}
        async with self.github._session.get(
            api_url, params=params, headers=headers
        ) as resp:
            last_page_url = get_last_page_url(resp.headers.get("Link"))
            if last_page_url is not None:
                return int(dict(parse.parse_qsl(last_page_url))["page"])
        return 0