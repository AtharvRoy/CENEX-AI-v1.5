# Sprint 08: Frontend (Next.js Dashboard)

**Duration:** Week 15-16  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 01-07 (Backend complete)

## Goals

Build the Next.js frontend with:
1. Landing page + marketing site
2. User authentication (login/register)
3. Dashboard (signals, portfolio, performance)
4. Signal detail page (agent reasoning, charts)
5. Broker connection flow
6. Responsive design (mobile-friendly)

## Deliverables

### 1. Next.js Project Setup
- `frontend/` directory structure
- TypeScript + TailwindCSS
- App Router (Next.js 14+)
- Authentication (NextAuth.js)
- API client (Axios/Fetch)

### 2. Pages & Routes

#### Public Pages
- `/` - Landing page (hero, features, pricing)
- `/login` - Login page
- `/register` - Registration page
- `/pricing` - Pricing tiers (Free, Premium, Pro)

#### Protected Pages (Requires Auth)
- `/dashboard` - Main dashboard (signals feed, portfolio summary)
- `/signals` - All signals (list view, filters)
- `/signals/[id]` - Signal detail (agent reasoning, charts)
- `/portfolio` - Portfolio overview (positions, P&L)
- `/performance` - Performance analytics (win rates, charts)
- `/settings` - Account settings, broker connection
- `/settings/broker` - Broker OAuth flow

### 3. Components

#### Layout Components
- `Navbar` - Top navigation (logo, links, user menu)
- `Sidebar` - Dashboard sidebar (navigation)
- `Footer` - Site footer (links, social)

#### Dashboard Components
- `SignalCard` - Individual signal display (BUY/SELL, confidence)
- `PortfolioSummary` - Portfolio value, P&L, positions count
- `PerformanceChart` - Win rate, Sharpe ratio visualization
- `AgentBreakdown` - Agent outputs visualization

#### Signal Components
- `SignalList` - List of signals (filterable, sortable)
- `SignalDetail` - Full signal breakdown (agent reasoning, price chart)
- `ExecuteTradeButton` - Execute signal via broker
- `SignalReasoningTree` - Visual breakdown of agent outputs

#### Forms
- `LoginForm` - Email + password
- `RegisterForm` - User registration
- `BrokerConnectForm` - Initiate broker OAuth

### 4. API Integration
- `lib/api/client.ts` - Axios client with auth headers
- `lib/api/signals.ts` - Signal API calls
- `lib/api/portfolio.ts` - Portfolio API calls
- `lib/api/auth.ts` - Authentication API calls

### 5. Authentication Flow (NextAuth.js)
- JWT-based auth (matches backend)
- Protected routes with middleware
- Auto-refresh tokens
- Logout functionality

### 6. State Management
- **Option A:** React Context (simple, no extra deps)
- **Option B:** Zustand (lightweight state management)
- **Decision:** Use React Context for MVP

### 7. Charts & Visualizations
- **Library:** Recharts (React-friendly, lightweight)
- **Charts:**
  - Price chart (candlestick)
  - Performance line chart (P&L over time)
  - Win rate bar chart (by signal type)
  - Agent accuracy radar chart

## Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** TailwindCSS
- **Auth:** NextAuth.js
- **Charts:** Recharts
- **Icons:** Lucide React
- **HTTP Client:** Axios
- **State:** React Context API
- **Deployment:** Vercel

## Dependencies

```json
{
  "dependencies": {
    "next": "^14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "next-auth": "^4.24.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0",
    "lucide-react": "^0.300.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "date-fns": "^3.0.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "typescript": "^5",
    "tailwindcss": "^3.4.0",
    "postcss": "^8",
    "autoprefixer": "^10",
    "eslint": "^8",
    "eslint-config-next": "14.1.0"
  }
}
```

## Project Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/
│   │   ├── dashboard/
│   │   ├── signals/
│   │   │   └── [id]/
│   │   ├── portfolio/
│   │   ├── performance/
│   │   └── settings/
│   ├── layout.tsx
│   └── page.tsx (landing)
├── components/
│   ├── ui/ (shadcn components)
│   ├── layout/
│   ├── dashboard/
│   └── signals/
├── lib/
│   ├── api/
│   ├── auth/
│   └── utils/
├── public/
│   └── images/
├── styles/
│   └── globals.css
└── package.json
```

## Key Pages Design

### 1. Landing Page (`/`)
```tsx
- Hero section: "AI-Powered Trading Signals for Indian Markets"
- Feature highlights: Multi-agent AI, Risk-first design, Self-learning
- Live signal feed (sample/demo)
- Pricing cards (Free, Premium, Pro)
- CTA: "Start Free Trial"
```

### 2. Dashboard (`/dashboard`)
```tsx
<DashboardLayout>
  <PortfolioSummary />  {/* Total value, P&L, positions */}
  
  <div className="grid grid-cols-2 gap-4">
    <PerformanceChart />  {/* Win rate, Sharpe ratio */}
    <RecentSignals />     {/* Last 5 signals */}
  </div>
  
  <SignalFeed />  {/* Live signal stream */}
</DashboardLayout>
```

### 3. Signal Detail (`/signals/[id]`)
```tsx
<SignalDetailPage>
  <SignalHeader>
    RELIANCE | BUY | Confidence: 85%
  </SignalHeader>
  
  <PriceChart symbol="RELIANCE" />
  
  <AgentBreakdown>
    - Quant Agent: BUY (78%)
    - Sentiment Agent: BUY (65%)
    - Regime Agent: HOLD (82%)
    - Risk Agent: APPROVE (85%)
  </AgentBreakdown>
  
  <ReasoningTree>
    {/* Visual breakdown of feature importance */}
  </ReasoningTree>
  
  <ExecuteTradeButton signal={signal} />
</SignalDetailPage>
```

### 4. Broker Connection Flow (`/settings/broker`)
```tsx
<BrokerSettings>
  <h2>Connect Your Broker</h2>
  
  <BrokerCard broker="zerodha">
    <button onClick={() => initiateZerodhaOAuth()}>
      Connect Zerodha
    </button>
  </BrokerCard>
  
  {/* After connection: */}
  <ConnectedBroker>
    ✅ Zerodha connected
    Margin Available: ₹50,000
    <button onClick={disconnectBroker}>Disconnect</button>
  </ConnectedBroker>
</BrokerSettings>
```

## Authentication Flow

### NextAuth.js Setup
```ts
// app/api/auth/[...nextauth]/route.ts
import NextAuth from "next-auth"
import CredentialsProvider from "next-auth/providers/credentials"

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Call backend /api/auth/login
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`, {
          method: "POST",
          body: JSON.stringify(credentials),
          headers: { "Content-Type": "application/json" }
        })
        
        const user = await res.json()
        
        if (res.ok && user) {
          return user  // Returns JWT token + user info
        }
        return null
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.access_token
      }
      return token
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken
      return session
    }
  },
  pages: {
    signIn: "/login"
  }
})

export { handler as GET, handler as POST }
```

## API Client

```ts
// lib/api/client.ts
import axios from "axios"
import { getSession } from "next-auth/react"

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json"
  }
})

// Attach JWT token to requests
apiClient.interceptors.request.use(async (config) => {
  const session = await getSession()
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`
  }
  return config
})

export default apiClient
```

```ts
// lib/api/signals.ts
import apiClient from "./client"

export async function getSignals(params?: { limit?: number; symbol?: string }) {
  const { data } = await apiClient.get("/api/signals/latest", { params })
  return data
}

export async function getSignalById(id: string) {
  const { data } = await apiClient.get(`/api/signals/${id}`)
  return data
}

export async function executeSignal(signalId: string, quantity?: number) {
  const { data } = await apiClient.post(`/api/signals/${signalId}/execute`, { quantity })
  return data
}
```

## Styling (TailwindCSS)

### Theme Configuration
```js
// tailwind.config.ts
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#0ea5e9',
          900: '#0c4a6e',
        },
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
      }
    }
  }
}
```

### Signal Card Component
```tsx
export function SignalCard({ signal }) {
  const signalColor = {
    STRONG_BUY: "bg-green-600",
    BUY: "bg-green-500",
    HOLD: "bg-gray-500",
    SELL: "bg-red-500",
    STRONG_SELL: "bg-red-600"
  }[signal.signal_type]
  
  return (
    <div className="border rounded-lg p-4 hover:shadow-lg transition">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">{signal.symbol}</h3>
        <span className={`${signalColor} text-white px-3 py-1 rounded-full text-sm`}>
          {signal.signal_type}
        </span>
      </div>
      
      <div className="mt-2 text-sm text-gray-600">
        Confidence: {(signal.confidence * 100).toFixed(0)}%
      </div>
      
      <div className="mt-2 flex gap-2">
        <span>Entry: ₹{signal.price_entry}</span>
        <span>Target: ₹{signal.price_target}</span>
        <span>SL: ₹{signal.price_stoploss}</span>
      </div>
      
      <Link href={`/signals/${signal.id}`}>
        <button className="mt-3 w-full bg-primary-500 text-white py-2 rounded">
          View Details
        </button>
      </Link>
    </div>
  )
}
```

## Performance Optimization

- **Image optimization:** Next.js Image component
- **Code splitting:** Automatic (Next.js App Router)
- **SSR:** Server-render dashboard for speed
- **Caching:** SWR or React Query for API data
- **Lazy loading:** Load charts only when visible

## Testing

- **Unit tests:** Jest + React Testing Library
- **E2E tests:** Playwright (login flow, signal execution)
- **Accessibility:** WCAG 2.1 AA compliance

## Deployment (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel

# Set environment variables in Vercel dashboard:
NEXT_PUBLIC_API_URL=https://api.cenex.ai
NEXTAUTH_SECRET=<generated-secret>
NEXTAUTH_URL=https://cenex.ai
```

## Acceptance Criteria

- [ ] Landing page deployed and accessible
- [ ] User registration + login works
- [ ] Dashboard displays signals and portfolio
- [ ] Signal detail page shows agent reasoning
- [ ] Broker connection flow works (OAuth)
- [ ] Responsive design (mobile + desktop)
- [ ] Performance: <3s initial page load

## Next Sprint

**Sprint 09: Deployment & DevOps** - Docker, CI/CD, monitoring

---

**Assigned to:** Sub-agent (frontend)  
**Start Date:** TBD (after Sprint 07)  
**Target Completion:** TBD  
