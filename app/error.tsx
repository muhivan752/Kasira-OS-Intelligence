'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)] px-4 text-[var(--text-body)]">
      <div className="text-center max-w-md">
        <h2 className="text-2xl font-semibold text-[var(--text-strong)] mb-2">
          Halaman belum dapat dimuat
        </h2>
        <p className="text-[var(--text-muted)] mb-6">
          Coba muat kembali halaman ini.
        </p>
        <button
          onClick={reset}
          className="ks-btn"
        >
          Coba Lagi
        </button>
      </div>
    </div>
  )
}
