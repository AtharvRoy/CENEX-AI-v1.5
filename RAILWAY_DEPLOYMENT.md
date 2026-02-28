# Railway Deployment Guide

Railway detected your multi-service app but needs manual configuration.

## Option 1: Deploy Each Service Separately (Recommended)

### Step 1: Deploy Backend
1. Go to https://railway.app/new
2. Click **"Empty Project"**
3. Click **"+ New"** → **"GitHub Repo"**
4. Select **AtharvRoy/CENEX-AI-v1.5**
5. Click **Settings** → **Root Directory** → Set to: `backend`
6. Click **Variables** → Add:
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   SECRET_KEY=your-secret-key-here
   PORT=8000
   ```
7. Click **Deploy**

### Step 2: Add PostgreSQL
1. Click **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Railway auto-connects to backend

### Step 3: Add Redis
1. Click **"+ New"** → **"Database"** → **"Redis"**
2. Railway auto-connects to backend

### Step 4: Deploy Frontend
1. Click **"+ New"** → **"GitHub Repo"**
2. Select **AtharvRoy/CENEX-AI-v1.5** again
3. Click **Settings** → **Root Directory** → Set to: `frontend`
4. Click **Variables** → Add:
   ```
   NEXT_PUBLIC_API_URL=${{Backend.RAILWAY_PUBLIC_DOMAIN}}
   ```
5. Click **Deploy**

---

## Option 2: Use Render Instead (Simpler)

Render handles multi-service apps better.

### 1. Go to https://render.com/
2. Click **"New +"** → **"Blueprint"**
3. Connect GitHub → Select **CENEX-AI-v1.5**

Render will auto-detect docker-compose.yml and create all services.

---

## Option 3: Deploy Backend Only First

Deploy just the backend to test:

1. Create new Railway project
2. Deploy from GitHub
3. Set root directory: `backend`
4. Add PostgreSQL + Redis
5. Get backend URL (e.g., https://cenex-backend.railway.app)
6. Test API: https://cenex-backend.railway.app/docs

Then deploy frontend separately later.

---

## Simplest: Use Render with Docker Compose

Render supports docker-compose.yml natively:

1. https://render.com/
2. New Blueprint
3. Connect repo
4. Render auto-creates all 5 services (backend, frontend, db, redis, celery)
5. Done in 5 minutes

---

**Recommendation:** Try **Render** - it's designed for multi-service apps like yours.
