import { useState, useEffect, useCallback } from 'react';
import type { WatchlistResponse } from '../types/market';
import { api } from '../services/api';
import Dashboard from './Dashboard';

export default function DashboardPage() {
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getWatchlistChanges();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error fetching data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return <Dashboard data={data} loading={loading} error={error} onRefetch={fetchData} />;
}
