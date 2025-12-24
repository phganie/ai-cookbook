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
   - `OPENAI_API_KEY` (required)
   - `DATABASE_URL` (optional, defaults to SQLite)

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

