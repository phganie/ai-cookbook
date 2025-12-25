# CookClip Backend

FastAPI backend for CookClip recipe extraction using Vertex AI (Gemini).

## Quick Start (Local Development)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (local dev only)
cp .env.example .env
# Edit .env with your VERTEX_PROJECT_ID

# Authenticate for local development
gcloud auth application-default login

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Local Development Setup

### Installation

**Using pip:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

**Using Poetry:**
```bash
poetry install
```

### Environment Variables (`.env`)

The `.env` file is **only used for local development**. Production uses Cloud Run environment variables.

Create `.env` from the example:
```bash
cp .env.example .env
```

Required variables:
- `VERTEX_PROJECT_ID` - Your Google Cloud project ID
- `VERTEX_LOCATION` (optional, default: `us-central1`)
- `VERTEX_MODEL` (optional, default: `gemini-1.5-flash`)
- `DATABASE_URL` (optional, default: `sqlite:///./cookclip.db`)

### Local Authentication

For local development, authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

This sets up Application Default Credentials (ADC) on your machine. **You do not need to download service account keys.**

### Running Locally

```bash
source .venv/bin/activate  # or: poetry shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API available at `http://localhost:8000`

## Production Deployment (Cloud Run)

### Overview

In production, the backend runs on **Google Cloud Run** with automatic authentication via service accounts. No API keys or manual auth required.

### Authentication in Production

**How it works:**
- Cloud Run automatically attaches a service account to your service
- Vertex AI SDK uses Application Default Credentials (ADC)
- Credentials are provided automatically by Cloud Run
- **Zero configuration needed** - no API keys, no service account JSON files

### Deployment

The backend includes a `Dockerfile` for Cloud Run deployment.

**Deploy via Cloud Build (recommended):**
1. Push your code to a Git repository connected to Cloud Build
2. Cloud Build will:
   - Build the Docker image from `Dockerfile`
   - Push to Container Registry
   - Deploy to Cloud Run

**Manual deployment:**
```bash
# Build and deploy
gcloud run deploy cookclip-server \
  --source . \
  --region us-central1 \
  --service-account cookclip-server@PROJECT_ID.iam.gserviceaccount.com
```

### Environment Variables in Production

Set via Cloud Run console or `gcloud`:

- `VERTEX_PROJECT_ID` - Your GCP project ID
- `VERTEX_LOCATION` - Vertex AI region (e.g., `us-central1`)
- `VERTEX_MODEL` - Model name (e.g., `gemini-1.5-flash`)
- `DATABASE_URL` - Database connection string (use Secret Manager for sensitive values)
- `ENVIRONMENT` - Set to `production`

**Note:** The `.env` file is **not used in production**. All configuration comes from Cloud Run environment variables.

## Testing

```bash
# Run all tests
python -m pytest

# Run without Vertex AI integration tests
python -m pytest -m "not vertex_ai"

# Run with coverage
python -m pytest --cov=app --cov-report=html
```

See `app/tests/README.md` for more details.

## Project Structure

```
server/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Settings and environment variables
│   ├── database.py       # SQLAlchemy setup
│   ├── models.py         # Database models
│   ├── schemas.py        # Pydantic schemas
│   ├── services/
│   │   ├── llm.py        # Vertex AI integration
│   │   ├── youtube.py    # YouTube transcript extraction
│   │   └── recipes.py    # Recipe database operations
│   └── tests/            # Test suite
├── Dockerfile            # Production container
├── requirements.txt      # Production dependencies
└── requirements-dev.txt  # Development dependencies
```

## Tech Stack

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **PostgreSQL/SQLite** - Database
- **Google Vertex AI (Gemini)** - LLM for recipe extraction
- **youtube-transcript-api** - YouTube transcript fetching
