/**
 * Signals API client
 */

import apiClient from './client';

export interface Signal {
  id: number;
  symbol: string;
  exchange: string;
  signal_type: string;
  confidence: number;
  price_entry: number;
  price_target: number;
  price_stoploss: number;
  reasoning: any;
  regime: string;
  created_at: string;
}

export async function getSignals(params?: {
  limit?: number;
  symbol?: string;
  min_confidence?: number;
}) {
  const { data } = await apiClient.get<Signal[]>('/api/signals/latest', { params });
  return data;
}

export async function getSignalById(id: string | number) {
  const { data } = await apiClient.get<Signal>(`/api/signals/${id}`);
  return data;
}

export async function generateSignal(symbol: string) {
  const { data} = await apiClient.post(`/api/signals/generate/${symbol}`);
  return data;
}

export async function executeSignal(signalId: string | number, quantity?: number) {
  const { data } = await apiClient.post(`/api/signals/${signalId}/execute`, { quantity });
  return data;
}
