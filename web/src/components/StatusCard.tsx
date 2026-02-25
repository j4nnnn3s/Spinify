import { memo } from 'react'

interface StatusCardProps {
  label: string
  value: string
  /** Optional id for aria-labelledby. */
  id?: string
}

function StatusCardInner({ label, value, id }: StatusCardProps) {
  return (
    <article
      className="rounded-xl border border-neutral-800 p-4 bg-neutral-900/30 transition-colors hover:border-neutral-700 focus-within:ring-2 focus-within:ring-spotify-green/50 focus-within:ring-offset-2 focus-within:ring-offset-neutral-950"
      aria-labelledby={id}
    >
      <p
        id={id}
        className="text-xs text-neutral-500 uppercase tracking-wider mb-1"
      >
        {label}
      </p>
      <p className="font-medium">{value}</p>
    </article>
  )
}

export const StatusCard = memo(StatusCardInner)
