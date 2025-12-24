# CookClip Frontend

Next.js frontend for CookClip.

## Installation

```bash
npm install
```

## Environment Setup

1. Copy `env.example` to `.env.local`:
   ```bash
   cp env.example .env.local
   ```

2. Edit `.env.local` and set `NEXT_PUBLIC_API_BASE_URL` to match your backend URL.

## Running

```bash
# Development
npm run dev

# Production build
npm run build
npm start
```

The app will be available at `http://localhost:3000`

## Dependencies

All dependencies are managed via `package.json`. Install with `npm install`.

