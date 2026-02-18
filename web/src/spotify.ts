/**
 * Parse Spotify web URLs and return normalized URI + type.
 * e.g. https://open.spotify.com/playlist/0LJtBRZxHuskZSvIua9FfI?si=... → { type: 'playlist', uri: 'spotify:playlist:0LJtBRZxHuskZSvIua9FfI' }
 */
const SPOTIFY_URL_REGEX = /^https?:\/\/(?:open\.)?spotify\.com\/(album|playlist)\/([a-zA-Z0-9]+)(?:\?|$)/i

export function parseSpotifyUrl(
  input: string
): { type: 'album' | 'playlist'; uri: string } | null {
  const trimmed = input.trim()
  const match = trimmed.match(SPOTIFY_URL_REGEX)
  if (!match) return null
  const [, kind, id] = match
  const type = kind === 'album' ? 'album' : 'playlist'
  return { type, uri: `spotify:${type}:${id}` }
}

export function isSpotifyUrl(input: string): boolean {
  return parseSpotifyUrl(input) !== null
}
