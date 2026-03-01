"""Tone-arm and turntable motor endpoints."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from spinify.api.state import AppState, get_state
from spinify.config import STEPS_PER_REV
from spinify.core.playback_sync import sync_tone_arm_and_platter_to_playback

router = APIRouter()


class ToneArmBody(BaseModel):
    position: Literal["absolute", "relative"] = "relative"
    steps: Optional[int] = None
    angle_deg: Optional[float] = None
    from_settings: bool = False


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
        state.motor_service.move_tone_arm(
            body.steps,
            absolute=(body.position == "absolute"),
            from_settings=body.from_settings,
        )
        return {"ok": True}
    return {"ok": False, "error": "Provide steps or angle_deg"}


@router.post("/tone-arm/sync")
def sync_tone_arm(state: AppState = Depends(get_state)):
    """Sync tone-arm and platter to Spotify playback. Stop platter when paused or context mismatch."""
    return sync_tone_arm_and_platter_to_playback(state.motor_service, state.nfc_service)


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
