# WhatsApp Lead Flow - Product Requirements Document

## Original Problem Statement
Build a WhatsApp Q&A Chatbot platform to qualify leads, gather data through sequential questions, map responses to products/categories, and export leads. Support bulk messaging, AI reminders, contact management, and admin tools.

## Core Features (Implemented)
- Bulk WhatsApp messaging (concurrent, connection-pooled)
- AI-powered Reminder Bot via WhatsApp
- Lead Qualification Chatbot with trigger keywords
- Universal Webhook per user (`/api/webhook/{user_id}`)
- Contact Management with birthday/anniversary logic
- Indiamart webhook integration
- Admin panel with user feature gating and "Login As"
- Campaign history with "Retry Failed Messages"

## Architecture
- **Backend**: FastAPI + MongoDB (Motor) + httpx connection pooling
- **Frontend**: React + Shadcn UI
- **3rd Party**: BizChat API (WhatsApp), OpenAI GPT

## Recent Changes (April 2026)
- Fixed HTTP 429 rate limiting in bulk messaging — added retry with exponential backoff, adaptive batch delay, reduced concurrency
- Fixed "Retry Failed Messages" routing — frontend was calling wrong API path

## Backlog
- P1: Indiamart Pull API (deferred by user)
- P2: Voice Call Reminders (deferred by user)
- P3: Chatbot Analytics Dashboard (to be discussed)
