'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Building2,
  Users,
  Store,
  ShoppingCart,
  DollarSign,
  Crown,
  Phone,
  Calendar,
  Power,
  PowerOff,
  Check,
  CreditCard,
  FileText,
  Zap,
  SkipForward,
  ExternalLink,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import {
  getSuperadminTenantDetail,
  updateTenantTier,
  updateTenantStatus,
  getTenantInvoices,
  generateTenantInvoice,
  activateTenantBilling,
} from '@/app/actions/superadmin';

export default function TenantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tenantId = params.id as string;

  const [tenant, setTenant] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tierValue, setTierValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState('');
  const [invoices, setInvoices] = useState<any[]>([]);
  const [billingAction, setBillingAction] = useState('');

  async function load() {
    const data = await getSuperadminTenantDetail(tenantId);
    if (!data) {
      router.push('/superadmin/tenants');
      return;
    }
    setTenant(data);
    setTierValue(data.subscription_tier || 'starter');
    const invs = await getTenantInvoices(tenantId);
    setInvoices(invs);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, [tenantId]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const handleSaveTier = async () => {
    setSaving(true);
    const result = await updateTenantTier(tenantId, tierValue);
    if (result.success) {
      showToast('Tier berhasil diubah');
      await load();
    }
    setSaving(false);
  };

  const handleToggleActive = async () => {
    setSaving(true);
    const newActive = !tenant.is_active;
    const result = await updateTenantStatus(tenantId, newActive, newActive ? 'active' : 'suspended');
    if (result.success) {
      showToast(newActive ? 'Tenant diaktifkan' : 'Tenant disuspend');
      await load();
    }
    setSaving(false);
  };

  const handleGenerateInvoice = async () => {
    setBillingAction('generate');
    const result = await generateTenantInvoice(tenantId);
    if (result.success) {
      showToast(result.message || 'Invoice dibuat');
      await load();
    } else {
      showToast(result.message || 'Gagal');
    }
    setBillingAction('');
  };

  const handleActivateBilling = async () => {
    setBillingAction('activate');
    const result = await activateTenantBilling(tenantId);
    if (result.success) {
      showToast('Tenant diaktifkan + invoice marked paid');
      await load();
    } else {
      showToast(result.message || 'Gagal');
    }
    setBillingAction('');
  };

  const handleSkipBilling = async () => {
    setBillingAction('skip');
    // Skip = activate tenant without needing payment
    const result = await activateTenantBilling(tenantId);
    if (result.success) {
      showToast('Billing di-skip, tenant aktif');
      await load();
    } else {
      showToast(result.message || 'Gagal');
    }
    setBillingAction('');
  };

  const TIER_PRICES: Record<string, number> = {
    starter: 99000, pro: 299000, business: 499000, enterprise: 0,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Memuat detail tenant...</div>
      </div>
    );
  }

  const formatCurrency = (n: number) =>
    new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(n);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-500/10 border border-green-500/20 text-green-400 px-4 py-2.5 rounded-lg text-sm flex items-center gap-2 animate-fade-in">
          <Check className="w-4 h-4" /> {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/superadmin/tenants" className="p-2 rounded-lg hover:bg-gray-800 text-gray-500 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Building2 className="w-6 h-6 text-gray-600" />
            {tenant.name}
          </h1>
          <p className="text-gray-500 text-sm mt-0.5">{tenant.schema_name}</p>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <InfoCard icon={Users} label="Users" value={tenant.users?.length || 0} color="text-purple-400" bg="bg-purple-500/10" />
        <InfoCard icon={Store} label="Outlets" value={tenant.outlets?.length || 0} color="text-blue-400" bg="bg-blue-500/10" />
        <InfoCard icon={ShoppingCart} label="Orders" value={tenant.order_count} color="text-green-400" bg="bg-green-500/10" />
        <InfoCard icon={DollarSign} label="Revenue" value={formatCurrency(tenant.revenue_total)} color="text-yellow-400" bg="bg-yellow-500/10" />
      </div>

      {/* Details Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Subscription */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Subscription</h2>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Status</span>
              {tenant.is_active ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/10 text-green-400">Active</span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400">Suspended</span>
              )}
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Tier</span>
              <div className="flex items-center gap-2">
                <select
                  value={tierValue}
                  onChange={(e) => setTierValue(e.target.value)}
                  className="bg-gray-800 border border-gray-700 text-white text-xs rounded-lg px-2 py-1 focus:outline-none"
                >
                  <option value="starter">Starter</option>
                  <option value="pro">Pro</option>
                  <option value="business">Business</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                {tierValue !== (tenant.subscription_tier || 'starter') && (
                  <button
                    onClick={handleSaveTier}
                    disabled={saving}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg disabled:opacity-50"
                  >
                    Save
                  </button>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Created</span>
              <span className="text-sm text-gray-300">
                {new Date(tenant.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'long', year: 'numeric' })}
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-gray-800">
            <button
              onClick={handleToggleActive}
              disabled={saving}
              className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50
                ${tenant.is_active
                  ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                  : 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                }`}
            >
              {tenant.is_active ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
              {tenant.is_active ? 'Suspend Tenant' : 'Activate Tenant'}
            </button>
          </div>
        </div>

        {/* Owner Info */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Owner</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Nama</span>
              <span className="text-sm text-gray-300">{tenant.owner_name || '-'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Phone</span>
              <span className="text-sm text-gray-300 flex items-center gap-1">
                <Phone className="w-3 h-3" /> {tenant.owner_phone || '-'}
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-gray-800">
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Outlets</h3>
            <div className="space-y-1.5">
              {(tenant.outlets || []).map((o: any) => (
                <div key={o.id} className="flex items-center gap-2 text-sm text-gray-400">
                  <Store className="w-3.5 h-3.5 text-gray-600" /> {o.name}
                </div>
              ))}
              {(!tenant.outlets || tenant.outlets.length === 0) && (
                <div className="text-xs text-gray-600">Belum ada outlet</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Billing Section */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
            <CreditCard className="w-4 h-4" /> Billing
          </h2>
          <span className="text-xs text-gray-500">
            {formatCurrency(TIER_PRICES[tenant.subscription_tier || 'starter'] || 0)}/bulan
          </span>
        </div>

        <div className="p-5 space-y-4">
          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleGenerateInvoice}
              disabled={!!billingAction}
              className="flex items-center gap-1.5 px-3 py-2 bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 rounded-lg text-xs font-medium disabled:opacity-50 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              {billingAction === 'generate' ? 'Loading...' : 'Generate Invoice'}
            </button>

            <button
              onClick={handleActivateBilling}
              disabled={!!billingAction}
              className="flex items-center gap-1.5 px-3 py-2 bg-green-600/10 text-green-400 hover:bg-green-600/20 rounded-lg text-xs font-medium disabled:opacity-50 transition-colors"
            >
              <Zap className="w-3.5 h-3.5" />
              {billingAction === 'activate' ? 'Loading...' : 'Activate (Mark Paid)'}
            </button>

            <button
              onClick={handleSkipBilling}
              disabled={!!billingAction}
              className="flex items-center gap-1.5 px-3 py-2 bg-amber-600/10 text-amber-400 hover:bg-amber-600/20 rounded-lg text-xs font-medium disabled:opacity-50 transition-colors"
            >
              <SkipForward className="w-3.5 h-3.5" />
              {billingAction === 'skip' ? 'Loading...' : 'Skip Billing'}
            </button>
          </div>

          {/* Invoice History */}
          {invoices.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase px-3 py-2">Periode</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase px-3 py-2">Amount</th>
                    <th className="text-center text-xs font-semibold text-gray-500 uppercase px-3 py-2">Status</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase px-3 py-2">Paid</th>
                    <th className="text-left text-xs font-semibold text-gray-500 uppercase px-3 py-2">Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {invoices.map((inv: any) => (
                    <tr key={inv.id}>
                      <td className="px-3 py-2 text-xs text-gray-300">
                        {inv.billing_period_start ? new Date(inv.billing_period_start).toLocaleDateString('id-ID', { month: 'short', year: 'numeric' }) : '-'}
                      </td>
                      <td className="px-3 py-2 text-xs text-white font-medium">{formatCurrency(inv.amount)}</td>
                      <td className="px-3 py-2 text-center">
                        <InvoiceStatusBadge status={inv.status} />
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-400">
                        {inv.paid_at ? new Date(inv.paid_at).toLocaleDateString('id-ID') : '-'}
                      </td>
                      <td className="px-3 py-2">
                        {inv.xendit_invoice_url ? (
                          <a href={inv.xendit_invoice_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        ) : (
                          <span className="text-gray-600 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center text-gray-600 text-xs py-4">Belum ada invoice</div>
          )}
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Users ({tenant.users?.length || 0})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-5 py-2.5">Nama</th>
                <th className="text-left text-xs font-semibold text-gray-500 uppercase px-5 py-2.5">Phone</th>
                <th className="text-center text-xs font-semibold text-gray-500 uppercase px-5 py-2.5">Role</th>
                <th className="text-center text-xs font-semibold text-gray-500 uppercase px-5 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {(tenant.users || []).map((u: any) => (
                <tr key={u.id}>
                  <td className="px-5 py-2.5 text-sm text-white">{u.name}</td>
                  <td className="px-5 py-2.5 text-sm text-gray-400">{u.phone}</td>
                  <td className="px-5 py-2.5 text-center">
                    {u.is_superuser ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400">Owner</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-800 text-gray-400">Kasir</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 text-center">
                    {u.is_active ? (
                      <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function InvoiceStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; color: string }> = {
    pending: { label: 'Pending', color: 'bg-yellow-500/10 text-yellow-400' },
    paid: { label: 'Paid', color: 'bg-green-500/10 text-green-400' },
    expired: { label: 'Expired', color: 'bg-red-500/10 text-red-400' },
    grace: { label: 'Grace', color: 'bg-orange-500/10 text-orange-400' },
    suspended: { label: 'Suspended', color: 'bg-red-500/10 text-red-400' },
    cancelled: { label: 'Cancelled', color: 'bg-gray-500/10 text-gray-400' },
  };
  const c = config[status] || config.pending;
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${c.color}`}>
      {c.label}
    </span>
  );
}

function InfoCard({ icon: Icon, label, value, color, bg }: {
  icon: any; label: string; value: string | number; color: string; bg: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className={`p-2 rounded-lg ${bg} w-fit mb-3`}>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div className="text-xl font-bold text-white truncate">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}
