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
  Lock,
  Bot,
  CalendarDays
} from 'lucide-react';
import { logout } from '@/app/actions/auth';
import { getCurrentUser, getOutlets } from '@/app/actions/api';
import { Logo } from '@/components/ui/logo';

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Menu', href: '/dashboard/menu', icon: MenuIcon },
  { name: 'Kasir', href: '/dashboard/kasir', icon: Users },
  { name: 'Laporan', href: '/dashboard/laporan', icon: BarChart3 },
  { name: 'Pengaturan', href: '/dashboard/settings', icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [outletName, setOutletName] = useState('Loading...');
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    async function loadData() {
      try {
        const user = await getCurrentUser();
        if (!user) {
          router.push('/login');
          return;
        }
        const outlets = await getOutlets();
        if (outlets && outlets.length > 0) {
          setOutletName(outlets[0].name);
        } else {
          setOutletName('Belum ada Outlet');
        }
      } catch (error) {
        console.error('Failed to load user data', error);
      }
    }
    loadData();
  }, [router]);

  const handleLogout = async () => {
    await logout();
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
            <div className="flex items-center gap-3">
              <Logo size="sm" variant="light" showWordmark={false} />
              <span className="text-lg font-bold text-gray-900 truncate max-w-[150px]">
                {outletName}
              </span>
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
            {navigation.map((item) => {
              const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                    ${isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }
                  `}
                >
                  <item.icon className={`w-5 h-5 ${isActive ? 'text-blue-700' : 'text-gray-400'}`} />
                  {item.name}
                </Link>
              );
            })}

            {/* Pro Features */}
            <div className="pt-3 mt-3 border-t border-gray-100">
              <p className="px-3 mb-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Pro</p>
              <Link
                href="/dashboard/reservasi"
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${pathname.startsWith('/dashboard/reservasi')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                  }
                `}
              >
                <CalendarDays className={`w-5 h-5 ${pathname.startsWith('/dashboard/reservasi') ? 'text-blue-500' : 'text-gray-400'}`} />
                <span className="flex-1">Reservasi</span>
                <span className="inline-flex items-center gap-0.5 bg-blue-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  PRO
                </span>
              </Link>
              <Link
                href="/dashboard/ai"
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${pathname.startsWith('/dashboard/ai')
                    ? 'bg-purple-50 text-purple-700'
                    : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                  }
                `}
              >
                <Bot className={`w-5 h-5 ${pathname.startsWith('/dashboard/ai') ? 'text-purple-500' : 'text-gray-400'}`} />
                <span className="flex-1">AI Asisten</span>
                <span className="inline-flex items-center gap-0.5 bg-purple-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  PRO
                </span>
              </Link>
              <Link
                href="/dashboard/pro"
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${pathname.startsWith('/dashboard/pro')
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
                  }
                `}
              >
                <Star className={`w-5 h-5 ${pathname.startsWith('/dashboard/pro') ? 'text-yellow-500' : 'text-gray-400'}`} />
                <span className="flex-1">Fitur Pro</span>
                <span className="inline-flex items-center gap-0.5 bg-yellow-400 text-yellow-900 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  <Lock className="w-2.5 h-2.5" />
                  PRO
                </span>
              </Link>
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
          </div>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-gray-500 hover:bg-gray-100 rounded-md"
          >
            <MenuIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
