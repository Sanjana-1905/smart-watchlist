import type { Freshness, Reason, AttentionLevel } from './market';
export interface Analytics {
  identity: { symbol: string; company_name: string; exchange: string; sector: string | null; is_in_watchlist: boolean };
  observation: { current_price: number | null; observed_at: string | null; source: string | null; session_date: string | null; freshness: Freshness & { market_status: string } };
  temporal: { previous_session_close: number | null; previous_session_date: string | null; previous_session_observed_at: string | null; session_change_pct: number | null; session_return: number | null; last_viewed_price: number | null; last_viewed_at: string | null; since_last_view_pct: number | null; since_view_return: number | null };
  volume: { current_session_volume: number | null; baseline_average_volume: number | null; volume_ratio: number | null; baseline_sample_count: number };
  volatility: { canonical_value: number; raw_value: number | null; effective_floor: number; floor_applied: boolean; sample_count: number; unusualness_ratio: number } | null;
  technical: { previous_window_max_close: number; sample_count: number; is_new_high: boolean } | null;
  attention: { return_contribution: number; volume_contribution: number; technical_contribution: number; objective_exact: number; objective_score: number } | null;
  personal: { since_view_contribution: number; profile_contribution: number; profile_reasons: Reason[]; personal_exact: number; preference_fit: number } | null;
  final: { attention_score: number; attention_level: AttentionLevel; cap: number } | null;
  availability: { analytics_available: boolean; reason: string | null };
  reasons: Reason[];
  history: { timestamp: string; close: number; volume: number; source: string }[];
}
