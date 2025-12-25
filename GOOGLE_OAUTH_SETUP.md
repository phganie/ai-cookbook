# Google OAuth Setup Guide

This guide will walk you through setting up Google OAuth authentication for CookClip.

## Step 1: Go to Google Cloud Console

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account

## Step 2: Create or Select a Project

1. Click the project dropdown at the top of the page
2. Either:
   - **Select an existing project** (e.g., `ai-cookbook-xxxx` if you already have one)
   - **Create a new project**: Click "New Project" → Enter project name → Click "Create"

## Step 3: Create OAuth 2.0 Credentials

**Note:** You don't need to enable any APIs for basic OAuth 2.0. You can go directly to creating credentials.

## Step 4: Navigate to Credentials

1. In the left sidebar, go to **"APIs & Services"** → **"Credentials"**
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

## Step 5: Configure OAuth Client (Web Application)

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

### Step 1: Update Google Cloud Console OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Find your OAuth 2.0 Client ID (the one you created earlier)
3. Click **Edit** (pencil icon)
4. Add your production URLs:

   **Authorized JavaScript origins:**
   - Click **"+ ADD URI"**
   - Add: `https://your-production-domain.com` (e.g., `https://cookclip.vercel.app`)
   - Keep `http://localhost:3000` for local development

   **Authorized redirect URIs:**
   - Click **"+ ADD URI"**
   - Add: `https://your-production-domain.com/auth/google/callback`
   - Keep `http://localhost:3000/auth/google/callback` for local development

5. Click **SAVE**

### Step 2: Set Environment Variables in Production

#### For Backend (Cloud Run / Server)

Set these environment variables in your deployment platform:

```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
GOOGLE_OAUTH_REDIRECT_URI=https://your-production-domain.com/auth/google/callback
SECRET_KEY=your-strong-secret-key-min-32-characters
```

**Cloud Run Setup:**
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select your service
3. Click **EDIT & DEPLOY NEW REVISION**
4. Go to **Variables & Secrets** tab
5. Add each variable:
   - Click **ADD VARIABLE**
   - Enter variable name and value
   - Click **SAVE**
6. Deploy the new revision

**Or using gcloud CLI:**
```bash
gcloud run services update YOUR_SERVICE_NAME \
  --set-env-vars="GOOGLE_OAUTH_CLIENT_ID=your-client-id,GOOGLE_OAUTH_CLIENT_SECRET=your-secret,GOOGLE_OAUTH_REDIRECT_URI=https://your-domain.com/auth/google/callback" \
  --region=us-central1
```

#### For Frontend (Vercel / Client)

Set this environment variable:

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.run.app
```

**Vercel Setup:**
1. Go to your project on [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Settings** → **Environment Variables**
3. Add:
   - **Name**: `NEXT_PUBLIC_API_BASE_URL`
   - **Value**: `https://your-backend-url.run.app` (your Cloud Run backend URL)
   - **Environment**: Production (and Preview if needed)
4. Click **Save**
5. Redeploy your application (or it will auto-deploy on next push)

### Step 3: Verify Production Setup

1. **Test the OAuth flow:**
   - Visit your production frontend URL
   - Click "Sign Up" or "Login"
   - Click "Sign in with Google"
   - You should be redirected to Google's login page
   - After signing in, you should be redirected back to your app

2. **Common Issues:**

   **"redirect_uri_mismatch" error:**
   - Ensure the redirect URI in Google Cloud Console **exactly matches** the one in your backend environment variables
   - Check for trailing slashes, `http://` vs `https://`, and subdomain mismatches
   - The redirect URI must be the **frontend URL**, not the backend URL

   **"invalid_client" error:**
   - Verify your Client ID and Secret are correct in backend environment variables
   - Make sure there are no extra spaces or quotes

   **CORS errors:**
   - Ensure your backend CORS settings allow your production frontend domain
   - Check `server/app/main.py` CORS configuration

### Step 4: Security Best Practices

1. **Never commit secrets to git:**
   - Use environment variables only
   - Add `.env` to `.gitignore` (should already be there)

2. **Use different OAuth credentials for production:**
   - You can create a separate OAuth client ID for production
   - This allows you to revoke access independently

3. **Rotate secrets regularly:**
   - Update `SECRET_KEY` periodically
   - Regenerate OAuth client secret if compromised

4. **Monitor OAuth usage:**
   - Check Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs
   - Review usage metrics and errors

### Quick Checklist

- [ ] Added production URLs to Google Cloud Console OAuth credentials
- [ ] Set `GOOGLE_OAUTH_CLIENT_ID` in backend environment
- [ ] Set `GOOGLE_OAUTH_CLIENT_SECRET` in backend environment
- [ ] Set `GOOGLE_OAUTH_REDIRECT_URI` in backend environment (production URL)
- [ ] Set `SECRET_KEY` in backend environment (strong, random, 32+ chars)
- [ ] Set `NEXT_PUBLIC_API_BASE_URL` in frontend environment (backend URL)
- [ ] Tested OAuth flow in production
- [ ] Verified CORS settings allow production frontend domain

