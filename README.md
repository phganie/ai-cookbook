# CookClip – Video → Recipe MVP

CookClip turns cooking videos into trustworthy, step-by-step recipes you can actually follow. Paste a YouTube URL, and the app extracts a clean ingredient list and clear instructions—each step linked back to the exact timestamp in the video.

## Features

- 🎥 **Video to Recipe Extraction** – Extract structured recipes from YouTube cooking videos
- 🔐 **User Authentication** – Sign up/login with email/password or Google OAuth
- 💾 **Recipe Library** – Save and organize your favorite recipes
- 🤖 **Ask AI** – Get answers to questions about recipes using AI
- ✅ **Interactive Cook Mode** – Check off ingredients and steps as you cook
- 📊 **Password Strength Validation** – Real-time password strength feedback
- 🎯 **Smart Fallbacks** – Automatic fallback to audio transcription when captions aren't available

## Project Structure

```
cookbook/
├── server/          # FastAPI backend (Python)
│   ├── app/
│   │   ├── models.py          # Database models (User, Recipe)
│   │   ├── schemas/           # Pydantic schemas (auth, recipe)
│   │   ├── services/          # Business logic (auth, LLM, recipes, etc.)
│   │   └── main.py            # FastAPI app entry point
│   └── requirements.txt       # Python dependencies
├── client/          # Next.js frontend (TypeScript + Tailwind)
│   ├── app/
│   │   ├── auth/              # Authentication pages (login, signup)
│   │   ├── components/        # React components
│   │   ├── contexts/          # React contexts (AuthContext)
│   │   └── page.tsx           # Home page
│   └── package.json           # Node.js dependencies
├── shared/          # Shared TypeScript types
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
   # Create .env file in server/ directory
   # Add your configuration:
   
   # Required: Vertex AI
   VERTEX_PROJECT_ID=your-gcp-project-id
   VERTEX_LOCATION=us-central1
   VERTEX_MODEL=gemini-2.0-flash
   
   # Optional: Database (defaults to SQLite)
   DATABASE_URL=postgresql+psycopg2://username@localhost:5432/cookclip
   # or leave unset to use: sqlite:///./cookclip.db
   
   # Required: Authentication
   SECRET_KEY=your-very-long-random-secret-key-at-least-32-characters
   
   # Optional: Google OAuth (for Google sign-in)
   GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/auth/google/callback
   
   # Optional: Audio transcription fallback
   ENABLE_AUDIO_FALLBACK=0  # Set to 1 to enable
   GCP_PROJECT_ID=your-gcp-project-id  # Reuses VERTEX_PROJECT_ID if not set
   ```
   
   **Note:** See `GOOGLE_OAUTH_SETUP.md` for detailed Google OAuth setup instructions.

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

#### Authentication (Public)
- **`POST /api/auth/signup`** – Register new user
  - Body: `{ "email": "user@example.com", "password": "..." }`
  - Returns: JWT token and user info

- **`POST /api/auth/login`** – Login with email/password
  - Body: `{ "email": "user@example.com", "password": "..." }`
  - Returns: JWT token and user info

- **`POST /api/auth/token`** – OAuth2 compatible token endpoint (form data)
  - Form data: `username` (email), `password`
  - Returns: JWT token and user info

- **`GET /api/auth/me`** – Get current user info (requires authentication)
  - Headers: `Authorization: Bearer <token>`
  - Returns: User object

- **`GET /api/auth/google/url`** – Get Google OAuth authorization URL
  - Returns: `{ "auth_url": "..." }`

- **`POST /api/auth/google`** – Handle Google OAuth callback
  - Body: `{ "code": "...", "redirect_uri": "..." }`
  - Returns: JWT token and user info

#### Recipe Extraction (Public)
- **`POST /api/extract`** – Extract recipe from YouTube URL
  - Body: `{ "url": "https://youtube.com/watch?v=..." }`
  - Returns: Structured recipe JSON with ingredients, steps, timestamps, and video metadata

- **`POST /api/extract/ask`** – Ask AI about extracted recipe (before saving)
  - Body: `{ "recipe": {...}, "transcript": "...", "question": "..." }`
  - Returns: `{ "answer": "..." }`

#### Recipes (Protected - requires authentication)
- **`POST /api/recipes`** – Save recipe to database
  - Headers: `Authorization: Bearer <token>`
  - Body: `{ "source_url": "...", "source_platform": "youtube", "data": {...}, "transcript": "..." }`
  - Returns: Saved recipe with ID

- **`GET /api/recipes`** – List all saved recipes for current user
  - Headers: `Authorization: Bearer <token>`
  - Returns: Array of recipe objects

- **`GET /api/recipes/:id`** – Get single recipe by ID
  - Headers: `Authorization: Bearer <token>`
  - Returns: Recipe object

- **`DELETE /api/recipes/:id`** – Delete recipe by ID
  - Headers: `Authorization: Bearer <token>`
  - Returns: Success message

- **`GET /api/recipes/by-url`** – Find recipe by source URL
  - Headers: `Authorization: Bearer <token>`
  - Query: `?source_url=...`
  - Returns: `{ "id": "..." }` or `{ "id": null }`

- **`POST /api/recipes/:id/ask`** – Ask AI about saved recipe
  - Headers: `Authorization: Bearer <token>`
  - Body: `{ "recipe_id": "...", "question": "..." }`
  - Returns: `{ "answer": "..." }`

## Frontend Pages

- **`/`** – Home page: Paste YouTube URL, extract recipe, preview, and save
  - Extract recipes from YouTube videos
  - View recipe with ingredients and steps
  - Ask AI questions about the recipe
  - Save to library (requires login)

- **`/auth/login`** – Login page
  - Email/password login
  - Google OAuth sign-in option
  - Password strength validation

- **`/auth/signup`** – Sign up page
  - Email/password registration with password strength validation
  - Real-time password matching validation
  - Show/hide password toggles
  - Google OAuth sign-up option

- **`/auth/google/callback`** – Google OAuth callback handler

- **`/library`** – Recipe library (requires authentication)
  - Browse all saved recipes
  - Quick access to recipe details

- **`/recipes/[id]`** – Recipe detail page (requires authentication)
  - View full recipe with ingredients and steps
  - Interactive checkboxes for ingredients and steps
  - Ask AI questions about the recipe
  - Jump to video timestamps

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
| `VERTEX_LOCATION` | No | `us-central1` | GCP region for Vertex AI |
| `VERTEX_MODEL` | No | `gemini-2.0-flash` | Gemini model name |
| `DATABASE_URL` | No | `sqlite:///./cookclip.db` | Database connection string |
| `SECRET_KEY` | Yes | - | Secret key for JWT tokens (min 32 characters) |
| `GOOGLE_OAUTH_CLIENT_ID` | No | - | Google OAuth client ID (for Google sign-in) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | No | - | Google OAuth client secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | No | - | Google OAuth redirect URI |
| `ENABLE_AUDIO_FALLBACK` | No | `0` | Set to `1` to enable audio transcription fallback |
| `GCP_PROJECT_ID` | No | - | GCP project for Speech-to-Text (reuses VERTEX_PROJECT_ID) |
| `GCP_LOCATION` | No | `us-central1` | GCP location for Speech-to-Text |
| `STT_LANGUAGE_CODE` | No | `en-US` | Language code for transcription |
| `STT_MODEL` | No | - | Speech-to-Text model (e.g., `latest_long`) |
| `STT_MAX_AUDIO_SECONDS` | No | `600` | Maximum audio duration in seconds |
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
- **Google Cloud Speech-to-Text** – Audio transcription fallback
- **yt-dlp** – Video/audio download and metadata extraction
- **python-jose** – JWT token handling
- **passlib[bcrypt]** – Password hashing
- **google-auth-oauthlib** – Google OAuth integration
- **Pydantic** – Data validation and settings management

### Frontend
- **Next.js 14** – React framework (App Router)
- **TypeScript** – Type safety
- **Tailwind CSS** – Styling
- **React** – UI library
- **zxcvbn** – Password strength validation

## Authentication

CookClip supports two authentication methods:

1. **Email/Password** – Traditional signup with password requirements:
   - Minimum 8 characters
   - At least one uppercase letter
   - At least one lowercase letter
   - At least one number
   - At least one special character
   - Real-time password strength validation using zxcvbn

2. **Google OAuth** – Sign in with Google account
   - See `GOOGLE_OAUTH_SETUP.md` for setup instructions
   - Automatically links Google accounts to existing email accounts if email matches

All recipe-related endpoints require authentication. Users can only access their own saved recipes.

## Password Security

- Passwords are hashed using bcrypt
- Real-time password strength feedback during signup
- Password matching validation for confirm password field
- Show/hide password toggles for better UX

## Additional Resources

- **Google OAuth Setup**: See `GOOGLE_OAUTH_SETUP.md` for detailed Google OAuth configuration
- **Backend Documentation**: See `server/README.md` for backend-specific details
- **Testing**: See `server/app/tests/` for test examples

## License

MVP – for demo use only.

