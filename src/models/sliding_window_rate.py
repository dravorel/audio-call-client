from collections import deque


class SlidingWindowRate:
    def __init__(self, window: float = 1.0):
        self.window = window
        self.timestamps = deque()

    def add(self, timestamp: float) -> None:
        self.timestamps.append(timestamp)
        self._remove_old(timestamp)

    def average(self, now: float) -> float:
        self._remove_old(now)
        return len(self.timestamps) / self.window

    def _remove_old(self, now: float) -> None:
        while self.timestamps and now - self.timestamps[0] > self.window:
            self.timestamps.popleft()
