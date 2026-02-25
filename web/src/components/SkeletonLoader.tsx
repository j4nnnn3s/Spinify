import { memo } from 'react'

interface SkeletonLoaderProps {
  /** Optional class for the root. */
  className?: string
  /** 'card' = main now-playing card, 'grid' = bottom status grid, 'full' = both */
  variant?: 'card' | 'grid' | 'full'
}

function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-neutral-800 bg-neutral-900/50 overflow-hidden animate-fade-in ${className}`}
      role="status"
      aria-label="Loading"
    >
      <div className="p-6">
        <div className="h-6 w-32 rounded bg-neutral-800 animate-pulse mb-4" />
        <div className="flex flex-col sm:flex-row gap-6 items-start">
          <div className="w-48 h-48 rounded-xl bg-neutral-800 animate-pulse flex-shrink-0" />
          <div className="flex-1 min-w-0 space-y-3">
            <div className="h-4 w-3/4 rounded bg-neutral-800 animate-pulse" />
            <div className="h-4 w-1/2 rounded bg-neutral-800 animate-pulse" />
            <div className="h-3 w-1/3 rounded bg-neutral-800 animate-pulse" />
            <div className="flex gap-2 pt-2">
              <div className="h-10 w-24 rounded-full bg-neutral-800 animate-pulse" />
              <div className="h-10 w-28 rounded-full bg-neutral-800 animate-pulse" />
            </div>
          </div>
        </div>
      </div>
      <div className="h-1 bg-neutral-800">
        <div className="h-full w-1/3 bg-neutral-700 animate-pulse rounded-r" />
      </div>
    </div>
  )
}

function SkeletonGrid({ className = '' }: { className?: string }) {
  return (
    <div
      className={`grid grid-cols-1 sm:grid-cols-2 gap-4 animate-fade-in ${className}`}
      role="status"
      aria-label="Loading"
    >
      {[1, 2].map((i) => (
        <div key={i} className="rounded-xl border border-neutral-800 p-4 flex gap-4 items-center">
          <div className="w-16 h-16 rounded-lg bg-neutral-800 animate-pulse flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-20 rounded bg-neutral-800 animate-pulse" />
            <div className="h-4 w-full rounded bg-neutral-800 animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  )
}

function SkeletonLoaderInner({ className = '', variant = 'full' }: SkeletonLoaderProps) {
  if (variant === 'card') return <SkeletonCard className={className} />
  if (variant === 'grid') return <SkeletonGrid className={className} />
  return (
    <div className={`space-y-8 animate-fade-in ${className}`} role="status" aria-label="Loading">
      <SkeletonCard />
      <SkeletonGrid />
    </div>
  )
}

export const SkeletonLoader = memo(SkeletonLoaderInner)
