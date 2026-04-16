'use client'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex items-center justify-center min-h-[60vh] px-4">
      <div className="text-center max-w-md">
        <div className="text-5xl mb-4">⚠️</div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Gagal Memuat Halaman
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Terjadi kesalahan saat memuat data. Periksa koneksi internet Anda dan coba lagi.
        </p>
        <button
          onClick={reset}
          className="px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium"
        >
          Muat Ulang
        </button>
      </div>
    </div>
  )
}
