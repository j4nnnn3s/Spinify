"""Persist and load record mappings (JSON)."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from spinify.config import RECORD_MAPPINGS_PATH, ensure_data_dir
from spinify.models.record import RecordMapping


def _path() -> Path:
    ensure_data_dir()
    return RECORD_MAPPINGS_PATH


def load_mappings() -> List[RecordMapping]:
    """Load all record mappings from disk."""
    p = _path()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for item in data.get("records", []):
        try:
            out.append(
                RecordMapping(
                    record_id=item["record_id"],
                    nfc_uid=item["nfc_uid"],
                    name=item["name"],
                    spotify_uri=item["spotify_uri"],
                    type=item["type"],
                    created_at=item["created_at"],
                )
            )
        except (KeyError, TypeError):
            continue
    return out


def save_mappings(mappings: List[RecordMapping]) -> None:
    """Save all record mappings to disk."""
    p = _path()
    data = {
        "records": [
            {
                "record_id": m.record_id,
                "nfc_uid": m.nfc_uid,
                "name": m.name,
                "spotify_uri": m.spotify_uri,
                "type": m.type,
                "created_at": m.created_at,
            }
            for m in mappings
        ]
    }
    p.write_text(json.dumps(data, indent=2))


def get_mapping_by_uid(mappings: List[RecordMapping], nfc_uid: str) -> Optional[RecordMapping]:
    """Return mapping for NFC UID or None."""
    for m in mappings:
        if m.nfc_uid.lower() == nfc_uid.lower():
            return m
    return None


def get_mapping_by_id(mappings: List[RecordMapping], record_id: str) -> Optional[RecordMapping]:
    """Return mapping by record_id or None."""
    for m in mappings:
        if m.record_id == record_id:
            return m
    return None


def add_mapping(
    mappings: List[RecordMapping],
    nfc_uid: str,
    name: str,
    spotify_uri: str,
    type_: str,
) -> RecordMapping:
    """Append a new mapping and save. type_ is 'album' or 'playlist'."""
    record_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    m = RecordMapping(
        record_id=record_id,
        nfc_uid=nfc_uid,
        name=name,
        spotify_uri=spotify_uri,
        type=type_,
        created_at=created_at,
    )
    mappings.append(m)
    save_mappings(mappings)
    return m


def update_mapping(
    mappings: List[RecordMapping],
    record_id: str,
    *,
    name: Optional[str] = None,
    spotify_uri: Optional[str] = None,
    type_: Optional[str] = None,
) -> Optional[RecordMapping]:
    """Update mapping by record_id; save. Returns updated mapping or None."""
    for i, m in enumerate(mappings):
        if m.record_id == record_id:
            new_name = name if name is not None else m.name
            new_uri = spotify_uri if spotify_uri is not None else m.spotify_uri
            new_type = type_ if type_ is not None else m.type
            updated = RecordMapping(
                m.record_id, m.nfc_uid, new_name, new_uri, new_type, m.created_at
            )
            mappings[i] = updated
            save_mappings(mappings)
            return updated
    return None


def delete_mapping(mappings: List[RecordMapping], record_id: str) -> bool:
    """Remove mapping by record_id; save. Returns True if found and removed."""
    for i, m in enumerate(mappings):
        if m.record_id == record_id:
            mappings.pop(i)
            save_mappings(mappings)
            return True
    return False
