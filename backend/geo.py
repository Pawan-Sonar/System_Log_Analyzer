"""Best-effort IP geolocation. Uses ip-api.com free tier (no key) with timeout & cache.

Falls back gracefully (returns empty result) on network failure or for private IPs.
"""
from __future__ import annotations
import asyncio
import ipaddress
import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

_cache: Dict[str, dict] = {}


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return True


def _lookup_sync(ip: str) -> dict:
    if ip in _cache:
        return _cache[ip]
    if _is_private(ip):
        result = {"ip": ip, "country": "Private Network", "city": "—", "lat": None, "lon": None}
        _cache[ip] = result
        return result
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,city,lat,lon"},
            timeout=3,
        )
        data = r.json() if r.ok else {}
        if data.get("status") == "success":
            result = {
                "ip": ip,
                "country": data.get("country"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
            }
        else:
            result = {"ip": ip, "country": None, "city": None, "lat": None, "lon": None}
    except Exception as e:  # noqa: BLE001
        logger.warning("Geo lookup failed for %s: %s", ip, e)
        result = {"ip": ip, "country": None, "city": None, "lat": None, "lon": None}
    _cache[ip] = result
    return result


async def lookup(ip: str) -> dict:
    return await asyncio.to_thread(_lookup_sync, ip)


async def lookup_many(ips: list[str]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    tasks = [lookup(ip) for ip in ips]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for ip, res in zip(ips, results):
        if isinstance(res, Exception):
            out[ip] = {"ip": ip, "country": None, "city": None}
        else:
            out[ip] = res
    return out
