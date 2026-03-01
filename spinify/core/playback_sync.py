"""Shared logic to sync tone-arm and platter to Spotify playback. Used by API and button service."""
import logging
from typing import Any

from spinify.core.playback_cooldown import is_rotation_scan_active, is_within_cooldown
from spinify.core.record_store import get_mapping_by_uid, load_mappings
from spinify.core.spotify_client import get_context_track_position, get_spotify_client

logger = logging.getLogger(__name__)


def _stop_platter_and_home(motor_service) -> None:
    """Stop turntable and move tone-arm to home. Idempotent."""
    logger.info("Sync: stopping platter and homing tone-arm")
    motor_service.turntable_stop()
    motor_service.move_tone_arm_to_angle(0.0)


def sync_tone_arm_and_platter_to_playback(motor_service, nfc_service) -> dict[str, Any]:
    """Sync tone-arm and platter to Spotify playback.

    Takes motor_service and nfc_service (no AppState). Only stops platter and
    homes tone-arm when we are certain playback stopped (no Spotify, playback
    error, or is_playing is False). Transient failures (no_playback, no_nfc,
    context_mismatch, etc.) are ignored so a single missed NFC read or Spotify
    API blip does not stop the platter.

    Returns a dict suitable for API response: ok, reason, and when ok=True
    also fraction, track_index, total_tracks.
    """
    sp = get_spotify_client()
    if sp is None:
        if is_within_cooldown():
            logger.debug("Sync: cooldown (no_spotify)")
            return {"ok": False, "reason": "cooldown"}
        _stop_platter_and_home(motor_service)
        logger.info("Sync: no Spotify client, stopped")
        return {"ok": False, "reason": "no_spotify"}

    try:
        pb = sp.current_playback()
    except Exception as e:
        if is_within_cooldown():
            logger.debug("Sync: cooldown (playback_error: %s)", e)
            return {"ok": False, "reason": "cooldown"}
        _stop_platter_and_home(motor_service)
        logger.warning("Sync: playback_error (%s), stopped", e)
        return {"ok": False, "reason": "playback_error"}

    if not pb:
        logger.debug("Sync: no_playback (transient, not stopping)")
        return {"ok": False, "reason": "no_playback"}

    is_playing = bool(pb.get("is_playing", False))
    context = pb.get("context") or {}
    context_uri = context.get("uri")
    item = pb.get("item") or {}
    track_uri = item.get("uri", "")
    position_ms = int(pb.get("progress_ms") or 0)
    duration_ms = int(item.get("duration_ms") or 0)

    if not is_playing:
        if is_within_cooldown():
            logger.debug("Sync: cooldown (paused)")
            return {"ok": False, "reason": "cooldown"}
        _stop_platter_and_home(motor_service)
        logger.info("Sync: paused, stopped")
        return {"ok": False, "reason": "paused"}

    placed = nfc_service.get_current()
    if placed is None:
        logger.debug("Sync: no_nfc (transient, not stopping)")
        return {"ok": False, "reason": "no_nfc"}

    mappings = load_mappings()
    mapping = get_mapping_by_uid(mappings, placed.nfc_uid)
    if mapping is None or not mapping.spotify_uri:
        logger.debug("Sync: no_mapping (not stopping)")
        return {"ok": False, "reason": "no_mapping"}

    if not context_uri or context_uri != mapping.spotify_uri:
        logger.debug("Sync: context_mismatch (not stopping)")
        return {"ok": False, "reason": "context_mismatch"}

    ctx_pos = get_context_track_position(context_uri, track_uri)
    if ctx_pos is None:
        logger.debug("Sync: context_position_unavailable")
        return {"ok": False, "reason": "context_position_unavailable"}

    if is_rotation_scan_active():
        logger.debug("Sync: rotation_scan_active, skipping (do not override platter/tone-arm)")
        return {"ok": False, "reason": "rotation_scan"}

    total_tracks = max(1, int(ctx_pos.get("total_tracks") or 1))
    track_index = max(0, int(ctx_pos.get("track_index") or 0))

    track_progress = 0.0
    if duration_ms > 0:
        track_progress = max(0.0, min(1.0, position_ms / duration_ms))

    playlist_fraction = (track_index + track_progress) / float(total_tracks)
    playlist_fraction = max(0.0, min(1.0, playlist_fraction))

    motor_service.turntable_start(direction=-1)
    motor_service.sync_tone_arm_to_fraction(playlist_fraction)

    logger.debug(
        "Sync: ok fraction=%.3f track=%s/%s",
        playlist_fraction,
        track_index + 1,
        total_tracks,
    )
    return {
        "ok": True,
        "fraction": playlist_fraction,
        "track_index": track_index,
        "total_tracks": total_tracks,
    }
