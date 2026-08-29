# WhatsApp Lead Flow / BizChat API — Product Requirements Document

## Original Problem Statement
Build a WhatsApp platform for bulk messaging, AI reminders, lead qualification chatbot, contact management, and admin tools. The chatbot uses trigger-based flows to collect lead data through sequential questions. Runs on a resource-constrained self-hosted server (2 cores / 3GB RAM), so everything must be memory- and payload-safe.

## Core Features (Implemented)
- **Bulk WhatsApp Messaging** — concurrent sending with connection pooling, 429 handling, adaptive batch delay
- **AI-powered Reminder Bot** via WhatsApp
- **Lead Qualification Chatbot** — trigger keywords, sequential questions, WhatsApp notifications
- **Universal Webhook** per user (`/api/webhook/{user_id}`) — Chatbot → Reminder Bot routing
- **Contact Management** with birthday/anniversary automation
- **Indiamart Webhook** integration
- **Admin Panel** — user feature gating, "Login As" impersonation, retry failed messages, tiered daily limits
- **Read/Delivery receipts + button-click tracking** on campaigns
- **Drip campaigns** (messages/day + start time), mandatory campaign name, template reference field
- **Chunked campaign creation** (`init` → `recipients` chunks → `start`) for 30k+ recipient lists
- **Campaign chain splitting** — >3000 recipients auto-split into "Day X/Y" (drip) or "Part X/Y" (normal) campaigns linked by `chainId`, parts auto-start one after another
- **Hybrid media storage** — Emergent Object Storage when `EMERGENT_LLM_KEY` exists, otherwise local disk `backend/uploads/`
- **Phone normalization** — libphonenumber-js on the frontend, invalid numbers dropped, country dial-code prefixing

## Architecture
- **Backend**: FastAPI + MongoDB (Motor) + httpx connection pooling
- **Frontend**: React + Shadcn UI
- **3rd Party**: BizChat API (WhatsApp), OpenAI GPT, Emergent Object Storage

## Key API Endpoints
- `POST /api/messages/send` — create + start a campaign (`campaignName` required)
- `POST /api/messages/campaigns/init` → `/{id}/recipients` (chunks) → `/{id}/start` — large lists
- `POST /api/messages/campaigns/{id}/retry-failed`
- `POST /api/users/refresh-daily-usage` — admin: recompute dailyUsage for all users
- `POST /api/users/{user_id}/refresh-daily-usage` — admin or self
- `GET/PUT /api/chatbot/settings`, `GET/POST/PUT/DELETE /api/chatbot/flows`, `GET /api/chatbot/leads`
- `POST /api/upload/media` — object storage or local fallback
- `POST /api/webhook/{user_id}` — incoming messages + delivery/read statuses

## Changelog (recent)
- **June 2026 — Daily Usage accuracy (P0 fixed)**: `recalculate_daily_usage()` in `utils/daily_limit.py` recomputes `dailyUsage` from each recipient's actual `sentAt` inside the current 24h window (aggregation with `$filter`, no `$unwind`), instead of the old `campaign.createdAt >= lastResetDateTime` filter which ignored campaigns created on earlier days and resumed/retried today. Failed messages have no `sentAt`, so quota is auto-refunded. `update_last_activity()` no longer slides `lastResetDateTime` forward on every send (it only seeds it when missing), so the 24h window actually expires. Admin Dashboard gained a "Refresh Daily Usage" header button + a "Used Today" column with a per-row refresh icon. Tests: `backend/tests/test_dailyusage_backfill.py` (5/5) and `backend/tests/test_refresh_daily_usage.py` (10/10); admin UI verified by the testing agent (iteration_11.json, 100% backend + frontend).
- **Aug/June 2026 — Campaign chain splitting**: >3000 recipients split into linked campaigns named "(Day X/Y)" or "(Part X/Y)"; Campaign Details shows chain membership. Test: `backend/tests/test_campaign_chain.py`.
- **Large-campaign fix**: chunked create flow (1,000-row chunks) — 30k recipients upload in ~5s; draft campaigns hidden from lists.
- **Upload storage auto-detection** + local disk fallback for the self-hosted server. Test: `backend/tests/test_upload_fallback.py`.
- **Phone validation** restored on the active send flow (`utils/phoneValidator.js`, 245-country picker, "Re-check with +NN").
- **Drip campaigns / campaign name / template reference** — see `test_drip_campaign.py`, `test_drip_and_campaign_name.py`.
- Earlier: self-healing campaign workers + watchdog, wamid extraction fix, tiered daily limits (`dailyLimit == -1` = unlimited), BizChat template auto-fetch.

## Backlog
- P1: Indiamart Pull API — fetch existing/historical leads
- P2: Voice call reminders
- P3: Nightly auto-refresh of daily usage (3 AM IST via scheduler) — endpoint now exists, just needs the cron
- P3: Chatbot analytics dashboard (conversion rates, drop-off points)
- P3: "Test Flow" chatbot simulator in the dashboard
- P3: Monthly cleanup of unused uploaded media
- P3 (noted by review): `refresh-daily-usage` for all users is sequential and capped at 1000 users — paginate if the user base grows

## Test Credentials
See `/app/memory/test_credentials.md` (qaadmin@example.com / Admin@12345, qatest@example.com / Test@12345).
