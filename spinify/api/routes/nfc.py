"""NFC current record and scan endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends

from spinify.api.state import AppState, get_state
from spinify.core.spotify_client import get_cover_url_for_uri
from spinify.models.record import RecordMapping

router = APIRouter()


def _mapping_to_dict(m: RecordMapping) -> dict:
    return {
        "record_id": m.record_id,
        "nfc_uid": m.nfc_uid,
        "name": m.name,
        "spotify_uri": m.spotify_uri,
        "type": m.type,
        "created_at": m.created_at,
    }


@router.get("/current")
def get_current(state: AppState = Depends(get_state)):
    """Return currently placed record (UID + mapping if known)."""
    placed = state.nfc_service.get_current()
    if placed is None:
        return {"uid": None, "record": None, "record_cover_url": None}
    record_dict = _mapping_to_dict(placed.mapping) if placed.mapping else None
    record_cover_url = None
    if placed.mapping and placed.mapping.spotify_uri:
        record_cover_url = get_cover_url_for_uri(placed.mapping.spotify_uri)
    return {
        "uid": placed.nfc_uid,
        "record": record_dict,
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
    state: AppState = Depends(get_state),
):
    """For development: set simulated UID when hardware is simulated."""
    state.nfc_service.set_simulated_uid(uid)
    return {"ok": True, "uid": uid}
