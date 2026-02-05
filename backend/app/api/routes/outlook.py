"""Outlook OAuth and connection management routes."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db.database import get_database
from app.db.queries import outlook as outlook_queries
from app.services.outlook_service import outlook_service
import app.core.config as config_module

router = APIRouter(prefix="/outlook", tags=["outlook"])


# ============== Response Models ============== #

class OutlookStatusResponse(BaseModel):
    connected: bool
    userEmail: Optional[str] = None
    lastConnectedAt: Optional[str] = None
    lastTestAt: Optional[str] = None
    lastSyncAt: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    userEmail: Optional[str] = None
    error: Optional[str] = None


class AuthUrlResponse(BaseModel):
    authUrl: str


# ============== Endpoints ============== #

@router.get("/status", response_model=OutlookStatusResponse)
async def get_outlook_status():
    """Get current Outlook connection status."""
    db = await get_database()
    connection = await outlook_queries.get_active_connection(db)
    
    if not connection:
        return OutlookStatusResponse(connected=False)
    
    return OutlookStatusResponse(
        connected=True,
        userEmail=connection["userEmail"],
        lastConnectedAt=connection["lastConnectedAt"],
        lastTestAt=connection["lastTestAt"],
        lastSyncAt=connection["lastSyncAt"],
    )


@router.get("/auth-url", response_model=AuthUrlResponse)
async def get_auth_url(return_path: Optional[str] = Query(default="/settings")):
    """
    Get OAuth authorization URL to start the connection flow.
    
    Args:
        return_path: Frontend path to redirect to after OAuth completes
    """
    # Validate that Outlook credentials are configured
    if not config_module.settings.outlook_client_id or not config_module.settings.outlook_client_secret:
        raise HTTPException(
            status_code=400,
            detail="Outlook credentials not configured. Please set Client ID and Client Secret in Settings first."
        )
    
    # Use return_path as state for redirect after OAuth
    auth_url = outlook_service.get_auth_url(state=return_path or "/settings")
    
    return AuthUrlResponse(authUrl=auth_url)


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """
    OAuth callback endpoint. Microsoft redirects here after user consent.
    
    Exchanges auth code for tokens, fetches user profile, and persists connection.
    Then redirects back to frontend with success/error status.
    """
    # Determine frontend URL for redirect
    frontend_url = "http://localhost:5173"
    return_path = state or "/settings"
    
    # Handle OAuth errors
    if error:
        error_msg = error_description or error
        return RedirectResponse(
            url=f"{frontend_url}{return_path}?outlook_error={error_msg}"
        )
    
    if not code:
        return RedirectResponse(
            url=f"{frontend_url}{return_path}?outlook_error=No authorization code received"
        )
    
    try:
        # Exchange code for tokens
        token_result = await outlook_service.exchange_code_for_tokens(code)
        
        access_token = token_result["access_token"]
        refresh_token = token_result["refresh_token"]
        expires_in = token_result.get("expires_in", 3600)
        token_expires_at = outlook_service.calculate_token_expiry(expires_in)
        
        # Get user profile (email)
        user_profile = await outlook_service.get_user_profile(access_token)
        user_email = user_profile.get("mail") or user_profile.get("userPrincipalName", "unknown")
        
        # Get allowed sender domains from settings (for future scanning)
        allowed_domains = config_module.settings.outlook_allowed_sender_domains or None
        
        # Persist connection
        db = await get_database()
        await outlook_queries.create_or_update_connection(
            db=db,
            user_email=user_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            allowed_sender_domains=allowed_domains,
        )
        
        # Redirect to frontend with success
        return RedirectResponse(
            url=f"{frontend_url}{return_path}?outlook_connected=true"
        )
        
    except Exception as e:
        # Redirect to frontend with error
        error_msg = str(e).replace(" ", "+")
        return RedirectResponse(
            url=f"{frontend_url}{return_path}?outlook_error={error_msg}"
        )


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection():
    """
    Test the Outlook connection by calling Graph API /me endpoint.
    
    Refreshes token if expired, then validates connection.
    """
    db = await get_database()
    connection = await outlook_queries.get_active_connection(db)
    
    if not connection:
        return TestConnectionResponse(
            success=False,
            error="No active Outlook connection. Please connect first."
        )
    
    try:
        access_token = connection["accessToken"]
        refresh_token = connection["refreshToken"]
        token_expires_at = datetime.fromisoformat(connection["tokenExpiresAt"])
        
        # Refresh token if expired or expiring soon
        if outlook_service.is_token_expired(token_expires_at):
            try:
                token_result = await outlook_service.refresh_access_token(refresh_token)
                access_token = token_result["access_token"]
                new_refresh_token = token_result.get("refresh_token", refresh_token)
                expires_in = token_result.get("expires_in", 3600)
                new_expires_at = outlook_service.calculate_token_expiry(expires_in)
                
                # Update tokens in database
                await outlook_queries.update_tokens(
                    db=db,
                    connection_id=connection["id"],
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    token_expires_at=new_expires_at,
                )
            except Exception as e:
                return TestConnectionResponse(
                    success=False,
                    error=f"Token refresh failed: {str(e)}. Please reconnect."
                )
        
        # Test connection by calling /me
        user_profile = await outlook_service.get_user_profile(access_token)
        user_email = user_profile.get("mail") or user_profile.get("userPrincipalName", "unknown")
        
        # Update test timestamp
        await outlook_queries.update_test_timestamp(db, connection["id"])
        
        return TestConnectionResponse(
            success=True,
            userEmail=user_email,
        )
        
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            error=str(e)
        )


@router.post("/disconnect")
async def disconnect_outlook():
    """
    Disconnect Outlook by deactivating the connection and clearing tokens.
    """
    db = await get_database()
    connection = await outlook_queries.get_active_connection(db)
    
    if not connection:
        return {"success": True, "message": "No active connection to disconnect"}
    
    await outlook_queries.deactivate_connection(db, connection["id"])
    
    return {"success": True, "message": "Outlook disconnected successfully"}
