"""Shared serialization utilities for game state optimization using msgpack."""

import hashlib
from typing import Any

import msgpack


def pack_game_state(state_data: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """
    Pack game state using msgpack with statistics.

    Args:
        state_data: Dictionary representation of game state

    Returns:
        Tuple of (packed_bytes, stats_dict)
    """
    # Convert to msgpack binary format
    packed = msgpack.packb(state_data, use_bin_type=True)

    # Calculate statistics (comparing to JSON equivalent)
    import json

    json_size = len(json.dumps(state_data, separators=(",", ":")).encode("utf-8"))
    packed_size = len(packed)  # type: ignore
    size_reduction = (1 - packed_size / json_size) * 100 if json_size > 0 else 0

    stats = {
        "json_size": json_size,
        "packed_size": packed_size,
        "size_reduction": size_reduction,
        "format": "msgpack",
    }

    return packed, stats  # type: ignore


def unpack_game_state(packed_data: bytes) -> dict[str, Any]:
    """
    Unpack game state from msgpack format.

    Args:
        packed_data: Binary msgpack data

    Returns:
        Dictionary representation of game state
    """
    return msgpack.unpackb(packed_data, raw=False, strict_map_key=False)


def get_state_hash(state_data: dict[str, Any]) -> str:
    """
    Generate MD5 hash of state for change detection.

    Args:
        state_data: Dictionary representation of game state

    Returns:
        MD5 hash string
    """
    # Use msgpack for consistent hashing (more reliable than JSON)
    packed = msgpack.packb(state_data, use_bin_type=True)
    return hashlib.md5(packed).hexdigest()  # type: ignore
