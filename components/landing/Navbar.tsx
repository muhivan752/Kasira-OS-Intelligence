'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';
import { Logo } from '@/components/ui/logo';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  const navLinks = [
    { name: 'Fitur', href: '#features' },
    { name: 'Harga', href: '#pricing' },
    { name: 'Demo', href: '/warung-demo' },
  ];

  return (
    <nav className="fixed w-full bg-white/80 backdrop-blur-md z-50 border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center gap-2">
              <Logo size="sm" variant="light" />
            </Link>
          </div>
          
          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-8">
            <div className="flex gap-6">
              {navLinks.map((link) => (
                <Link 
                  key={link.name} 
                  href={link.href}
                  className="text-sm font-medium text-gray-600 hover:text-emerald-600 transition-colors"
                >
                  {link.name}
                </Link>
              ))}
            </div>
            <div className="flex items-center gap-4">
              <Link 
                href="/login"
                className="text-sm font-medium text-gray-900 hover:text-emerald-600 transition-colors"
              >
                Masuk
              </Link>
              <Link 
                href="/register"
                className="text-sm font-medium bg-emerald-500 text-white px-5 py-2.5 rounded-full hover:bg-emerald-600 transition-colors shadow-sm"
              >
                Coba Gratis
              </Link>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-gray-600 hover:text-gray-900 focus:outline-none p-2"
            >
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Nav */}
      {isOpen && (
        <div className="md:hidden bg-white border-b border-gray-100 absolute w-full">
          <div className="px-4 pt-2 pb-6 space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className="block px-3 py-3 text-base font-medium text-gray-900 hover:bg-gray-50 rounded-lg"
                onClick={() => setIsOpen(false)}
              >
                {link.name}
              </Link>
            ))}
            <div className="pt-4 flex flex-col gap-3 px-3">
              <Link
                href="/login"
                className="w-full text-center px-4 py-3 text-base font-medium text-gray-900 border border-gray-200 rounded-xl hover:bg-gray-50"
                onClick={() => setIsOpen(false)}
              >
                Masuk
              </Link>
              <Link
                href="/register"
                className="w-full text-center px-4 py-3 text-base font-medium bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 shadow-sm"
                onClick={() => setIsOpen(false)}
              >
                Coba Gratis
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
