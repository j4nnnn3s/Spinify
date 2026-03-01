"""Cooldown after local playback start and rotation-scan guard so periodic sync does not interfere."""
import time

COOLDOWN_SEC = 3.0

_last_local_start_monotonic: float = 0.0
_rotation_scan_until: float = 0.0


def record_local_start() -> None:
    """Call when playback was just started locally (button or API)."""
    global _last_local_start_monotonic
    _last_local_start_monotonic = time.monotonic()


def is_within_cooldown() -> bool:
    """True if we are within COOLDOWN_SEC of the last local start (sync should not stop platter)."""
    return (time.monotonic() - _last_local_start_monotonic) < COOLDOWN_SEC


def set_rotation_scan_until(monotonic_deadline: float) -> None:
    """Call when starting NFC rotation scan; playback_sync will not touch platter/tone-arm until this time."""
    global _rotation_scan_until
    _rotation_scan_until = monotonic_deadline


def is_rotation_scan_active() -> bool:
    """True if we are in the NFC rotation scan window (sync should not change platter direction or tone-arm)."""
    return time.monotonic() < _rotation_scan_until
