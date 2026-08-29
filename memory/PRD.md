# WhatsApp Lead Flow - Product Requirements Document

## Original Problem Statement
Build a WhatsApp platform for bulk messaging, AI reminders, lead qualification chatbot, contact management, and admin tools. The chatbot should use trigger-based flows to collect lead data through sequential questions.

## Core Features (Implemented)
- **Bulk WhatsApp Messaging** — concurrent sending with connection pooling, 429 rate limit handling, adaptive batch delay
- **AI-powered Reminder Bot** via WhatsApp
- **Lead Qualification Chatbot** — simplified flow model with trigger keywords, sequential questions (text/button/list), WhatsApp notifications
- **Universal Webhook** per user (`/api/webhook/{user_id}`) — routes Chatbot → Reminder Bot
- **Contact Management** with birthday/anniversary automation
- **Indiamart Webhook** integration
- **Admin Panel** — user feature gating, "Login As" impersonation, retry failed messages

## Architecture
- **Backend**: FastAPI + MongoDB (Motor) + httpx connection pooling
- **Frontend**: React + Shadcn UI
- **3rd Party**: BizChat API (WhatsApp), OpenAI GPT

## Chatbot Data Model (Simplified — April 2026)
- `chatbot_settings`: Global on/off, defaultNotifyPhone, follow-up config
- `chatbot_flows`: name, triggerKeywords[], greetingMessage, completionMessage, questions[{questionText, questionType, options[]}], notifyPhone, isActive
- `chatbot_conversations`: flowId, clientPhone, currentStep (int), answers[], status
- `chatbot_leads`: flowId, flowName, clientPhone, answers[], status

## Key API Endpoints
- `POST /api/webhook/{user_id}` — Universal webhook for all incoming WhatsApp messages
- `GET/PUT /api/chatbot/settings` — Global chatbot settings
- `GET/POST/PUT/DELETE /api/chatbot/flows` — Flow CRUD
- `GET /api/chatbot/leads` — Leads with filters, pagination, stats
- `GET /api/chatbot/leads/export` — CSV export
- `POST /api/messages/campaigns/{id}/retry-failed` — Retry failed bulk messages
- `POST /api/auth/login-as/{user_id}` — Admin impersonation

## Recent Changes (April 2026)
- **Chatbot Simplification**: Replaced 5-tab (Settings/Categories/Products/Flows/Leads) with 3-tab (Flows/Leads/Settings). Flow model now contains all config inline.
- **429 Rate Limiting**: Added retry with exponential backoff, reduced batch size, adaptive delay
- **Retry Failed Fix**: Frontend path corrected from `/campaigns/` to `/messages/campaigns/`
- **Self-healing Campaign Workers (Apr 28, 2026)**: Permanent fix for campaigns getting stuck in PROCESSING status after server restarts. Added:
  - `lastHeartbeatAt` written on every batch by `process_campaign` (`/app/backend/routes/messages.py`)
  - `ACTIVE_CAMPAIGNS` in-process set to prevent duplicate workers for the same campaign
  - `watchdog_stuck_campaigns` task (runs every 30s) — finds PROCESSING campaigns with stale/missing heartbeat (>90s) and re-spawns the worker
  - `startup_resume_processing_campaigns` task — runs once at boot, immediately resumes all PROCESSING campaigns left over from a crashed process
  - `_resume_stuck_campaign` helper with safety checks (missing BizChat creds → PAUSED with actionable error)
  - Idempotent by design: `process_campaign` already skips non-PENDING recipients, so re-spawning never duplicates messages
- **BizChat Template Auto-fetch + Language Auto-fill (Apr 30, 2026)**: Eliminates the #1 cause of HTTP 422 errors.
  - New `GET /api/templates` endpoint proxies BizChat's `/{vendorUid}/contact/template-list` (`/app/backend/routes/bizchat_templates.py`)
  - Defensive parser handles BizChat's deeply-nested `{data: {templateList: {data: [...]}}}` shape and extracts `name`, `language`, `status`, `category`, `components` per template
  - Frontend `SendMessagesNew.js`: template picker in "Fetch from BizChat" tab now auto-fills `templateLanguage` from the selected template's metadata; shows "Language auto-filled: xx" hint below
  - Frontend `SendMessagesSimple.js`: added BizChat template picker dropdown + refresh button above the Template Name input; selecting a template auto-fills both name AND language
- **Read/Delivery Receipts + Tiered Daily Limits (May 1, 2026)**:
  - Backend service `/app/backend/services/message_status_service.py` defensively parses status webhooks (Cloud-API `statuses[]`, BizChat `data.status`, flat `wamid+status`) and updates campaign recipient status with strict precedence: `pending → sent → delivered → read` (never downgrade; `failed` is terminal)
  - `extract_status_data` aliases handle BSP variations: `success/accepted/queued/submitted → sent`, `received → delivered`, `seen/viewed → read`, `failure/error/rejected/undeliverable → failed`
  - Webhook (`/app/backend/routes/webhook.py`) checks for status payloads first; if found, processes them and short-circuits before message extraction
  - Schema additions: `MessageStatus.READ`, `RecipientInfo.deliveredAt/readAt`, `Campaign.deliveredCount/readCount`
  - `CampaignDetails.js`: 6-card stat grid now shows Total / Sent / **Delivered (✓✓)** / **Read (👁)** / Failed / Pending with conversion-rate %
  - Tier-based admin limits in `AdminDashboard.js`: dropdown limited to **Tier 1 (250) → Tier 2 (2,000) → Tier 3 (10,000) → Tier 4 (100,000) → Unlimited**. Legacy values (e.g., 1,000) display gracefully until admin upgrades.
  - `dailyLimit == -1` is the **truly unlimited** sentinel: the `daily_limit.py` reset logic and `messages.py` send/process gates skip the cap entirely; `UserDashboard.js` shows `∞` instead of a number.
- **BizChat-specific webhook shape support (May 1, 2026)**: Added BizChat's actual production payload shape `{contact:{}, message:{whatsapp_message_id, status, body:null, is_new_message:false}}` to `extract_status_data` parser. Previously only Cloud-API style `statuses[]` was recognized.
- **wamid extraction fix on send (May 1, 2026)**: BizChat's `send-template-message` response is double-nested as `{result, message, data:{wamid, log_uid, ...}}`. The original code read top-level `data.message_id` which was always None, so no campaign recipients had `messageId` populated → status webhooks couldn't match → no Delivered/Read counts updated. Now reads `data.data.wamid` (with fallbacks) in both the main send loop and the auto-retry loop in `routes/messages.py`.
- **Button-click tracking (May 1, 2026)**: New service `/app/backend/services/button_click_service.py` detects WhatsApp template button taps via 3 webhook shapes (BizChat `replied_to_whatsapp_message_id`+body, Cloud-API `interactive.button_reply`, Cloud-API `button.text`). Records per recipient: `clickedButton` + `clickedAt`. First-click-wins (subsequent clicks ignored). UI on `CampaignDetails.js` adds: 
  - "Clicked" column in recipients table with the button text
  - Summary badges showing click breakdown (e.g. "Yes!: 12 · Call Us: 7 · No click: 81")
  - Filter dropdown: All / Clicked any / Did NOT click / specific button
  - CSV export expanded with `Clicked Button`, `Clicked At`, `Delivered At`, `Read At` columns; respects active filter so admin can download only "people who clicked Yes" for follow-up calls.

## Backlog
- P1: Indiamart Pull API (deferred by user)
- P2: Voice Call Reminders (deferred by user)
- P3: Chatbot Analytics Dashboard (to be discussed)

## Update — June 2026 (Daily Sending Limit / Drip)
Implemented:
- **Daily Sending Limit (drip) on Send Messages**: user sets messages/day + optional daily start time (browser local time, blank = start now). Live estimate: "N recipients at X/day -> campaign will finish in D days (around <date>)". Backend sends up to `dripDailyLimit` per rolling 24h window anchored at `dripStartAt`, then parks the campaign as `scheduled` for the next window (picked up by the existing scheduler). Fields on campaign: `dripEnabled, dripDailyLimit, dripStartAt, dripWindowIndex, dripSentInWindow`. Blocked at creation if messages/day > account dailyLimit. "Schedule for later" is disabled while drip is on.
- **Campaign Name is now mandatory** (frontend disables send + red note; backend returns 400).
- **Template Name (Your Reference)**: optional field on Send Messages (auto-filled when a Saved Template is loaded), stored as `campaign.templateReference`, shown in Campaign Details next to "BizChat Template Name".
- Fixed datetime-local `min` to use local time instead of UTC.

Tests: `/app/backend/tests/test_drip_campaign.py` (standalone async, window logic incl. completion), `/app/backend/tests/test_drip_and_campaign_name.py` (pytest, 11/11), frontend flows verified by testing agent (iteration_9.json, 100%).

Still open:
- (P0) "Refresh Daily Usage" admin utility misses messages sent today by campaigns created on earlier days (retried/resumed/drip campaigns). Needs a decision on tracking daily sends per campaign.
- (P3) Nightly cron for the Daily Usage refresh.
- **Media uploads moved to Emergent Object Storage** (Aug 29, 2026): `POST /api/upload/media` now stores files in object storage (`bizchat/uploads/{userId}/{uuid}.ext`), records metadata in `media_files`, and returns `/api/upload/media/{file_id}` — a public (unauthenticated) URL so WhatsApp/BizChat can fetch template media. Pod-local `uploads/` static mounts are kept only for older files. Verified with a round-trip upload + public fetch (bytes match).
- Media upload QA (Aug 29, 2026): image/video/document verified in both Send Messages and My Templates. Fixed (a) object storage `.env` key loading (400 on init), (b) MIME fallback so videos get `video/mp4` not octet-stream, (c) MyTemplates stale-state bug that silently dropped the uploaded document URL, (d) added label to document filename input.
