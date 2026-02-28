'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import apiClient from '@/lib/api/client';

interface Position {
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_percent: number;
}

export default function PortfolioPage() {
  const router = useRouter();
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [brokerConnected, setBrokerConnected] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchPortfolio();
  }, [router]);

  const fetchPortfolio = async () => {
    try {
      const { data } = await apiClient.get('/api/broker/positions');
      setPositions(data.positions || []);
      setBrokerConnected(true);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setBrokerConnected(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const totalPnl = positions.reduce((sum, pos) => sum + pos.pnl, 0);
  const totalValue = positions.reduce((sum, pos) => sum + (pos.current_price * pos.quantity), 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Portfolio</h1>

        {!brokerConnected && !loading && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-8">
            <h3 className="text-lg font-semibold text-yellow-900 mb-2">No Broker Connected</h3>
            <p className="text-yellow-700 mb-4">
              Connect your broker account to sync your portfolio and execute trades.
            </p>
            <button
              onClick={() => router.push('/settings')}
              className="bg-yellow-600 text-white px-4 py-2 rounded-lg hover:bg-yellow-700"
            >
              Connect Broker
            </button>
          </div>
        )}

        {brokerConnected && (
          <>
            {/* Summary Stats */}
            <div className="grid md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Total Value</p>
                <p className="text-3xl font-bold text-gray-900">₹{totalValue.toFixed(2)}</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Total P&L</p>
                <p className={`text-3xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {totalPnl >= 0 ? '+' : ''}₹{totalPnl.toFixed(2)}
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500 mb-1">Open Positions</p>
                <p className="text-3xl font-bold text-gray-900">{positions.length}</p>
              </div>
            </div>

            {/* Positions Table */}
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="text-gray-600 mt-4">Loading positions...</p>
              </div>
            ) : positions.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-lg shadow">
                <p className="text-gray-600">No open positions</p>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entry Price</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Current Price</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L %</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {positions.map((position, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                          {position.symbol}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                          {position.quantity}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                          ₹{position.entry_price.toFixed(2)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-gray-900">
                          ₹{position.current_price.toFixed(2)}
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap font-semibold ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {position.pnl >= 0 ? '+' : ''}₹{position.pnl.toFixed(2)}
                        </td>
                        <td className={`px-6 py-4 whitespace-nowrap font-semibold ${position.pnl_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {position.pnl_percent >= 0 ? '+' : ''}{position.pnl_percent.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
