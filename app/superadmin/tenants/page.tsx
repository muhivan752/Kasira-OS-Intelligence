'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  Building2,
  Users,
  Store,
  ChevronRight,
  Power,
  PowerOff,
} from 'lucide-react';
import { getSuperadminTenants, updateTenantTier, updateTenantStatus } from '@/app/actions/superadmin';

const TIERS = ['all', 'starter', 'pro', 'business', 'enterprise'] as const;

export default function TenantsPage() {
  const [tenants, setTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterTier, setFilterTier] = useState('all');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const params: any = {};
    if (filterTier !== 'all') params.tier = filterTier;
    if (search.trim()) params.search = search.trim();
    const result = await getSuperadminTenants(params);
    setTenants(result.tenants || []);
    setLoading(false);
  }, [filterTier, search]);

  useEffect(() => {
    load();
  }, [load]);

  const handleTierChange = async (tenantId: string, newTier: string) => {
    setActionLoading(tenantId);
    const result = await updateTenantTier(tenantId, newTier);
    if (result.success) await load();
    setActionLoading(null);
  };

  const handleToggleActive = async (tenantId: string, currentActive: boolean) => {
    setActionLoading(tenantId);
    const result = await updateTenantStatus(tenantId, !currentActive, !currentActive ? 'active' : 'suspended');
    if (result.success) await load();
    setActionLoading(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Tenant Management</h1>
        <p className="text-gray-500 text-sm mt-1">Kelola semua tenant Kasira</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Cari nama tenant..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-gray-700"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          {TIERS.map((t) => (
            <button
              key={t}
              onClick={() => setFilterTier(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                ${filterTier === t ? 'bg-gray-700 text-white' : 'bg-gray-900 text-gray-500 hover:bg-gray-800'}`}
            >
              {t === 'all' ? 'Semua' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="px-5 py-12 text-center text-gray-600 text-sm">Memuat...</div>
        ) : tenants.length === 0 ? (
          <div className="px-5 py-12 text-center text-gray-600 text-sm">Tidak ada tenant ditemukan</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Tenant</th>
                  <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Owner</th>
                  <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Tier</th>
                  <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Users</th>
                  <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Outlets</th>
                  <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
                  <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Created</th>
                  <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {tenants.map((t: any) => (
                  <tr key={t.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="px-5 py-3">
                      <Link href={`/superadmin/tenants/${t.id}`} className="flex items-center gap-2 group">
                        <Building2 className="w-4 h-4 text-gray-600" />
                        <span className="text-sm font-medium text-white group-hover:text-blue-400 transition-colors">{t.name}</span>
                        <ChevronRight className="w-3 h-3 text-gray-700 group-hover:text-blue-400 transition-colors" />
                      </Link>
                    </td>
                    <td className="px-5 py-3">
                      <div className="text-sm text-gray-300">{t.owner_name || '-'}</div>
                      <div className="text-xs text-gray-600">{t.owner_phone || ''}</div>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <select
                        value={t.subscription_tier || 'starter'}
                        onChange={(e) => handleTierChange(t.id, e.target.value)}
                        disabled={actionLoading === t.id}
                        className="bg-gray-800 border border-gray-700 text-white text-xs rounded-lg px-2 py-1 focus:outline-none focus:border-gray-600 disabled:opacity-50"
                      >
                        <option value="starter">Starter</option>
                        <option value="pro">Pro</option>
                        <option value="business">Business</option>
                        <option value="enterprise">Enterprise</option>
                      </select>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <div className="flex items-center justify-center gap-1 text-sm text-gray-400">
                        <Users className="w-3.5 h-3.5" /> {t.user_count}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <div className="flex items-center justify-center gap-1 text-sm text-gray-400">
                        <Store className="w-3.5 h-3.5" /> {t.outlet_count}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-center">
                      {t.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-500/10 text-green-400">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/10 text-red-400">
                          Suspended
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-center text-xs text-gray-500">
                      {new Date(t.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => handleToggleActive(t.id, t.is_active)}
                        disabled={actionLoading === t.id}
                        title={t.is_active ? 'Suspend' : 'Activate'}
                        className={`p-1.5 rounded-lg transition-colors disabled:opacity-50
                          ${t.is_active
                            ? 'text-red-400 hover:bg-red-500/10'
                            : 'text-green-400 hover:bg-green-500/10'
                          }`}
                      >
                        {t.is_active ? <PowerOff className="w-4 h-4" /> : <Power className="w-4 h-4" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
