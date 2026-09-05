import type {
  WatchlistResponse,
  BasicWatchlistItem,
  UserProfile,
  Stock,
  PriceSnapshot,
} from '../types/market';
import { getToken, clearToken } from './authStorage';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Fires a global event so AuthContext can react to session expiry/invalidation
 * without api.ts needing to know about React state.
 */
async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event('auth:unauthorized'));
  }

  return res;
}

export interface AuthUser {
  id: string;
  email: string | null;
  display_name: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authApi = {
  async login(email: string, password: string): Promise<TokenResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.error?.message || 'Login failed');
    }
    return res.json();
  },

  async register(email: string, password: string, display_name?: string): Promise<TokenResponse> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: display_name || null }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.error?.message || 'Registration failed');
    }
    return res.json();
  },

  async me(): Promise<AuthUser> {
    const res = await authFetch('/auth/me');
    if (!res.ok) throw new Error('Failed to fetch current user');
    return res.json();
  },
};

export const api = {
  async getWatchlistChanges(): Promise<WatchlistResponse> {
    const res = await authFetch('/watchlist/changes');
    if (!res.ok) throw new Error('Failed to fetch watchlist changes');
    return res.json();
  },

  async getWatchlist(): Promise<BasicWatchlistItem[]> {
    const res = await authFetch('/watchlist');
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    return res.json();
  },

  async getProfile(): Promise<UserProfile> {
    const res = await authFetch('/profile');
    if (!res.ok) throw new Error('Failed to fetch profile');
    return res.json();
  },

  async updateProfile(data: Partial<UserProfile>): Promise<UserProfile> {
    const res = await authFetch('/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update profile');
    return res.json();
  },

  async markViewed(symbol: string): Promise<void> {
    const res = await authFetch('/watchlist/viewed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    });
    if (!res.ok) throw new Error('Failed to mark viewed');
  },

  async addWatchlistStock(symbol: string): Promise<void> {
    const res = await authFetch('/watchlist/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    });
    if (!res.ok) throw new Error('Failed to add stock');
  },

  async removeWatchlistStock(symbol: string): Promise<void> {
    const res = await authFetch(`/watchlist/items/${symbol}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to remove stock');
  },

  async getStock(symbol: string): Promise<Stock> {
    const res = await authFetch(`/stocks/${symbol}`);
    if (!res.ok) throw new Error('Failed to fetch stock');
    return res.json();
  },

  async getStockHistory(symbol: string): Promise<PriceSnapshot[]> {
    const res = await authFetch(`/stocks/${symbol}/history`);
    if (!res.ok) throw new Error('Failed to fetch stock history');
    return res.json();
  },
};
