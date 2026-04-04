'use client';

import Link from 'next/link';
import {
  Lock,
  CalendarCheck,
  Bot,
  Star,
  Receipt,
  Building2,
  BarChart3,
  MessageCircle
} from 'lucide-react';

const PRO_FEATURES = [
  {
    icon: CalendarCheck,
    name: 'Reservasi & Booking',
    description: 'Pelanggan bisa booking meja via storefront. Konfirmasi otomatis + notifikasi WA.',
  },
  {
    icon: Bot,
    name: 'AI Chatbot Owner',
    description: 'Tanya laporan & insight bisnis via WhatsApp. "Produk terlaris minggu ini?"',
  },
  {
    icon: Star,
    name: 'Loyalty Points',
    description: 'Program poin otomatis. 1 poin per Rp10.000. Redeem langsung di kasir.',
  },
  {
    icon: Receipt,
    name: 'Tab / Bon Pelanggan',
    description: 'Pembayaran cicil atau bon langganan. Cocok untuk pelanggan tetap.',
  },
  {
    icon: Building2,
    name: 'Multi-Outlet',
    description: 'Kelola banyak cabang dalam satu akun. Laporan konsolidasi semua outlet.',
  },
  {
    icon: BarChart3,
    name: 'Laporan Lanjutan',
    description: 'Analitik HPP, tren penjualan, perbandingan antar periode, export Excel.',
  },
];

const WA_NUMBER = '6285270782220';
const WA_MESSAGE = encodeURIComponent('Halo Kasira, saya tertarik upgrade ke Pro. Bisa info lebih lanjut?');

export default function ProPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-1.5 rounded-full text-sm font-semibold mb-4">
          <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
          Kasira Pro
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-3">Tingkatkan Bisnis Anda</h1>
        <p className="text-gray-500 text-base">
          Fitur-fitur Pro dirancang untuk cafe yang sudah berkembang dan butuh lebih dari sekadar POS.
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {PRO_FEATURES.map((feature) => (
          <div
            key={feature.name}
            className="relative bg-white rounded-xl border border-gray-200 p-6 overflow-hidden group"
          >
            {/* Grayscale overlay */}
            <div className="absolute inset-0 bg-white/60 backdrop-blur-[1px] z-10 rounded-xl" />

            {/* PRO badge */}
            <div className="absolute top-4 right-4 z-20">
              <span className="inline-flex items-center gap-1 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-0.5 rounded-full">
                <Star className="w-3 h-3 fill-yellow-900" />
                PRO
              </span>
            </div>

            {/* Lock icon */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="bg-gray-900/80 rounded-full p-3">
                <Lock className="w-5 h-5 text-white" />
              </div>
            </div>

            {/* Content (behind overlay) */}
            <div className="relative z-0">
              <div className="w-11 h-11 rounded-lg bg-blue-50 flex items-center justify-center mb-4">
                <feature.icon className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-1">{feature.name}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{feature.description}</p>
            </div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-8 text-center text-white">
        <h2 className="text-2xl font-bold mb-2">Siap Upgrade ke Pro?</h2>
        <p className="text-blue-100 mb-6 text-sm">
          Hubungi kami via WhatsApp. Aktivasi manual oleh tim Kasira, efektif hari yang sama.
        </p>
        <a
          href={`https://wa.me/${WA_NUMBER}?text=${WA_MESSAGE}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold px-6 py-3 rounded-xl hover:bg-blue-50 transition-colors"
        >
          <MessageCircle className="w-5 h-5" />
          Chat WhatsApp Sekarang
        </a>
      </div>
    </div>
  );
}
