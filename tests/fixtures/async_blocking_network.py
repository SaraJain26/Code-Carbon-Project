"""Async blocking and network benchmark fixture."""

import time
import requests


async def fetch_blocking(urls: list[str]) -> list[str]:
    results = []
    for url in urls:
        time.sleep(0.1)
        response = requests.get(url)
        results.append(response.text)
    return results


def poll_status(url: str, attempts: int) -> list[int]:
    statuses = []
    for _ in range(attempts):
        response = requests.get(url)
        statuses.append(response.status_code)
    return statuses
