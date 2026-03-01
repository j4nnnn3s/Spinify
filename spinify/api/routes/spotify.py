"""Spotify OAuth: auth URL and callback."""
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from spinify.api.state import AppState, get_state
from spinify.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
    SPINIFY_WEB_ORIGIN,
    SPOTIFY_TOKEN_CACHE,
)
from spinify.core.spotify_client import (
    exchange_code_and_save_token,
    get_default_device,
    get_spotify_client,
    set_default_device,
)

router = APIRouter()


class CompleteLoginBody(BaseModel):
    """Either the full redirect URL (with ?code=...) or the code alone."""
    redirect_url: Optional[str] = None
    code: Optional[str] = None


@router.get("/auth-url")
def get_auth_url(state: AppState = Depends(get_state)):
    """Return Spotify OAuth authorization URL and whether the user is logged in."""
    if not SPOTIFY_CLIENT_ID:
        return {"auth_url": None, "error": "SPOTIFY_CLIENT_ID not set", "logged_in": False}
    logged_in = get_spotify_client() is not None
    base = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SPOTIFY_SCOPES,
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url, "logged_in": logged_in}


@router.get("/callback")
def spotify_callback(code: str | None = None, state: AppState = Depends(get_state)):
    """Exchange code for tokens, store on device, then redirect to web app or show success."""
    if not code:
        return HTMLResponse(
            "<body><p>Missing authorization code. Try logging in again from the Connect page.</p></body>",
            status_code=400,
        )
    if not exchange_code_and_save_token(code):
        return HTMLResponse(
            "<body><p>Failed to link Spotify. Check backend logs and try again.</p></body>",
            status_code=500,
        )
    if SPINIFY_WEB_ORIGIN:
        redirect_url = f"{SPINIFY_WEB_ORIGIN.rstrip('/')}/connect?spotify=success"
        return RedirectResponse(url=redirect_url, status_code=302)
    return HTMLResponse(
        "<body><p>Spotify linked successfully. You can close this window.</p></body>"
    )


@router.post("/complete-login")
def complete_login(body: CompleteLoginBody, state: AppState = Depends(get_state)):
    """
    Exchange an auth code for tokens and save (for Pi / manual flow).
    Send either the full redirect URL (after Spotify redirected you and the page failed to load)
    or just the code.
    """
    code: Optional[str] = None
    if body.code:
        code = body.code.strip()
    elif body.redirect_url:
        url = body.redirect_url.strip()
        if "?" in url:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            code = (params.get("code") or [None])[0]
        if not code:
            raise HTTPException(
                status_code=400,
                detail="No 'code' in redirect URL. Paste the full URL from the address bar after logging in.",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Send either 'redirect_url' or 'code' in the request body.",
        )
    if not exchange_code_and_save_token(code):
        raise HTTPException(
            status_code=502,
            detail="Failed to exchange code for tokens. Check SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and redirect_uri.",
        )
    return {"ok": True, "message": "Spotify linked successfully."}


@router.post("/logout")
def logout(state: AppState = Depends(get_state)):
    """Clear the Spotify token so the user is logged out."""
    try:
        if SPOTIFY_TOKEN_CACHE.exists():
            SPOTIFY_TOKEN_CACHE.unlink()
    except OSError:
        pass
    return {"ok": True}


@router.get("/default-device")
def get_default_device_route(state: AppState = Depends(get_state)):
    """Return the saved default playback device for display on Settings."""
    return get_default_device()


@router.post("/default-device/save-current")
def save_current_device_as_default(state: AppState = Depends(get_state)):
    """Save the device from current playback as the default. Requires something to be playing."""
    sp = get_spotify_client()
    if sp is None:
        raise HTTPException(
            status_code=503,
            detail="Spotify not linked. Use the Connect page to log in.",
        )
    try:
        pb = sp.current_playback()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    device = (pb or {}).get("device")
    if not device or not device.get("id"):
        raise HTTPException(
            status_code=400,
            detail="Play something on the device you want to set as default, then try again.",
        )
    set_default_device(device["id"], device.get("name"))
    return {"device_id": device["id"], "name": device.get("name") or ""}
