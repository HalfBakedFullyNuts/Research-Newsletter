# Research Newsletter (R.N.)

**Mission:** Inspire professionals to trust science by delivering automated, topic-specific research updates directly to their inbox.

## Overview

A subscription-based service where professionals from any domain select research topics and receive curated email digests of the latest academic publications. Bridges the gap between theory (academia) and practice (industry).

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  OpenAlex    │    │  Topic       │    │  Email       │
│  API         │───▶│  Classifier  │───▶│  Generator   │
│  (Free)      │    │  (ML/Rule)   │    │  (Gmail API) │
└──────────────┘    └──────────────┘    └──────────────┘
       ▲                     │                      │
       │                     ▼                      ▼
       │            ┌──────────────────┐    ┌──────────────┐
       │            │   Topic DB       │    │  SMTP/API    │
       │            │  (SQLite/Postgres)│    │  (Outreach)  │
       │            └──────────────────┘    └──────────────┘
       │
       └── Topic Keywords/Concepts ← User Preferences
```

## Tech Stack

- **Backend:** Python 3.13+ (FastAPI for future web, scripts for MVP)
- **Research Data:** OpenAlex API (free, comprehensive, rate-limited)
- **Email:** Gmail API (MVP), SMTP (production)
- **Database:** SQLite (MVP), PostgreSQL (production)
- **Payments:** Stripe (planned for later)
- **Deployment:** Fly.io (current infrastructure)

## MVP Scope (Phase 1)

1. ✅ OpenAlex integration (existing from alina_research_feed.py)
2. Topic classification and scoring
3. Email generation with digest formatting
4. Local subscriber/topic management (SQLite)
5. Scheduled cron jobs for periodic fetch/send

## Project Structure

```
Research-Newsletter/
├── src/
│   ├── core/        # Main application logic
│   │   ├── config.py    # Configuration
│   │   ├── openalex.py  # API client wrapper
│   │   ├── classifier.py # Topic relevance scoring
│   │   └── scheduler.py # Job scheduling
│   ├── email/       # Email generation & delivery
│   │   ├── generator.py # Markdown to HTML digest
│   │   └── sender.py    # Gmail API integration
│   ├── topics/      # Topic management
│   │   ├── manager.py   # CRUD for topics
│   │   └── categories.json # Predefined research domains
│   └── web/         # Future web interface
├── tests/
├── scripts/
│   ├── fetch.py     # CLI: Fetch latest papers for a topic
│   └── send.py      # CLI: Send digest to a subscriber
├── docs/
├── cache/           # Local SQLite DB
├── .env.example
└── README.md
```

## Configuration

Copy `.env.example` to `.env` and set:
- `GOOGLE_API_TOKEN_PATH` (or use existing `~/.hermes/google_token.json`)
- `ADMIN_EMAIL` (your Gmail for sending)
- `OPENALEX_RATE_LIMIT` (optional, default handled)

## Development Decisions

See the "Research Newsletter - Dev Decisions" page in Notion (Lupus HQ) for detailed rationale on all technical choices.

## License

TBD
