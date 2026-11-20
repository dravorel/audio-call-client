import os
import re
import sys
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# ==========================================================
# Environment
# ==========================================================

load_dotenv()

FROZEN = getattr(sys, "frozen", False)


# ==========================================================
# Paths
# ==========================================================

if FROZEN:
    PROJECT_DIR = Path(sys.executable).parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_DIR))
else:
    PROJECT_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = PROJECT_DIR

EXTERNAL_DIR = RESOURCE_DIR / "external"


# ==========================================================
# Server
# ==========================================================

SERVER_URL = os.getenv("SERVER_URL")

if not SERVER_URL:
    raise ValueError("SERVER_URL is not configured in .env")

SYNC_CALL_URL = f"{SERVER_URL}/api/calls/{{room_id}}/sync"
SERVER_TIME_URL = f"{SERVER_URL}/api/time"

SERVER_TIMEOUT = {
    "connect": 5.0,
    "write": 10.0,
    "read": 30.0,
    "pool": 5.0,
}

# ==========================================================
# Audio
# ==========================================================

SupportedAudioCodec = Literal["pcm", "opus"]

FORMAT_VERSION = 1
AUDIO_CODEC: SupportedAudioCodec = "opus"
AUDIO_SAMPLE_RATE = 48_000
AUDIO_BITRATE = 32_000
AUDIO_CHANNELS = 1
AUDIO_FRAME_DURATION = 0.020
AUDIO_FRAME_SIZE = round(AUDIO_SAMPLE_RATE * AUDIO_FRAME_DURATION)
AUDIO_SAMPLE_WIDTH = 2

TIME_BUFFER_SIZE = 2.0

ENABLE_AUDIO_PLAYER = True
ENABLE_AUDIO_RECORDER = True


# ==========================================================
# Synchronization
# ==========================================================

SYNC_FREQUENCY = 0.1


# ==========================================================
# Protocol
# ==========================================================

CHUNK_DATA_SEPARATOR = b"--- BINARY DATA ---"
CHUNK_SEPARATOR = b"--- CHUNK SEPARATOR ---"


# ==========================================================
# Validation
# ==========================================================

ROOM_ID_REGEX = re.compile(r"^[A-Za-z_]{1,30}$")
