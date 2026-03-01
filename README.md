# Spinify

A haptic turntable controller for Spotify. Place an NFC-tagged record on the platter, press play, and control Spotify playback with a physical turntable: tone-arm position follows playback position, and the platter spins while music plays.

**Hardware:** Raspberry Pi Zero 2 W, RC522 NFC reader, 28BYJ-48 steppers (turntable + tone-arm), ULN2003 drivers, start/stop button.

**Software:** Python core (FastAPI, Spotipy), local REST API, optional web UI for Spotify auth and record mapping.

---

## Quick start

1. **Create a virtual environment and install:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -e .
   ```

2. **Run the API (no hardware required for development):**

   ```bash
   python -m spinify.main
   ```

   By default the server runs at `http://0.0.0.0:8000`. Without Pi hardware, motors and NFC are simulated (use `POST /api/nfc/simulate` with `uid` to simulate a placed record).

3. **Optional: run with real hardware on a Raspberry Pi**

   Install optional dependencies and enable SPI/GPIO:

   ```bash
   pip install -e ".[pi]"
   sudo raspi-config   # Interface Options → SPI → Enable
   ```

   Unset simulation so the RC522 and GPIO are used:

   ```bash
   export SPINIFY_SIMULATE_HARDWARE=0
   python -m spinify.main
   ```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values. The app loads `.env` from the project root (via python-dotenv when available).

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SPINIFY_API_HOST` | API bind address | `0.0.0.0` |
| `SPINIFY_API_PORT` | API port | `8000` |
| `SPINIFY_SIMULATE_HARDWARE` | Simulate motors/NFC (no Pi) | `0` |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID | — |
| `SPOTIFY_CLIENT_SECRET` | Spotify app secret | — |
| `SPOTIFY_REDIRECT_URI` | OAuth redirect (e.g. `http://<pi-ip>:8000/api/spotify/callback`) | `http://localhost:8000/api/spotify/callback` |
| `SPINIFY_WEB_ORIGIN` | After OAuth, redirect user here (e.g. `http://localhost:5173`) | — |

Optional (motor/calibration; defaults are usually fine):

| Variable | Description | Default |
|----------|-------------|---------|
| `SPINIFY_STEPS_PER_REV` | Turntable steps per revolution (half-steps) | `4096` |
| `SPINIFY_TONE_ARM_STEPS_PER_REV` | Tone-arm steps per revolution | `512` |
| `SPINIFY_TONE_ARM_MAX_STEPS` | Max tone-arm travel from home (steps) | `512` |
| `SPINIFY_TONE_ARM_RECORD_START_STEPS` | Record start position (from calibration script) | — |
| `SPINIFY_TONE_ARM_RECORD_END_STEPS` | Record end position (from calibration script) | — |
| `SPINIFY_TURNTABLE_STEPS_PER_SEC` | Turntable speed (half-steps per second) | `333.33` |
| `SPINIFY_TURNTABLE_RPM` | Target RPM when API uses `speed_rpm` | `33.33` |

**Spotify Developer Dashboard:** In your app’s settings, under **Redirect URIs**, add exactly the same value as `SPOTIFY_REDIRECT_URI`.

**Development (no HTTPS, dynamic Pi IP):** Spotify allows **http** redirects only for `localhost` and `127.0.0.1`. For development, use localhost only:

- Add **one** Redirect URI in the Dashboard: `http://localhost:8000/api/spotify/callback`
- Run the API on your PC (`python -m spinify.main`). Leave `SPOTIFY_REDIRECT_URI` at its default so the callback hits your local server.
- Open the web UI at `http://localhost:5173` and use “Login with Spotify” from there. No Pi and no HTTPS needed.

For a Pi with a dynamic IP or without HTTPS, the Dashboard won’t accept a plain `http://<pi-ip>:8000/...` redirect. **Manual login on the Pi:** Run the API on the Pi with `SPOTIFY_REDIRECT_URI=http://localhost:8000/api/spotify/callback` (default). Open the web UI (on the Pi or from another device that can reach the Pi), go to Connect, and use **Manual login**: (1) Open the shown login URL in any browser (e.g. on your phone), (2) log in to Spotify, (3) when the redirect fails to load (e.g. “can’t connect”), copy the **full URL** from the address bar, (4) paste it into “Paste redirect URL” on the Connect page and click **Complete login**. The backend exchanges the code and saves the token; no Pi redirect URI in the Dashboard needed.

The `data/` directory is created automatically and holds `record_mappings.json` (NFC → Spotify mappings), `.spotify-token` (OAuth tokens), and `.spotify-default-device` (saved Spotify device).

**Physical button**  
One GPIO button toggles play for the current NFC record: press to start (or pause) the album/playlist mapped to the placed record. If no record or no mapping is detected, the platter does one rotation scan to try to read a tag. When playing, the platter and tone-arm stay in sync with Spotify (via the Dashboard or the tone-arm sync API). Cooldowns prevent the periodic sync from stopping the platter immediately after you press the button to start.

**Scripts**  
`scripts/calibrate_tone_arm.py` sets the physical record start/end positions used for tone-arm fraction 0→1. Run from the project root: `python scripts/calibrate_tone_arm.py`. Jog the tone-arm with **j** / **l** or arrow keys; press **s** to save the start position, **e** to save the end position, **q** to quit and print the env vars. Add the printed `SPINIFY_TONE_ARM_RECORD_START_STEPS` and `SPINIFY_TONE_ARM_RECORD_END_STEPS` to your `.env`.

---

## API overview

- **Motors:** `GET/POST /api/motors/tone-arm`, `POST /api/motors/tone-arm/sync`, `GET /api/motors/turntable`, `POST /api/motors/turntable/start`, `POST /api/motors/turntable/stop`
- **NFC:** `GET /api/nfc/current`, `POST /api/nfc/scan`, `POST /api/nfc/simulate` (dev only)
- **Playback:** `GET /api/playback`, `POST /api/playback/start`, `POST /api/playback/stop`, `GET /api/playback/position`
- **Records:** `GET/POST /api/records`, `PATCH/DELETE /api/records/{id}`
- **Spotify:** `GET /api/spotify/auth-url`, `GET /api/spotify/callback`, `POST /api/spotify/complete-login` (manual: send `redirect_url` or `code`), `POST /api/spotify/logout`, `GET /api/spotify/default-device`, `POST /api/spotify/default-device/save-current`

OpenAPI docs: `http://localhost:8000/docs` when the server is running.

---

## Web interface

From the repo root, run the web UI (Vite dev server with API proxy):

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. The app proxies `/api` to `http://localhost:8000`, so start the Spinify API first. You get:

- **Dashboard** – current record, playback state, play/stop
- **Records** – list and add record mappings (NFC UID → Spotify album/playlist)
- **Connect** – link Spotify account (opens backend auth URL)

To build for production: `npm run build`. Serve the `web/dist` folder (e.g. mount as static in the FastAPI app).

---

## Project layout

```
spinify/                 # Python backend
├── main.py              # Entry: uvicorn API server
├── config.py            # Env and GPIO/motor config
├── api/
│   ├── app.py           # FastAPI app, CORS, state, lifespan (NFC + button)
│   ├── state.py         # AppState, get_state (motor, NFC, button services)
│   └── routes/          # motors, nfc, playback, records, spotify
├── core/
│   ├── motor_service.py # Steppers (turntable + tone-arm)
│   ├── nfc_service.py   # RC522 read loop
│   ├── button_service.py   # GPIO button: start/stop playback for current record
│   ├── playback_sync.py   # Sync tone-arm and platter to Spotify playback
│   ├── playback_cooldown.py  # Cooldown after local start (avoids sync fighting button)
│   ├── spotify_client.py # Spotipy wrapper, auth, start/pause/current_playback
│   └── record_store.py  # Persist record mappings (JSON)
└── models/              # RecordMapping, PlaybackState, ToneArmPosition, etc.

scripts/
└── calibrate_tone_arm.py   # Jog tone-arm, save start/end; prints env vars for .env

data/                    # Created at runtime
├── record_mappings.json
├── .spotify-token
└── .spotify-default-device

web/                     # React frontend (Vite + Tailwind)
├── src/
│   ├── App.tsx          # Router and layout
│   ├── api.ts           # API client
│   └── pages/           # Dashboard, Records, Connect
├── index.html
└── package.json
```

Additional docs (e.g. LaTeX quickstart) live in `docs/`.

---
