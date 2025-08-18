"""Network compression utilities for game state optimization."""

import gzip
import hashlib


def compress_game_state(state_json: str) -> tuple[bytes, dict]:
    """
    Compress game state JSON and return compression stats.

    Returns:
        Tuple of (compressed_bytes, stats_dict)
    """
    data_bytes = state_json.encode("utf-8")
    compressed = gzip.compress(data_bytes, compresslevel=6)

    original_size = len(data_bytes)
    compressed_size = len(compressed)
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

    stats = {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": compression_ratio,
    }

    return compressed, stats


def get_state_hash(state_json: str) -> str:
    """Generate MD5 hash of state for change detection."""
    return hashlib.md5(state_json.encode("utf-8")).hexdigest()


def decompress_game_state(compressed_data: bytes) -> str:
    """Decompress game state data."""
    return gzip.decompress(compressed_data).decode("utf-8")
