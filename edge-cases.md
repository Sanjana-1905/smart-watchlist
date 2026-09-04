# Edge cases

- No previous view state: since_view_return is null, not silently defaulted.
  UI shows "no baseline yet" rather than faking a comparison.
- Deleted/re-added watchlist stock: user_view_state for that stock is deleted
  on removal, so re-adding starts with a clean baseline.
- Duplicate watchlist add: rejected at DB level (UNIQUE constraint) + 409/400
  with a clear error code, not a raw stack trace.
- Provider failure: never falls back to mock silently. Serves last-known-good
  observation marked STALE, or UNAVAILABLE if no prior observation exists.
- Market closed: last valid close is shown as "Last Close", not flagged as
  a scary STALE state — freshness incorporates market_clock status.
- Concurrent profile update: optimistic concurrency via version column,
  mismatched version returns 409 Conflict.
- Duplicate mutating request: idempotency key (Redis-backed) returns the
  cached prior result instead of double-applying the action.
