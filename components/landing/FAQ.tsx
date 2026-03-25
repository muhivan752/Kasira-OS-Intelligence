'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const faqs = [
  {
    q: "Apakah benar-benar gratis 30 hari?",
    a: "Ya, gratis penuh 30 hari tanpa perlu kartu kredit. Cancel kapan saja."
  },
  {
    q: "Apakah QRIS ada biaya komisi ke Kasira?",
    a: "Tidak ada. Kasira zero komisi selamanya. Lo daftar Midtrans sendiri, uang langsung masuk ke rekening lo."
  },
  {
    q: "Bisa pakai di HP Android biasa?",
    a: "Ya, app kasir bisa diinstall di HP Android manapun. Tidak perlu tablet khusus."
  },
  {
    q: "Bagaimana kalau internet mati?",
    a: "App kasir tetap bisa transaksi saat offline. Data otomatis sync saat internet kembali."
  },
  {
    q: "Apakah data saya aman?",
    a: "Data tersimpan di server Indonesia dengan enkripsi AES-256. Backup otomatis tiap 6 jam."
  }
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="py-24 bg-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight mb-4">
            Pertanyaan yang sering ditanyakan
          </h2>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div 
              key={index} 
              className="border border-gray-200 rounded-2xl overflow-hidden bg-white hover:border-emerald-200 transition-colors"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full flex justify-between items-center p-6 text-left focus:outline-none"
              >
                <span className="font-semibold text-gray-900 text-lg">{faq.q}</span>
                {openIndex === index ? (
                  <ChevronUp className="w-5 h-5 text-emerald-500 shrink-0" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400 shrink-0" />
                )}
              </button>
              
              {openIndex === index && (
                <div className="px-6 pb-6 text-gray-600 leading-relaxed">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
