# Repurpose.ai

Turn YouTube videos into blogs, LinkedIn posts, and Twitter threads — with optional writing style matching.

## What it does

1. Paste a YouTube URL
2. Pick an output format (blog, LinkedIn, Twitter)
3. Optionally match a writing style from sample text
4. Get AI-generated content in seconds

Authenticated via Google OAuth. All content is saved to your account.

## Tech Stack

**Backend** — Python (FastAPI), Groq Whisper API (transcription), Google Gemini + LlamaIndex (content generation), SQLAlchemy + NeonDB (PostgreSQL), JWT auth

**Frontend** — React 19, Vite

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                        # API routes + middleware
│   │   ├── auth.py                        # Google OAuth + JWT
│   │   ├── database.py                    # SQLAlchemy models (User, Style, Blog)
│   │   ├── schema.sql                     # DDL for manual DB setup
│   │   └── services/
│   │       ├── audio_downloader.py        # yt-dlp YouTube audio download
│   │       ├── transcriber.py             # Groq Whisper transcription
│   │       ├── style_analyzer.py          # Writing style analysis via Gemini
│   │       └── generate_blog_from_style.py # Content generation via LlamaIndex
│   ├── requirements.txt
│   └── runtime.txt
├── frontend/
│   ├── src/
│   │   ├── api/repurpose.js               # API client
│   │   ├── context/AuthContext.jsx         # Auth state
│   │   └── components/                    # UI components
│   ├── package.json
│   └── vite.config.js
└── env.example
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [NeonDB](https://neon.tech) account (free tier works)
- [Google Cloud](https://console.cloud.google.com) project with OAuth credentials
- [Gemini API key](https://ai.google.dev/)
- [Groq API key](https://console.groq.com/)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend

```bash
cd frontend
npm install
```

### 3. Environment variables

Copy `env.example` to `.env` in the project root and fill in your keys. See the file for descriptions of each variable.

### 4. Database

Create a project on [NeonDB](https://neon.tech), copy the connection string into `NEON_DATABASE_URL` in `.env`. Tables are auto-created on first startup, or you can run `backend/app/schema.sql` manually.

### 5. Google OAuth

In Google Cloud Console, create OAuth 2.0 credentials and add `http://localhost:8000/auth/callback` as an authorized redirect URI.

## Running locally

Start both in separate terminals:

```bash
# Backend (from backend/)
uvicorn app.main:app --reload --port 8000

# Frontend (from frontend/)
npm run dev
```

Frontend runs at `http://localhost:5173`, backend at `http://localhost:8000`. The Vite dev server proxies `/api` and `/auth` requests to the backend.

## API Endpoints

Interactive docs available at `http://localhost:8000/docs` when running.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/google` | Start Google OAuth flow |
| GET | `/auth/callback` | OAuth callback |
| GET | `/auth/me` | Get current user |
| POST | `/api/download` | Download YouTube audio |
| POST | `/api/transcribe` | Transcribe audio via Groq |
| POST | `/api/analyze-style` | Analyze writing style |
| POST | `/api/generate-blog` | Generate content |
| GET | `/api/styles` | List saved styles |
| POST | `/api/styles` | Create a style |
| DELETE | `/api/styles/{id}` | Delete a style |
| GET | `/api/blogs` | List generated content |
| DELETE | `/api/blogs/{id}` | Delete content |

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for instructions on deploying to Vercel (frontend) + Render (backend).
