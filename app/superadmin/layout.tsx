'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Building2,
  LogOut,
  X,
  Menu as MenuIcon,
  Shield,
} from 'lucide-react';
import { logout } from '@/app/actions/auth';
import { getCurrentUser } from '@/app/actions/api';

export default function SuperadminLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [adminName, setAdminName] = useState('');
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    async function checkAccess() {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/login');
          return;
        }
        setAdminName(user.full_name || 'Admin');
        setLoading(false);
      } catch {
        router.push('/login');
      }
    }
    checkAccess();
  }, [router]);

  const handleLogout = async () => {
    await logout();
  };

  const nav = [
    { name: 'Overview', href: '/superadmin', icon: LayoutDashboard },
    { name: 'Tenants', href: '/superadmin/tenants', icon: Building2 },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400">Memuat...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 border-r border-gray-800 transform transition-transform duration-300 lg:translate-x-0 lg:static lg:inset-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full flex flex-col">
          <div className="flex items-center justify-between h-16 px-5 border-b border-gray-800">
            <div className="flex items-center gap-2">
              <Shield className="w-6 h-6 text-red-500" />
              <span className="text-base font-bold text-white">Superadmin</span>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="lg:hidden p-2 text-gray-500 hover:bg-gray-800 rounded-md">
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 px-3 py-4 space-y-1">
            {nav.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/superadmin' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                    ${isActive ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'}`}
                >
                  <item.icon className={`w-5 h-5 ${isActive ? 'text-red-500' : 'text-gray-500'}`} />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-gray-800">
            <div className="text-xs text-gray-500 mb-2 px-3">{adminName}</div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 w-full px-3 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5" />
              Keluar
            </button>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <div className="lg:hidden flex items-center justify-between h-16 px-4 bg-gray-900 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-red-500" />
            <span className="text-sm font-bold text-white">Superadmin</span>
          </div>
          <button onClick={() => setSidebarOpen(true)} className="p-2 text-gray-400 hover:bg-gray-800 rounded-md">
            <MenuIcon className="w-6 h-6" />
          </button>
        </div>
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
