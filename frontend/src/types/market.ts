export interface Reason {
  type: string;
  value: number | string | boolean;
  message: string;
}

export interface Freshness {
  status: string;
  observed_at: string;
  source: string;
  age_minutes: number | null;
}

export interface WatchlistItem {
  symbol: string;
  company_name: string;
  current_price: number;
  session_change_pct: number;
  since_last_view_pct: number | null;
  objective_score: number;
  preference_fit: number;
  attention_score: number;
  attention_level: 'LOW' | 'MEDIUM' | 'HIGH';
  reasons: Reason[];
  freshness: Freshness;
}

export interface WatchlistResponse {
  generated_at: string;
  market_status: string;
  items: WatchlistItem[];
}

export interface BasicWatchlistItem {
  symbol: string;
  company_name: string;
  added_at: string;
}

export interface UserProfile {
  risk_profile: 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';
  attention_style: 'MOMENTUM' | 'STABILITY' | 'BALANCED';
  time_horizon: 'SHORT_TERM' | 'LONG_TERM';
  version: number;
}

export type AttentionLevel = 'LOW' | 'MEDIUM' | 'HIGH';
