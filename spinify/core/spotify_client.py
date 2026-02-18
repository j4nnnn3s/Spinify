"""Spotify API client via Spotipy; uses cached OAuth token."""
from typing import Optional

from spinify.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
    SPOTIFY_TOKEN_CACHE,
)

_spotify_client: Optional["Spotify"] = None


def get_spotify_client() -> Optional["Spotify"]:
    """Return an authenticated Spotipy Spotify client, or None if not logged in."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    try:
        from spotipy import Spotify
        from spotipy.cache_handler import CacheFileHandler
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        return None

    cache_path = str(SPOTIFY_TOKEN_CACHE)
    cache = CacheFileHandler(cache_path=cache_path)
    auth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPES,
        cache_handler=cache,
    )
    token_info = auth.validate_token(cache.get_cached_token())
    if token_info is None:
        return None
    return Spotify(auth_manager=auth)


def get_cover_url_for_uri(uri: str) -> Optional[str]:
    """Return cover image URL for a Spotify album or playlist URI, or None."""
    if not uri or ":" not in uri:
        return None
    parts = uri.split(":")
    if len(parts) < 3:
        return None
    kind, id_ = parts[1].lower(), parts[2]
    sp = get_spotify_client()
    if sp is None:
        return None
    try:
        if kind == "album":
            album = sp.album(id_)
            images = (album or {}).get("images") or []
        elif kind == "playlist":
            playlist = sp.playlist(id_)
            images = (playlist or {}).get("images") or []
        else:
            return None
        return images[0]["url"] if images else None
    except Exception:
        return None


def exchange_code_and_save_token(code: str) -> bool:
    """Exchange OAuth code for tokens and save to cache. Returns True on success."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return False
    try:
        from spotipy.cache_handler import CacheFileHandler
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        return False

    cache_path = str(SPOTIFY_TOKEN_CACHE)
    cache = CacheFileHandler(cache_path=cache_path)
    auth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPES,
        cache_handler=cache,
    )
    try:
        auth.get_access_token(code=code, check_cache=False)
        return True
    except Exception:
        return False
