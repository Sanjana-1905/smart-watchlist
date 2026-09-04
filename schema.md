# Schema — six tables, frozen

users (id, created_at)

stocks (id, symbol UNIQUE, company_name, exchange, sector)

watchlist_items (id, user_id FK, stock_id FK, added_at, version)
  UNIQUE(user_id, stock_id)

price_snapshots (id, stock_id FK, timestamp, open, high, low, close, volume, source)
  INDEX (stock_id, timestamp)

user_view_state (user_id FK, stock_id FK, last_viewed_at, last_viewed_price)
  PRIMARY KEY (user_id, stock_id)

user_profiles (user_id FK PK, risk_profile, attention_style, time_horizon, version)
  risk_profile: CONSERVATIVE | BALANCED | AGGRESSIVE
  attention_style: MOMENTUM | STABILITY | BALANCED
  time_horizon: SHORT_TERM | LONG_TERM

No seventh table. Redis holds only disposable operational state.
