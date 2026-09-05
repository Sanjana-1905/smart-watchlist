import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { WatchlistResponse } from '../types/market';
import DataFreshness, { sourceLabel } from '../components/DataFreshness';
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
    return <div className="min-h-screen flex items-center justify-center text-slate-600 bg-slate-50">Loading...</div>;
  }

  if (error) {
    return <div className="min-h-screen flex items-center justify-center text-red-600 bg-slate-50">Error: {error}</div>;
  }

  if (!data) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50">No data</div>;
  }

  const isEmpty = data.items.length === 0;
  // Dashboard "Top 3" meaningful items (HIGH or MEDIUM)
  const meaningfulItems = data.items.filter(i => i.attention_level === 'HIGH' || i.attention_level === 'MEDIUM').slice(0, 3);
  const normalItemsCount = data.items.filter(i => i.attention_level === 'LOW').length;
  const sources = [...new Set(data.items.map(i => sourceLabel(i.freshness.source)))];
  const watchlistedSymbols = data.items.map(i => i.symbol);

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="px-4 sm:px-8 py-4 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto flex flex-wrap gap-4 justify-between items-center">
          <h1 className="text-lg font-bold text-slate-900">Smart Watchlist</h1>
          <div className="flex flex-wrap min-w-0 items-center gap-4 text-sm font-medium">
            <span className="text-slate-600 break-all">{user?.display_name || user?.email || 'Profile'}</span>
            <button onClick={handleLogout} className="text-slate-400 hover:text-slate-900 transition-colors">Logout</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-10">
        <div className="mb-10">
          <h2 className="text-3xl font-bold text-slate-900 tracking-tight">
            Welcome back{user?.display_name ? `, ${user.display_name.split(' ')[0]}` : ''}
          </h2>
          <div className="text-slate-600 mt-2 flex flex-wrap items-center gap-2">
            <span>{new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' })}</span>
            <span>·</span>
            <span>Market {data.market_status}</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {sources.length ? sources.join(' · ') : 'No market observations available'}
          </p>
        </div>

        <hr className="border-slate-200 mb-10" />

        {showAddStock && (
          <section className="mb-10 bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-sm font-semibold text-slate-900">Add a stock to your watchlist</h3>
              <button onClick={() => setShowAddStock(false)} className="text-slate-400 hover:text-slate-900 text-sm">Close</button>
            </div>
            <AddStockPanel
              watchlistedSymbols={watchlistedSymbols}
              onAdded={() => {
                onRefetch();
              }}
            />
          </section>
        )}

        {isEmpty ? (
          <section className="mb-12 py-16 bg-white rounded-lg border border-slate-200 text-center shadow-sm">
            <h2 className="text-xl font-bold text-slate-900">Your watchlist is empty</h2>
            <p className="text-slate-600 mt-2 max-w-md mx-auto">
              Add stocks to start tracking what changes between your visits.
            </p>
            <button
              onClick={() => setShowAddStock(true)}
              className="mt-6 bg-slate-900 text-white rounded-lg px-6 py-2.5 text-sm font-semibold hover:bg-slate-800 transition-colors shadow-sm"
            >
              + Add stock
            </button>
          </section>
        ) : (
          <>
            {meaningfulItems.length > 0 ? (
              <section className="mb-10">
                <div className="mb-6">
                  <p className="text-xs font-bold tracking-widest text-slate-500 uppercase mb-2">WHAT DESERVES YOUR ATTENTION</p>
                  <h3 className="text-lg text-slate-900 font-medium">
                    {meaningfulItems.length === 3 ? 'Top 3 stocks' : `${meaningfulItems.length} ${meaningfulItems.length === 1 ? 'stock' : 'stocks'}`} to review
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {meaningfulItems.map((item) => (
                    <AttentionCard key={item.symbol} item={item} />
                  ))}
                </div>
              </section>
            ) : (
              <section className="mb-10 py-16 bg-white rounded-lg border border-slate-200 text-center shadow-sm">
                <h2 className="text-xl font-bold text-slate-900 mb-2">✓ You're caught up</h2>
                <p className="text-slate-600 max-w-md mx-auto leading-relaxed">
                  No watchlist stocks currently have medium or high attention.<br/>
                  We'll stay quiet until something deserves attention.
                </p>
              </section>
            )}

            {normalItemsCount > 0 && meaningfulItems.length > 0 && (
              <p className="text-sm font-bold text-slate-400 tracking-widest uppercase text-center mb-10">
                {normalItemsCount} OTHER {normalItemsCount === 1 ? 'STOCK IS' : 'STOCKS ARE'} WITHIN NORMAL RANGES
              </p>
            )}

            <hr className="border-slate-200 mb-10" />

            <section>
              <div className="mb-6 flex flex-wrap gap-4 justify-between items-end">
                <p className="text-xs font-bold tracking-widest text-slate-500 uppercase">YOUR WATCHLIST</p>
                <button
                  onClick={() => setShowAddStock(v => !v)}
                  className="text-sm font-medium text-slate-900 border border-slate-300 bg-white rounded-lg px-4 py-2 hover:bg-slate-50 transition-colors shadow-sm"
                >
                  + Add stock
                </button>
              </div>

              <div role="region" aria-label="Watchlist table, scroll horizontally for all columns" tabIndex={0} className="overflow-x-auto bg-white border border-slate-200 rounded-lg shadow-sm">
                <table className="w-full min-w-[760px] text-sm text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                    <tr>
                      <th className="py-4 px-6 font-semibold w-1/4">Stock</th>
                      <th className="text-right py-4 px-6 font-semibold">Price</th>
                      <th className="text-right py-4 px-6 font-semibold group">
                        Today
                        <p className="text-[10px] font-normal text-slate-400 uppercase tracking-wider mt-0.5">vs previous close</p>
                      </th>
                      <th className="text-right py-4 px-6 font-semibold group">
                        Since checked
                        <p className="text-[10px] font-normal text-slate-400 uppercase tracking-wider mt-0.5">vs your last view</p>
                      </th>
                      <th className="text-right py-4 px-6 font-semibold">Attention</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.items.map((item) => (
                      <tr
                        key={item.symbol}
                        className="hover:bg-slate-50 transition-colors"
                      >
                        <td className="py-4 px-6">
                          <Link className="font-bold text-slate-900 text-base rounded hover:underline" to={`/stock/${item.symbol}`}>{item.symbol}<span className="sr-only"> details</span></Link>
                          <p className="text-xs text-slate-500 mt-0.5 truncate max-w-[200px]">{item.company_name}</p>
                          <div className="mt-2"><DataFreshness freshness={item.freshness} /></div>
                        </td>
                        <td className="text-right py-4 px-6 font-medium text-slate-900 text-base">₹{item.current_price.toFixed(2)}</td>
                        <td className={`text-right py-4 px-6 font-medium text-base ${
                          item.session_change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {item.session_change_pct >= 0 ? '+' : ''}{item.session_change_pct.toFixed(2)}%
                        </td>
                        <td className="text-right py-4 px-6 font-medium text-base">
                          {item.since_last_view_pct !== null ? (
                            <span className={item.since_last_view_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                              {item.since_last_view_pct >= 0 ? '+' : ''}{item.since_last_view_pct.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-slate-500">No baseline yet</span>
                          )}
                        </td>
                        <td className="text-right py-4 px-6">
                          <div className="flex justify-end items-center gap-3">
                            <span className={`font-bold text-base ${item.attention_level === 'LOW' ? 'text-slate-400' : 'text-slate-900'}`}>
                              {item.attention_score.toFixed(1)}
                            </span>
                            <span className={`px-2.5 py-1 rounded text-[11px] font-bold tracking-wider ${
                              item.attention_level === 'HIGH' ? 'bg-slate-900 text-white' :
                              item.attention_level === 'MEDIUM' ? 'border border-slate-300 text-slate-600 bg-slate-50' :
                              'text-slate-400'
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
          </>
        )}
      </main>
    </div>
  );
}
