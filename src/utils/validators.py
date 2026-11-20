import argparse
import re

from config import ROOM_ID_REGEX


def validate_room_id(value: str) -> str:
    if not re.fullmatch(ROOM_ID_REGEX, value):
        raise argparse.ArgumentTypeError(
            "Room ID must contain only latin letters, numbers and underscores"
        )

    return value
