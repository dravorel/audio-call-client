import argparse
import asyncio
import datetime
import json
import secrets
import sys
import time

import httpx
import sounddevice as sd

from config import (
    SYNC_FREQUENCY,
    SERVER_URL,
    SYNC_CALL_URL,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    TIME_BUFFER_SIZE,
    CHUNK_SEPARATOR,
    CHUNK_DATA_SEPARATOR,
    FORMAT_VERSION,
    SERVER_TIMEOUT,
    AUDIO_CODEC,
    AUDIO_BITRATE,
    AUDIO_FRAME_SIZE,
    AUDIO_FRAME_DURATION,
    ENABLE_AUDIO_PLAYER,
    ENABLE_AUDIO_RECORDER,
)
from models.audio_player import AudioPlayer, VoidAudioPlayer, AbstractAudioPlayer
from models.audio_recorder import (
    AudioRecorder,
    VoidAudioRecorder,
    AbstractAudioRecorder,
)
from models.server_clock import ServerClock
from models.sliding_window_rate import SlidingWindowRate
from utils.audio_lib import AUDIO_LIB_CLASS_MAP, AbstractAudioLib
from utils.validators import validate_room_id


def print_config():
    print(" Config ".center(30, "="))
    print(f"Server URL: {SERVER_URL}")
    print(f"Audio codec: {AUDIO_CODEC}")
    print(f"Audio sample rate: {AUDIO_SAMPLE_RATE}")
    print(f"Audio bitrate: {AUDIO_BITRATE}")
    print(f"Audio channels: {AUDIO_CHANNELS}")
    print(f"Audio frame duration: {round(AUDIO_FRAME_DURATION * 1000)} ms")
    print(f"Audio frame size: {AUDIO_FRAME_SIZE}")
    print(f"Update interval: {round(SYNC_FREQUENCY * 1000)} ms")
    print("=" * 30)


def input_room_id() -> str:
    while True:
        room_id = input("Enter room ID: ").strip()
        try:
            validate_room_id(room_id)
            return room_id
        except argparse.ArgumentTypeError as e:
            print(f"[ERROR] {e}")


def get_and_start_player() -> AbstractAudioPlayer:
    print("Init audio player...")
    if ENABLE_AUDIO_PLAYER:
        try:
            player_class = AudioPlayer

        except sd.PortAudioError:
            print("[ERROR] Audio player device not found")
            player_class = VoidAudioPlayer
    else:
        player_class = VoidAudioPlayer

    player = player_class(
        sample_rate=AUDIO_SAMPLE_RATE,
        channels=AUDIO_CHANNELS,
        frame_size=AUDIO_FRAME_SIZE,
    )
    player.start()

    if player_class != VoidAudioPlayer:
        print("Audio player started")

    return player


def get_and_start_recorder() -> AbstractAudioRecorder:
    print("Init audio recorder...")
    if ENABLE_AUDIO_RECORDER:
        try:
            recorder_class = AudioRecorder
        except sd.PortAudioError:
            print("[ERROR] Audio recording device not found")
            recorder_class = VoidAudioRecorder
    else:
        recorder_class = VoidAudioRecorder

    recorder = recorder_class(
        sample_rate=AUDIO_SAMPLE_RATE,
        channels=AUDIO_CHANNELS,
        frame_size=AUDIO_FRAME_SIZE,
        time_buffer=TIME_BUFFER_SIZE,
    )
    recorder.start()

    if recorder_class != VoidAudioRecorder:
        print("Audio recording started")

    return recorder


def get_audio_lib() -> AbstractAudioLib:
    audio_lib_class = AUDIO_LIB_CLASS_MAP.get(AUDIO_CODEC)
    if audio_lib_class is None:
        raise ValueError(f"Unknown audio codec: {AUDIO_CODEC}")

    audio_lib = audio_lib_class(
        sample_rate=AUDIO_SAMPLE_RATE,
        bitrate=AUDIO_BITRATE,
        channels=AUDIO_CHANNELS,
        frame_size=AUDIO_FRAME_SIZE,
    )
    return audio_lib


def check_received_chunk(
    metadata: dict[str, any],
    audio_lib: AbstractAudioLib,
) -> bool:
    codec = metadata["codec"]
    sample_rate = metadata["sample_rate"]
    channels = metadata["channels"]

    if codec != audio_lib.CODEC:
        print(
            f"[ERROR] Received audio codec: {codec}, expected: {audio_lib.CODEC}",
            file=sys.stderr,
        )
        return False

    if sample_rate != audio_lib.sample_rate:
        print(
            f"[ERROR] Received sample rate: {sample_rate}, "
            f"expected: {audio_lib.sample_rate}"
        )
        return False

    if channels != audio_lib.channels:
        print(f"[ERROR] Received channels: {channels}, expected: {audio_lib.channels}")
        return False

    return True


def audio_test() -> None:
    recorder = get_and_start_recorder()

    time.sleep(0.5)
    c1 = recorder.get_chunk()

    time.sleep(1.2)
    c2 = recorder.get_chunk()

    time.sleep(0.3)
    c3 = recorder.get_chunk()

    time.sleep(3)
    c4 = recorder.get_chunk()

    c = c1 + c2 + c3 + c4
    print(f"Size: {len(c) / 1024 / 5:0.3f} KB/s")

    player = get_and_start_player()
    player.add(c)
    time.sleep(5.0)

    print("END")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("room_id", nargs="?", type=validate_room_id, help="Room ID")
    parser.add_argument("--audio-test", action="store_true")
    args = parser.parse_args()

    print_config()

    if args.audio_test:
        audio_test()
        return

    room_id = args.room_id or input_room_id()
    your_user_id = secrets.token_hex(16)
    print(f"Your user ID: {your_user_id}")
    user_set = {your_user_id}

    print("Time synchronization with server...")
    clock = ServerClock(url=f"{SERVER_URL}/api/time")
    await clock.sync()
    server_timestamp_accuracy = await clock.accuracy()

    player = get_and_start_player()
    recorder = get_and_start_recorder()
    audio_lib = get_audio_lib()

    try:
        call_start_time = time.perf_counter()
        requested_timestamp = await clock.timestamp()
        recorded_chunk_index = 0
        elapsed = SYNC_FREQUENCY
        request_timestamps = SlidingWindowRate(2.0)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(**SERVER_TIMEOUT),
        ) as client:
            while True:
                await asyncio.sleep(max(0.0, SYNC_FREQUENCY - elapsed))
                cycle_start_time = time.perf_counter()
                print(f"\n[{str(datetime.datetime.now().time())[:12]}]")

                chunk = recorder.get_chunk()
                encoded_chunk = audio_lib.encode(chunk)
                chunk_duration = audio_lib.get_duration(encoded_chunk)
                chunk_timestamp = await clock.timestamp() - chunk_duration
                recorded_chunk_index += 1

                print(
                    f"Recorded {round(chunk_duration * 1000)} ms "
                    f"({len(encoded_chunk) / 1024:.3f} KB)"
                )

                send_data = {
                    "format_version": FORMAT_VERSION,
                    "requested_timestamp": requested_timestamp,
                    "chunk": {
                        "index": recorded_chunk_index,
                        "user_id": your_user_id,
                        "timestamp": chunk_timestamp,
                        "duration": chunk_duration,
                        "codec": audio_lib.CODEC,
                        "sample_rate": audio_lib.sample_rate,
                        "channels": audio_lib.channels,
                    },
                }

                try:
                    print("Sending request to server...")
                    response = await client.post(
                        SYNC_CALL_URL.format(room_id=room_id),
                        files={
                            "audio": (
                                "audio",
                                encoded_chunk,
                                "application/octet-stream",
                            ),
                            "metadata": (
                                None,
                                json.dumps(send_data),
                                "application/json",
                            ),
                        },
                    )
                    ping = response.elapsed.total_seconds()
                    print(f"Ping: {round(ping * 1000)} ms")
                    response.raise_for_status()

                    response_timestamp = await clock.timestamp()
                    request_timestamps.add(response_timestamp)
                    sync_frequency = request_timestamps.average(
                        response_timestamp
                    )
                    print(f"Sync frequency: {sync_frequency:.1f} request/s")

                    if response.content:
                        received_chunks: list[tuple[dict[str, any], bytes]] = []

                        for data in response.content.split(CHUNK_SEPARATOR):
                            raw_metadata, chunk = data.split(CHUNK_DATA_SEPARATOR)
                            received_chunks.append(
                                (json.loads(raw_metadata.decode("utf-8")), chunk)
                            )

                        requested_timestamp = received_chunks[-1][0]["timestamp"]
                        player_queue_duration = player.get_queue_duration()

                        for metadata, chunk in received_chunks:
                            if not check_received_chunk(
                                metadata=metadata,
                                audio_lib=audio_lib,
                            ):
                                continue

                            user_id = metadata["user_id"]
                            if user_id not in user_set:
                                user_set.add(user_id)
                                print(f"User connected: {user_id[:6]}…")

                            chunk_index = metadata["index"]
                            chunk_duration = metadata["duration"]
                            print(
                                f"Received audio from user {user_id[:6]}…: "
                                f"#{chunk_index} "
                                f"{round(chunk_duration * 1000)} ms "
                                f"{len(chunk) / 1024:.3f} KB"
                            )
                            decoded_chunk = audio_lib.decode(chunk)
                            player.add(decoded_chunk)

                        first_timestamp = received_chunks[0][0]["timestamp"]
                        one_way_latency = response_timestamp - first_timestamp
                        audio_playback_delay = (
                            one_way_latency
                            + player_queue_duration
                            + player.latency
                            + recorder.latency
                            + server_timestamp_accuracy
                        )

                        print(
                            "Audio delivery latency: "
                            f"{round(one_way_latency * 1000)} ms"
                        )
                        print(
                            "Audio queue duration: "
                            f"{round(player_queue_duration * 1000)} ms"
                        )
                        print(
                            "End to end audio latency: "
                            f"{round(audio_playback_delay * 1000)} ms"
                        )

                except httpx.HTTPError as e:
                    print(f"[ERROR] {e.__class__} {e}")
                    await asyncio.sleep(2.0)

                cur_time = time.perf_counter()
                call_duration = int(cur_time - call_start_time)
                print(
                    f"Call duration: {call_duration // 60:02}:{call_duration % 60:02}"
                )

                elapsed = cur_time - cycle_start_time

    except asyncio.CancelledError:
        print()

    finally:
        player.stop()
        recorder.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
