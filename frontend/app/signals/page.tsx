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

export default function SignalsPage() {
  const router = useRouter();
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('recent');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchSignals();
  }, [router]);

  const fetchSignals = async () => {
    try {
      const data = await getSignals({ limit: 50 });
      setSignals(data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredSignals = signals.filter((signal) => {
    if (filter === 'all') return true;
    if (filter === 'buy') return signal.signal_type.includes('BUY');
    if (filter === 'sell') return signal.signal_type.includes('SELL');
    if (filter === 'high_confidence') return signal.confidence > 0.8;
    return true;
  });

  const sortedSignals = [...filteredSignals].sort((a, b) => {
    if (sortBy === 'recent') {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    }
    if (sortBy === 'confidence') {
      return b.confidence - a.confidence;
    }
    return 0;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">All Signals</h1>
          <button
            onClick={fetchSignals}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
          >
            Refresh
          </button>
        </div>

        {/* Filters & Sort */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Filter</label>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">All Signals</option>
                <option value="buy">Buy Signals</option>
                <option value="sell">Sell Signals</option>
                <option value="high_confidence">High Confidence (&gt;80%)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="recent">Most Recent</option>
                <option value="confidence">Highest Confidence</option>
              </select>
            </div>

            <div className="ml-auto flex items-end">
              <div className="text-sm text-gray-600">
                Showing {sortedSignals.length} of {signals.length} signals
              </div>
            </div>
          </div>
        </div>

        {/* Signals Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="text-gray-600 mt-4">Loading signals...</p>
          </div>
        ) : sortedSignals.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600">No signals match your filters</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sortedSignals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
