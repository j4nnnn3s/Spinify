"""Shared application state (injected into routes)."""

from spinify.core.motor_service import MotorService
from spinify.core.nfc_service import NFCService


class AppState:
    def __init__(self) -> None:
        self.motor_service = MotorService()
        self._nfc_service: NFCService | None = None

    @property
    def nfc_service(self) -> NFCService:
        if self._nfc_service is None:
            self._nfc_service = NFCService()
        return self._nfc_service


_state = AppState()


def get_state() -> AppState:
    return _state
