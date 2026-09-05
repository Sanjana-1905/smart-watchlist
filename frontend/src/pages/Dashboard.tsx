import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { WatchlistResponse } from '../types/market';
import AttentionCard from '../components/AttentionCard';
import AddStockPanel from '../components/AddStockPanel';
import { useAuth } from '../context/AuthContext';

interface DashboardProps {
  data: WatchlistResponse | null;
  loading: boolean;
  error: string | null;
  onRefetch: () => void;
}

export default function Dashboard({ data, loading, error, onRefetch }: DashboardProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [showAddStock, setShowAddStock] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-600">Loading...</div>;
  }

  if (error) {
    return <div className="min-h-screen flex items-center justify-center text-red-600">Error: {error}</div>;
  }

  if (!data) {
    return <div className="min-h-screen flex items-center justify-center">No data</div>;
  }

  const isEmpty = data.items.length === 0;
  const topItems = data.items.slice(0, 3);
  const hasHighAttention = topItems.some(i => i.attention_level !== 'LOW');
  const watchlistedSymbols = data.items.map(i => i.symbol);

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 px-8 py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <h1 className="text-lg font-semibold text-gray-900">smart watchlist</h1>
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>Market {data.market_status}</span>
            {user?.display_name && <span className="text-gray-400">·</span>}
            {user?.display_name && <span>{user.display_name}</span>}
            <button
              onClick={() => setShowAddStock(v => !v)}
              className="text-gray-900 font-medium border border-gray-300 rounded px-3 py-1.5 hover:bg-gray-50"
            >
              + Add stock
            </button>
            <button
              onClick={handleLogout}
              className="text-gray-500 hover:text-gray-900 font-medium"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-8 py-12">
        {showAddStock && (
          <section className="mb-12 border border-gray-200 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Add a stock to your watchlist</h3>
            <AddStockPanel
              watchlistedSymbols={watchlistedSymbols}
              onAdded={() => {
                onRefetch();
              }}
            />
          </section>
        )}

        {isEmpty && (
          <section className="mb-16 text-center py-12">
            <h2 className="text-2xl font-bold text-gray-900">Your watchlist is empty</h2>
            <p className="text-gray-600 mt-2">
              Add stocks to start tracking what changes between visits.
            </p>
            <button
              onClick={() => setShowAddStock(true)}
              className="mt-6 bg-gray-900 text-white rounded px-6 py-2 text-sm font-semibold hover:bg-gray-800"
            >
              + Add stock
            </button>
          </section>
        )}

        {!isEmpty && hasHighAttention && (
          <section className="mb-16">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900">
                {topItems.length} {topItems.length === 1 ? 'change' : 'changes'} worth your attention
              </h2>
              <p className="text-gray-600 mt-2">
                Since your last check, these moved enough to stand out.
              </p>
              <p className="text-xs text-gray-500 mt-4">Updated {new Date(data.generated_at).toLocaleTimeString()}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {topItems.map((item) => (
                <AttentionCard key={item.symbol} item={item} onViewDetails={(symbol) => navigate(`/stock/${symbol}`)} />
              ))}
            </div>
          </section>
        )}

        {!isEmpty && !hasHighAttention && (
          <section className="mb-16 text-center py-12">
            <h2 className="text-2xl font-bold text-gray-900">Nothing unusual right now</h2>
            <p className="text-gray-600 mt-2">Your watchlist is behaving within its recent range.</p>
          </section>
        )}

        {!isEmpty && (
          <section>
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Your watchlist</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-200 text-gray-600">
                  <tr>
                    <th className="text-left py-3 px-4 font-semibold">Company</th>
                    <th className="text-right py-3 px-4 font-semibold">Price</th>
                    <th className="text-right py-3 px-4 font-semibold">Today</th>
                    <th className="text-right py-3 px-4 font-semibold">Since checked</th>
                    <th className="text-right py-3 px-4 font-semibold">Attention</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {data.items.map((item) => (
                    <tr
                      key={item.symbol}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/stock/${item.symbol}`)}
                    >
                      <td className="py-4 px-4">
                        <p className="font-semibold text-gray-900">{item.symbol}</p>
                        <p className="text-xs text-gray-600">{item.company_name}</p>
                      </td>
                      <td className="text-right py-4 px-4 font-semibold">₹{item.current_price.toFixed(2)}</td>
                      <td className={`text-right py-4 px-4 font-semibold ${
                        item.session_change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {item.session_change_pct >= 0 ? '+' : ''}{item.session_change_pct.toFixed(2)}%
                      </td>
                      <td className="text-right py-4 px-4">
                        {item.since_last_view_pct !== null ? (
                          <span className={item.since_last_view_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                            {item.since_last_view_pct >= 0 ? '+' : ''}{item.since_last_view_pct.toFixed(2)}%
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="text-right py-4 px-4">
                        <div className="flex justify-end items-center gap-2">
                          <span className="font-bold">{item.attention_score.toFixed(0)}</span>
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${
                            item.attention_level === 'HIGH' ? 'bg-gray-900 text-white' :
                            item.attention_level === 'MEDIUM' ? 'border border-gray-400 text-gray-700' :
                            'text-gray-400'
                          }`}>
                            {item.attention_level}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
