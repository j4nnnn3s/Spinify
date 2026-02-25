"""Record metadata and placed-record state."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class PlacedRecord:
    """In-memory state: currently placed record from NFC read."""
    nfc_uid: str
    spotify_uri: Optional[str]


@dataclass
class RecordMapping:
    """Stored mapping: NFC UID to Spotify album/playlist (in record_mappings.json)."""
    record_id: str
    nfc_uid: str
    name: str
    spotify_uri: str
    type: str  # "album" | "playlist"
    created_at: str
