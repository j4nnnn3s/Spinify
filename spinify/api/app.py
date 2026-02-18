"""FastAPI app, CORS, and route registration."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from spinify.api.state import AppState, get_state
from spinify.config import ensure_data_dir

# Import routes after state to avoid circular imports
from spinify.api.routes import motors, nfc, playback, records, spotify

# Re-export for backwards compatibility
__all__ = ["app", "AppState", "get_state"]

_state = get_state()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dir()
    _state.load_mappings()
    _state.nfc_service.start_polling(interval_sec=0.5)
    yield
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
