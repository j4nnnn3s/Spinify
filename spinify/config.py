"""Configuration: env, GPIO pins, motor steps, Spotify credentials."""
import os
from pathlib import Path

# Base paths (project root = parent of spinify package)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root so SPOTIFY_CLIENT_ID etc. are set
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass
DATA_DIR = BASE_DIR / "data"
RECORD_MAPPINGS_PATH = DATA_DIR / "record_mappings.json"
SPOTIFY_TOKEN_CACHE = DATA_DIR / ".spotify-token"

# API
API_HOST = os.getenv("SPINIFY_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("SPINIFY_API_PORT", "8000"))

# Spotify (OAuth; tokens stored on device after first connect)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback")
SPOTIFY_SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
# After OAuth callback, redirect here (e.g. http://localhost:5173 for Vite dev)
SPINIFY_WEB_ORIGIN = os.getenv("SPINIFY_WEB_ORIGIN", "")

# GPIO (BCM unless noted)
PIN_RC522_RST = 25  # BCM 25 = physical pin 22
PIN_RC522_RST_BOARD = 22  # physical pin 22 (for pimylifeup MFRC522, which uses BOARD by default)
PIN_RC522_SDA = 8  # CE0
PIN_BUTTON = 23
# Turntable ULN2003 IN1–4
PIN_TURNTABLE = (17, 18, 27, 22)
# Tone-arm ULN2003 IN1–4
PIN_TONE_ARM = (5, 6, 13, 19)

# Motor calibration
# Default: turntable assumes 4096 steps/rev, tone-arm 512 steps/rev (your measured value)
STEPS_PER_REV = int(os.getenv("SPINIFY_STEPS_PER_REV", "4096"))
TONE_ARM_STEPS_PER_REV = int(os.getenv("SPINIFY_TONE_ARM_STEPS_PER_REV", "512"))
TONE_ARM_MAX_STEPS = int(os.getenv("SPINIFY_TONE_ARM_MAX_STEPS", "512"))  # limited arc

# Acceleration (min/max delay between steps in seconds)
MOTOR_MIN_DELAY = 0.001
MOTOR_MAX_DELAY = 0.008
TURNTABLE_TARGET_RPM = float(os.getenv("SPINIFY_TURNTABLE_RPM", "33.33"))

# Hardware simulation (for development without Pi)
SIMULATE_HARDWARE = os.getenv("SPINIFY_SIMULATE_HARDWARE", "0").lower() in ("1", "true", "yes")

def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
