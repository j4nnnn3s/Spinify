"""Physical button: start/stop playback for the current NFC record."""
import logging
import threading
import time

from spinify.core.playback_cooldown import record_local_start, set_rotation_scan_until
from spinify.core.playback_sync import sync_tone_arm_and_platter_to_playback
from spinify.config import (
    PIN_BUTTON,
    SIMULATE_HARDWARE,
    STEPS_PER_REV,
    TURNTABLE_TARGET_STEPS_PER_SEC,
)

logger = logging.getLogger(__name__)

_GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    pass

POLL_INTERVAL_SEC = 0.02
DEBOUNCE_SEC = 0.4
NFC_SCAN_INTERVAL_SEC = 0.25

# After starting a rotation scan, ignore "pause" for this long so we don't stop the platter
# when the next poll sees NFC + playing (tag was just found by the scan).
_rotation_scan_cooldown_until = 0.0


def _shorten_rotation_scan_cooldown() -> None:
    """Call when we found a tag and started playback; allow pause after a short window."""
    global _rotation_scan_cooldown_until
    _rotation_scan_cooldown_until = time.monotonic() + 1.5


def _normalize_uri(uri: str | None) -> str:
    """Normalize for comparison (strip, lower)."""
    return (uri or "").strip().lower()


def _spotify_uri_id(uri: str | None) -> str | None:
    """Extract Spotify ID from spotify:type:id or https://open.spotify.com/type/id for comparison."""
    u = (uri or "").strip().lower()
    if not u:
        return None
    if ":" in u:
        return u.split(":")[-1].split("?")[0]
    if "spotify.com/" in u:
        parts = u.split("spotify.com/")[-1].split("/")
        return parts[0].split("?")[0] if parts else None
    return None


NFC_SCAN_ROTATIONS = 3  # Number of full platter rotations while scanning for NFC tag


def _on_nfc_tag_found(nfc_service, motor_service, mapping) -> bool:
    """Start playback for mapping and sync tone-arm. Returns True if successful."""
    from spinify.core.spotify_client import get_spotify_client, start_playback_with_fallback

    sp = get_spotify_client()
    if sp is None:
        return False
    try:
        start_playback_with_fallback(context_uri=mapping.spotify_uri)
        record_local_start()
        logger.info("Button: found tag, started %s", mapping.spotify_uri)
    except Exception as e:
        logger.warning("Button: start_playback failed: %s", e)
        return False
    _shorten_rotation_scan_cooldown()  # Allow pause after ~1.5 s instead of full scan duration
    time.sleep(0.4)
    for _ in range(2):
        result = sync_tone_arm_and_platter_to_playback(motor_service, nfc_service)
        if result.get("ok"):
            logger.info("Button: synced tone-arm to fraction %.3f", result.get("fraction", 0))
            return True
        time.sleep(0.3)
    return True


def _rotation_scan_for_nfc(nfc_service, motor_service) -> None:
    """Start platter (direction=-1), run multiple rotations while polling NFC; start playback if tag found, else stop platter.
    Used when platter is not spinning; sync is blocked from touching platter during this scan.
    """
    from spinify.core.record_store import get_mapping_by_uid, load_mappings

    one_rotation_sec = STEPS_PER_REV / TURNTABLE_TARGET_STEPS_PER_SEC
    scan_duration_sec = NFC_SCAN_ROTATIONS * one_rotation_sec
    motor_service.turntable_start(direction=-1)  # Inverted direction for scan
    start = time.monotonic()
    while time.monotonic() - start < scan_duration_sec:
        time.sleep(NFC_SCAN_INTERVAL_SEC)
        placed = nfc_service.get_current()
        if placed is None:
            continue
        mappings = load_mappings()
        mapping = get_mapping_by_uid(mappings, placed.nfc_uid)
        if mapping is None or not mapping.spotify_uri:
            continue
        _on_nfc_tag_found(nfc_service, motor_service, mapping)
        return
    motor_service.turntable_stop()
    logger.info("Button: rotation scan finished, no tag read, stopped platter")


def _poll_nfc_while_spinning(nfc_service, motor_service) -> None:
    """Poll NFC for a scan duration without touching the platter (use existing spin from sync).
    If tag with mapping found, start playback and sync; else stop platter after timeout.
    """
    from spinify.core.record_store import get_mapping_by_uid, load_mappings

    one_rotation_sec = STEPS_PER_REV / TURNTABLE_TARGET_STEPS_PER_SEC
    scan_duration_sec = NFC_SCAN_ROTATIONS * one_rotation_sec
    start = time.monotonic()
    while time.monotonic() - start < scan_duration_sec:
        time.sleep(NFC_SCAN_INTERVAL_SEC)
        placed = nfc_service.get_current()
        if placed is None:
            continue
        mappings = load_mappings()
        mapping = get_mapping_by_uid(mappings, placed.nfc_uid)
        if mapping is None or not mapping.spotify_uri:
            continue
        _on_nfc_tag_found(nfc_service, motor_service, mapping)
        return
    motor_service.turntable_stop()
    logger.info("Button: poll-while-spinning finished, no tag read, stopped platter")


def _toggle_playback_for_current_record(nfc_service, motor_service) -> None:
    """Toggle playback only for the playlist/album of the current NFC record; also control platter and tone-arm."""
    global _rotation_scan_cooldown_until
    from spinify.core.record_store import get_mapping_by_uid, load_mappings
    from spinify.core.spotify_client import get_spotify_client, start_playback_with_fallback

    one_rotation_sec = STEPS_PER_REV / TURNTABLE_TARGET_STEPS_PER_SEC
    scan_duration_sec = NFC_SCAN_ROTATIONS * one_rotation_sec

    placed = nfc_service.get_current()
    if placed is None:
        # NFC missed a read – if platter is spinning and something is playing, user likely wants to pause
        if motor_service.get_turntable_state().is_spinning:
            sp = get_spotify_client()
            if sp:
                try:
                    pb = sp.current_playback()
                    if pb and pb.get("is_playing"):
                        logger.info("Button: no NFC read but platter spinning and playing – pausing")
                        try:
                            sp.pause_playback()
                            motor_service.turntable_stop()
                            motor_service.move_tone_arm_to_angle(0.0)
                        except Exception as e:
                            logger.warning("Button: pause/stop failed: %s", e)
                        return
                except Exception as e:
                    logger.warning("Button: current_playback failed: %s", e)
            logger.debug("Button: no NFC record, platter spinning – polling for tag")
            _rotation_scan_cooldown_until = time.monotonic() + scan_duration_sec
            thread = threading.Thread(
                target=_poll_nfc_while_spinning,
                args=(nfc_service, motor_service),
                daemon=True,
            )
            thread.start()
            return
        logger.debug("Button: no NFC record, starting rotation scan")
        _rotation_scan_cooldown_until = time.monotonic() + scan_duration_sec
        set_rotation_scan_until(_rotation_scan_cooldown_until)
        thread = threading.Thread(
            target=_rotation_scan_for_nfc,
            args=(nfc_service, motor_service),
            daemon=True,
        )
        thread.start()
        return
    mappings = load_mappings()
    mapping = get_mapping_by_uid(mappings, placed.nfc_uid)
    if mapping is None or not mapping.spotify_uri:
        _rotation_scan_cooldown_until = time.monotonic() + scan_duration_sec
        if motor_service.get_turntable_state().is_spinning:
            logger.info("Button: no mapping for current record, platter already spinning – polling for tag")
            thread = threading.Thread(
                target=_poll_nfc_while_spinning,
                args=(nfc_service, motor_service),
                daemon=True,
            )
        else:
            logger.info("Button: no mapping for current record, starting rotation scan")
            set_rotation_scan_until(_rotation_scan_cooldown_until)
            thread = threading.Thread(
                target=_rotation_scan_for_nfc,
                args=(nfc_service, motor_service),
                daemon=True,
            )
        thread.start()
        return
    record_uri = mapping.spotify_uri

    sp = get_spotify_client()
    if sp is None:
        logger.debug("Button: no Spotify client, skipping")
        return
    try:
        pb = sp.current_playback()
    except Exception as e:
        logger.warning("Button: current_playback failed: %s", e)
        return
    is_playing = bool(pb.get("is_playing", False)) if pb else False
    logger.info("Button: current_playback: is_playing=%s", is_playing)
    # context.uri is what is currently playing (album or playlist); use this, not the track's album
    current_context = ((pb or {}).get("context") or {}).get("uri")
    logger.info("Button: current_context: %s", current_context)
    norm_record = _normalize_uri(record_uri)
    norm_context = _normalize_uri(current_context)
    record_id = _spotify_uri_id(record_uri)
    logger.info("Button: record_id: %s", record_id)
    context_id = _spotify_uri_id(current_context)
    # Same record: context (album or playlist) URI matches record URI, or same ID; or Spotify omits context
    same_context = (
        (norm_record and norm_context == norm_record)
        or (record_id and context_id and record_id == context_id)
        or (is_playing and norm_record and not norm_context)
    )

    if is_playing and same_context:
        if time.monotonic() < _rotation_scan_cooldown_until:
            logger.debug("Button: skipping pause, rotation scan cooldown active")
            return
        try:
            sp.pause_playback()
            logger.info("Button: paused playback")
        except Exception as e:
            logger.warning("Button: pause_playback failed: %s", e)
        try:
            motor_service.turntable_stop()
        except Exception as e:
            logger.warning("Button: turntable_stop failed: %s", e)
        try:
            motor_service.move_tone_arm_to_angle(0.0)
        except Exception as e:
            logger.warning("Button: move_tone_arm_to_angle failed: %s", e)
        logger.info("Button: stopped platter and homed tone-arm")
    else:
        if is_playing:
            logger.info(
                "Button: not pausing (context mismatch): current_context=%s record_uri=%s",
                current_context,
                record_uri,
            )
        try:
            start_playback_with_fallback(context_uri=record_uri)
            motor_service.turntable_start(direction=1)
            record_local_start()
            logger.info("Button: started record context and platter")
            # Sync tone-arm to current track; Spotify may need a moment to report new playback.
            time.sleep(0.4)
            for _ in range(2):
                result = sync_tone_arm_and_platter_to_playback(motor_service, nfc_service)
                if result.get("ok"):
                    logger.info("Button: synced tone-arm to fraction %.3f", result.get("fraction", 0))
                    break
                time.sleep(0.3)
        except Exception as e:
            logger.warning("Button: start or motors failed: %s", e)


class ButtonService:
    """Watches GPIO button (polling loop) and toggles Spotify playback + platter/tone-arm for the current record."""

    def __init__(self, nfc_service, motor_service, simulate: bool = SIMULATE_HARDWARE or not _GPIO_AVAILABLE) -> None:
        self._nfc_service = nfc_service
        self._motor_service = motor_service
        self._simulate = simulate
        self._last_press_time = 0.0
        self._stop = False
        self._thread: threading.Thread | None = None

    def _poll_loop(self) -> None:
        while not self._stop:
            try:
                if GPIO.input(PIN_BUTTON) == GPIO.LOW:
                    now = time.monotonic()
                    if now - self._last_press_time >= DEBOUNCE_SEC:
                        self._last_press_time = now
                        _toggle_playback_for_current_record(self._nfc_service, self._motor_service)
            except Exception as e:
                logger.warning("Button poll: %s", e)
            time.sleep(POLL_INTERVAL_SEC)

    def start(self) -> None:
        if self._simulate:
            logger.info("Button service: skipped (SIMULATE_HARDWARE=1)")
            return
        if not _GPIO_AVAILABLE:
            logger.warning("Button service: skipped (RPi.GPIO not available)")
            return
        if self._thread is not None and self._thread.is_alive():
            return
        try:
            GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._stop = False
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
            logger.info("Button service: started on GPIO %s (BCM), polling", PIN_BUTTON)
        except Exception as e:
            logger.warning("Button service: failed to start: %s", e)

    def stop(self) -> None:
        self._stop = True
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
