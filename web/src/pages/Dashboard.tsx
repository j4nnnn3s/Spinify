import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, type NfcCurrent, type PlaybackState } from '../api'
import { RecordCard } from '../components/RecordCard'
import { SkeletonLoader } from '../components/SkeletonLoader'
import { StatusCard } from '../components/StatusCard'
import { usePolling } from '../hooks/usePolling'

export default function Dashboard() {
  const [nfc, setNfc] = useState<NfcCurrent | null>(null)
  const [playback, setPlayback] = useState<PlaybackState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [action, setAction] = useState<'idle' | 'start' | 'stop'>('idle')

  const refresh = useCallback(async () => {
    try {
      const [nfcRes, playbackRes] = await Promise.all([
        api.nfc.current(),
        api.playback.get(),
      ])
      setNfc(nfcRes)
      setPlayback(playbackRes)
      setError(null)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load'
      setError(msg)
      toast.error(msg ?? 'Failed to load', { id: 'dashboard-error', duration: 5000 })
    } finally {
      setLoading(false)
    }
  }, [])

  const recordIsPlaying = Boolean(
    playback?.is_playing &&
      nfc?.spotify_uri &&
      playback?.context_uri &&
      nfc.spotify_uri === playback.context_uri
  )

  const syncToneArm = useCallback(async () => {
    if (!nfc?.uid) return
    try {
      await api.motors.toneArm.sync()
    } catch {
      // Ignore sync errors; UI stays responsive
    }
  }, [nfc?.uid])

  usePolling(refresh, {
    activeIntervalMs: 2000,
    idleIntervalMs: 5000,
    isActive: Boolean(playback?.is_playing),
    runOnMount: true,
  })

  usePolling(syncToneArm, {
    activeIntervalMs: 3000,
    idleIntervalMs: 5000,
    isActive: Boolean(nfc?.uid),
    runOnMount: false,
  })

  const handlePlayPause = async () => {
    setAction(playback?.is_playing ? 'stop' : 'start')
    try {
      if (playback?.is_playing) await api.playback.stop()
      else await api.playback.start(nfc?.spotify_uri ?? undefined)
      await refresh()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed'
      toast.error(msg ?? 'Request failed')
    } finally {
      setAction('idle')
    }
  }

  const handlePlayRecord = async () => {
    if (!nfc?.spotify_uri) return
    setAction('start')
    try {
      await api.playback.start(nfc.spotify_uri)
      await refresh()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed'
      toast.error(msg ?? 'Request failed')
    } finally {
      setAction('idle')
    }
  }

  const playStopButton = (
    <button
      type="button"
      onClick={handlePlayPause}
      disabled={action !== 'idle'}
      className="focus-ring touch-target inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-[44px]"
      aria-label={playback?.is_playing ? 'Stop playback' : 'Start playback'}
    >
      {action !== 'idle' ? '…' : playback?.is_playing ? 'Stop' : 'Play'}
    </button>
  )

  if (loading) {
    return (
      <div className="space-y-8" role="region" aria-label="Dashboard">
        <SkeletonLoader variant="full" />
      </div>
    )
  }

  if (error) {
    return (
      <section
        className="rounded-lg bg-red-950/40 border border-red-900/50 text-red-200 px-4 py-3 animate-fade-in"
        role="alert"
        aria-live="assertive"
      >
        <p>{error}</p>
        <button
          onClick={() => {
            setLoading(true)
            refresh()
          }}
          className="focus-ring mt-3 touch-target inline-block px-4 py-2 rounded-full bg-red-900/50 hover:bg-red-900 text-sm font-medium min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          Retry
        </button>
      </section>
    )
  }

  const progress =
    playback && playback.duration_ms > 0
      ? (playback.position_ms / playback.duration_ms) * 100
      : 0

  const playbackStatus =
    recordIsPlaying ? 'Playing' : playback?.is_playing ? 'Other' : 'Stopped'

  return (
    <div className="space-y-8 animate-fade-in" role="region" aria-label="Dashboard">
      {!nfc?.uid ? (
        <section
          className="rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8 sm:p-12 text-center"
          aria-labelledby="no-record-heading"
        >
          <h2 id="no-record-heading" className="text-neutral-400 mb-2">
            No record on the platter
          </h2>
          <p className="text-sm text-neutral-500 mb-6">
            Place an NFC-tagged record to see it here
          </p>
          <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">
            Soft control
          </p>
          {playStopButton}
        </section>
      ) : (
        <section
          className={`rounded-2xl border border-neutral-800 bg-neutral-900/50 overflow-hidden transition-shadow hover:border-neutral-700 ${
            recordIsPlaying ? 'ring-1 ring-spotify-green/30' : ''
          }`}
          aria-labelledby="now-playing-heading"
        >
          <div className="p-4 sm:p-6">
            <h1
              id="now-playing-heading"
              className="text-xl sm:text-2xl font-semibold tracking-tight mb-4"
            >
              Now playing
            </h1>
            <div className="flex flex-col sm:flex-row gap-6 items-start">
              <div
                className={`w-full sm:w-48 h-48 rounded-xl bg-neutral-800 flex-shrink-0 flex items-center justify-center overflow-hidden ${
                  recordIsPlaying ? 'animate-pulse-soft' : ''
                }`}
              >
                {playback?.context_image_url ? (
                  <img
                    src={playback.context_image_url}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : nfc?.spotify_uri ? (
                  <span className="text-sm font-medium text-neutral-400">
                    Record
                  </span>
                ) : (
                  <span className="text-sm text-neutral-500">Unmapped</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-neutral-500 uppercase tracking-wider mb-1">
                  Record
                </p>
                <h2 className="text-lg sm:text-xl font-semibold truncate">
                  {playback?.track_name || '—'}
                </h2>
                <p className="text-neutral-400 truncate">
                  {playback?.artist_name || '—'}
                </p>
                <p className="text-sm text-neutral-500 mt-1 truncate">
                  {playback?.album_name || '—'}
                </p>
                {playback && playback.track_index >= 0 && (
                  <p className="text-xs text-neutral-500 mt-1" aria-hidden>
                    Track {playback.track_index + 1}
                  </p>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  {playStopButton}
                  {nfc?.uid && (
                    <Link
                      to={`/records?uid=${encodeURIComponent(nfc.uid)}`}
                      className="focus-ring touch-target inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-neutral-700 hover:bg-neutral-600 text-white font-semibold text-sm transition-colors min-h-[44px]"
                      aria-label="Map this record"
                    >
                      Map this record
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="h-1 bg-neutral-800" role="presentation">
            <div
              className="h-full bg-spotify-green transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <RecordCard
          coverUrl={nfc?.record_cover_url ?? null}
          spotifyUri={nfc?.spotify_uri ?? null}
          uid={nfc?.uid ?? null}
          recordName={nfc?.record_name ?? null}
          label="Current record"
        >
          {nfc?.spotify_uri && !recordIsPlaying && (
            <button
              type="button"
              onClick={handlePlayRecord}
              disabled={action !== 'idle'}
              className="focus-ring touch-target mt-2 inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-xs disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-[44px]"
              aria-label="Play this record"
            >
              {action === 'start' ? '…' : 'Play'}
            </button>
          )}
        </RecordCard>
        <StatusCard
          id="playback-status-label"
          label="Playback"
          value={playbackStatus}
        />
      </div>

      {nfc?.uid && (
        <details
          className="rounded-xl border border-neutral-800 overflow-hidden"
          aria-label="NFC details"
        >
          <summary
            className="list-none p-4 cursor-pointer hover:bg-neutral-800/50 transition-colors focus-ring rounded-xl focus:outline-none"
            tabIndex={0}
          >
            <span className="text-sm text-neutral-500 uppercase tracking-wider">
              NFC details
            </span>
            <span className="ml-2 text-neutral-400 text-sm font-mono">
              UID: {nfc.uid}
            </span>
          </summary>
          <div className="px-4 pb-4 pt-0 text-sm text-neutral-500 font-mono break-all">
            {nfc.record_name ?? 'No record mapped'}
          </div>
        </details>
      )}

    </div>
  )
}
