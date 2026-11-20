import threading
from abc import abstractmethod

import sounddevice as sd

from config import AUDIO_SAMPLE_WIDTH


class AbstractAudioRecorder:
    CODEC: str

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        frame_size: int,
        time_buffer: float | None = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = frame_size
        self.time_buffer = time_buffer

    @property
    @abstractmethod
    def latency(self) -> float:
        pass

    @property
    def frame_bytes(self) -> int:
        return self.frame_size * self.channels * AUDIO_SAMPLE_WIDTH

    @property
    def buffer_size(self) -> int:
        return round(self.sample_rate * self.channels * 2 * self.time_buffer)

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def get_chunk(self) -> bytes:
        pass


class VoidAudioRecorder(AbstractAudioRecorder):
    CODEC = ""

    @property
    def latency(self) -> float:
        return 0.0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def get_chunk(self) -> bytes:
        return bytes()


class AudioRecorder(AbstractAudioRecorder):
    CODEC = "pcm_s16le"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._buffer = bytearray()
        self._lock = threading.Lock()

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._callback,
            latency="low",
        )

    @property
    def latency(self) -> float:
        return self._stream.latency

    def start(self) -> None:
        self._stream.start()

    def stop(self) -> None:
        self._stream.stop()
        self._stream.close()

    def get_chunk(self) -> bytes:
        with self._lock:
            size = len(self._buffer) - len(self._buffer) % self.frame_bytes
            chunk = self._buffer[:size]
            self._buffer = self._buffer[size:]

        return chunk

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            print("Input audio status:", status)

        with self._lock:
            self._buffer.extend(indata.tobytes())

            if self.buffer_size:
                self._buffer = self._buffer[: self.buffer_size]
