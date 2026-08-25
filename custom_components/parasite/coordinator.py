"""Data coordinator for Parasite Pool."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Mapping
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE_URL, DOMAIN, REQUEST_TIMEOUT, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)
_DIFFICULTY_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([kKmMgGtTpPeEzZyY]?)\s*$")
_DIFFICULTY_MULTIPLIERS = {
    "": 1,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
    "P": 1e15,
    "E": 1e18,
    "Z": 1e21,
    "Y": 1e24,
}


def _as_number(value: Any) -> float | int | None:
    """Safely turn API values into numeric sensor states."""
    if isinstance(value, bool):
        return None
    try:
        return float(value) if isinstance(value, str) and "." in value else int(value)
    except (TypeError, ValueError):
        return None


def parse_difficulty(value: Any) -> float | int | None:
    """Convert a raw difficulty number or compact API value (for example 63.3T)."""
    numeric = _as_number(value)
    if numeric is not None:
        return numeric
    if not isinstance(value, str):
        return None
    match = _DIFFICULTY_RE.fullmatch(value)
    if not match:
        return None
    return float(match.group(1)) * _DIFFICULTY_MULTIPLIERS[match.group(2).upper()]


def parse_uptime_seconds(value: Any) -> int | None:
    """Convert the API uptime string (for example '491d 23h') to seconds."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if not isinstance(value, str):
        return None
    parts = re.findall(r"(\d+)\s*([dhms])", value.lower())
    if not parts:
        return None
    factors = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(int(amount) * factors[unit] for amount, unit in parts)


def format_compact_number(value: Any) -> str | None:
    """Format large difficulty/work values for a compact dashboard state."""
    numeric = _as_number(value)
    if numeric is None:
        return None
    for divisor, suffix in (
        (1e24, "Y"),
        (1e21, "Z"),
        (1e18, "E"),
        (1e15, "P"),
        (1e12, "T"),
        (1e9, "B"),
        (1e6, "M"),
        (1e3, "K"),
    ):
        if abs(numeric) >= divisor:
            return f"{numeric / divisor:.2f} {suffix}"
    return f"{numeric:.0f}"


class ParasiteDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and normalize public Parasite Pool API data."""

    def __init__(self, hass: HomeAssistant, bitcoin_address: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.address = bitcoin_address
        self.session = async_get_clientsession(hass)

    async def _async_get_json(self, path: str, *, required: bool = False) -> Any:
        """Fetch one API endpoint, allowing optional personal endpoints to be absent."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self.session.get(f"{API_BASE_URL}{path}") as response:
                    if response.status == 404 and not required:
                        return None
                    if response.status in (401, 403):
                        raise ConfigEntryAuthFailed("Parasite Pool rejected the request")
                    response.raise_for_status()
                    return await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            if required:
                raise UpdateFailed(f"Error communicating with Parasite Pool: {err}") from err
            _LOGGER.debug("Optional Parasite endpoint %s unavailable: %s", path, err)
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch pool data and the configured miner's public stats."""
        pool, user, account, leaderboard = await asyncio.gather(
            self._async_get_json("/pool-stats", required=True),
            self._async_get_json(f"/user/{self.address}"),
            self._async_get_json(f"/account/{self.address}"),
            self._async_get_json("/leaderboard?type=combined&limit=100"),
        )
        if not isinstance(pool, Mapping):
            raise UpdateFailed("Parasite Pool returned an unexpected pool-stats response")
        user = user if isinstance(user, Mapping) else {}
        account = account if isinstance(account, Mapping) else {}

        workers_data = user.get("workerData")
        if isinstance(workers_data, list):
            worker_hashrate = sum(
                _as_number(worker.get("hashrate")) or 0
                for worker in workers_data
                if isinstance(worker, Mapping)
            )
        else:
            worker_hashrate = None
        personal_hashrate = worker_hashrate if worker_hashrate is not None else _as_number(user.get("hashrate"))

        address_short = f"{self.address[:4]}...{self.address[-4:]}".lower()
        rank = None
        if isinstance(leaderboard, list):
            for position, item in enumerate(leaderboard, start=1):
                if isinstance(item, Mapping) and str(item.get("address", "")).lower() == address_short:
                    rank = position
                    break

        account_data = account.get("account")
        total_work = (
            _as_number(account_data.get("total_diff"))
            if isinstance(account_data, Mapping)
            else None
        )
        personal_best_difficulty = parse_difficulty(user.get("bestDifficulty"))
        pool_best_difficulty = parse_difficulty(pool.get("highestDifficulty"))
        return {
            "personal_hashrate_th": (personal_hashrate / 1e12) if personal_hashrate is not None else None,
            "personal_best_difficulty": format_compact_number(personal_best_difficulty),
            "personal_best_difficulty_raw": personal_best_difficulty,
            "total_work": format_compact_number(total_work),
            "total_work_raw": total_work,
            "worker_count": _as_number(user.get("workers")),
            "uptime_seconds": parse_uptime_seconds(user.get("uptime")),
            "rank": rank,
            "pool_hashrate_ph": (_as_number(pool.get("hashrate")) or 0) / 1e15,
            "pool_best_difficulty": format_compact_number(pool_best_difficulty),
            "pool_best_difficulty_raw": pool_best_difficulty,
            "raw_uptime": user.get("uptime"),
            "raw_pool_best_difficulty": pool.get("highestDifficulty"),
        }
