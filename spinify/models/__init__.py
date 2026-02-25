"""Data models for records, playback, and motors."""
from spinify.models.record import PlacedRecord
from spinify.models.playback import PlaybackState
from spinify.models.motors import SpinState, ToneArmPosition

__all__ = [
    "PlacedRecord",
    "PlaybackState",
    "ToneArmPosition",
    "SpinState",
]
