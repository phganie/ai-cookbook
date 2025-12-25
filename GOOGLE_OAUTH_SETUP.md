# Google OAuth Setup Guide

This guide will walk you through setting up Google OAuth authentication for CookClip.

## Step 1: Go to Google Cloud Console

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account

## Step 2: Create or Select a Project

1. Click the project dropdown at the top of the page
2. Either:
   - **Select an existing project** (e.g., `ai-cookbook-482307` if you already have one)
   - **Create a new project**: Click "New Project" → Enter project name → Click "Create"

## Step 3: Enable Google+ API (or Google Identity Services)

1. In the left sidebar, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google+ API"** or **"Google Identity Services"**
3. Click on it and click **"Enable"**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"OAuth client ID"**

### If you see "Configure OAuth consent screen" first:
1. Click **"CONFIGURE CONSENT SCREEN"**
2. Choose **"External"** (unless you have a Google Workspace account)
3. Click **"CREATE"**
4. Fill in the required fields:
   - **App name**: `CookClip` (or your app name)
   - **User support email**: Your email
   - **Developer contact email**: Your email
5. Click **"SAVE AND CONTINUE"** through the steps (you can skip optional fields for now)
6. Go back to **"Credentials"** → **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

## Step 5: Configure OAuth Client

1. **Application type**: Select **"Web application"**
2. **Name**: Enter `CookClip Web Client` (or any name)
3. **Authorized JavaScript origins**: 
   - Click **"+ ADD URI"**
   - Add: `http://localhost:3000`
   - (For production, add your production URL)
4. **Authorized redirect URIs**:
   - Click **"+ ADD URI"**
   - Add: `http://localhost:3000/auth/google/callback`
   - (For production, add: `https://yourdomain.com/auth/google/callback`)
5. Click **"CREATE"**

## Step 6: Copy Your Credentials

After creating, you'll see a popup with:
- **Your Client ID** (looks like: `123456789-abcdefghijklmnop.apps.googleusercontent.com`)
- **Your Client Secret** (looks like: `GOCSPX-abcdefghijklmnopqrstuvwxyz`)

**Copy both of these!** You won't be able to see the secret again.

## Step 7: Add to Your .env File

1. Create or edit `.env` file in the `server/` directory
2. Add these lines:

```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/auth/google/callback
```

**Important**: 
- Replace `your-client-id-here` with your actual Client ID
- Replace `your-client-secret-here` with your actual Client Secret
- For production, change `http://localhost:3000` to your production URL

## Step 8: Restart Your Server

After adding the environment variables, restart your FastAPI server:

```bash
cd server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Step 9: Test It

1. Go to your frontend (http://localhost:3000)
2. Click "Sign Up" or "Login"
3. You should see a "Continue with Google" button
4. Click it and you should be redirected to Google's login page

## Troubleshooting

### "503 Service Unavailable" when clicking Google sign-in
- Check that all three environment variables are set correctly
- Make sure there are no extra spaces in your `.env` file
- Restart your server after adding the variables

### "redirect_uri_mismatch" error
- Make sure the redirect URI in your `.env` exactly matches what you added in Google Cloud Console
- Check for trailing slashes or `http://` vs `https://` mismatches

### "invalid_client" error
- Verify your Client ID and Client Secret are correct
- Make sure you copied the entire Client ID (it's long!)

## Production Setup

For production deployment:

1. In Google Cloud Console, add your production URL to:
   - **Authorized JavaScript origins**: `https://yourdomain.com`
   - **Authorized redirect URIs**: `https://yourdomain.com/auth/google/callback`

2. Update your `.env` (or environment variables in your hosting platform):
   ```bash
   GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/auth/google/callback
   ```

3. Make sure your production environment has these variables set!

