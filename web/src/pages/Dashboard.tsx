import { useEffect, useState } from 'react'
import { api, type NfcCurrent, type PlaybackState } from '../api'

export default function Dashboard() {
  const [nfc, setNfc] = useState<NfcCurrent | null>(null)
  const [playback, setPlayback] = useState<PlaybackState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState<'idle' | 'start' | 'stop'>('idle')

  const refresh = async () => {
    try {
      const [nfcRes, playbackRes] = await Promise.all([
        api.nfc.current(),
        api.playback.get(),
      ])
      setNfc(nfcRes)
      setPlayback(playbackRes)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const t = setInterval(refresh, 2000)
    return () => clearInterval(t)
  }, [])

  const handlePlayPause = async () => {
    setAction(playback?.is_playing ? 'stop' : 'start')
    try {
      if (playback?.is_playing) await api.playback.stop()
      else await api.playback.start(nfc?.record?.spotify_uri)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setAction('idle')
    }
  }

  const handlePlayRecord = async () => {
    if (!nfc?.record?.spotify_uri) return
    setAction('start')
    try {
      await api.playback.start(nfc.record.spotify_uri)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setAction('idle')
    }
  }

  const playStopButton = (
    <button
      type="button"
      onClick={handlePlayPause}
      disabled={action !== 'idle'}
      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
    >
      {action !== 'idle' ? '…' : playback?.is_playing ? 'Stop' : 'Play'}
    </button>
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 border-2 border-spotify-green border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-950/40 border border-red-900/50 text-red-200 px-4 py-3">
        {error}
        <button onClick={refresh} className="ml-3 text-sm underline">Retry</button>
      </div>
    )
  }

  const progress = playback && playback.duration_ms > 0
    ? (playback.position_ms / playback.duration_ms) * 100
    : 0

  const recordIsPlaying = Boolean(
    playback?.is_playing &&
    nfc?.record?.spotify_uri &&
    playback?.context_uri &&
    nfc.record.spotify_uri === playback.context_uri
  )

  return (
    <div className="space-y-8">
      {!nfc?.uid ? (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/50 p-12 text-center">
          <p className="text-neutral-400 mb-2">No record on the platter</p>
          <p className="text-sm text-neutral-500 mb-6">Place an NFC-tagged record to see it here</p>
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Soft control</p>
          {playStopButton}
        </div>
      ) : (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/50 overflow-hidden">
          <div className="p-6">
            <h1 className="text-2xl font-semibold tracking-tight mb-4">Now playing</h1>
            <div className="flex flex-col sm:flex-row gap-6 items-start">
            <div className="w-48 h-48 rounded-xl bg-neutral-800 flex-shrink-0 flex items-center justify-center overflow-hidden">
              {playback?.context_image_url ? (
                <img
                  src={playback.context_image_url}
                  alt={nfc.record?.name ?? 'Album or playlist cover'}
                  className="w-full h-full object-cover"
                />
              ) : nfc.record ? (
                <span className="text-sm font-medium text-neutral-400">{nfc.record.name}</span>
              ) : (
                <span className="text-sm text-neutral-500">Unmapped</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-neutral-500 uppercase tracking-wider mb-1">
                {nfc.record?.type ?? 'Record'}
              </p>
              <h2 className="text-xl font-semibold truncate">
                {playback?.track_name || '—'}
              </h2>
              <p className="text-neutral-400 truncate">{playback?.artist_name || '—'}</p>
              <p className="text-sm text-neutral-500 mt-1 truncate">{playback?.album_name || '—'}</p>
              <div className="mt-4">{playStopButton}</div>
            </div>
            </div>
          </div>
          <div className="h-1 bg-neutral-800">
            <div
              className="h-full bg-spotify-green transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-xl border border-neutral-800 p-4 flex gap-4 items-center">
          <div className="w-16 h-16 rounded-lg bg-neutral-800 flex-shrink-0 overflow-hidden flex items-center justify-center">
            {nfc?.record_cover_url ? (
              <img
                src={nfc.record_cover_url}
                alt={nfc?.record?.name ?? 'Record cover'}
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-xs text-neutral-500">
                {nfc?.record ? 'No image' : '—'}
              </span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Current record</p>
            <p className="font-medium truncate">{nfc?.record?.name ?? (nfc?.uid ? `UID: ${nfc.uid}` : '—')}</p>
            {nfc?.record && !recordIsPlaying && (
              <button
                type="button"
                onClick={handlePlayRecord}
                disabled={action !== 'idle'}
                className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-xs disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {action === 'start' ? '…' : 'Play'}
              </button>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-neutral-800 p-4">
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Playback</p>
          <p className="font-medium">
            {recordIsPlaying ? 'Playing' : playback?.is_playing ? 'Other' : 'Stopped'}
          </p>
        </div>
      </div>
    </div>
  )
}
