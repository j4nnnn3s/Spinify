"""Tone-arm and turntable motor endpoints."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from spinify.api.state import AppState, get_state
from spinify.config import STEPS_PER_REV, TONE_ARM_STEPS_PER_REV, TURNTABLE_TARGET_RPM
from spinify.core.record_store import get_mapping_by_uid, load_mappings
from spinify.core.spotify_client import get_context_track_position, get_spotify_client

router = APIRouter()


class ToneArmBody(BaseModel):
    position: Literal["absolute", "relative"] = "relative"
    steps: Optional[int] = None
    angle_deg: Optional[float] = None


class TurntableStartBody(BaseModel):
    direction: int = 1
    speed_rpm: Optional[float] = None


@router.get("/tone-arm")
def get_tone_arm(state: AppState = Depends(get_state)):
    """Return current tone-arm position."""
    pos = state.motor_service.get_tone_arm_position()
    return {
        "steps_from_home": pos.steps_from_home,
        "angle_deg": pos.current_angle_deg,
        "total_steps_per_rev": pos.total_steps_per_rev,
    }


@router.post("/tone-arm")
def post_tone_arm(body: ToneArmBody, state: AppState = Depends(get_state)):
    """Move tone-arm by steps (relative/absolute) or to angle_deg."""
    if body.angle_deg is not None:
        state.motor_service.move_tone_arm_to_angle(body.angle_deg)
        return {"ok": True}
    if body.steps is not None:
        state.motor_service.move_tone_arm(body.steps, absolute=(body.position == "absolute"))
        return {"ok": True}
    return {"ok": False, "error": "Provide steps or angle_deg"}


@router.post("/tone-arm/sync")
def sync_tone_arm(state: AppState = Depends(get_state)):
    """Sync tone-arm position with current Spotify playback if NFC record matches context."""
    # Get current NFC-mapped record
    placed = state.nfc_service.get_current()
    if placed is None:
        return {"ok": False, "reason": "no_nfc"}

    mappings = load_mappings()
    mapping = get_mapping_by_uid(mappings, placed.nfc_uid)
    if mapping is None or not mapping.spotify_uri:
        return {"ok": False, "reason": "no_mapping"}

    sp = get_spotify_client()
    if sp is None:
        return {"ok": False, "reason": "no_spotify"}

    try:
        pb = sp.current_playback()
    except Exception:
        state.motor_service.turntable_stop()
        state.motor_service.move_tone_arm_to_angle(0.0)
        return {"ok": False, "reason": "playback_error"}

    if not pb:
        state.motor_service.turntable_stop()
        state.motor_service.move_tone_arm_to_angle(0.0)
        return {"ok": False, "reason": "no_playback"}

    is_playing = bool(pb.get("is_playing", False))
    context = pb.get("context") or {}
    context_uri = context.get("uri")
    item = pb.get("item") or {}
    track_uri = item.get("uri", "")
    position_ms = int(pb.get("progress_ms") or 0)
    duration_ms = int(item.get("duration_ms") or 0)

    # If playback is paused, always stop spinning and send tone-arm home.
    if not is_playing:
        state.motor_service.turntable_stop()
        state.motor_service.move_tone_arm_to_angle(0.0)
        return {"ok": False, "reason": "paused"}

    # If another playlist/album is playing, stop spinning and send tone-arm home.
    if not context_uri or context_uri != mapping.spotify_uri:
        state.motor_service.turntable_stop()
        state.motor_service.move_tone_arm_to_angle(0.0)
        return {"ok": False, "reason": "context_mismatch"}

    ctx_pos = get_context_track_position(context_uri, track_uri)
    if ctx_pos is None:
        return {"ok": False, "reason": "context_position_unavailable"}

    total_tracks = max(1, int(ctx_pos.get("total_tracks") or 1))
    track_index = max(0, int(ctx_pos.get("track_index") or 0))

    # Fraction within current track
    track_progress = 0.0
    if duration_ms > 0:
        track_progress = max(0.0, min(1.0, position_ms / duration_ms))

    playlist_fraction = (track_index + track_progress) / float(total_tracks)
    playlist_fraction = max(0.0, min(1.0, playlist_fraction))

    state.motor_service.sync_tone_arm_to_fraction(playlist_fraction)

    return {
        "ok": True,
        "fraction": playlist_fraction,
        "track_index": track_index,
        "total_tracks": total_tracks,
    }


@router.get("/turntable")
def get_turntable(state: AppState = Depends(get_state)):
    """Return turntable spin state."""
    s = state.motor_service.get_turntable_state()
    rpm = (s.current_speed_steps_per_sec / STEPS_PER_REV) * 60.0
    return {
        "is_spinning": s.is_spinning,
        "direction": s.direction,
        "speed_rpm": round(rpm, 2),
    }


@router.post("/turntable/start")
def turntable_start(body: TurntableStartBody, state: AppState = Depends(get_state)):
    """Start turntable with optional direction and speed_rpm."""
    state.motor_service.turntable_start(
        direction=body.direction, speed_rpm=body.speed_rpm
    )
    return {"ok": True}


@router.post("/turntable/stop")
def turntable_stop(state: AppState = Depends(get_state)):
    """Stop turntable with deceleration."""
    state.motor_service.turntable_stop()
    return {"ok": True}
