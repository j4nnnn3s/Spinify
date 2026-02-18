"""Playback state from Spotify."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlaybackState:
    """Current playback state from Spotify API."""
    is_playing: bool
    context_uri: Optional[str]
    track_uri: str
    track_index: int
    position_ms: int
    duration_ms: int
    track_name: str
    album_name: str
    artist_name: str
