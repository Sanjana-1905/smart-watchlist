import { useEffect, useState } from 'react';
import type { Stock } from '../types/market';
import { api } from '../services/api';

interface AddStockPanelProps {
  watchlistedSymbols: string[];
  onAdded: () => void;
}

export default function AddStockPanel({ watchlistedSymbols, onAdded }: AddStockPanelProps) {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingSymbol, setAddingSymbol] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAllStocks()
      .then(setStocks)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load stocks'))
      .finally(() => setLoading(false));
  }, []);

  const watchlistedSet = new Set(watchlistedSymbols);

  const handleAdd = async (symbol: string) => {
    setAddingSymbol(symbol);
    setError(null);
    try {
      await api.addWatchlistStock(symbol);
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add stock');
    } finally {
      setAddingSymbol(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading stock catalog...</p>;
  }

  return (
    <div>
      {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {stocks.map((stock) => {
          const isWatchlisted = watchlistedSet.has(stock.symbol);
          return (
            <div
              key={stock.id}
              className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3"
            >
              <div>
                <p className="font-medium text-gray-900">{stock.symbol}</p>
                <p className="text-xs text-gray-500">{stock.company_name}</p>
              </div>
              <button
                disabled={isWatchlisted || addingSymbol === stock.symbol}
                onClick={() => handleAdd(stock.symbol)}
                className={
                  isWatchlisted
                    ? 'text-xs text-gray-400 font-medium'
                    : 'text-xs text-white bg-gray-900 hover:bg-gray-800 rounded px-3 py-1.5 font-semibold disabled:opacity-50'
                }
              >
                {isWatchlisted ? 'Watching' : addingSymbol === stock.symbol ? 'Adding...' : 'Add'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
