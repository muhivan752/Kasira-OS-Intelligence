'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Menu as MenuIcon,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Store,
  X,
  CalendarDays,
  Lock,
  Package,
  Smartphone,
  Globe,
  ChefHat,
  ShoppingCart,
  Wallet,
  MessageCircle,
  Calculator,
} from 'lucide-react';
import { logout } from '@/app/actions/auth';
import { getAccountAccess } from '@/app/actions/accounts';
import { getCurrentUser, getOutlets } from '@/app/actions/api';
import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/ui/theme-toggle';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [accessMode, setAccessMode] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktop, setDesktop] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);
  const [outletName, setOutletName] = useState('Memuat...');
  const [tier, setTier] = useState('starter');
  const [subStatus, setSubStatus] = useState('active');
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const isPro = ['pro', 'business', 'enterprise'].includes(tier);

  useEffect(() => {
    const query = window.matchMedia('(min-width: 1024px)');
    const sync = () => setDesktop(query.matches);
    sync(); query.addEventListener('change', sync);
    return () => query.removeEventListener('change', sync);
  }, []);
  useEffect(() => {
    if (sidebarOpen) closeButton.current?.focus();
    else if (wasOpen.current) menuButton.current?.focus();
    wasOpen.current = sidebarOpen;
  }, [sidebarOpen]);

  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') setSidebarOpen(false); };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const access = await getAccountAccess();
        if (!access.success) { router.push('/login'); return; }
        setAccessMode(access.data.enforcement_mode);
        const user = await getCurrentUser();
        if (!user) {
          router.push('/login');
          return;
        }
        setTier(user.subscription_tier || 'starter');
        setSubStatus(user.subscription_status || 'active');
        const outlets = access.data.outlets;
        if (outlets && outlets.length > 0) {
          setOutletName(outlets[0].name);
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
    if (loggingOut) return;
    setLoggingOut(true);
    setLogoutError(null);
    try {
      const result = await logout();
      if (result && !result.success) setLogoutError(result.message);
    } catch {
      setLogoutError('Logout belum terkonfirmasi. Periksa koneksi lalu coba lagi.');
    } finally {
      setLoggingOut(false);
    }
  };

  // Build navigation based on tier
  const mainNav = accessMode === 'managed' ? [{ name: 'Tim & absensi', href: '/dashboard/hris', icon: Users }] : [
    { name: 'Beranda', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Menu', href: '/dashboard/menu', icon: MenuIcon },
    { name: 'Toko Online', href: '/dashboard/toko', icon: Globe },
    { name: 'Kasir', href: '/dashboard/kasir', icon: Store },
    { name: 'Pelanggan', href: '/dashboard/pelanggan', icon: Users },
    { name: 'Pembelian', href: '/dashboard/pembelian', icon: ShoppingCart },
    { name: 'Keuangan', href: '/dashboard/keuangan', icon: Wallet },
    { name: 'Tim & absensi', href: '/dashboard/hris', icon: Users },
    { name: 'Promo WA', href: '/dashboard/promo', icon: MessageCircle },
    { name: 'Laporan', href: '/dashboard/laporan', icon: BarChart3 },
  ];

  const proNav = accessMode === 'managed' ? [] : [
    { name: 'Atur HPP', href: '/dashboard/hpp', icon: Calculator },
    { name: 'Bahan Baku', href: '/dashboard/bahan-baku', icon: Package },
    { name: 'Reservasi', href: '/dashboard/reservasi', icon: CalendarDays },
    { name: 'AI Asisten', href: '/dashboard/ai', icon: MessageCircle },
  ];

  const bottomNav = [
    { name: 'Akun saya', href: '/dashboard/account', icon: Users },
    ...(accessMode === 'managed' ? [] : [
    { name: 'Download POS', href: '/download', icon: Smartphone },
    ...(isPro ? [{ name: 'Download Dapur', href: '/download', icon: ChefHat }] : []),
    { name: 'Pengaturan', href: '/dashboard/settings', icon: Settings },
    ]),
  ];

  const renderNavItem = (item: { name: string; href: string; icon: any }, locked = false) => {
    const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
    return (
      <Link
        key={item.name}
        onClick={() => setSidebarOpen(false)}
        href={locked ? '/dashboard/pro' : item.href}
        className={`
          flex items-center gap-3 px-3 py-2.5 min-h-11 rounded-lg text-sm font-medium transition-colors
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
    <div className="merchant-shell min-h-screen bg-gray-50 flex">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-900/80 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div inert={!desktop && !sidebarOpen} aria-hidden={!desktop && !sidebarOpen} className={`
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
                <span className="inline-flex items-center gap-1 bg-[var(--brand-fill)] text-[var(--brand-on-fill)] text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0">
                  Pro
                </span>
              )}
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              ref={closeButton}
              aria-label="Tutup menu"
              className="lg:hidden p-2 min-h-11 min-w-11 text-gray-500 hover:bg-gray-100 rounded-md"
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
                <p className="px-3 mb-2 text-sm text-gray-500">Fitur paket Pro</p>
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
            <div className="hidden lg:flex items-center justify-between mb-3 text-sm text-[var(--text-muted)]"><span>Tampilan</span><ThemeToggle /></div>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="flex items-center gap-3 w-full min-h-11 px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
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
          <div className="flex items-center gap-2 min-w-0">
            <Logo size="sm" variant="light" showWordmark={false} />
            <span className="text-base font-bold text-gray-900 truncate max-w-[120px]">
              {outletName}
            </span>
            {isPro && (
              <span className="inline-flex items-center gap-1 bg-[var(--brand-fill)] text-[var(--brand-on-fill)] text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0">
                Pro
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            {/* Keluar juga ada di footer sidebar, tapi di HP itu ketutup menu
                hamburger dan harus di-scroll ke paling bawah — praktisnya
                nggak keliatan. Ditaruh langsung di header biar kejangkau. */}
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label="Keluar"
              title="Keluar"
              className="p-2 min-h-11 min-w-11 text-red-600 hover:bg-red-50 rounded-md"
            >
              <LogOut className="w-5 h-5" />
            </button>
            <button
              onClick={() => setSidebarOpen(true)}
              ref={menuButton}
              aria-label="Buka menu"
              aria-expanded={sidebarOpen}
              className="p-2 min-h-11 min-w-11 text-gray-500 hover:bg-gray-100 rounded-md"
            >
              <MenuIcon className="w-6 h-6" />
            </button>
          </div>
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
          {logoutError && <p role="alert" className="mb-4 text-[var(--danger)]">{logoutError}</p>}
          {!accessMode ? <p role="status">Memuat akses akun…</p> : accessMode === 'managed' && !['/dashboard/hris', '/dashboard/account'].includes(pathname) ? <div><p>Fitur ini belum tersedia untuk pengaturan akses akun Anda.</p><Link href="/dashboard/hris">Buka tim dan absensi</Link></div> : children}
        </main>
      </div>
    </div>
  );
}
