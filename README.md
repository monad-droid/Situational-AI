# Situational AI

**A threshold-triggered health coach that won't leave you alone until you hit your goal.**

Native iOS app + FastAPI backend. Set a body weight threshold, and when you cross it, an AI coach activates via push notifications. It doesn't stop until you're back under. This is not a passive health tracker — it's designed to be annoying on purpose.

**CMD Loop Holdings LLC** — Subscription: $6.99/month

## Architecture

```
iOS App (Swift/SwiftUI)                    Backend (FastAPI)
┌──────────────────────┐                   ┌─────────────────────────────┐
│ HealthKit Manager    │                   │ Sample Ingestion + Dedup    │
│  └ HKObserverQuery   │──POST /samples──▶│ Threshold Engine (no LLM)   │
│  └ HKAnchoredObject  │                   │ Quiet Hours Enforcement     │
│                      │                   │ Nudge Rate Limiter          │
│ Dashboard View       │                   │                             │
│ Coach Chat View      │──POST /chat─────▶│ Coaching Provider Layer     │
│ Settings View        │                   │  ├ GPT-5 Mini (nudges)     │
│                      │                   │  └ Claude Haiku 4.5 (chat) │
│ Push Notification    │◀──APNs──────────│ Push Service (APNs)         │
│ Sign in with Apple   │──POST /auth────▶│ Auth + Subscriptions        │
└──────────────────────┘                   └─────────────────────────────┘
```

## AI Model Strategy

| Task | Model | Why |
|------|-------|-----|
| Threshold evaluation | Deterministic code | It's an `if` statement. No LLM needed. |
| Push notification nudges | GPT-5 Mini | Cheap, good at conversational text. 2-3 sentences. |
| Deep coaching chat | Claude Haiku 4.5 | Higher quality reasoning, less sycophantic. |

**Cost per heavy user**: ~$1.46/month (10 nudges/day + 10 chat messages/day). At $6.99/month = 79% gross margin.

## v0.1 Scope

- [x] iOS app with Sign in with Apple
- [x] One metric: body weight (hardcoded)
- [x] One threshold per user
- [x] HealthKit integration (HKObserverQuery + HKAnchoredObjectQuery)
- [x] Push notification nudges (GPT-5 Mini)
- [x] Coaching chat with 10 messages/day cap (Claude Haiku 4.5)
- [x] Quiet hours with timezone support
- [x] Sample deduplication + nudge idempotency
- [x] Paid tier only

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment config
│   ├── database.py          # Async SQLAlchemy setup
│   ├── models/
│   │   ├── user.py          # User, subscription tier, push token
│   │   ├── threshold.py     # Threshold definitions
│   │   ├── metric_log.py    # HealthKit samples (deduplicated)
│   │   ├── coaching_message.py  # Nudges + queued messages
│   │   └── chat_session.py  # Chat conversations
│   ├── services/
│   │   ├── system_prompt.py      # Cacheable coaching prompt
│   │   ├── threshold_engine.py   # Deterministic evaluation
│   │   ├── coaching_provider.py  # GPT-5 Mini + Claude Haiku 4.5
│   │   ├── nudge_service.py      # Full nudge pipeline orchestration
│   │   ├── quiet_hours.py        # Timezone-aware quiet hours
│   │   └── push_service.py       # APNs integration
│   └── routers/
│       ├── auth.py           # Sign in with Apple
│       ├── samples.py        # POST /api/samples
│       ├── thresholds.py     # CRUD thresholds
│       ├── chat.py           # POST /api/chat
│       └── subscriptions.py  # StoreKit validation + settings

ios/SituationalAI/
├── App/
│   └── SituationalAIApp.swift    # App entry + push notification setup
├── Views/
│   ├── OnboardingView.swift      # Sign in with Apple
│   ├── MainTabView.swift         # Tab navigation
│   ├── DashboardView.swift       # Weight display + threshold setup
│   ├── CoachChatView.swift       # Chat with coach (Claude Haiku 4.5)
│   └── SettingsView.swift        # Quiet hours, HealthKit, account
├── Models/
│   └── AppModels.swift           # API request/response types
├── Services/
│   ├── APIClient.swift           # Backend HTTP client
│   └── AuthManager.swift         # Sign in with Apple state
└── HealthKit/
    └── HealthKitManager.swift    # HKObserver + HKAnchoredObject queries
```

## Backend Setup

```bash
# 1. Install dependencies
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env with your API keys, database URL, APNs credentials

# 3. Run
uvicorn backend.app.main:app --reload
```

### Required Environment Variables

- `DATABASE_URL` — PostgreSQL connection string
- `OPENAI_API_KEY` — For GPT-5 Mini nudges
- `ANTHROPIC_API_KEY` — For Claude Haiku 4.5 chat
- `APNS_KEY_PATH`, `APNS_KEY_ID`, `APNS_TEAM_ID` — Apple Push Notification credentials
- `SECRET_KEY` — JWT signing key

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/apple` | POST | Sign in with Apple token exchange |
| `/api/samples` | POST | Receive HealthKit samples, evaluate thresholds, trigger nudges |
| `/api/thresholds` | GET/POST | CRUD for threshold configuration |
| `/api/chat` | POST | Coaching chat (Claude Haiku 4.5, 10 msg/day limit) |
| `/api/subscription/verify` | POST | App Store Server API validation |
| `/api/push-token` | POST | Update APNs device token |
| `/api/user/settings` | POST | Update timezone + quiet hours |
| `/health` | GET | Health check |

## Key Design Decisions

1. **Threshold evaluation is deterministic** — no LLM. It's an `if` statement. The backend is the single source of truth.
2. **System prompt is a cacheable prefix** — user context is injected separately to maximize prompt cache hits.
3. **Quiet hours are mandatory** — a 2 AM push notification will cause users to disable notifications permanently.
4. **Nudge idempotency** — `last_nudge_at` per threshold + min interval prevents duplicate coaching from batched HealthKit deliveries.
5. **APNs collapse-id** — per threshold, so multiple deliveries collapse into one notification.
6. **Queued messages have no content** — generated fresh at delivery time with current context (not stale data from hours ago).
7. **Provider abstraction** — each provider implements its own caching. OpenAI and Anthropic caching work differently.

## v0.2 Roadmap

- Multiple metrics (steps, heart rate, blood pressure)
- Unlimited thresholds (paid tier)
- Custom coach personas
- Free tier (1 threshold, nudges only, no chat)
- App Store Server Notifications V2 webhook
- Annual subscription discount
