import type {
  WatchlistResponse,
  BasicWatchlistItem,
  UserProfile,
} from '../types/market';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = {
  async getWatchlistChanges(): Promise<WatchlistResponse> {
    const res = await fetch(`${API_BASE}/watchlist/changes`);
    if (!res.ok) throw new Error('Failed to fetch watchlist changes');
    return res.json();
  },

  async getWatchlist(): Promise<BasicWatchlistItem[]> {
    const res = await fetch(`${API_BASE}/watchlist`);
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    return res.json();
  },

  async getProfile(): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/profile`);
    if (!res.ok) throw new Error('Failed to fetch profile');
    return res.json();
  },

  async updateProfile(data: Partial<UserProfile>): Promise<UserProfile> {
    const res = await fetch(`${API_BASE}/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update profile');
    return res.json();
  },

  async markViewed(symbol: string): Promise<void> {
    const res = await fetch(`${API_BASE}/watchlist/viewed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    });
    if (!res.ok) throw new Error('Failed to mark viewed');
  },

  async addWatchlistStock(symbol: string): Promise<void> {
    const res = await fetch(`${API_BASE}/watchlist/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    });
    if (!res.ok) throw new Error('Failed to add stock');
  },

  async removeWatchlistStock(symbol: string): Promise<void> {
    const res = await fetch(`${API_BASE}/watchlist/items/${symbol}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to remove stock');
  },
};
