"""Data coordinator for Parasite Pool."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import Mapping
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE_URL,
    DOMAIN,
    PROVIDER_CKPOOL,
    PROVIDER_CKPOOL_EU,
    REQUEST_TIMEOUT,
    UPDATE_INTERVAL,
)

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
_HISTORY_REFRESH_SECONDS = 300


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


def parse_hashrate_hs(value: Any) -> float | int | None:
    """Convert CKPool compact hashrates (for example 3.7T) to H/s."""
    return parse_difficulty(value)


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

    def __init__(
        self,
        hass: HomeAssistant,
        bitcoin_address: str,
        provider: str,
        ckpool_url: str | None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.address = bitcoin_address
        self.provider = provider
        self.ckpool_url = ckpool_url.rstrip("/") if ckpool_url else None
        self.session = async_get_clientsession(hass)
        self._last_history_fetch = 0.0
        self._hashrate_24h_th: float | None = None

    async def _async_get_json(
        self, path: str, *, required: bool = False, base_url: str | None = None
    ) -> Any:
        """Fetch one API endpoint, allowing optional personal endpoints to be absent."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self.session.get(f"{base_url or API_BASE_URL}{path}") as response:
                    if response.status == 404 and not required:
                        return None
                    if response.status in (401, 403):
                        raise ConfigEntryAuthFailed("Parasite Pool rejected the request")
                    response.raise_for_status()
                    payload = await response.text()
                    try:
                        return json.loads(payload)
                    except json.JSONDecodeError:
                        # CKPool's pool.status can be multiple JSON objects,
                        # one per line, rather than a JSON array.
                        decoder = json.JSONDecoder()
                        values = []
                        offset = 0
                        while offset < len(payload):
                            while offset < len(payload) and payload[offset].isspace():
                                offset += 1
                            if offset >= len(payload):
                                break
                            value, offset = decoder.raw_decode(payload, offset)
                            values.append(value)
                        return values or None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, json.JSONDecodeError) as err:
            if required:
                raise UpdateFailed(f"Error communicating with Parasite Pool: {err}") from err
            _LOGGER.debug("Optional Parasite endpoint %s unavailable: %s", path, err)
            return None

    async def _async_get_first_available_json(
        self, paths: tuple[str, ...], *, required: bool = False
    ) -> Any:
        """Try common CKPool URL layouts used by public and self-hosted pools."""
        for path in paths:
            value = await self._async_get_json(path, base_url=self.ckpool_url)
            if value is not None:
                return value
        if required:
            raise UpdateFailed("Could not retrieve CKPool pool statistics")
        return None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch pool data and the configured miner's public stats."""
        if self.provider in (PROVIDER_CKPOOL, PROVIDER_CKPOOL_EU):
            return await self._async_update_ckpool_data()

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

        # The public historical endpoint returns sampled hashrate values for the
        # requested period. Refresh it less often than the live 30-second data.
        if time.monotonic() - self._last_history_fetch >= _HISTORY_REFRESH_SECONDS:
            history = await self._async_get_json(
                f"/user/{self.address}/historical?period=1d&interval=15m"
            )
            if isinstance(history, list):
                samples = [
                    _as_number(point.get("hashrate"))
                    for point in history
                    if isinstance(point, Mapping) and _as_number(point.get("hashrate")) is not None
                ]
                self._hashrate_24h_th = (
                    sum(samples) / len(samples) / 1e12 if samples else None
                )
            else:
                self._hashrate_24h_th = None
            self._last_history_fetch = time.monotonic()

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
            "hashrate_24h_th": self._hashrate_24h_th,
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

    async def _async_update_ckpool_data(self) -> dict[str, Any]:
        """Fetch and normalize the standard public CKPool stats endpoints."""
        user, pool = await asyncio.gather(
            self._async_get_first_available_json(
                (f"/users/{self.address}", f"/api/users/{self.address}")
            ),
            self._async_get_first_available_json(
                ("/pool/pool.status", "/api/pool/pool.status"), required=True
            ),
        )
        user = user if isinstance(user, Mapping) else {}
        pool_sections = pool if isinstance(pool, list) else [pool]
        pool_sections = [section for section in pool_sections if isinstance(section, Mapping)]

        def pool_value(*keys: str) -> Any:
            for section in pool_sections:
                for key in keys:
                    if key in section:
                        return section[key]
            return None

        authorised = _as_number(user.get("authorised"))
        uptime_seconds = (
            max(0, int(time.time() - authorised)) if authorised else None
        )
        current_hashrate = parse_hashrate_hs(
            user.get("hashrate5m") or user.get("hashrate1m") or user.get("hashrate1hr")
        )
        hashrate_24h = parse_hashrate_hs(user.get("hashrate1d"))
        personal_best = parse_difficulty(user.get("bestever") or user.get("bestshare"))
        pool_hashrate = parse_hashrate_hs(pool_value("hashrate1hr", "hashrate5m"))
        pool_best = parse_difficulty(pool_value("bestshare"))

        return {
            "personal_hashrate_th": current_hashrate / 1e12 if current_hashrate is not None else None,
            "hashrate_24h_th": hashrate_24h / 1e12 if hashrate_24h is not None else None,
            "personal_best_difficulty": format_compact_number(personal_best),
            "personal_best_difficulty_raw": personal_best,
            "total_work": None,
            "total_work_raw": None,
            "worker_count": _as_number(user.get("workers")),
            "uptime_seconds": uptime_seconds,
            "rank": None,
            "pool_hashrate_ph": pool_hashrate / 1e15 if pool_hashrate is not None else None,
            "pool_best_difficulty": format_compact_number(pool_best),
            "pool_best_difficulty_raw": pool_best,
            "raw_uptime": None,
            "raw_pool_best_difficulty": pool_value("bestshare"),
        }
