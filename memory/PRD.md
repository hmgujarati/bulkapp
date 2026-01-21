# WhatsApp Bulk Messenger - Product Requirements Document

## Original Problem Statement
Build a full-stack website for sending bulk WhatsApp messages using the `bizchatapi.in` API. Later expanded to include a "Reminder Bot" feature using AI-powered natural language processing.

## User Personas
1. **Admin** - Manages users, can view all campaigns, configure system
2. **User** - Sends bulk WhatsApp messages, manages templates, views campaign history

## Core Requirements (Completed)
- [x] User authentication (admin/user roles)
- [x] Admin dashboard for user management
- [x] User dashboard with campaign creation
- [x] Message templates with personalization ({name} placeholders)
- [x] Media support (image, video, document) with 5MB limit
- [x] Location sharing support
- [x] Campaign scheduling (immediate or scheduled)
- [x] Background job processing for scheduled campaigns (APScheduler)
- [x] Campaign history and statistics
- [x] Settings page for password change
- [x] Super admin protection (cannot be deleted/paused)

## Technical Architecture
- **Frontend:** React, react-router-dom, axios, shadcn/ui, sonner (toasts), papaparse, lucide-react
- **Backend:** FastAPI (monolithic server.py), MongoDB (motor), JWT auth, bcrypt, httpx
- **File Handling:** Static files served via `/api/uploads/...`
- **Scheduling:** APScheduler for background campaign processing

## Current Status (January 2025)

### Fixed Issues
- **Session Instability (P1):** FIXED - Token validation added on app load, improved 401 error handling

### Implementation Details (Session Fix)
1. `App.js` now validates tokens by calling `/auth/me` on app load
2. `api.js` only clears session on definite auth errors (401/403 with specific messages)
3. Network errors no longer trigger unnecessary logouts
4. Added 30-second timeout to API calls

## Upcoming Features: Reminder Bot

### User Requirements
- Natural language reminder creation (e.g., "remind me to call Harsh at 10 am tomorrow")
- Number management with timezone support
- Use pre-approved Meta template IDs OR 24-hour session window for direct messages
- Reminders filterable by day, week, or custom date range (up to 15 days)
- Delete reminders functionality
- Users provide their own OpenAI API keys (GPT-3.5-Turbo recommended)

### Meta Template Strategy (User-Confirmed)
1. Use pre-approved template ID for business-initiated messages
2. Provide documentation for users to create templates in Meta Business Manager
3. Utilize 24-hour session window when available for direct messages

### Implementation Phases
- **Phase 1:** Backend models (`reminder_numbers`, `reminders`) and CRUD APIs
- **Phase 2:** OpenAI integration for NLP parsing
- **Phase 3:** Scheduler integration with `bizchatapi.in`
- **Phase 4:** Frontend UI for reminder management

## API Endpoints
- `/api/auth/login` - User login
- `/api/auth/me` - Session validation (NEW)
- `/api/auth/register` - Admin-only user creation
- `/api/auth/change-password` - Password change
- `/api/users` - User management (admin)
- `/api/messages/send` - Send campaigns
- `/api/campaigns` - Campaign management
- `/api/saved-templates` - User template presets
- `/api/upload/media` - File uploads
- `/api/uploads/{type}/{filename}` - Serve uploaded files

## Key Files
- `/app/backend/server.py` - All backend logic (needs refactoring)
- `/app/frontend/src/App.js` - Main app with session management
- `/app/frontend/src/utils/api.js` - API client with auth interceptors
- `/app/frontend/src/pages/` - All page components

## Credentials
- **Admin:** bizchatapi@gmail.com / adminpassword

## Backlog
1. **Backend Refactoring:** Split server.py into modular routers
2. **Reminder Bot Feature:** Full implementation after refactoring
3. **Error Handling:** Improved error messages throughout the app
