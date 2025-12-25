# CookClip Backend

FastAPI backend for CookClip recipe extraction.

## Installation

### Option 1: Using pip + requirements.txt

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development (includes linting tools)
pip install -r requirements-dev.txt
```

### Option 2: Using Poetry

```bash
poetry install
```

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   - `VERTEX_PROJECT_ID` (required) - Your Google Cloud project ID
   - `VERTEX_LOCATION` (optional, defaults to us-central1)
   - `VERTEX_MODEL` (optional, defaults to gemini-1.5-flash)
   - `DATABASE_URL` (optional, defaults to SQLite)

3. Set up Google Cloud authentication:
   ```bash
   # Option A: Application Default Credentials (recommended for local dev)
   gcloud auth application-default login
   
   # Option B: Service Account Key
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   ```

## Running

```bash
# Activate venv (if using pip)
source .venv/bin/activate

# Or use Poetry shell
poetry shell

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

