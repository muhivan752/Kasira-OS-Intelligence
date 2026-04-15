'use client';

import { useState, useEffect } from 'react';
import { getBillingInfo, getBillingInvoices, retryInvoicePayment } from '@/app/actions/api';
import { Loader2, CreditCard, Crown, AlertTriangle, ExternalLink, CheckCircle, Clock, XCircle } from 'lucide-react';
import Link from 'next/link';

const TIER_COLORS: Record<string, string> = {
  starter: 'bg-gray-100 text-gray-700',
  pro: 'bg-blue-100 text-blue-700',
  business: 'bg-purple-100 text-purple-700',
  enterprise: 'bg-amber-100 text-amber-700',
};

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  pending: { label: 'Menunggu Pembayaran', color: 'bg-yellow-100 text-yellow-700', icon: Clock },
  paid: { label: 'Lunas', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  expired: { label: 'Kedaluwarsa', color: 'bg-red-100 text-red-700', icon: XCircle },
  grace: { label: 'Grace Period', color: 'bg-orange-100 text-orange-700', icon: AlertTriangle },
  suspended: { label: 'Ditangguhkan', color: 'bg-red-100 text-red-700', icon: XCircle },
  cancelled: { label: 'Dibatalkan', color: 'bg-gray-100 text-gray-500', icon: XCircle },
};

function formatCurrency(amount: number) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount);
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function BillingPage() {
  const [loading, setLoading] = useState(true);
  const [billing, setBilling] = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [retrying, setRetrying] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [info, invList] = await Promise.all([
        getBillingInfo(),
        getBillingInvoices(),
      ]);
      setBilling(info);
      setInvoices(invList || []);
    } catch (e) {
      console.error('Failed to load billing:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleRetry(invoiceId: string) {
    setRetrying(invoiceId);
    try {
      const result = await retryInvoicePayment(invoiceId);
      if (result?.xendit_invoice_url) {
        window.open(result.xendit_invoice_url, '_blank');
      }
      await loadData();
    } catch (e: any) {
      alert(e.message || 'Gagal membuat invoice');
    } finally {
      setRetrying(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!billing) {
    return (
      <div className="p-6 text-center text-gray-500">
        Gagal memuat data billing.
      </div>
    );
  }

  const unpaidInvoice = billing.latest_invoice && !['paid', 'cancelled'].includes(billing.latest_invoice.status)
    ? billing.latest_invoice
    : null;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-6">
      <div className="flex items-center gap-3">
        <CreditCard className="w-6 h-6 text-gray-700" />
        <h1 className="text-xl font-bold text-gray-900">Langganan & Billing</h1>
      </div>

      {/* Unpaid Invoice Alert */}
      {unpaidInvoice && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-amber-800">
              {unpaidInvoice.status === 'grace' ? 'Pembayaran jatuh tempo!' : 'Ada invoice belum dibayar'}
            </p>
            <p className="text-sm text-amber-700 mt-1">
              {formatCurrency(unpaidInvoice.amount)} — jatuh tempo {formatDate(unpaidInvoice.due_date)}
            </p>
            <div className="mt-3 bg-white rounded-lg p-3 border border-amber-200 text-sm">
              <p className="font-semibold text-amber-800 mb-1.5">Transfer ke:</p>
              <p className="text-amber-700">Bank <strong>Mandiri</strong> — <span className="font-mono font-bold">1060021987147</span></p>
              <p className="text-amber-700">a.n. <strong>MIRFAN</strong></p>
              <p className="text-xs text-amber-500 mt-1.5">Konfirmasi pembayaran via WhatsApp setelah transfer.</p>
            </div>
            <a
              href="https://wa.me/6285270782220?text=Halo%20Kasira%2C%20saya%20sudah%20transfer%20untuk%20pembayaran%20invoice."
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-2 px-4 py-2 bg-amber-600 text-white text-sm font-semibold rounded-lg hover:bg-amber-700 transition"
            >
              Konfirmasi via WhatsApp
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}

      {/* Current Plan */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center gap-2">
          <Crown className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-bold text-gray-900">Paket Saat Ini</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-4 mb-4">
            <span className={`px-3 py-1 rounded-full text-sm font-bold ${TIER_COLORS[billing.tier] || TIER_COLORS.starter}`}>
              {billing.tier_label}
            </span>
            <span className="text-2xl font-bold text-gray-900">
              {formatCurrency(billing.price)}
              <span className="text-sm font-normal text-gray-500">/bulan</span>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Status</span>
              <p className="font-semibold text-gray-900 capitalize">{billing.subscription_status || 'active'}</p>
            </div>
            <div>
              <span className="text-gray-500">Tanggal Billing</span>
              <p className="font-semibold text-gray-900">Tanggal {billing.billing_day} setiap bulan</p>
            </div>
            <div>
              <span className="text-gray-500">Billing Berikutnya</span>
              <p className="font-semibold text-gray-900">
                {billing.next_billing_date ? formatDate(billing.next_billing_date) : 'Belum diatur'}
              </p>
            </div>
          </div>

          {billing.tier === 'starter' && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <Link
                href="/dashboard/pro"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-semibold rounded-lg hover:from-blue-700 hover:to-indigo-700 transition"
              >
                <Crown className="w-4 h-4" />
                Upgrade ke Pro
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Invoice History */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-900">Riwayat Invoice</h2>
        </div>

        {invoices.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">
            Belum ada invoice.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-left">
                <tr>
                  <th className="px-6 py-3 font-medium">Periode</th>
                  <th className="px-6 py-3 font-medium">Paket</th>
                  <th className="px-6 py-3 font-medium">Jumlah</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Dibayar</th>
                  <th className="px-6 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map((inv: any) => {
                  const cfg = STATUS_CONFIG[inv.status] || STATUS_CONFIG.pending;
                  const StatusIcon = cfg.icon;
                  const canPay = ['pending', 'expired', 'grace', 'suspended'].includes(inv.status);

                  return (
                    <tr key={inv.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 whitespace-nowrap">
                        {formatDate(inv.billing_period_start)} - {formatDate(inv.billing_period_end)}
                      </td>
                      <td className="px-6 py-3 capitalize">{inv.tier}</td>
                      <td className="px-6 py-3 font-medium">{formatCurrency(inv.amount)}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color}`}>
                          <StatusIcon className="w-3 h-3" />
                          {cfg.label}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-gray-500">{formatDate(inv.paid_at)}</td>
                      <td className="px-6 py-3">
                        {canPay && inv.xendit_invoice_url && (
                          <a
                            href={inv.xendit_invoice_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-700 text-xs font-semibold"
                          >
                            Bayar
                          </a>
                        )}
                        {canPay && !inv.xendit_invoice_url && (
                          <button
                            onClick={() => handleRetry(inv.id)}
                            disabled={retrying === inv.id}
                            className="text-blue-600 hover:text-blue-700 text-xs font-semibold disabled:opacity-50"
                          >
                            {retrying === inv.id ? 'Loading...' : 'Buat Invoice'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
