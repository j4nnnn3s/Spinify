import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, type Record } from '../api'

export default function Records() {
  const [searchParams] = useSearchParams()
  const prefilledUid = searchParams.get('uid') ?? ''

  const [records, setRecords] = useState<Record[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [addUid, setAddUid] = useState(prefilledUid)
  const [addUrl, setAddUrl] = useState('')
  const [addSubmitting, setAddSubmitting] = useState(false)
  const [scanning, setScanning] = useState(false)

  const [editRecord, setEditRecord] = useState<Record | null>(null)
  const [editName, setEditName] = useState('')
  const [editUri, setEditUri] = useState('')
  const [editType, setEditType] = useState('')
  const [editSubmitting, setEditSubmitting] = useState(false)

  const refresh = async () => {
    try {
      const list = await api.records.list()
      setRecords(list)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  useEffect(() => {
    if (prefilledUid) setAddUid(prefilledUid)
  }, [prefilledUid])

  const handleScan = async () => {
    setScanning(true)
    try {
      const res = await api.nfc.scan()
      if (res.uid) setAddUid(res.uid)
      else toast.error('No tag detected')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    const uid = addUid.trim()
    const url = addUrl.trim()
    if (!uid || !url) return
    setAddSubmitting(true)
    try {
      await api.records.create({ nfc_uid: uid, spotify_url: url })
      toast.success('Record mapped')
      setAddUrl('')
      if (!prefilledUid) setAddUid('')
      await refresh()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to add')
    } finally {
      setAddSubmitting(false)
    }
  }

  const openEdit = (r: Record) => {
    setEditRecord(r)
    setEditName(r.name)
    setEditUri(r.spotify_uri)
    setEditType(r.type)
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editRecord) return
    setEditSubmitting(true)
    try {
      await api.records.update(editRecord.record_id, {
        name: editName || undefined,
        spotify_uri: editUri || undefined,
        type: editType || undefined,
      })
      toast.success('Record updated')
      setEditRecord(null)
      await refresh()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to update')
    } finally {
      setEditSubmitting(false)
    }
  }

  const handleDelete = async (record_id: string) => {
    if (!confirm('Delete this mapping?')) return
    try {
      await api.records.delete(record_id)
      toast.success('Record deleted')
      await refresh()
      if (editRecord?.record_id === record_id) setEditRecord(null)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to delete')
    }
  }

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
        <button onClick={() => { setLoading(true); refresh() }} className="ml-3 text-sm underline">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold tracking-tight">Record mappings</h1>
      <p className="text-neutral-400 text-sm">
        Map NFC tag UIDs to Spotify albums or playlists. Type and title are filled from Spotify when you add a URL.
      </p>

      <section className="rounded-2xl border border-neutral-800 bg-neutral-900/50 p-6">
        <h2 className="text-lg font-medium mb-4">Add mapping</h2>
        <form onSubmit={handleAdd} className="space-y-4">
          <div className="flex flex-wrap gap-2 items-end">
            <div className="min-w-0 flex-1">
              <label className="block text-xs text-neutral-500 uppercase tracking-wider mb-1">
                NFC UID
              </label>
              <input
                type="text"
                value={addUid}
                onChange={(e) => setAddUid(e.target.value)}
                placeholder="e.g. 88047739"
                className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm font-mono"
              />
            </div>
            <button
              type="button"
              onClick={handleScan}
              disabled={scanning}
              className="px-4 py-2 rounded-full bg-neutral-700 hover:bg-neutral-600 text-sm font-medium disabled:opacity-50"
            >
              {scanning ? '…' : 'Scan'}
            </button>
          </div>
          <div>
            <label className="block text-xs text-neutral-500 uppercase tracking-wider mb-1">
              Spotify URL
            </label>
            <input
              type="text"
              value={addUrl}
              onChange={(e) => setAddUrl(e.target.value)}
              placeholder="https://open.spotify.com/album/... or playlist/..."
              className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
              required
            />
          </div>
          <button
            type="submit"
            disabled={addSubmitting || !addUid.trim() || !addUrl.trim()}
            className="px-4 py-2 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-sm disabled:opacity-50"
          >
            {addSubmitting ? 'Adding…' : 'Add mapping'}
          </button>
        </form>
      </section>

      <section>
        <h2 className="text-lg font-medium mb-4">Mappings</h2>
        {records.length === 0 ? (
          <p className="text-neutral-500 text-sm">No mappings yet. Add one above.</p>
        ) : (
          <ul className="space-y-3">
            {records.map((r) => (
              <li
                key={r.record_id}
                className="rounded-xl border border-neutral-800 p-4 flex flex-wrap items-center justify-between gap-4"
              >
                <div className="min-w-0">
                  <p className="font-medium truncate">{r.name || '—'}</p>
                  <p className="text-sm text-neutral-500">
                    <span className="capitalize">{r.type}</span> · UID: <span className="font-mono">{r.nfc_uid}</span>
                  </p>
                  <p className="text-xs text-neutral-600 truncate mt-1">{r.spotify_uri}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => openEdit(r)}
                    className="px-3 py-1.5 rounded-full bg-neutral-700 hover:bg-neutral-600 text-sm"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(r.record_id)}
                    className="px-3 py-1.5 rounded-full bg-red-900/50 hover:bg-red-900 text-red-200 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {editRecord && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-10"
          onClick={() => setEditRecord(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-record-heading"
        >
          <div
            className="bg-neutral-900 border border-neutral-700 rounded-2xl p-6 w-full max-w-md shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="edit-record-heading" className="text-lg font-semibold mb-4">
              Edit mapping
            </h2>
            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-sm text-neutral-400 mb-1">Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-400 mb-1">Spotify URI</label>
                <input
                  type="text"
                  value={editUri}
                  onChange={(e) => setEditUri(e.target.value)}
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-neutral-400 mb-1">Type</label>
                <select
                  value={editType}
                  onChange={(e) => setEditType(e.target.value)}
                  className="w-full rounded-lg bg-neutral-800 border border-neutral-700 px-3 py-2 text-sm"
                >
                  <option value="album">Album</option>
                  <option value="playlist">Playlist</option>
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={editSubmitting}
                  className="px-4 py-2 rounded-full bg-spotify-green hover:bg-spotify-green-hover text-black font-semibold text-sm disabled:opacity-50"
                >
                  {editSubmitting ? 'Saving…' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={() => setEditRecord(null)}
                  className="px-4 py-2 rounded-full bg-neutral-700 hover:bg-neutral-600 text-sm"
                >
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
