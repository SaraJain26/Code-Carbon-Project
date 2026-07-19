"""Async and network benchmark."""

import aiohttp
import requests


async def fetch_all(urls: list[str]) -> list[str]:
    results = []
    async with aiohttp.ClientSession() as session:
        for url in urls:
            async with session.get(url) as response:
                results.append(await response.text())
    return results


def poll_status(url: str, attempts: int) -> list[int]:
    statuses = []
    for _ in range(attempts):
        response = requests.get(url)
        statuses.append(response.status_code)
    return statuses
