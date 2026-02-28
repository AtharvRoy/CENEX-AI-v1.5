# Cenex AI - Institutional-Grade AI Financial Intelligence Platform

**Status:** Phase 1 MVP - In Development

## Project Structure

```
cenex-ai/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Config, auth, database
│   │   ├── models/   # SQLAlchemy models
│   │   ├── services/ # Business logic (data, features, ML)
│   │   └── agents/   # Multi-agent intelligence (Quant, Sentiment, Regime, Risk)
│   └── tests/
├── frontend/         # Next.js frontend
├── data/            # Data storage (Parquet files, cache)
├── scripts/         # Deployment, migration, setup scripts
└── docs/            # Architecture, API docs, sprint planning
```

## Phase 1 MVP Goals (Months 1-4)

- [x] Project scaffolding
- [ ] Backend foundation (FastAPI + DB + Auth)
- [ ] Data Layer (market data ingestion)
- [ ] Feature Factory (technical indicators)
- [ ] Multi-Agent Intelligence (4 agents)
- [ ] Meta Decision Engine (signal generation)
- [ ] Signal Quality Engine (filtering)
- [ ] Performance Memory (tracking)
- [ ] Broker Integration (Zerodha Kite)
- [ ] Frontend (dashboard + signals)
- [ ] Deployment (Docker + hosting)

## Tech Stack

**Backend:** Python 3.11+, FastAPI, SQLAlchemy, TimescaleDB, Redis, Celery  
**Frontend:** Next.js 14+, React, TailwindCSS, Recharts  
**ML:** scikit-learn, LightGBM, XGBoost, PyTorch, Transformers  
**Storage:** PostgreSQL + TimescaleDB, Cloudflare R2, Redis  
**Infra:** Docker, Railway/Render, Cloudflare CDN  

## Development Status

**Current Sprint:** Backend Foundation  
**Active Sub-agents:** TBD  
**Last Updated:** 2026-02-28  

## Quick Start

(Coming soon - setup instructions)

## Documentation

See `docs/` for:
- Architecture overview
- API documentation
- Sprint planning
- Database schema

---

**Built by CNX Studios**
