'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import apiClient from '@/lib/api/client';

interface PerformanceData {
  overall: {
    total_signals: number;
    win_rate: number;
    avg_pnl_percent: number;
    sharpe_ratio: number;
    max_drawdown: number;
  };
  by_signal_type: Record<string, { count: number; win_rate: number }>;
  by_regime: Record<string, { count: number; win_rate: number }>;
  agents: Record<string, { accuracy: number; total_predictions: number }>;
}

export default function PerformancePage() {
  const router = useRouter();
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchPerformance();
  }, [router]);

  const fetchPerformance = async () => {
    try {
      const { data: perfData } = await apiClient.get('/api/performance/summary');
      setData(perfData);
    } catch (err) {
      console.error('Failed to load performance data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="text-gray-600 mt-4">Loading performance data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Performance Analytics</h1>

        {!data ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-600">No performance data available yet</p>
            <p className="text-sm text-gray-500 mt-2">Data will appear after trades are executed</p>
          </div>
        ) : (
          <>
            {/* Overall Stats */}
            <div className="grid md:grid-cols-5 gap-6 mb-8">
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Total Signals</p>
                <p className="text-3xl font-bold text-gray-900">{data.overall.total_signals}</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Win Rate</p>
                <p className="text-3xl font-bold text-green-600">
                  {(data.overall.win_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Avg P&L</p>
                <p className="text-3xl font-bold text-indigo-600">
                  {data.overall.avg_pnl_percent.toFixed(2)}%
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Sharpe Ratio</p>
                <p className="text-3xl font-bold text-blue-600">
                  {data.overall.sharpe_ratio.toFixed(2)}
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Max Drawdown</p>
                <p className="text-3xl font-bold text-red-600">
                  {(data.overall.max_drawdown * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* By Signal Type */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Win Rate by Signal Type</h2>
                <div className="space-y-4">
                  {Object.entries(data.by_signal_type).map(([signalType, stats]) => (
                    <div key={signalType}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm font-medium text-gray-700">{signalType}</span>
                        <span className="text-sm font-semibold text-gray-900">
                          {(stats.win_rate * 100).toFixed(1)}% ({stats.count})
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full"
                          style={{ width: `${stats.win_rate * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* By Regime */}
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Win Rate by Market Regime</h2>
                <div className="space-y-4">
                  {Object.entries(data.by_regime).map(([regime, stats]) => (
                    <div key={regime}>
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-sm font-medium text-gray-700 capitalize">
                          {regime.replace('_', ' ')}
                        </span>
                        <span className="text-sm font-semibold text-gray-900">
                          {(stats.win_rate * 100).toFixed(1)}% ({stats.count})
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${stats.win_rate * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Agent Performance */}
              <div className="bg-white rounded-lg shadow p-6 md:col-span-2">
                <h2 className="text-xl font-bold text-gray-900 mb-4">AI Agent Accuracy</h2>
                <div className="grid md:grid-cols-4 gap-4">
                  {Object.entries(data.agents).map(([agentName, stats]) => (
                    <div key={agentName} className="text-center p-4 bg-indigo-50 rounded-lg">
                      <p className="text-sm text-gray-600 capitalize mb-2">{agentName} Agent</p>
                      <p className="text-3xl font-bold text-indigo-600">
                        {(stats.accuracy * 100).toFixed(1)}%
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {stats.total_predictions} predictions
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
