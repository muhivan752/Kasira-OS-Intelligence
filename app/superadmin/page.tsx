'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Building2,
  Users,
  TrendingUp,
  Star,
  Crown,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { getSuperadminStats, getSuperadminTenants } from '@/app/actions/superadmin';

export default function SuperadminOverview() {
  const [stats, setStats] = useState<any>(null);
  const [recentTenants, setRecentTenants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      const [s, t] = await Promise.all([
        getSuperadminStats(),
        getSuperadminTenants(),
      ]);
      if (!s) {
        setError('Akses ditolak. Pastikan akun Anda terdaftar sebagai superadmin.');
        setLoading(false);
        return;
      }
      setStats(s);
      setRecentTenants((t.tenants || []).slice(0, 5));
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Memuat data platform...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-6 py-4 rounded-xl text-sm">
          {error}
        </div>
      </div>
    );
  }

  const statCards = [
    { label: 'Total Tenants', value: stats.total_tenants, icon: Building2, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { label: 'Active', value: stats.active_tenants, icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-500/10' },
    { label: 'Total Users', value: stats.total_users, icon: Users, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { label: 'New (7d)', value: stats.new_tenants_7d, icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  ];

  const tierCards = [
    { label: 'Starter', value: stats.starter_count, icon: Star, color: 'text-gray-400' },
    { label: 'Pro', value: stats.pro_count, icon: Crown, color: 'text-blue-400' },
    { label: 'Business', value: stats.business_count, icon: Crown, color: 'text-amber-400' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Platform Overview</h1>
        <p className="text-gray-500 text-sm mt-1">Kasira SaaS — semua tenant & metrik</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 rounded-lg ${card.bg}`}>
                <card.icon className={`w-5 h-5 ${card.color}`} />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">{card.value}</div>
            <div className="text-xs text-gray-500 mt-1">{card.label}</div>
          </div>
        ))}
      </div>

      {/* Tier Breakdown */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Tier Breakdown</h2>
        <div className="grid grid-cols-3 gap-4">
          {tierCards.map((tc) => (
            <div key={tc.label} className="text-center">
              <tc.icon className={`w-6 h-6 mx-auto mb-2 ${tc.color}`} />
              <div className="text-xl font-bold text-white">{tc.value}</div>
              <div className="text-xs text-gray-500">{tc.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Tenants */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Tenant Terbaru</h2>
          <Link href="/superadmin/tenants" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
            Lihat Semua <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="divide-y divide-gray-800">
          {recentTenants.map((t: any) => (
            <Link key={t.id} href={`/superadmin/tenants/${t.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-gray-800/50 transition-colors">
              <div>
                <div className="text-sm font-medium text-white">{t.name}</div>
                <div className="text-xs text-gray-500">{t.owner_name || 'No owner'} &middot; {t.owner_phone || '-'}</div>
              </div>
              <div className="flex items-center gap-3">
                <TierBadge tier={t.subscription_tier} />
                <div className="text-xs text-gray-600">
                  {new Date(t.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                </div>
              </div>
            </Link>
          ))}
          {recentTenants.length === 0 && (
            <div className="px-5 py-8 text-center text-gray-600 text-sm">Belum ada tenant</div>
          )}
        </div>
      </div>
    </div>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const styles: Record<string, string> = {
    starter: 'bg-gray-800 text-gray-400',
    pro: 'bg-blue-500/10 text-blue-400',
    business: 'bg-amber-500/10 text-amber-400',
    enterprise: 'bg-purple-500/10 text-purple-400',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${styles[tier] || styles.starter}`}>
      {tier || 'starter'}
    </span>
  );
}
