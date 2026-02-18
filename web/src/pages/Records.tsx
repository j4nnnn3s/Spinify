import { useEffect, useState } from 'react'
import { api, type RecordMapping } from '../api'
import { parseSpotifyUrl } from '../spotify'

export default function Records() {
  const [records, setRecords] = useState<RecordMapping[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scanUid, setScanUid] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newUri, setNewUri] = useState('')
  const [newType, setNewType] = useState<'album' | 'playlist'>('album')
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    try {
      const res = await api.records.list()
      setRecords(res.records)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleScan = async () => {
    try {
      const res = await api.nfc.scan()
      setScanUid(res.uid ?? '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scan failed')
    }
  }

  const handleSimulate = (uid: string) => {
    api.nfc.simulate(uid).then(() => setScanUid(uid)).catch(() => {})
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const uid = scanUid.trim()
    if (!uid || !newName.trim() || !newUri.trim()) return
    const parsed = parseSpotifyUrl(newUri)
    const spotifyUri = parsed ? parsed.uri : newUri.trim()
    const spotifyType = parsed ? parsed.type : newType
    setSubmitting(true)
    try {
      await api.records.create({
        nfc_uid: uid,
        name: newName.trim(),
        spotify_uri: spotifyUri,
        type: spotifyType,
      })
      setAddOpen(false)
      setNewName('')
      setNewUri('')
      setScanUid('')
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Remove this record mapping?')) return
    try {
      await api.records.delete(id)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 border-2 border-spotify-green border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Record mappings</h1>
        <button
          onClick={() => setAddOpen(true)}
          className="px-4 py-2 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-sm transition-colors"
        >
          Add record
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-950/40 border border-red-900/50 text-red-200 px-4 py-3">
          {error}
        </div>
      )}

      {records.length === 0 ? (
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/50 p-12 text-center">
          <p className="text-neutral-400 mb-2">No record mappings yet</p>
          <p className="text-sm text-neutral-500 mb-4">Map an NFC tag to a Spotify album or playlist</p>
          <button
            onClick={() => setAddOpen(true)}
            className="text-spotify-green hover:underline text-sm"
          >
            Add your first record
          </button>
        </div>
      ) : (
        <ul className="space-y-3">
          {records.map((r) => (
            <li
              key={r.record_id}
              className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="font-medium truncate">{r.name}</p>
                <p className="text-sm text-neutral-500 truncate">{r.spotify_uri}</p>
                <p className="text-xs text-neutral-600 mt-0.5">UID: {r.nfc_uid}</p>
              </div>
              <button
                onClick={() => handleDelete(r.record_id)}
                className="text-sm text-red-400 hover:text-red-300 transition-colors"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {addOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-10" onClick={() => setAddOpen(false)}>
          <div className="bg-neutral-900 border border-neutral-700 rounded-2xl p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">Add record mapping</h2>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="block text-sm text-neutral-400 mb-1">NFC UID</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={scanUid}
                    onChange={(e) => setScanUid(e.target.value)}
                    placeholder="Place tag and scan, or enter UID"
                    className="flex-1 rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
                  />
                  <button type="button" onClick={handleScan} className="px-3 py-2 rounded-lg bg-neutral-700 hover:bg-neutral-600 text-sm">
                    Scan
                  </button>
                </div>
                <p className="text-xs text-neutral-500 mt-1">Dev: simulate UID e.g. <button type="button" onClick={() => handleSimulate('abc123')} className="text-spotify-green hover:underline">abc123</button></p>
              </div>
              <div>
                <label className="block text-sm text-neutral-400 mb-1">Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Jazz Night"
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-400 mb-1">Spotify URL or URI</label>
                <input
                  type="text"
                  value={newUri}
                  onChange={(e) => {
                    const v = e.target.value
                    setNewUri(v)
                    const parsed = parseSpotifyUrl(v)
                    if (parsed) setNewType(parsed.type)
                  }}
                  placeholder="https://open.spotify.com/playlist/... or spotify:playlist:..."
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
                  required
                />
                <p className="text-xs text-neutral-500 mt-1">Paste a link or URI; type is set from URL if detected.</p>
              </div>
              <div>
                <label className="block text-sm text-neutral-400 mb-1">Type</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as 'album' | 'playlist')}
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
                >
                  <option value="album">Album</option>
                  <option value="playlist">Playlist</option>
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={submitting} className="px-4 py-2 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-sm disabled:opacity-50">
                  {submitting ? '…' : 'Save'}
                </button>
                <button type="button" onClick={() => setAddOpen(false)} className="px-4 py-2 rounded-full bg-neutral-700 hover:bg-neutral-600 text-sm">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
