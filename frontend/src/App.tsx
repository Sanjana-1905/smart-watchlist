import { useState, useEffect } from 'react';
import type { WatchlistResponse } from './types/market';
import { api } from './services/api';
import Dashboard from './pages/Dashboard';

function App() {
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const result = await api.getWatchlistChanges();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error fetching data');
    } finally {
      setLoading(false);
    }
  };

  return <Dashboard data={data} loading={loading} error={error} />;
}

export default App;
