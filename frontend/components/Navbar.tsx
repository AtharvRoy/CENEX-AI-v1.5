'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { logout } from '@/lib/api/auth';

export default function Navbar() {
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/dashboard" className="text-2xl font-bold text-indigo-600">
            🔱 Cenex AI
          </Link>

          {/* Navigation */}
          <div className="hidden md:flex space-x-8">
            <Link href="/dashboard" className="text-gray-700 hover:text-indigo-600 font-medium">
              Dashboard
            </Link>
            <Link href="/signals" className="text-gray-700 hover:text-indigo-600 font-medium">
              Signals
            </Link>
            <Link href="/portfolio" className="text-gray-700 hover:text-indigo-600 font-medium">
              Portfolio
            </Link>
            <Link href="/performance" className="text-gray-700 hover:text-indigo-600 font-medium">
              Performance
            </Link>
            <Link href="/settings" className="text-gray-700 hover:text-indigo-600 font-medium">
              Settings
            </Link>
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <button
              onClick={handleLogout}
              className="text-gray-700 hover:text-red-600 font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
