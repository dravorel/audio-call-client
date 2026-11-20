import threading
import time
from abc import abstractmethod
from collections import deque

import numpy as np
import sounddevice as sd

from config import AUDIO_SAMPLE_WIDTH


class AbstractAudioPlayer:
    CODEC: str

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        frame_size: int,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = frame_size

    @property
    @abstractmethod
    def latency(self) -> float:
        pass

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def add(self, data: bytes) -> None:
        pass

    @abstractmethod
    def get_queue_duration(self) -> float:
        pass


class VoidAudioPlayer(AbstractAudioPlayer):
    CODEC = ""

    @property
    def latency(self) -> float:
        return 0.0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def add(self, data: bytes) -> None:
        pass

    def get_queue_duration(self) -> float:
        return 0.0


class AudioPlayer(AbstractAudioPlayer):
    CODEC = "pcm_s16le"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.frame_bytes = self.frame_size * self.channels * AUDIO_SAMPLE_WIDTH

        self._queue = deque()
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            latency="low",
        )
        self._thread = threading.Thread(
            target=self._play_loop,
            daemon=True,
        )
        self._lock = threading.Lock()
        self._running = False
        self._prev_audio = None

    @property
    def latency(self) -> float:
        return self._stream.latency

    def start(self):
        self._running = True
        self._stream.start()
        self._thread.start()

    def stop(self):
        self._running = False
        self._thread.join()
        self._stream.stop()
        self._stream.close()

    def add(self, data: bytes):
        audio = np.frombuffer(data, dtype=np.int16)
        audio = audio.reshape(-1, self.channels)

        with self._lock:
            self._queue.append(audio)

    def get_queue_duration(self) -> float:
        with self._lock:
            n = sum(len(x) for x in self._queue)
            n += 0 if self._prev_audio is None else len(self._prev_audio)

        return n / self.sample_rate

    def _play_loop(self):
        while self._running:
            with self._lock:
                if self._queue:
                    audio = self._queue.popleft()
                    self._prev_audio = audio
                else:
                    audio = None

            if audio is None:
                time.sleep(0.01)
                continue

            self._stream.write(audio)
