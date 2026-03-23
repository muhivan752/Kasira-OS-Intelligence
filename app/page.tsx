import Link from "next/link";
import { ArrowRight, Terminal } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F5F5F5] text-[#141414] font-sans flex flex-col items-center justify-center p-8">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-sm border border-black/5 p-12 text-center">
        <div className="w-16 h-16 bg-[#FF5C00]/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Terminal className="w-8 h-8 text-[#FF5C00]" />
        </div>
        
        <h1 className="text-4xl font-bold tracking-tight mb-4" style={{ fontFamily: 'var(--font-sans)' }}>
          Kasira API & Self-Order
        </h1>
        
        <p className="text-lg text-gray-500 mb-8">
          Backend FastAPI sedang berjalan. Aplikasi Kasir (Flutter) tersedia di dalam folder <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">kasir_app/</code>.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
          <div className="p-6 rounded-xl border border-black/5 bg-gray-50">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              FastAPI Backend
            </h3>
            <p className="text-sm text-gray-500 mb-4">API endpoints untuk POS, Orders, Payments, dan Midtrans Webhook.</p>
            <a href="/docs" target="_blank" className="text-[#FF5C00] text-sm font-medium flex items-center gap-1 hover:underline">
              Buka Swagger UI <ArrowRight className="w-4 h-4" />
            </a>
          </div>

          <div className="p-6 rounded-xl border border-black/5 bg-gray-50">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              Flutter Kasir App
            </h3>
            <p className="text-sm text-gray-500 mb-4">UI Kasir dengan Riverpod & GoRouter. Download source code untuk di-run lokal.</p>
            <span className="text-gray-400 text-sm font-medium flex items-center gap-1">
              (Lihat folder kasir_app)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
