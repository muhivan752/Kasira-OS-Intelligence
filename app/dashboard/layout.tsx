'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Menu as MenuIcon,
  Users,
  BarChart3,
  Settings,
  LogOut,
  X,
  Star,
  Bot,
  CalendarDays,
  Crown,
  Lock,
  Package,
  Smartphone,
} from 'lucide-react';
import { logout } from '@/app/actions/auth';
import { getCurrentUser, getOutlets } from '@/app/actions/api';
import { Logo } from '@/components/ui/logo';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [outletName, setOutletName] = useState('Memuat...');
  const [tier, setTier] = useState('starter');
  const [subStatus, setSubStatus] = useState('active');
  const [stockMode, setStockMode] = useState('simple');
  const pathname = usePathname();
  const router = useRouter();

  const isPro = ['pro', 'business', 'enterprise'].includes(tier);

  useEffect(() => {
    async function loadData() {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/login');
          return;
        }
        setTier(user.subscription_tier || 'starter');
        setSubStatus(user.subscription_status || 'active');
        const outlets = await getOutlets();
        if (outlets && outlets.length > 0) {
          setOutletName(outlets[0].name);
          setStockMode(outlets[0].stock_mode || 'simple');
        } else {
          setOutletName('Belum ada Outlet');
        }
      } catch (error: any) {
        if (error?.message === 'SESSION_EXPIRED' || error?.message === 'Unauthorized') {
          router.push('/login');
          return;
        }
        console.error('Failed to load user data', error);
      }
    }
    loadData();
  }, [router]);

  const handleLogout = async () => {
    await logout();
  };

  // Build navigation based on tier
  const mainNav = [
    { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Menu', href: '/dashboard/menu', icon: MenuIcon },
    { name: 'Kasir', href: '/dashboard/kasir', icon: Users },
    { name: 'Laporan', href: '/dashboard/laporan', icon: BarChart3 },
  ];

  const proNav = [
    ...(stockMode === 'recipe' ? [{ name: 'Bahan Baku', href: '/dashboard/bahan-baku', icon: Package }] : []),
    { name: 'Reservasi', href: '/dashboard/reservasi', icon: CalendarDays },
    { name: 'AI Asisten', href: '/dashboard/ai', icon: Bot },
  ];

  const bottomNav = [
    { name: 'Download Kasir', href: '/download', icon: Smartphone },
    { name: 'Pengaturan', href: '/dashboard/settings', icon: Settings },
  ];

  const renderNavItem = (item: { name: string; href: string; icon: any }, locked = false) => {
    const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
    return (
      <Link
        key={item.name}
        href={locked ? '/dashboard/pro' : item.href}
        className={`
          flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
          ${isActive
            ? 'bg-blue-50 text-blue-700'
            : locked
              ? 'text-gray-400 hover:bg-gray-50'
              : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
          }
        `}
      >
        <item.icon className={`w-5 h-5 ${isActive ? 'text-blue-700' : locked ? 'text-gray-300' : 'text-gray-400'}`} />
        <span className="flex-1">{item.name}</span>
        {locked && <Lock className="w-3.5 h-3.5 text-gray-300" />}
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-900/80 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full flex flex-col">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
            <div className="flex items-center gap-3 min-w-0">
              <Logo size="sm" variant="light" showWordmark={false} />
              <div className="min-w-0">
                <span className="text-base font-bold text-gray-900 truncate block max-w-[140px]">
                  {outletName}
                </span>
              </div>
              {isPro && (
                <span className="inline-flex items-center gap-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0">
                  <Crown className="w-3 h-3" />
                  PRO
                </span>
              )}
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 text-gray-500 hover:bg-gray-100 rounded-md"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
            {/* Main navigation — always visible */}
            {mainNav.map((item) => renderNavItem(item))}

            {/* Pro features — unlocked for Pro, locked for Starter */}
            {isPro ? (
              <>
                {proNav.map((item) => renderNavItem(item))}
              </>
            ) : (
              <div className="pt-3 mt-3 border-t border-gray-100">
                <p className="px-3 mb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">Upgrade ke Pro</p>
                {proNav.map((item) => renderNavItem(item, true))}
                <Link
                  href="/dashboard/pro"
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors mt-1
                    ${pathname.startsWith('/dashboard/pro')
                      ? 'bg-yellow-50 text-yellow-700'
                      : 'text-yellow-600 hover:bg-yellow-50'
                    }
                  `}
                >
                  <Star className={`w-5 h-5 ${pathname.startsWith('/dashboard/pro') ? 'text-yellow-500' : 'text-yellow-400'}`} />
                  <span className="flex-1">Lihat Fitur Pro</span>
                </Link>
              </div>
            )}

            {/* Spacer */}
            <div className="flex-1" />

            {/* Bottom nav */}
            <div className="pt-3 mt-3 border-t border-gray-100">
              {bottomNav.map((item) => renderNavItem(item))}
            </div>
          </nav>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-gray-200">
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Keluar
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile Header */}
        <div className="lg:hidden flex items-center justify-between h-16 px-4 bg-white border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Logo size="sm" variant="light" showWordmark={false} />
            <span className="text-lg font-bold text-gray-900 truncate max-w-[150px]">
              {outletName}
            </span>
            {isPro && (
              <span className="inline-flex items-center gap-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                <Crown className="w-3 h-3" />
                PRO
              </span>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-md"
          >
            <MenuIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Billing Warning Banner */}
        {['grace', 'suspended'].includes(subStatus) && (
          <div className={`px-4 py-2.5 text-sm font-medium text-center ${
            subStatus === 'suspended'
              ? 'bg-red-600 text-white'
              : 'bg-amber-500 text-white'
          }`}>
            {subStatus === 'suspended'
              ? 'Akun bisnis Anda ditangguhkan karena pembayaran belum diterima.'
              : 'Pembayaran langganan Anda sudah jatuh tempo. Segera bayar untuk menghindari penangguhan.'}
            {' '}
            <Link href="/dashboard/settings/billing" className="underline font-bold">
              Lihat Billing
            </Link>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
