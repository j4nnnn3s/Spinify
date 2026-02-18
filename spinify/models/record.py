"""Record metadata and placed-record state."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RecordMapping:
    """Stored mapping: NFC UID -> Spotify album/playlist."""
    record_id: str
    nfc_uid: str
    name: str
    spotify_uri: str
    type: str  # "album" | "playlist"
    created_at: str


@dataclass
class PlacedRecord:
    """In-memory state: currently placed record from NFC read."""
    nfc_uid: str
    record_id: Optional[str]
    mapping: Optional[RecordMapping]
