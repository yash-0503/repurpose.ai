# Deployment Guide — Vercel + Render

Frontend on **Vercel**, backend on **Render**, database on **NeonDB**.

---

## 1. Code changes before deploying

The codebase currently assumes same-origin (localhost proxy). Deploying to two separate domains requires a few changes.

### Frontend: make API URL configurable

In `frontend/src/api/repurpose.js`, the API base is hardcoded to relative paths. In production the frontend (Vercel) and backend (Render) are on different domains, so we need an absolute URL.

```js
// frontend/src/api/repurpose.js — change the first two lines:
const BACKEND_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = `${BACKEND_URL}/api`;
const AUTH_BASE = `${BACKEND_URL}/auth`;
```

Locally this still works (empty string = relative URLs = Vite proxy). In production, set `VITE_API_URL` on Vercel.

### Frontend: add SPA rewrite for Vercel

Create `frontend/vercel.json`:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Without this, refreshing any page on Vercel returns a 404.

### Backend: make CORS configurable

In `backend/app/main.py`, replace the hardcoded CORS origins:

```python
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Backend: make OAuth redirect configurable

In the `google_callback` function in `backend/app/main.py`, the frontend redirect is hardcoded to `localhost:5173`:

```python
# Change this:
frontend_url = f"http://localhost:5173/?token={access_token}"

# To this:
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
frontend_url = f"{FRONTEND_URL}/?token={access_token}"
```

Move `FRONTEND_URL` to the top of the file with the other config so it's not re-read on every request.

---

## 2. Database — NeonDB

If you haven't already:

1. Create a project at [neon.tech](https://neon.tech) (free tier: 3 GB storage)
2. Copy the connection string — you'll add it as `NEON_DATABASE_URL` on Render
3. Tables are auto-created on startup, or run `backend/app/schema.sql` in the NeonDB SQL editor

---

## 3. Deploy backend on Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) and create a **Web Service**
3. Connect your GitHub repo
4. Configure the service:

| Setting | Value |
|---------|-------|
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

5. Add environment variables in the Render dashboard:

| Variable | Value |
|----------|-------|
| `NEON_DATABASE_URL` | Your Neon connection string |
| `GEMINI_API_KEY` | From [ai.google.dev](https://ai.google.dev/) |
| `GROQ_API_KEY` | From [console.groq.com](https://console.groq.com/) |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `JWT_SECRET` | Run `openssl rand -hex 32` to generate |
| `FRONTEND_URL` | `https://your-app.vercel.app` (fill in after Vercel deploy) |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app,http://localhost:5173` |

6. Deploy. Note your Render URL (e.g. `https://repurpose-ai.onrender.com`).

> **Free tier note:** Render free instances spin down after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

---

## 4. Deploy frontend on Vercel

1. Go to [vercel.com](https://vercel.com) and import your GitHub repo
2. Configure:

| Setting | Value |
|---------|-------|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

3. Add one environment variable:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://your-backend.onrender.com` (your Render URL from step 3) |

4. Deploy. Note your Vercel URL (e.g. `https://your-app.vercel.app`).

5. Go back to Render and update `FRONTEND_URL` and `ALLOWED_ORIGINS` with your actual Vercel URL.

---

## 5. Update Google OAuth

In the [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

1. Open your OAuth 2.0 client
2. Under **Authorized redirect URIs**, add:
   - `https://your-backend.onrender.com/auth/callback`
3. Keep `http://localhost:8000/auth/callback` for local development

---

## 6. Verify

1. Open your Vercel URL
2. Click "Sign in with Google" — should redirect through Render and back
3. Paste a YouTube URL and run through the full pipeline
4. Check Render logs if anything fails

---

## Checklist

- [ ] Code changes applied (API URL, CORS, OAuth redirect, `vercel.json`)
- [ ] NeonDB project created, connection string saved
- [ ] Backend deployed on Render with all env vars set
- [ ] Frontend deployed on Vercel with `VITE_API_URL` set
- [ ] `FRONTEND_URL` and `ALLOWED_ORIGINS` on Render updated with actual Vercel URL
- [ ] Google OAuth redirect URI added for Render backend URL
- [ ] Full pipeline tested end-to-end
