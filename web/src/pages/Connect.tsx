import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Connect() {
  const [authUrl, setAuthUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [pasteUrl, setPasteUrl] = useState('')
  const [pasteError, setPasteError] = useState<string | null>(null)
  const [pasteSuccess, setPasteSuccess] = useState(false)
  const [completing, setCompleting] = useState(false)

  useEffect(() => {
    let cancelled = false
    const minDisplayMs = 400
    const started = Date.now()

    api.spotify
      .authUrl()
      .then((res) => {
        if (cancelled) return
        if (res.error) setError(res.error)
        const url = res.auth_url ?? null
        const elapsed = Date.now() - started
        const delay = Math.max(0, minDisplayMs - elapsed)
        setTimeout(() => {
          if (!cancelled) {
            setAuthUrl(url)
            setLoading(false)
          }
        }, delay)
      })
      .catch((e) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Failed to load')
        const elapsed = Date.now() - started
        const delay = Math.max(0, minDisplayMs - elapsed)
        setTimeout(() => {
          if (!cancelled) setLoading(false)
        }, delay)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const canLogin = !!authUrl && !error

  const handleCompleteLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = pasteUrl.trim()
    if (!trimmed) return
    setCompleting(true)
    setPasteError(null)
    setPasteSuccess(false)
    try {
      if (trimmed.includes('code=') || trimmed.startsWith('http')) {
        await api.spotify.completeLogin({ redirect_url: trimmed })
      } else {
        await api.spotify.completeLogin({ code: trimmed })
      }
      setPasteSuccess(true)
      setPasteUrl('')
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : 'Complete login failed')
    } finally {
      setCompleting(false)
    }
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold tracking-tight">Connect Spotify</h1>

      {error && (
        <div className="rounded-lg bg-amber-950/40 border border-amber-900/50 text-amber-200 px-4 py-3">
          {error}
        </div>
      )}

      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8">
        <p className="text-neutral-400 mb-6">
          Link your Spotify account so Spinify can control playback. You only need to do this once per device.
        </p>
        {canLogin ? (
          <a
            href={authUrl!}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold transition-colors"
          >
            <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.405.12-.781-.18-.901-.576-.12-.405.18-.781.576-.901 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.059zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.479.12-1.02.6-1.14C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
            </svg>
            Login with Spotify
          </a>
        ) : (
          <button
            type="button"
            disabled
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-spotify-green/70 text-black font-semibold cursor-not-allowed"
          >
            {loading ? (
              <span className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" aria-hidden />
            ) : (
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.405.12-.781-.18-.901-.576-.12-.405.18-.781.576-.901 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.059zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.479.12-1.02.6-1.14C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
              </svg>
            )}
            Login with Spotify
          </button>
        )}
        {!loading && !canLogin && !error && (
          <p className="text-sm text-neutral-500 mt-4">
            Set <code className="bg-neutral-800 px-1 rounded">SPOTIFY_CLIENT_ID</code> and redirect URI in the backend to enable login.
          </p>
        )}

        {canLogin && (
          <>
            <div className="mt-8 pt-8 border-t border-neutral-700">
              <p className="text-sm font-medium text-neutral-300 mb-2">Manual login (e.g. on Pi)</p>
              <p className="text-sm text-neutral-500 mb-3">
                Open the URL below in any browser (e.g. on your phone). After logging in, Spotify will redirect you; if the page fails to load, copy the <strong>full URL</strong> from the address bar and paste it here.
              </p>
              <div className="mb-3">
                <label className="block text-xs text-neutral-500 mb-1">Login URL (open in browser)</label>
                <input
                  type="text"
                  readOnly
                  value={authUrl ?? ''}
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm text-neutral-300 font-mono break-all"
                  onFocus={(e) => e.target.select()}
                />
              </div>
              <form onSubmit={handleCompleteLogin} className="space-y-2">
                <label className="block text-xs text-neutral-500">Paste redirect URL or code</label>
                <textarea
                  value={pasteUrl}
                  onChange={(e) => setPasteUrl(e.target.value)}
                  placeholder="http://localhost:8000/api/spotify/callback?code=... or just the code"
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm font-mono placeholder:text-neutral-600 min-h-[80px]"
                  rows={3}
                />
                {pasteError && (
                  <p className="text-sm text-amber-400">{pasteError}</p>
                )}
                {pasteSuccess && (
                  <p className="text-sm text-spotify-green">Spotify linked. You can use playback now.</p>
                )}
                <button
                  type="submit"
                  disabled={completing || !pasteUrl.trim()}
                  className="px-4 py-2 rounded-full bg-neutral-700 hover:bg-neutral-600 disabled:opacity-50 text-sm font-medium"
                >
                  {completing ? '…' : 'Complete login'}
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
