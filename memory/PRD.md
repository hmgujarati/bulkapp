# WhatsApp Bulk Messenger - Product Requirements Document

## Original Problem Statement
Build a full-stack website for sending bulk WhatsApp messages using the `bizchatapi.in` API. The scope expanded to include a "Reminder Bot", Contact Management, Indiamart Integration, and a WhatsApp Lead Qualification Chatbot. The overall goal is a multi-featured WhatsApp automation platform.

## User Personas
1. **Admin** - Manages users, can view all campaigns, configure system, enable/disable features per user
2. **User** - Sends bulk WhatsApp messages, manages templates, views campaign history, uses chatbot

## Core Requirements (All Completed)
- [x] User authentication (admin/user roles)
- [x] Admin dashboard for user management with feature-gating
- [x] User dashboard with campaign creation
- [x] Message templates with personalization
- [x] Media support (image, video, document) with 5MB limit
- [x] Campaign scheduling (immediate or scheduled)
- [x] Campaign history and statistics
- [x] Reminder Bot (natural language, recurring)
- [x] Contact Manager (birthday/anniversary auto-wishes)
- [x] Indiamart Integration (Push API webhook, auto-messaging)
- [x] **Lead Qualification Chatbot** (NEW - March 2026)

## Technical Architecture
- **Frontend:** React, react-router-dom, axios, shadcn/ui, sonner (toasts), lucide-react
- **Backend:** FastAPI (modular structure), MongoDB (motor), JWT auth, bcrypt, httpx
- **Scheduling:** Async background tasks for campaigns, reminders, auto-wishes, chatbot follow-ups

### Backend Structure
```
/app/backend/
├── server.py
├── models/
│   ├── schemas.py
│   ├── reminder_schemas.py
│   ├── contact_schemas.py
│   ├── indiamart_schemas.py
│   └── chatbot_schemas.py          # NEW
├── routes/
│   ├── auth.py
│   ├── users.py
│   ├── campaigns.py
│   ├── messages.py
│   ├── templates.py
│   ├── upload.py
│   ├── reminder_numbers.py
│   ├── reminders.py
│   ├── webhook.py                   # UPDATED (chatbot integration)
│   ├── contacts.py
│   ├── indiamart.py
│   └── chatbot.py                   # NEW
├── services/
│   ├── reminder_service.py
│   ├── auto_message_service.py
│   ├── indiamart_service.py
│   └── chatbot_service.py           # NEW
└── utils/
    ├── auth.py
    ├── database.py
    └── daily_limit.py
```

## Lead Qualification Chatbot (NEW - March 12, 2026)

### Feature Description
WhatsApp chatbot that qualifies leads by asking sequential questions. Supports:
- **Category → Product hierarchy** with bulk CSV upload for 1000s of products
- **Sequential question flows** per category (text, button, or list type)
- **Product search** - client types letters, bot searches and shows matching list via WhatsApp interactive messages
- **Follow-up reminders** - custom delay (any minutes), custom max attempts for abandoned conversations
- **Lead notifications** - main user gets all leads, category-assigned employees get product-specific leads
- **Lead routing** per category to assigned employee WhatsApp
- **Excel/CSV export** with filters (by product, date range, status)
- **Admin feature-gating** - chatbot can be enabled/disabled per user

### API Endpoints (Chatbot)
- `GET/PUT /api/chatbot/settings` - Chatbot settings (toggle, messages, follow-up config, notification)
- `GET/POST /api/chatbot/categories` - Categories CRUD
- `PUT/DELETE /api/chatbot/categories/{id}` - Category update/delete (cascades)
- `GET/POST /api/chatbot/products` - Products CRUD with search and filtering
- `PUT/DELETE /api/chatbot/products/{id}` - Product update/delete
- `POST /api/chatbot/products/bulk-upload` - CSV bulk upload
- `DELETE /api/chatbot/products/bulk-delete` - Bulk delete products
- `GET /api/chatbot/questions/{category_id}` - Get flow questions
- `POST /api/chatbot/questions` - Create question
- `PUT/DELETE /api/chatbot/questions/{id}` - Update/delete question
- `PUT /api/chatbot/questions/reorder/{category_id}` - Reorder questions
- `GET /api/chatbot/leads` - List leads with filters
- `PUT/DELETE /api/chatbot/leads/{id}` - Update/delete lead
- `GET /api/chatbot/leads/export` - Export leads as CSV
- `GET /api/chatbot/stats` - Chatbot statistics

### DB Collections (Chatbot)
- `chatbot_settings` - Per-user settings
- `chatbot_categories` - Categories with employee routing
- `chatbot_products` - Products under categories
- `chatbot_flow_questions` - Sequential qualifying questions per category
- `chatbot_conversations` - Active conversation sessions
- `chatbot_leads` - Completed/partial lead records

### WhatsApp Interactive Messages
Uses bizchatapi.in Send Interactive Message API:
- **Buttons** (up to 3) for category selection, yes/no questions
- **Lists** (up to 10 items per section) for product selection, multi-option questions
- **Text messages** for free-text questions and follow-ups

### Chatbot Conversation Flow
1. Client sends message → Webhook receives it
2. Check if chatbot is enabled for user
3. New conversation: Send greeting + category list (interactive list/buttons)
4. Client selects category → Check product count:
   - 0 products: Skip to questions
   - ≤10 products: Show list directly
   - >10 products: Ask client to search by typing letters
5. Client selects product → Start qualifying questions (sequential)
6. After all questions → Store lead, send notifications
7. If abandoned: Follow-up after configured delay, max attempts configurable

## Credentials
- **Admin:** bizchatapi@gmail.com / adminpassword
- **User:** rapidexpresstechnologies@gmail.com / [user-set]

## Feature Flags
Features controlled per-user by admin:
- bulk_messages, reminders, contacts, templates, campaigns, indiamart, chatbot

## Backlog / Future Tasks
1. **(P1) Indiamart Pull API** - Fetch historical leads (deferred by user)
2. **(P2) Voice Call Reminders** - Add voice call capabilities (deferred by user)

## Change Log

### March 12, 2026
- **NEW FEATURE:** Lead Qualification Chatbot
  - Backend: Full CRUD for categories, products, flow questions, leads
  - Backend: Chatbot conversation engine with WhatsApp interactive messages (buttons/lists)
  - Backend: Product search for categories with many products
  - Backend: Follow-up scheduler for abandoned conversations
  - Backend: Lead notifications to main user and category-assigned employees
  - Backend: CSV export for leads with filters
  - Backend: CSV bulk upload for products
  - Frontend: New ChatbotPage with 5 tabs (Settings, Categories, Products, Flows, Leads)
  - Admin: Chatbot feature added to feature-gating system
  - Webhook: Chatbot message handler integrated before reminder bot
  - Testing: 30/30 backend tests passed, all frontend tabs verified
