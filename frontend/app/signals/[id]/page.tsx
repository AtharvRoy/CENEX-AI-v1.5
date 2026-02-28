'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { getSignalById, executeSignal } from '@/lib/api/signals';

interface AgentOutput {
  agent_name: string;
  signal: string;
  confidence: number;
  reasoning: any;
}

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
  reasoning: {
    agent_outputs?: Record<string, AgentOutput>;
    meta_decision?: any;
    quality_checks?: any;
  };
  created_at: string;
}

export default function SignalDetailPage() {
  const router = useRouter();
  const params = useParams();
  const [signal, setSignal] = useState<Signal | null>(null);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchSignalDetail();
  }, [params.id, router]);

  const fetchSignalDetail = async () => {
    try {
      const data = await getSignalById(params.id as string);
      setSignal(data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError('Failed to load signal details');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!signal) return;
    
    setExecuting(true);
    try {
      await executeSignal(signal.id);
      alert('Trade executed successfully!');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to execute trade');
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            <p className="text-gray-600 mt-4">Loading signal...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !signal) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error || 'Signal not found'}
          </div>
        </div>
      </div>
    );
  }

  const signalColors: Record<string, string> = {
    STRONG_BUY: 'bg-green-600',
    BUY: 'bg-green-500',
    HOLD: 'bg-gray-500',
    SELL: 'bg-red-500',
    STRONG_SELL: 'bg-red-600',
  };

  const agentOutputs = signal.reasoning?.agent_outputs || {};

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="text-gray-600 hover:text-gray-900 mb-4"
          >
            ← Back
          </button>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">{signal.symbol.replace('.NS', '')}</h1>
              <p className="text-gray-600 mt-2">{signal.exchange} • {new Date(signal.created_at).toLocaleString()}</p>
            </div>
            <span className={`${signalColors[signal.signal_type]} text-white px-6 py-3 rounded-lg text-lg font-bold`}>
              {signal.signal_type.replace('_', ' ')}
            </span>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Confidence & Prices */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Signal Details</h2>
              
              <div className="mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Confidence</span>
                  <span className="font-semibold text-gray-900">{(signal.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`${signalColors[signal.signal_type]} h-3 rounded-full`}
                    style={{ width: `${signal.confidence * 100}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Entry Price</p>
                  <p className="text-2xl font-bold text-gray-900">₹{signal.price_entry.toFixed(2)}</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Target</p>
                  <p className="text-2xl font-bold text-green-600">₹{signal.price_target?.toFixed(2) || 'N/A'}</p>
                  <p className="text-xs text-green-600 mt-1">
                    +{((signal.price_target - signal.price_entry) / signal.price_entry * 100).toFixed(2)}%
                  </p>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-500 mb-1">Stop Loss</p>
                  <p className="text-2xl font-bold text-red-600">₹{signal.price_stoploss?.toFixed(2) || 'N/A'}</p>
                  <p className="text-xs text-red-600 mt-1">
                    {((signal.price_stoploss - signal.price_entry) / signal.price_entry * 100).toFixed(2)}%
                  </p>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                <div>
                  <p className="text-sm text-gray-600">Market Regime</p>
                  <p className="font-semibold text-gray-900">{signal.regime?.replace('_', ' ') || 'Unknown'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Risk/Reward</p>
                  <p className="font-semibold text-gray-900">
                    {(Math.abs(signal.price_target - signal.price_entry) / Math.abs(signal.price_entry - signal.price_stoploss)).toFixed(2)}
                  </p>
                </div>
              </div>
            </div>

            {/* Agent Breakdown */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">AI Agent Analysis</h2>
              
              {Object.entries(agentOutputs).map(([agentName, output]) => (
                <div key={agentName} className="mb-4 p-4 border border-gray-200 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="font-semibold text-gray-900 capitalize">{agentName} Agent</h3>
                    <div className="flex items-center space-x-3">
                      <span className="text-sm font-medium text-gray-600">
                        {output.signal}
                      </span>
                      <span className="text-sm font-semibold text-indigo-600">
                        {(output.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-indigo-600 h-2 rounded-full"
                      style={{ width: `${output.confidence * 100}%` }}
                    />
                  </div>
                  {output.reasoning && (
                    <div className="mt-2 text-xs text-gray-600">
                      <pre className="whitespace-pre-wrap">{JSON.stringify(output.reasoning, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))}

              {Object.keys(agentOutputs).length === 0 && (
                <p className="text-gray-500">No agent details available</p>
              )}
            </div>
          </div>

          {/* Action Panel */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Execute Trade</h3>
              <button
                onClick={handleExecute}
                disabled={executing}
                className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-indigo-400 transition"
              >
                {executing ? 'Executing...' : 'Execute via Broker'}
              </button>
              <p className="text-xs text-gray-500 mt-2">
                Requires connected broker account
              </p>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Signal Quality</h3>
              {signal.reasoning?.quality_checks && (
                <div className="space-y-2">
                  {Object.entries(signal.reasoning.quality_checks).map(([check, passed]) => (
                    <div key={check} className="flex justify-between items-center">
                      <span className="text-sm text-gray-600 capitalize">{check.replace('_', ' ')}</span>
                      <span className={`text-sm font-semibold ${passed ? 'text-green-600' : 'text-red-600'}`}>
                        {passed ? '✓ Pass' : '✗ Fail'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
