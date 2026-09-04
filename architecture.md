# Architecture — Smart Market Watchlist

## Core invariant
A user's watchlist contains at most one instance of a stock, and every attention
decision is derived from timestamped market observations plus that user's
persisted last-view state and preference profile.

## Data flow
Market provider -> Market service (validate/store) -> Attention engine
(objective signal) -> Preference policy (adjustment only, never changes facts)
-> API -> Frontend

## Stack
Backend: FastAPI + SQLAlchemy + Alembic + Pydantic
DB: PostgreSQL (source of truth)
Cache: Redis (disposable state only — quote cache, idempotency, provider health)
Jobs: APScheduler (60s poll loop, single process)
Providers: MockMarketDataProvider (default), YFinanceProvider (optional)
Frontend: React + TypeScript + Vite
Infra: Docker Compose, single-command startup

## Provider policy
One authoritative provider per runtime, set via MARKET_PROVIDER env var.
Live provider failures fall back to last-known-good with explicit staleness
metadata — never silently substitute mock data for a failed live call.
