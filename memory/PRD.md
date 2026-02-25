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
- **Backend:** FastAPI (modular structure), MongoDB (motor), JWT auth, bcrypt, httpx
- **File Handling:** Static files served via `/api/uploads/...`
- **Scheduling:** Async background tasks for campaign processing

### Backend Structure (Refactored v2.0.0)
```
/app/backend/
├── server.py           # Main app entry point
├── models/
│   └── schemas.py      # Pydantic models
├── routes/
│   ├── auth.py         # Authentication routes
│   ├── users.py        # User management routes
│   ├── campaigns.py    # Campaign routes
│   ├── messages.py     # Message sending routes
│   ├── templates.py    # Template routes
│   └── upload.py       # File upload routes
└── utils/
    ├── auth.py         # JWT and password utilities
    ├── database.py     # MongoDB connection
    └── helpers.py      # Phone number normalization, etc.
```

## Current Status (January 2025)

### Fixed Issues
- **Session Instability (P1):** FIXED - Token validation added on app load, improved 401 error handling
- **Backend Refactoring (P1):** COMPLETED - Monolithic server.py split into modular structure

### Implementation Details (Session Fix)
1. `App.js` now validates tokens by calling `/auth/me` on app load
2. `api.js` only clears session on definite auth errors (401/403 with specific messages)
3. Network errors no longer trigger unnecessary logouts
4. Added 30-second timeout to API calls

### Backend Refactoring Details
- Split 1100+ line `server.py` into modular structure
- Created separate route files: `auth.py`, `users.py`, `campaigns.py`, `messages.py`, `templates.py`, `upload.py`
- Added reminder routes: `reminder_numbers.py`, `reminders.py`
- Added reminder service: `services/reminder_service.py`
- Moved models to `models/schemas.py` and `models/reminder_schemas.py`
- Moved utilities to `utils/auth.py`, `utils/database.py`, `utils/helpers.py`
- Added health check endpoint: `/api/health`
- API version: 2.1.0

### Reminder Bot Implementation (Phase 1-4 COMPLETED)
- **Phase 1 (Backend Models):** Created `reminder_numbers`, `reminders`, `reminder_settings` DB models
- **Phase 2 (OpenAI Integration):** NLP parsing for natural language reminders using GPT-3.5-Turbo
- **Phase 3 (Scheduler):** Background task checks due reminders every 30 seconds
- **Phase 4 (Frontend UI):** Complete Reminders page with:
  - Phone numbers management with timezone support
  - Natural language reminder creation
  - Reminder list with filtering (all, today, week, pending, sent, failed)
  - Settings for OpenAI API key and Meta template ID

### Reminder Message Format
```
🔔 *Reminder Alert*

✨ [Your reminder message]

⏰ Scheduled: 4:30 PM
📅 21 Jan 2026

_- Your WhatsApp Assistant_
```

## Upcoming Features: Reminder Bot

### User Requirements (ALL IMPLEMENTED)
- ✅ Natural language reminder creation (e.g., "remind me to call Harsh at 10 am tomorrow")
- ✅ Number management with timezone support
- ✅ Use pre-approved Meta template IDs OR 24-hour session window for direct messages
- ✅ Reminders filterable by day, week, or custom date range (up to 15 days)
- ✅ Delete reminders functionality
- ✅ Users provide their own OpenAI API keys (GPT-3.5-Turbo)

### Meta Template Strategy (User-Confirmed & Implemented)
1. ✅ Use pre-approved template ID for business-initiated messages
2. ✅ Provide documentation for users to create templates in Meta Business Manager
3. ✅ Utilize 24-hour session window when available for direct messages

### API Endpoints (Reminder Bot)
- `GET /api/reminder-numbers` - List phone numbers
- `POST /api/reminder-numbers` - Add phone number
- `DELETE /api/reminder-numbers/{id}` - Delete phone number
- `GET /api/reminder-numbers/timezones` - Get available timezones
- `GET /api/reminders` - List reminders with filters
- `POST /api/reminders` - Create reminder using NLP
- `POST /api/reminders/direct` - Create reminder directly
- `DELETE /api/reminders/{id}` - Delete reminder
- `GET /api/reminders/settings` - Get user settings
- `PUT /api/reminders/settings` - Update settings (API key, template)

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
- `/app/backend/server.py` - Main app entry, router setup, startup events
- `/app/backend/routes/` - All API route handlers
- `/app/backend/routes/reminder_numbers.py` - Reminder numbers CRUD
- `/app/backend/routes/reminders.py` - Reminders CRUD with NLP parsing
- `/app/backend/models/schemas.py` - Pydantic models
- `/app/backend/models/reminder_schemas.py` - Reminder-specific models
- `/app/backend/services/reminder_service.py` - Reminder sending service
- `/app/backend/utils/` - Shared utilities
- `/app/frontend/src/App.js` - Main app with session management
- `/app/frontend/src/utils/api.js` - API client with auth interceptors
- `/app/frontend/src/pages/Reminders.js` - Reminder Bot UI
- `/app/frontend/src/pages/` - All page components
- `/app/frontend/src/components/Layout.js` - Navigation with Reminders link

## Credentials
- **Admin:** bizchatapi@gmail.com / adminpassword

## Backlog
1. ~~**Backend Refactoring:** Split server.py into modular routers~~ DONE
2. ~~**Reminder Bot Feature:** Full implementation (Phase 1-4)~~ DONE
3. ~~**Meta Template Documentation:** Guide for users to set up WhatsApp templates~~ DONE (Enhanced Feb 2025)
4. **Error Handling:** Improved error messages throughout the app
5. **User Testing:** Full E2E testing of reminder flow with real OpenAI key
6. **Retry Failed Reminders:** Add ability to retry failed reminders
7. **Frontend Refactoring:** Break down large components (SendMessagesSimple.js, MyTemplates.js)

## Change Log

### February 25, 2025
- **Fixed:** WhatsApp "show reminders" command now only shows reminders for the specific phone number that sent the message (not all user's numbers)
- **Fixed:** All WhatsApp delete commands (delete by number, delete by name, delete all) now filter by phone number
- **Fixed:** AI bot no longer replies to non-reminder messages (stops chatting, fixed "Your suggested reply to the user" bug)
- **Enhanced:** Meta Template Guide (`/app/META_TEMPLATE_GUIDE.md`) with 5 ready-to-use template designs for Meta approval
- **Added:** New "Template Guide" tab in Reminders page with:
  - Quick start steps for template approval
  - Ready-to-use templates with Copy buttons
  - Do's and Don'ts for template approval
  - Template status reference
  - Direct link to Meta Business Suite
- **Added:** Recurring Reminders feature:
  - Backend: RecurrenceConfig schema, calculate_next_occurrence(), auto-create next reminder after sending
  - Frontend: Repeat dropdown (Daily, Weekly, Monthly, Custom), weekday selector for weekly, interval settings
  - WhatsApp: Natural language support ("remind me daily", "every Monday", "every 2 weeks")
  - Reminders run forever until manually deleted
- **Updated:** Added detailed template approval best practices and troubleshooting guide

### WhatsApp Webhook Phone Filtering (Feb 2025)
The following functions now accept optional `phone` parameter to filter reminders:
- `get_reminders_list(user_id, timezone, phone=None)`
- `delete_reminder_by_name(user_id, search_text, timezone, phone=None)`
- `delete_reminder_by_number(user_id, reminder_num, timezone, phone=None)`
- `delete_all_matching_reminders(user_id, search_text, phone=None)`
- `delete_all_reminders(user_id, phone=None)`

## API Endpoints (Webhook)
- `POST /api/webhook/bizchat` - Receive incoming WhatsApp messages
- `GET /api/webhook/bizchat` - Webhook verification
