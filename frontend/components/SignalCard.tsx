import Link from 'next/link';

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

export default function SignalCard({ signal }: { signal: Signal }) {
  const signalColors: Record<string, string> = {
    STRONG_BUY: 'bg-green-600',
    BUY: 'bg-green-500',
    HOLD: 'bg-gray-500',
    SELL: 'bg-red-500',
    STRONG_SELL: 'bg-red-600',
    NO_SIGNAL: 'bg-gray-400',
  };

  const signalColor = signalColors[signal.signal_type] || 'bg-gray-500';

  const timeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-gray-900">{signal.symbol.replace('.NS', '')}</h3>
          <p className="text-sm text-gray-500">{signal.exchange}</p>
        </div>
        <span className={`${signalColor} text-white px-4 py-2 rounded-full text-sm font-semibold`}>
          {signal.signal_type.replace('_', ' ')}
        </span>
      </div>

      {/* Confidence */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">Confidence</span>
          <span className="font-semibold text-gray-900">{(signal.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`${signalColor} h-2 rounded-full`}
            style={{ width: `${signal.confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Prices */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500">Entry</p>
          <p className="text-sm font-semibold text-gray-900">₹{signal.price_entry.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Target</p>
          <p className="text-sm font-semibold text-green-600">₹{signal.price_target?.toFixed(2) || 'N/A'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Stop Loss</p>
          <p className="text-sm font-semibold text-red-600">₹{signal.price_stoploss?.toFixed(2) || 'N/A'}</p>
        </div>
      </div>

      {/* Regime & Time */}
      <div className="flex justify-between items-center pt-4 border-t border-gray-200">
        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
          {signal.regime?.replace('_', ' ') || 'Unknown'}
        </span>
        <span className="text-xs text-gray-500">{timeAgo(signal.created_at)}</span>
      </div>

      {/* View Details Button */}
      <Link href={`/signals/${signal.id}`}>
        <button className="w-full mt-4 bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 transition">
          View Details
        </button>
      </Link>
    </div>
  );
}
