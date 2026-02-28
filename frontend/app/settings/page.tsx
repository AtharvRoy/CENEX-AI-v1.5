'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import apiClient from '@/lib/api/client';
import { getCurrentUser } from '@/lib/api/auth';

interface User {
  id: number;
  email: string;
  full_name: string;
  tier: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [brokerConnected, setBrokerConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchUserData();
  }, [router]);

  const fetchUserData = async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);

      // Check broker connection
      try {
        await apiClient.get('/api/broker/positions');
        setBrokerConnected(true);
      } catch {
        setBrokerConnected(false);
      }
    } catch (err) {
      router.push('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectBroker = () => {
    // Initiate Zerodha OAuth flow
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/api/broker/zerodha/login`;
  };

  const handleDisconnectBroker = async () => {
    if (!confirm('Are you sure you want to disconnect your broker account?')) return;

    try {
      await apiClient.post('/api/broker/disconnect');
      setBrokerConnected(false);
      alert('Broker disconnected successfully');
    } catch (err) {
      alert('Failed to disconnect broker');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>

        {/* Account Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Account Information</h2>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-gray-500">Name</p>
              <p className="font-medium text-gray-900">{user?.full_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Email</p>
              <p className="font-medium text-gray-900">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Plan</p>
              <p className="font-medium text-gray-900 capitalize">
                {user?.tier} 
                {user?.tier === 'free' && (
                  <button className="ml-4 text-sm text-indigo-600 hover:text-indigo-700">
                    Upgrade to Premium →
                  </button>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Broker Connection */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Broker Connection</h2>

          {!brokerConnected ? (
            <div>
              <p className="text-gray-600 mb-4">
                Connect your broker account to execute trades directly from Cenex AI.
              </p>

              {/* Zerodha Card */}
              <div className="border border-gray-200 rounded-lg p-6 hover:border-indigo-500 transition">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Zerodha</h3>
                    <p className="text-sm text-gray-500 mt-1">India's leading broker</p>
                  </div>
                  <button
                    onClick={handleConnectBroker}
                    className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-indigo-700"
                  >
                    Connect
                  </button>
                </div>
              </div>

              {/* Coming Soon */}
              <div className="mt-4 space-y-3">
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 opacity-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">Upstox</h3>
                      <p className="text-xs text-gray-500">Coming soon</p>
                    </div>
                    <span className="text-xs text-gray-400 px-3 py-1 bg-gray-200 rounded">
                      Soon
                    </span>
                  </div>
                </div>
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 opacity-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">Angel One</h3>
                      <p className="text-xs text-gray-500">Coming soon</p>
                    </div>
                    <span className="text-xs text-gray-400 px-3 py-1 bg-gray-200 rounded">
                      Soon
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="border border-green-200 bg-green-50 rounded-lg p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-green-900">✓ Zerodha Connected</h3>
                  <p className="text-sm text-green-700 mt-1">Your broker account is active</p>
                </div>
                <button
                  onClick={handleDisconnectBroker}
                  className="text-sm text-red-600 hover:text-red-700 font-medium"
                >
                  Disconnect
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-lg shadow p-6 mt-6 border-2 border-red-200">
          <h2 className="text-xl font-bold text-red-600 mb-4">Danger Zone</h2>
          <p className="text-gray-600 mb-4">Permanently delete your account and all data.</p>
          <button className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">
            Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
