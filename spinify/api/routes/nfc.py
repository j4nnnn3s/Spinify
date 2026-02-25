"""NFC current record and scan endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends

from spinify.api.state import AppState, get_state
from spinify.core.record_store import get_mapping_by_uid, load_mappings
from spinify.core.spotify_client import get_cover_url_for_uri

router = APIRouter()


@router.get("/current")
def get_current(state: AppState = Depends(get_state)):
    """Return currently placed record (UID + Spotify URI from record_store)."""
    placed = state.nfc_service.get_current()
    if placed is None:
        return {"uid": None, "spotify_uri": None, "record_name": None, "record_cover_url": None}

    mappings = load_mappings()
    mapping = get_mapping_by_uid(mappings, placed.nfc_uid)
    spotify_uri = mapping.spotify_uri if mapping else None
    record_name = mapping.name if mapping else None
    record_cover_url = get_cover_url_for_uri(spotify_uri) if spotify_uri else None

    return {
        "uid": placed.nfc_uid,
        "spotify_uri": spotify_uri,
        "record_name": record_name,
        "record_cover_url": record_cover_url,
    }


@router.post("/scan")
def scan_once(state: AppState = Depends(get_state)):
    """One-shot NFC read; returns UID if tag present."""
    uid = state.nfc_service.scan_once()
    return {"uid": uid}


@router.post("/simulate")
def simulate_uid(
    uid: Optional[str] = None,
    spotify_uri: Optional[str] = None,
    state: AppState = Depends(get_state),
):
    """For development: set simulated UID when hardware is simulated."""
    state.nfc_service.set_simulated_uid(uid, spotify_uri)
    return {"ok": True, "uid": uid, "spotify_uri": spotify_uri}
