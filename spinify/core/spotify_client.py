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


def get_metadata_for_uri(uri: str) -> Optional[dict]:
    """Return type and name for a Spotify album or playlist URI, or None.
    Returns e.g. {"type": "album", "name": "Album Title"}."""
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
            if album:
                return {"type": "album", "name": album.get("name") or ""}
        elif kind == "playlist":
            playlist = sp.playlist(id_)
            if playlist:
                return {"type": "playlist", "name": playlist.get("name") or ""}
    except Exception:
        pass
    return None


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


def get_context_track_position(context_uri: str, track_uri: str) -> Optional[dict]:
    """Return total_tracks and track_index for a track within an album or playlist context.

    Returns e.g. {"total_tracks": 12, "track_index": 3} or None on error.
    """
    if not context_uri or ":" not in context_uri or not track_uri:
        return None
    context_parts = context_uri.split(":")
    if len(context_parts) < 3:
        return None
    kind, context_id = context_parts[1].lower(), context_parts[2]

    sp = get_spotify_client()
    if sp is None:
        return None

    try:
        if kind == "album":
            album = sp.album(context_id)
            if not album:
                return None
            total_tracks = int(album.get("total_tracks") or 0)
            tracks = (album.get("tracks") or {}).get("items") or []
            index = -1
            for i, t in enumerate(tracks):
                if t.get("uri") == track_uri:
                    index = i
                    break
            if total_tracks <= 0:
                total_tracks = max(len(tracks), 1)
            if index < 0:
                index = 0
            return {"total_tracks": total_tracks, "track_index": index}

        if kind == "playlist":
            playlist = sp.playlist(context_id)
            if not playlist:
                return None
            tracks_obj = playlist.get("tracks") or {}
            items = tracks_obj.get("items") or []
            total_tracks = int(tracks_obj.get("total") or len(items) or 0)
            index = -1
            for i, entry in enumerate(items):
                track = entry.get("track") or {}
                if track.get("uri") == track_uri:
                    index = i
                    break
            if index < 0 and items:
                # If we didn't find it, just assume current index is 0 as a safe fallback
                index = 0
            if total_tracks <= 0:
                total_tracks = max(len(items), 1)
            return {"total_tracks": total_tracks, "track_index": max(0, index)}
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
