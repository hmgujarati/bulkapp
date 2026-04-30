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

## Backlog
- P1: Indiamart Pull API (deferred by user)
- P2: Voice Call Reminders (deferred by user)
- P3: Chatbot Analytics Dashboard (to be discussed)
