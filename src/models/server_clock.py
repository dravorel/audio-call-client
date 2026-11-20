import asyncio
import time

import httpx

from config import SERVER_TIMEOUT


class ServerClock:
    def __init__(self, url: str):
        self.url = url

        self._server_time: float | None = None
        self._monotonic_time: float | None = None
        self._accuracy: float | None = None

        self._lock = asyncio.Lock()

    async def sync(self) -> None:
        async with httpx.AsyncClient() as client:
            t0 = time.monotonic()
            response = await client.get(
                self.url,
                timeout=httpx.Timeout(**SERVER_TIMEOUT),
            )
            response.raise_for_status()
            server_timestamp = response.json()["timestamp"]
            t1 = time.monotonic()
            rtt = t1 - t0

        async with self._lock:
            self._accuracy = rtt / 2
            self._server_time = server_timestamp + rtt / 2
            self._monotonic_time = t1

    async def timestamp(self) -> float:
        async with self._lock:
            if self._server_time is None:
                raise RuntimeError("Clock is not synchronized")

            return self._server_time + time.monotonic() - self._monotonic_time

    async def accuracy(self) -> float:
        async with self._lock:
            if self._server_time is None:
                raise RuntimeError("Clock is not synchronized")

            return self._accuracy
