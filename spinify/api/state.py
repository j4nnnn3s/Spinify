"""Shared application state (injected into routes)."""
from typing import List

from spinify.core.motor_service import MotorService
from spinify.core.nfc_service import NFCService
from spinify.core.record_store import (
    add_mapping,
    delete_mapping,
    get_mapping_by_id,
    get_mapping_by_uid,
    load_mappings,
    update_mapping,
)
from spinify.models.record import RecordMapping


class AppState:
    def __init__(self) -> None:
        self.motor_service = MotorService()
        self._mappings: List[RecordMapping] = []
        self._nfc_service: NFCService | None = None

    def get_mappings(self) -> List[RecordMapping]:
        return self._mappings

    def load_mappings(self) -> None:
        self._mappings = load_mappings()

    def get_mapping_by_uid(self, uid: str) -> RecordMapping | None:
        return get_mapping_by_uid(self._mappings, uid)

    def add_mapping(self, nfc_uid: str, name: str, spotify_uri: str, type_: str) -> RecordMapping:
        return add_mapping(self._mappings, nfc_uid, name, spotify_uri, type_)

    def update_mapping(
        self,
        record_id: str,
        *,
        name: str | None = None,
        spotify_uri: str | None = None,
        type_: str | None = None,
    ) -> RecordMapping | None:
        return update_mapping(
            self._mappings, record_id, name=name, spotify_uri=spotify_uri, type_=type_
        )

    def delete_mapping(self, record_id: str) -> bool:
        return delete_mapping(self._mappings, record_id)

    def get_mapping_by_id(self, record_id: str) -> RecordMapping | None:
        return get_mapping_by_id(self._mappings, record_id)

    @property
    def nfc_service(self) -> NFCService:
        if self._nfc_service is None:
            self._nfc_service = NFCService(get_mapping=self.get_mapping_by_uid)
        return self._nfc_service


_state = AppState()


def get_state() -> AppState:
    return _state
