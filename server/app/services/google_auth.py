"""
Google OAuth authentication service.
"""
import logging
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from ..config import get_settings

logger = logging.getLogger(__name__)


def exchange_code_for_token(authorization_code: str) -> Optional[dict]:
    """
    Exchange Google OAuth authorization code for ID token.
    
    Returns:
        dict with keys: 'sub' (user ID), 'email', 'name', 'picture' or None if invalid
    """
    settings = get_settings()
    
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        logger.warning("Google OAuth not configured")
        return None
    
    try:
        # Create flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.google_oauth_redirect_uri or ""],
                }
            },
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        )
        flow.redirect_uri = settings.google_oauth_redirect_uri
        
        # Exchange code for token
        flow.fetch_token(code=authorization_code)
        
        # Get ID token from credentials
        credentials = flow.credentials
        id_token_str = credentials.id_token
        
        if not id_token_str:
            logger.warning("No ID token in response")
            return None
        
        # Verify and decode ID token
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            Request(),
            settings.google_oauth_client_id
        )
        
        # Verify the issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        return {
            'sub': idinfo['sub'],  # Google user ID
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture'),
        }
    except ValueError as e:
        logger.warning("Invalid Google token: %s", e)
        return None
    except Exception as e:
        logger.exception("Error exchanging Google code: %s", e)
        return None
