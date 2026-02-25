"""Record mappings CRUD: NFC UID to Spotify album/playlist (stored in JSON)."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from spinify.api.state import AppState, get_state
from spinify.core.record_store import (
    add_mapping,
    delete_mapping,
    get_mapping_by_id,
    load_mappings,
    update_mapping,
)
from spinify.core.spotify_client import get_metadata_for_uri

router = APIRouter()

# Parse Spotify web URL to URI (same as web spotify.ts)
_SPOTIFY_URL_REGEX = re.compile(
    r"^https?://(?:open\.)?spotify\.com/(album|playlist)/([a-zA-Z0-9]+)(?:\?|$)",
    re.IGNORECASE,
)


def _parse_spotify_url(url: str) -> Optional[tuple[str, str]]:
    """Return (type, uri) e.g. ('album', 'spotify:album:id') or None."""
    match = _SPOTIFY_URL_REGEX.match(url.strip())
    if not match:
        return None
    kind, id_ = match.group(1).lower(), match.group(2)
    type_ = "album" if kind == "album" else "playlist"
    uri = f"spotify:{type_}:{id_}"
    return (type_, uri)


class CreateRecordBody(BaseModel):
    nfc_uid: str
    spotify_uri: Optional[str] = None
    spotify_url: Optional[str] = None


class UpdateRecordBody(BaseModel):
    name: Optional[str] = None
    spotify_uri: Optional[str] = None
    spotify_url: Optional[str] = None
    type: Optional[str] = None


def _record_to_dict(m):
    return {
        "record_id": m.record_id,
        "nfc_uid": m.nfc_uid,
        "name": m.name,
        "spotify_uri": m.spotify_uri,
        "type": m.type,
        "created_at": m.created_at,
    }


@router.get("/")
def list_records(state: AppState = Depends(get_state)):
    """List all record mappings."""
    mappings = load_mappings()
    return [_record_to_dict(m) for m in mappings]


@router.post("/")
def create_record(
    body: CreateRecordBody,
    state: AppState = Depends(get_state),
):
    """Create a record mapping. Provide spotify_uri or spotify_url; type and name are fetched from Spotify."""
    if not body.spotify_uri and not body.spotify_url:
        raise HTTPException(
            status_code=400,
            detail="Provide spotify_uri or spotify_url",
        )
    if body.spotify_url:
        parsed = _parse_spotify_url(body.spotify_url)
        if not parsed:
            raise HTTPException(status_code=400, detail="Invalid Spotify URL")
        _, spotify_uri = parsed
    else:
        spotify_uri = body.spotify_uri

    meta = get_metadata_for_uri(spotify_uri)
    if meta:
        name, type_ = meta.get("name") or "", meta.get("type") or "playlist"
    else:
        name, type_ = "", "playlist"
        if ":" in spotify_uri:
            parts = spotify_uri.split(":")
            if len(parts) >= 2:
                type_ = parts[1].lower() if parts[1].lower() in ("album", "playlist") else "playlist"

    mappings = load_mappings()
    record = add_mapping(mappings, body.nfc_uid, name, spotify_uri, type_)
    return _record_to_dict(record)


@router.patch("/{record_id}")
def update_record(
    record_id: str,
    body: UpdateRecordBody,
    state: AppState = Depends(get_state),
):
    """Update a record mapping. If spotify_uri/spotify_url changes, type and name are re-fetched from Spotify unless provided."""
    mappings = load_mappings()
    existing = get_mapping_by_id(mappings, record_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Record not found")

    spotify_uri = existing.spotify_uri
    if body.spotify_url:
        parsed = _parse_spotify_url(body.spotify_url)
        if not parsed:
            raise HTTPException(status_code=400, detail="Invalid Spotify URL")
        _, spotify_uri = parsed
    elif body.spotify_uri is not None:
        spotify_uri = body.spotify_uri

    name = body.name if body.name is not None else existing.name
    type_ = body.type if body.type is not None else existing.type

    if spotify_uri != existing.spotify_uri:
        meta = get_metadata_for_uri(spotify_uri)
        if meta:
            name = meta.get("name") or name
            type_ = meta.get("type") or type_

    updated = update_mapping(
        mappings,
        record_id,
        name=name,
        spotify_uri=spotify_uri,
        type_=type_,
    )
    return _record_to_dict(updated)


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: str,
    state: AppState = Depends(get_state),
):
    """Delete a record mapping."""
    mappings = load_mappings()
    if not delete_mapping(mappings, record_id):
        raise HTTPException(status_code=404, detail="Record not found")
