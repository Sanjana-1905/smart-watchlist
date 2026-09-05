  async getAllStocks(): Promise<Stock[]> {
    const res = await authFetch('/stocks');
    if (!res.ok) throw new Error('Failed to fetch stock catalog');
    return res.json();
  },
