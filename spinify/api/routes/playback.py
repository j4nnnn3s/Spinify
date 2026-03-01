"""Playback start/stop and current state (Spotify)."""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from spinify.api.state import AppState, get_state
from spinify.core.playback_cooldown import record_local_start
from spinify.core.spotify_client import get_spotify_client, start_playback_with_fallback

router = APIRouter()


def _empty_playback():
    return {
        "is_playing": False,
        "context_uri": None,
        "context_image_url": None,
        "track_uri": "",
        "track_index": 0,
        "position_ms": 0,
        "duration_ms": 0,
        "track_name": "",
        "album_name": "",
        "artist_name": "",
    }


def _map_playback(pb: dict) -> dict:
    """Map Spotify current_playback() response to our API shape."""
    if not pb:
        return _empty_playback()
    item = pb.get("item") or {}
    album = item.get("album") or {}
    artists = item.get("artists") or []
    context = pb.get("context") or {}
    images = album.get("images") or []
    context_image_url = images[0]["url"] if images else None
    return {
        "is_playing": bool(pb.get("is_playing", False)),
        "context_uri": context.get("uri"),
        "context_image_url": context_image_url,
        "track_uri": item.get("uri", ""),
        "track_index": max(0, (item.get("track_number") or 1) - 1),
        "position_ms": int(pb.get("progress_ms") or 0),
        "duration_ms": int(item.get("duration_ms") or 0),
        "track_name": item.get("name", ""),
        "album_name": album.get("name", ""),
        "artist_name": ", ".join(a.get("name", "") for a in artists),
    }


@router.get("")
def get_playback(state: AppState = Depends(get_state)):
    """Return current playback state from Spotify."""
    sp = get_spotify_client()
    if sp is None:
        return _empty_playback()
    try:
        pb = sp.current_playback()
        return _map_playback(pb)
    except Exception:
        return _empty_playback()


class PlaybackStartBody(BaseModel):
    context_uri: Optional[str] = None


@router.post("/start")
def playback_start(
    body: PlaybackStartBody | None = Body(None),
    state: AppState = Depends(get_state),
):
    """Start playback; optional context_uri (album or playlist URI)."""
    sp = get_spotify_client()
    if sp is None:
        raise HTTPException(
            status_code=503,
            detail="Spotify not linked. Use the Connect page to log in.",
        )
    context_uri = body.context_uri if body else None
    try:
        start_playback_with_fallback(context_uri=context_uri)
        record_local_start()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/stop")
def playback_stop(state: AppState = Depends(get_state)):
    """Stop (pause) playback."""
    sp = get_spotify_client()
    if sp is None:
        raise HTTPException(
            status_code=503,
            detail="Spotify not linked. Use the Connect page to log in.",
        )
    try:
        sp.pause_playback()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/position")
def get_position(state: AppState = Depends(get_state)):
    """Return position for tone-arm sync."""
    sp = get_spotify_client()
    if sp is None:
        return {"position_ms": 0, "duration_ms": 0, "track_index": 0}
    try:
        pb = sp.current_playback()
        if not pb:
            return {"position_ms": 0, "duration_ms": 0, "track_index": 0}
        item = pb.get("item") or {}
        return {
            "position_ms": int(pb.get("progress_ms") or 0),
            "duration_ms": int(item.get("duration_ms") or 0),
            "track_index": max(0, (item.get("track_number") or 1) - 1),
        }
    except Exception:
        return {"position_ms": 0, "duration_ms": 0, "track_index": 0}
