'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import SignalCard from '@/components/SignalCard';
import { getSignals } from '@/lib/api/signals';

interface Signal {
  id: number;
  symbol: string;
  exchange: string;
  signal_type: string;
  confidence: number;
  price_entry: number;
  price_target: number;
  price_stoploss: number;
  regime: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Fetch signals
    fetchSignals();
  }, [router]);

  const fetchSignals = async () => {
    try {
      const data = await getSignals({ limit: 20 });
      setSignals(data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError('Failed to load signals');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">AI-powered trading signals for Indian markets</p>
        </div>

        {/* Stats */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Total Signals</p>
            <p className="text-3xl font-bold text-gray-900">{signals.length}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">High Confidence</p>
            <p className="text-3xl font-bold text-green-600">
              {signals.filter(s => s.confidence > 0.8).length}
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Buy Signals</p>
            <p className="text-3xl font-bold text-blue-600">
              {signals.filter(s => s.signal_type.includes('BUY')).length}
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Sell Signals</p>
            <p className="text-3xl font-bold text-red-600">
              {signals.filter(s => s.signal_type.includes('SELL')).length}
            </p>
          </div>
        </div>

        {/* Signals Feed */}
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-900">Latest Signals</h2>
            <button
              onClick={fetchSignals}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
            >
              Refresh
            </button>
          </div>

          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              <p className="text-gray-600 mt-4">Loading signals...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
              {error}
            </div>
          )}

          {!loading && !error && signals.length === 0 && (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <p className="text-gray-600">No signals available yet.</p>
              <p className="text-sm text-gray-500 mt-2">
                Signals will appear here once the AI generates them.
              </p>
            </div>
          )}

          {!loading && !error && signals.length > 0 && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {signals.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
