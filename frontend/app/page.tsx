/**
 * Landing page for Cenex AI
 */

import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <nav className="flex justify-between items-center mb-16">
          <div className="text-2xl font-bold text-indigo-600">🔱 Cenex AI</div>
          <div className="space-x-4">
            <Link href="/login" className="text-gray-700 hover:text-indigo-600">
              Login
            </Link>
            <Link 
              href="/register" 
              className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700"
            >
              Get Started
            </Link>
          </div>
        </nav>

        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            AI-Powered Trading Signals for Indian Markets
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Institutional-grade multi-agent AI that generates high-confidence trading signals.
            Built for perfection, not speed.
          </p>
          <Link 
            href="/register"
            className="bg-indigo-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-indigo-700 inline-block"
          >
            Start Free Trial
          </Link>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-20">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-4">🧮</div>
            <h3 className="text-xl font-semibold mb-2">Multi-Agent Intelligence</h3>
            <p className="text-gray-600">
              4 specialized AI agents (Quant, Sentiment, Regime, Risk) analyze markets from different angles.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-4">⚠️</div>
            <h3 className="text-xl font-semibold mb-2">Risk-First Design</h3>
            <p className="text-gray-600">
              Not max profit — max risk-adjusted returns. Every signal validated by risk engine.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-4">🔄</div>
            <h3 className="text-xl font-semibold mb-2">Self-Learning Loop</h3>
            <p className="text-gray-600">
              Tracks every outcome, learns from wins/losses, gets better over time. Your competitive moat.
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid md:grid-cols-4 gap-6 mt-16 text-center">
          <div>
            <div className="text-4xl font-bold text-indigo-600">65%+</div>
            <div className="text-gray-600">Target Win Rate</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-indigo-600">&gt;1.5</div>
            <div className="text-gray-600">Sharpe Ratio</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-indigo-600">80%+</div>
            <div className="text-gray-600">Min Confidence</div>
          </div>
          <div>
            <div className="text-4xl font-bold text-indigo-600">&lt;15%</div>
            <div className="text-gray-600">Max Drawdown</div>
          </div>
        </div>

        {/* Pricing */}
        <div className="mt-20">
          <h2 className="text-3xl font-bold text-center mb-12">Simple Pricing</h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <div className="bg-white p-8 rounded-lg shadow-md border-2 border-gray-200">
              <h3 className="text-2xl font-bold mb-4">Free</h3>
              <div className="text-4xl font-bold mb-6">₹0<span className="text-lg text-gray-600">/month</span></div>
              <ul className="space-y-3 mb-8">
                <li>✅ 5 core indicators</li>
                <li>✅ Limited signals (5/day)</li>
                <li>✅ Basic portfolio tracking</li>
                <li>❌ No broker execution</li>
              </ul>
              <Link 
                href="/register"
                className="block text-center bg-gray-200 text-gray-800 px-6 py-3 rounded-lg font-semibold hover:bg-gray-300"
              >
                Start Free
              </Link>
            </div>

            <div className="bg-indigo-600 text-white p-8 rounded-lg shadow-md border-2 border-indigo-700">
              <div className="bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-1 rounded inline-block mb-2">
                RECOMMENDED
              </div>
              <h3 className="text-2xl font-bold mb-4">Premium</h3>
              <div className="text-4xl font-bold mb-6">₹3,999<span className="text-lg opacity-80">/month</span></div>
              <ul className="space-y-3 mb-8">
                <li>✅ Full multi-agent AI</li>
                <li>✅ Unlimited signals</li>
                <li>✅ Broker integration</li>
                <li>✅ Real-time risk intelligence</li>
                <li>✅ Performance analytics</li>
              </ul>
              <Link 
                href="/register"
                className="block text-center bg-white text-indigo-600 px-6 py-3 rounded-lg font-semibold hover:bg-gray-100"
              >
                Start 14-Day Trial
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8 mt-20">
        <div className="container mx-auto px-4 text-center">
          <p>© 2026 Cenex AI by CNX Studios. Built for perfection.</p>
        </div>
      </footer>
    </div>
  );
}
