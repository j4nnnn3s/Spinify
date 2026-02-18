"""CRUD for record ↔ album/playlist mapping."""
import re
from typing import Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from spinify.api.state import AppState, get_state
from spinify.models.record import RecordMapping

router = APIRouter()

# e.g. https://open.spotify.com/playlist/0LJtBRZxHuskZSvIua9FfI?si=...
_SPOTIFY_URL_RE = re.compile(
    r"^https?://(?:open\.)?spotify\.com/(album|playlist)/([a-zA-Z0-9]+)(?:\?|$)",
    re.IGNORECASE,
)


def _normalize_spotify_uri(uri: str, type_: Literal["album", "playlist"]) -> Tuple[str, Literal["album", "playlist"]]:
    """Convert Spotify URL to spotify:type:id, or return (uri, type_) as-is."""
    uri = uri.strip()
    m = _SPOTIFY_URL_RE.search(uri)
    if m:
        kind, id_ = m.group(1), m.group(2)
        return f"spotify:{kind}:{id_}", "album" if kind == "album" else "playlist"
    return uri, type_


class CreateRecordBody(BaseModel):
    nfc_uid: str
    name: str
    spotify_uri: str
    type: Literal["album", "playlist"]


class PatchRecordBody(BaseModel):
    name: Optional[str] = None
    spotify_uri: Optional[str] = None
    type: Optional[Literal["album", "playlist"]] = None


def _mapping_to_dict(m: RecordMapping) -> dict:
    return {
        "record_id": m.record_id,
        "nfc_uid": m.nfc_uid,
        "name": m.name,
        "spotify_uri": m.spotify_uri,
        "type": m.type,
        "created_at": m.created_at,
    }


@router.get("")
def list_records(state: AppState = Depends(get_state)):
    """Return all record mappings."""
    return {"records": [_mapping_to_dict(m) for m in state.get_mappings()]}


@router.post("")
def create_record(body: CreateRecordBody, state: AppState = Depends(get_state)):
    """Create a new record mapping. Accepts Spotify URL or spotify:type:id URI."""
    uri, type_ = _normalize_spotify_uri(body.spotify_uri, body.type)
    m = state.add_mapping(body.nfc_uid, body.name, uri, type_)
    return _mapping_to_dict(m)


@router.patch("/{record_id}")
def patch_record(record_id: str, body: PatchRecordBody, state: AppState = Depends(get_state)):
    """Update a record mapping. Accepts Spotify URL or spotify:type:id URI for spotify_uri."""
    uri = body.spotify_uri
    type_ = body.type
    if uri is not None:
        uri, inferred_type = _normalize_spotify_uri(uri, type_ or "playlist")
        if type_ is None:
            type_ = inferred_type
    m = state.update_mapping(
        record_id, name=body.name, spotify_uri=uri, type_=type_
    )
    if m is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return _mapping_to_dict(m)


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: str, state: AppState = Depends(get_state)):
    """Delete a record mapping."""
    if not state.delete_mapping(record_id):
        raise HTTPException(status_code=404, detail="Record not found")
