"""FastAPI app, CORS, and route registration."""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging in the worker process (so button_service etc. INFO logs are visible with uvicorn --reload)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(name)s: %(message)s",
)

from spinify.api.state import AppState, get_state
from spinify.config import ensure_data_dir
from spinify.core.playback_cooldown import is_within_cooldown
from spinify.core.playback_sync import sync_tone_arm_and_platter_to_playback

# Import routes after state to avoid circular imports
from spinify.api.routes import motors, nfc, playback, records, spotify

# Re-export for backwards compatibility
__all__ = ["app", "AppState", "get_state"]

_state = get_state()

PLAYBACK_SYNC_INTERVAL_SEC = 2.5
PLAYBACK_SYNC_FAST_INTERVAL_SEC = 0.4  # When playback was just started (button/API), sync more often


def _playback_sync_loop(stop_event: threading.Event) -> None:
    """Background loop: sync tone-arm and platter to Spotify playback every interval."""
    while True:
        # After button/API starts playback we sync more often so tone-arm catches up quickly
        interval = (
            PLAYBACK_SYNC_FAST_INTERVAL_SEC
            if is_within_cooldown()
            else PLAYBACK_SYNC_INTERVAL_SEC
        )
        if stop_event.wait(timeout=interval):
            break
        try:
            sync_tone_arm_and_platter_to_playback(_state.motor_service, _state.nfc_service)
        except Exception as e:
            logging.getLogger(__name__).warning("Playback sync: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dir()
    _state.nfc_service.start_polling(interval_sec=0.5)
    _state.button_service.start()

    _sync_stop = threading.Event()
    _sync_thread = threading.Thread(
        target=_playback_sync_loop,
        args=(_sync_stop,),
        daemon=True,
    )
    _sync_thread.start()
    logging.getLogger(__name__).info(
        "Playback sync thread started (interval %.1fs)", PLAYBACK_SYNC_INTERVAL_SEC
    )

    yield

    _sync_stop.set()
    _sync_thread.join(timeout=5.0)
    _state.button_service.stop()
    _state.nfc_service.stop_polling()


app = FastAPI(
    title="Spinify API",
    description="Local REST API for Spinify turntable controller",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(motors.router, prefix="/api/motors", tags=["motors"])
app.include_router(nfc.router, prefix="/api/nfc", tags=["nfc"])
app.include_router(playback.router, prefix="/api/playback", tags=["playback"])
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(spotify.router, prefix="/api/spotify", tags=["spotify"])
