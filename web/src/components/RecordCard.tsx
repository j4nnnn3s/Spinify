import { memo } from 'react'

interface RecordCardProps {
  coverUrl: string | null
  spotifyUri: string | null
  uid: string | null
  /** Record name (album/playlist title); shown instead of URI when set. */
  recordName?: string | null
  label?: string
  children?: React.ReactNode
  /** Optional: show compact (smaller) layout. */
  compact?: boolean
}

function RecordCardInner({
  coverUrl,
  spotifyUri,
  uid,
  recordName = null,
  label = 'Current record',
  children,
  compact = false,
}: RecordCardProps) {
  const size = compact ? 'w-14 h-14' : 'w-16 h-16'
  const rounded = compact ? 'rounded-lg' : 'rounded-xl'

  return (
    <article
      className="rounded-xl border border-neutral-800 p-4 flex gap-4 items-center bg-neutral-900/30 transition-colors hover:border-neutral-700 focus-within:ring-2 focus-within:ring-spotify-green/50 focus-within:ring-offset-2 focus-within:ring-offset-neutral-950"
      aria-labelledby="record-card-label"
    >
      <div
        className={`${size} rounded-lg bg-neutral-800 flex-shrink-0 overflow-hidden flex items-center justify-center ${rounded}`}
      >
        {coverUrl ? (
          <img
            src={coverUrl}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <span className="text-xs text-neutral-500" aria-hidden>
            {spotifyUri ? 'No image' : '—'}
          </span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p
          id="record-card-label"
          className="text-xs text-neutral-500 uppercase tracking-wider mb-1"
        >
          {label}
        </p>
        <p className="font-medium truncate text-sm sm:text-base">
          {recordName != null && recordName !== '' ? (
            recordName
          ) : spotifyUri ? (
            <span className="text-xs sm:text-sm text-neutral-400 break-all">{spotifyUri}</span>
          ) : uid ? (
            `UID: ${uid}`
          ) : (
            '—'
          )}
        </p>
        {children}
      </div>
    </article>
  )
}

export const RecordCard = memo(RecordCardInner)
