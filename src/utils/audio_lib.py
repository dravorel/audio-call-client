import struct
from abc import abstractmethod

from config import SupportedAudioCodec, AUDIO_SAMPLE_WIDTH
from external import import_external_libs

import_external_libs()
import opuslib


class AbstractAudioLib:
    CODEC: str

    def __init__(
        self,
        sample_rate: int,
        bitrate: int,
        channels: int,
        frame_size: int,
    ):
        self.sample_rate = sample_rate
        self.bitrate = bitrate
        self.channels = channels
        self.frame_size = frame_size

    @property
    def frame_bytes(self) -> int:
        return self.frame_size * self.channels * AUDIO_SAMPLE_WIDTH

    @abstractmethod
    def encode(self, chunk: bytes) -> bytes:
        pass

    @abstractmethod
    def decode(self, chunk: bytes) -> bytes:
        pass

    @abstractmethod
    def get_duration(self, chunk: bytes) -> float:
        pass


class PCMLib(AbstractAudioLib):
    CODEC = "pcm_s16le"

    def encode(self, chunk: bytes) -> bytes:
        return chunk

    def decode(self, chunk: bytes) -> bytes:
        return chunk

    def get_duration(self, chunk: bytes) -> float:
        bytes_per_second = self.sample_rate * self.channels * AUDIO_SAMPLE_WIDTH
        return len(chunk) / bytes_per_second


class OpusLib(AbstractAudioLib):
    CODEC = "opus"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._decoder = opuslib.Decoder(self.sample_rate, self.channels)
        self._encoder = opuslib.Encoder(
            fs=self.sample_rate,
            channels=self.channels,
            application=opuslib.APPLICATION_VOIP,
        )
        self._encoder.bitrate = self.bitrate

    def encode(self, chunk: bytes) -> bytes:
        encoded_chunks = []

        if len(chunk) % self.frame_bytes != 0:
            raise ValueError("Incomplete audio chunk")

        for i in range(0, len(chunk), self.frame_bytes):
            pcm_frame = bytes(chunk[i : i + self.frame_bytes])
            encoded = self._encoder.encode(pcm_frame, self.frame_size)
            encoded_chunks.append(len(encoded).to_bytes(2, "big"))
            encoded_chunks.append(encoded)

        return b"".join(encoded_chunks)

    def decode(self, chunk: bytes) -> bytes:
        offset = 0
        decoded_chunks = []

        while offset + 2 <= len(chunk):
            packet_size = struct.unpack("!H", chunk[offset : offset + 2])[0]
            offset += 2

            if packet_size == 0 or offset + packet_size > len(chunk):
                raise ValueError("Invalid Opus packet")

            packet = chunk[offset : offset + packet_size]
            offset += packet_size

            pcm = self._decoder.decode(packet, self.frame_size)
            decoded_chunks.append(pcm)

        if offset != len(chunk):
            raise ValueError("Incomplete audio chunk")

        return b"".join(decoded_chunks)

    def get_duration(self, chunk: bytes) -> float:
        offset = 0
        total_samples = 0

        while offset < len(chunk):
            packet_size = struct.unpack("!H", chunk[offset : offset + 2])[0]
            offset += 2

            if packet_size == 0 or offset + packet_size > len(chunk):
                raise ValueError("Invalid Opus packet")

            packet = chunk[offset : offset + packet_size]
            offset += packet_size

            pcm = self._decoder.decode(packet, self.frame_size)
            total_samples += len(pcm) // (2 * self.channels)

        return total_samples / self.sample_rate


AUDIO_LIB_CLASS_MAP: dict[SupportedAudioCodec, type[AbstractAudioLib]] = {
    "pcm": PCMLib,
    "opus": OpusLib,
}
