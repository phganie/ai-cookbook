# CookClip – Video → Recipe MVP

CookClip turns cooking videos into trustworthy, step-by-step recipes you can actually follow. Paste a YouTube URL, and the app extracts a clean ingredient list and clear instructions—each step linked back to the exact timestamp in the video.

## Project Structure

```
cookbook/
├── server/          # FastAPI backend (Python)
├── client/          # Next.js frontend (TypeScript + Tailwind)
└── README.md        # This file
```

## Quick Start

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **PostgreSQL** (optional; defaults to SQLite for local dev)
- **Google Cloud Project** with Vertex AI enabled (required for recipe extraction)

### Backend Setup

1. **Navigate to server directory:**
   ```bash
   cd server
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit .env and add your Vertex AI configuration:
   # VERTEX_PROJECT_ID=your-gcp-project-id
   # VERTEX_LOCATION=us-central1
   # VERTEX_MODEL=gemini-1.5-flash
   # DATABASE_URL=postgresql+psycopg2://username@localhost:5432/cookclip
   # (or leave DATABASE_URL unset to use SQLite)
   ```

5. **Set up Google Cloud authentication:**
   ```bash
   # Option A: Application Default Credentials (recommended for local dev)
   gcloud auth application-default login
   
   # Option B: Service Account Key
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

6. **Run the server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to client directory:**
   ```bash
   cd client
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   # Copy example env file
   cp env.example .env.local
   
   # Edit .env.local if your backend runs on a different port
   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

4. **Run the dev server:**
   ```bash
   npm run dev
   ```

The app will be available at `http://localhost:3000`

## API Endpoints

### Backend (`/api`)

- **`POST /api/extract`** – Extract recipe from YouTube URL
  - Body: `{ "url": "https://youtube.com/watch?v=..." }`
  - Returns: Structured recipe JSON with ingredients, steps, and timestamps

- **`POST /api/recipes`** – Save recipe to database
  - Body: `{ "source_url": "...", "source_platform": "youtube", "data": {...} }`
  - Returns: Saved recipe with ID

- **`GET /api/recipes`** – List all saved recipes
  - Returns: Array of recipe objects

- **`GET /api/recipes/:id`** – Get single recipe by ID
  - Returns: Recipe object

## Frontend Pages

- **`/`** – Home page: Paste YouTube URL, extract recipe, preview, and save
- **`/library`** – Browse all saved recipes
- **`/recipes/[id]`** – View recipe detail with cook mode (step-by-step with timestamps)

## Development

### Backend

- **Linting/Formatting:**
  ```bash
  pip install -r requirements-dev.txt
  black app/
  isort app/
  ```

- **Database migrations:** Currently using SQLAlchemy's `create_all()`. For production, consider Alembic.

### Frontend

- **Linting:**
  ```bash
  npm run lint
  ```

- **Production build:**
  ```bash
  npm run build
  npm start
  ```

## Environment Variables

### Backend (`server/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VERTEX_PROJECT_ID` | Yes | - | Google Cloud project ID with Vertex AI enabled |
| `VERTEX_LOCATION` | No | `us-central1` | GCP region for Vertex AI (e.g., us-central1, us-east1) |
| `VERTEX_MODEL` | No | `gemini-1.5-flash` | Gemini model name (gemini-1.5-flash, gemini-1.5-pro) |
| `DATABASE_URL` | No | `sqlite:///./cookclip.db` | Database connection string |
| `YOUTUBE_COOKIE` | No | - | Path to cookies file for restricted videos |
| `ENVIRONMENT` | No | `development` | Environment mode |
| `GOOGLE_APPLICATION_CREDENTIALS` | No* | - | Path to service account JSON (if not using ADC) |

\* Authentication required via either `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS`

### Frontend (`client/.env.local`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | No | `http://localhost:8000` | Backend API base URL |

## Tech Stack

### Backend
- **FastAPI** – Web framework
- **SQLAlchemy** – ORM
- **PostgreSQL/SQLite** – Database
- **Google Vertex AI (Gemini)** – LLM for recipe extraction with enterprise governance
- **youtube-transcript-api** – Transcript fetching
- **Whisper** – Audio transcription fallback
- **yt-dlp** – Video/audio download

### Frontend
- **Next.js 14** – React framework (App Router)
- **TypeScript** – Type safety
- **Tailwind CSS** – Styling
- **React** – UI library

## License

MVP – for demo use only.

