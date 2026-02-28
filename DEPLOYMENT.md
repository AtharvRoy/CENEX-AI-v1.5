# Cenex AI - Deployment Guide

## Phase 1 MVP - Complete Build

**Status:** ✅ All 8 sprints complete  
**Last Updated:** 2026-02-28 07:15 UTC

---

## What's Built

### Backend (FastAPI)
✅ Sprint 01: Backend foundation (FastAPI, database schema, JWT auth)  
✅ Sprint 02: Data layer (Yahoo Finance, TimescaleDB, Redis caching)  
✅ Sprint 03: Feature factory (indicators, regime detection, sentiment analysis)  
✅ Sprint 04: Multi-agent intelligence (4 AI agents + orchestrator)  
✅ Sprint 05: Meta decision engine + signal quality filtering  
✅ Sprint 06: Performance memory (self-learning loop)  
✅ Sprint 07: Broker integration (Zerodha Kite API)  

### Frontend (Next.js)
✅ Sprint 08: Frontend scaffolding + landing page + API client

### Infrastructure
✅ Docker setup (docker-compose.yml)  
✅ PostgreSQL + TimescaleDB  
✅ Redis  
✅ Celery workers  

---

## Quick Start (Local Development)

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### 1. Clone & Setup

```bash
cd /root/clawd/cenex-ai
```

### 2. Start Services

```bash
# Start all services (backend, database, redis, celery, frontend)
docker-compose up -d

# Check logs
docker-compose logs -f backend
```

### 3. Access Applications

- **Backend API:** http://localhost:8000/docs
- **Frontend:** http://localhost:3000
- **Health Check:** http://localhost:8000/health

### 4. Initialize Database

The database tables are auto-created on first run (development mode).

To manually initialize:
```bash
docker-compose exec backend python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (returns JWT token)
- `GET /api/auth/me` - Get current user info

### Signals
- `GET /api/signals/latest` - List latest signals
- `GET /api/signals/{id}` - Get signal details
- `POST /api/signals/generate/{symbol}` - Generate new signal
- `POST /api/signals/{id}/execute` - Execute signal via broker

### Market Data
- `GET /api/market/{symbol}/ohlcv` - Get OHLCV data
- `GET /api/market/{symbol}/latest` - Get latest price
- `POST /api/admin/market/backfill` - Backfill historical data

### Features
- `GET /api/features/{symbol}` - Get feature vector
- `GET /api/indicators/{symbol}` - Get technical indicators
- `GET /api/regime/{symbol}` - Get regime classification
- `GET /api/sentiment/{symbol}` - Get sentiment analysis

### Agents
- `POST /api/agents/analyze/{symbol}` - Run all agents
- `GET /api/agents/{agent_name}/{symbol}` - Run single agent

### Broker
- `POST /api/broker/connect` - Connect broker account (OAuth)
- `GET /api/broker/positions` - Get current positions
- `POST /api/broker/order` - Place order

### Performance
- `GET /api/performance/summary` - System performance metrics
- `GET /api/performance/agents` - Agent accuracy stats
- `GET /api/performance/regimes` - Regime-specific win rates

---

## Configuration

### Environment Variables

**Backend (.env)**
```bash
DATABASE_URL=postgresql+asyncpg://cenex:cenex_secure_2024@db:5432/cenex_ai
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
DEBUG=False
```

**Frontend (.env.local)**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Production Deployment

### 1. Build for Production

```bash
# Backend
cd backend
docker build -t cenex-backend:latest .

# Frontend
cd frontend
npm run build
docker build -t cenex-frontend:latest .
```

### 2. Deploy to Cloud (Railway/Render/AWS)

**Option A: Railway**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Deploy
railway up
```

**Option B: AWS (ECS/Fargate)**
- Push Docker images to ECR
- Create ECS task definitions
- Deploy via Fargate

### 3. Database Migration (Production)

```bash
# Use Alembic for migrations
cd backend
alembic upgrade head
```

---

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Test (End-to-End Signal Generation)
```bash
# 1. Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'

# 2. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}' | jq -r '.access_token')

# 3. Generate signal
curl -X POST http://localhost:8000/api/signals/generate/RELIANCE.NS \
  -H "Authorization: Bearer $TOKEN"
```

---

## Monitoring

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery
```

### Health Checks
- Backend: http://localhost:8000/health
- Database: `docker-compose exec db pg_isready`
- Redis: `docker-compose exec redis redis-cli ping`

---

## Troubleshooting

### Backend won't start
```bash
# Check database connection
docker-compose exec backend python -c "from app.core.database import engine; print(engine)"

# Check logs
docker-compose logs backend
```

### Celery tasks not running
```bash
# Check Celery worker
docker-compose logs celery

# Restart Celery
docker-compose restart celery celery-beat
```

### Frontend can't connect to backend
- Ensure `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS settings in backend/app/core/config.py

---

## Next Steps

1. **Backfill Market Data:**
   ```bash
   curl -X POST http://localhost:8000/api/admin/market/backfill \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"symbols":["RELIANCE.NS","TCS.NS","INFY.NS"],"days":90}'
   ```

2. **Train ML Models:**
   ```bash
   docker-compose exec backend python -m app.ml.train_quant_agent
   docker-compose exec backend python -m app.ml.train_sentiment_agent
   docker-compose exec backend python -m app.ml.train_meta_learner
   ```

3. **Generate First Signal:**
   ```bash
   curl -X POST http://localhost:8000/api/signals/generate/RELIANCE.NS \
     -H "Authorization: Bearer $TOKEN"
   ```

4. **Connect Broker (Zerodha):**
   - Visit http://localhost:3000/settings/broker
   - Follow OAuth flow

---

## Cost Estimates

**Development (Docker Compose on single machine):**
- Free (runs locally)

**Production (Railway/Render):**
- **Database (PostgreSQL):** $15-25/month
- **Backend (FastAPI):** $10-20/month
- **Frontend (Next.js):** $10/month (or free on Vercel)
- **Redis:** $5-10/month
- **Total:** ~$40-65/month (for 100-1000 users)

**Production (AWS):**
- **RDS PostgreSQL:** $30-50/month
- **ElastiCache Redis:** $15/month
- **ECS Fargate:** $25-50/month
- **S3 + CloudFront:** $5/month
- **Total:** ~$75-120/month (scalable to 10k+ users)

---

## Support

- **Documentation:** /root/clawd/cenex-ai/docs/
- **Architecture:** /root/clawd/cenex-ai/docs/ARCHITECTURE.md
- **Sprint Specs:** /root/clawd/cenex-ai/docs/sprints/

---

**Built by CNX Studios | Phase 1 MVP Complete 🎉**
