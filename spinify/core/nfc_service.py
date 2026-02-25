"""NFC (RC522) read loop: UID only. Spotify URI is resolved from record_store by UID."""
import threading
import time
from typing import Optional

# Keep reporting last seen UID for this long after reader misses the tag (e.g. record spinning)
_NFC_GRACE_SEC = 1.0

from spinify.config import PIN_RC522_RST_BOARD, SIMULATE_HARDWARE
from spinify.models.record import PlacedRecord

# Optional: MFRC522 for real hardware (mfrc522 or pi-rc522)
_RC522_AVAILABLE = False
_SIMPLE_READER = False
try:
    from mfrc522 import MFRC522
    _RC522_AVAILABLE = True
except ImportError:
    try:
        from mfrc522 import SimpleMFRC522
        _RC522_AVAILABLE = True
        _SIMPLE_READER = True
    except ImportError:
        pass


class NFCService:
    """Polls RC522 for tag UID. Spotify URI is resolved from record_store in the API layer."""

    def __init__(
        self,
        simulate: bool = SIMULATE_HARDWARE or not _RC522_AVAILABLE,
    ) -> None:
        self._simulate = simulate
        self._current_uid: Optional[str] = None
        self._last_seen_time: Optional[float] = None
        self._lock = threading.Lock()
        self._reader = None
        self._simple_reader = None
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_poll = False
        if not self._simulate and _RC522_AVAILABLE:
            if _SIMPLE_READER:
                self._simple_reader = SimpleMFRC522()
            else:
                self._reader = MFRC522(device=0, pin_rst=PIN_RC522_RST_BOARD)

    def get_current(self) -> Optional[PlacedRecord]:
        """Return currently placed record (UID only). URI is resolved from record_store in the API."""
        with self._lock:
            uid = self._current_uid
        if uid is None:
            return None
        return PlacedRecord(nfc_uid=uid, spotify_uri=None)

    def scan_once(self) -> Optional[str]:
        """One-shot read; returns UID if tag present, else None."""
        if self._simulate:
            with self._lock:
                return self._current_uid
        if not _RC522_AVAILABLE:
            return None
        if self._simple_reader is not None:
            try:
                _id, _text = self._simple_reader.read_no_block()
                return f"{_id:08x}" if _id is not None else None
            except Exception:
                return None
        if self._reader is None:
            return None
        try:
            (status, _) = self._reader.MFRC522_Request(self._reader.PICC_REQIDL)
            if status != self._reader.MI_OK:
                return None
            (status, backData) = self._reader.MFRC522_Anticoll()
            if status != self._reader.MI_OK or not backData or len(backData) < 4:
                return None
            return "".join(f"{b:02x}" for b in backData[:4])
        except Exception:
            return None

    def set_simulated_uid(self, uid: Optional[str], spotify_uri: Optional[str] = None) -> None:
        """For development: set simulated UID. URI is resolved from record_store in the API."""
        if not self._simulate:
            return
        with self._lock:
            self._current_uid = uid
            self._last_seen_time = time.time() if uid is not None else None

    def start_polling(self, interval_sec: float = 0.5) -> None:
        """Start background poll loop."""
        self._stop_poll = False

        def _poll_loop() -> None:
            while not self._stop_poll:
                uid = self.scan_once()
                with self._lock:
                    if uid is not None:
                        self._current_uid = uid
                        self._last_seen_time = time.time()
                    else:
                        if (
                            self._current_uid is not None
                            and self._last_seen_time is not None
                            and (time.time() - self._last_seen_time) > _NFC_GRACE_SEC
                        ):
                            self._current_uid = None
                            self._last_seen_time = None
                time.sleep(interval_sec)

        self._poll_thread = threading.Thread(target=_poll_loop, daemon=True)
        self._poll_thread.start()

    def stop_polling(self) -> None:
        """Stop background poll loop."""
        self._stop_poll = True
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None
