"""Outlook email integration service using MS Graph API.

Handles OAuth flow for personal Microsoft accounts and Graph API interactions.
"""

import httpx
from typing import Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlencode

import app.core.config as config_module


class OutlookService:
    """Service for OAuth and Graph API interactions with personal Outlook accounts."""
    
    # Use 'consumers' endpoint for personal Microsoft accounts
    AUTHORITY = "https://login.microsoftonline.com/consumers"
    
    # Delegated permissions for personal accounts
    SCOPES = ["User.Read", "Mail.Read", "offline_access"]
    
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    
    def __init__(self):
        self._client_id = None
        self._client_secret = None
        self._redirect_uri = None
    
    @property
    def client_id(self) -> str:
        """Get client ID from settings (allows runtime updates)."""
        return config_module.settings.outlook_client_id
    
    @property
    def client_secret(self) -> str:
        """Get client secret from settings (allows runtime updates)."""
        return config_module.settings.outlook_client_secret
    
    @property
    def redirect_uri(self) -> str:
        """Get redirect URI from settings (allows runtime updates)."""
        return config_module.settings.outlook_redirect_uri or "http://localhost:8000/api/outlook/callback"
    
    @property
    def allowed_sender_domains(self) -> List[str]:
        """Get allowed sender domains from settings."""
        domains_str = config_module.settings.outlook_allowed_sender_domains or ""
        if not domains_str:
            return []
        return [d.strip().lower() for d in domains_str.split(",") if d.strip()]
    
    @property
    def network_keywords(self) -> List[str]:
        """Get network detection keywords from settings."""
        keywords_str = config_module.settings.outlook_network_keywords or ""
        if not keywords_str:
            # Default keywords for expert networks
            return ["alphasights", "guidepoint", "glg", "tegus", "thirdbridge", "third bridge"]
        return [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
    
    def get_auth_url(self, state: str = "") -> str:
        """
        Generate OAuth authorization URL for user consent.
        
        Args:
            state: Optional state parameter for CSRF protection and return data
            
        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.SCOPES),
            "state": state,
        }
        
        return f"{self.AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Token response with access_token, refresh_token, expires_in
            
        Raises:
            Exception: If token exchange fails
        """
        token_url = f"{self.AUTHORITY}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "scope": " ".join(self.SCOPES),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            result = response.json()
            
            if response.status_code != 200 or "error" in result:
                error_desc = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Token exchange failed: {error_desc}")
            
            return result
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New token response with access_token, refresh_token, expires_in
            
        Raises:
            Exception: If token refresh fails
        """
        token_url = f"{self.AUTHORITY}/oauth2/v2.0/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(self.SCOPES),
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            result = response.json()
            
            if response.status_code != 200 or "error" in result:
                error_desc = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Token refresh failed: {error_desc}")
            
            return result
    
    async def get_user_profile(self, access_token: str) -> dict:
        """
        Get user profile from Graph API (for email and display name).
        
        Args:
            access_token: Valid access token
            
        Returns:
            User profile with mail, displayName, userPrincipalName
            
        Raises:
            Exception: If API call fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GRAPH_URL}/me",
                headers=headers,
                params={"$select": "mail,displayName,userPrincipalName"},
            )
            
            if response.status_code != 200:
                result = response.json()
                error_msg = result.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Failed to get user profile: {error_msg}")
            
            return response.json()
    
    def calculate_token_expiry(self, expires_in: int) -> datetime:
        """
        Calculate token expiry datetime from expires_in seconds.
        
        Args:
            expires_in: Seconds until token expires
            
        Returns:
            Datetime when token expires
        """
        return datetime.utcnow() + timedelta(seconds=expires_in)
    
    def is_token_expired(self, expires_at: datetime, buffer_seconds: int = 300) -> bool:
        """
        Check if token is expired or will expire soon.
        
        Args:
            expires_at: Token expiry datetime
            buffer_seconds: Consider expired if within this many seconds of expiry
            
        Returns:
            True if token is expired or expiring soon
        """
        return datetime.utcnow() >= (expires_at - timedelta(seconds=buffer_seconds))
    
    # ============== EMAIL SCANNING ============== #
    
    async def list_messages(
        self,
        access_token: str,
        top: int = 50,
        since: Optional[datetime] = None,
        include_body: bool = False,
        inbox_only: bool = True,
    ) -> List[dict]:
        """
        List messages from user's inbox, ordered newest first.
        
        Args:
            access_token: Valid access token
            top: Maximum number of messages to return
            since: Only return messages received after this datetime
            include_body: If True, include full body in response (avoids second API call)
            inbox_only: If True, only read from Inbox folder (not Sent, Drafts, etc.)
            
        Returns:
            List of message metadata objects with id, subject, from, receivedDateTime, bodyPreview, and optionally body
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Build query parameters
        select_fields = "id,subject,from,receivedDateTime,bodyPreview"
        if include_body:
            select_fields += ",body"
        
        params = {
            "$top": str(top),
            "$orderby": "receivedDateTime desc",
            "$select": select_fields,
        }
        
        # Add date filter if specified
        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"receivedDateTime ge {since_str}"
        
        # Use Inbox folder endpoint or all messages
        if inbox_only:
            endpoint = f"{self.GRAPH_URL}/me/mailFolders/Inbox/messages"
        else:
            endpoint = f"{self.GRAPH_URL}/me/messages"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                endpoint,
                headers=headers,
                params=params,
            )
            
            if response.status_code != 200:
                result = response.json()
                error_msg = result.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Failed to list messages: {error_msg}")
            
            data = response.json()
            return data.get("value", [])
    
    async def get_message_body(self, access_token: str, message_id: str) -> dict:
        """
        Get full message content including body.
        
        Args:
            access_token: Valid access token
            message_id: Outlook message ID
            
        Returns:
            Message object with body content
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        params = {
            "$select": "id,subject,from,receivedDateTime,body",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.GRAPH_URL}/me/messages/{message_id}",
                headers=headers,
                params=params,
            )
            
            if response.status_code != 200:
                result = response.json()
                error_msg = result.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Failed to get message: {error_msg}")
            
            return response.json()
    
    def filter_messages_by_sender_domain(
        self,
        messages: List[dict],
        allowed_domains: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Filter messages to only those from allowed sender domains.
        
        Args:
            messages: List of message objects
            allowed_domains: List of allowed domains (e.g., ['alphasights.com', 'guidepoint.com'])
                           If None or empty, uses domains from settings
            
        Returns:
            Filtered list of messages
        """
        domains = allowed_domains or self.allowed_sender_domains
        if not domains:
            # No domain filter configured - return all messages
            return messages
        
        filtered = []
        for msg in messages:
            sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "").lower()
            for domain in domains:
                if sender_email.endswith(f"@{domain}") or sender_email.endswith(f".{domain}"):
                    filtered.append(msg)
                    break
        
        return filtered
    
    def filter_messages_by_keywords(
        self,
        messages: List[dict],
        keywords: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Filter messages that contain network keywords in subject or body preview.
        
        Args:
            messages: List of message objects
            keywords: List of keywords to search for
                     If None, uses keywords from settings
            
        Returns:
            Filtered list of messages
        """
        kw_list = keywords or self.network_keywords
        if not kw_list:
            return messages
        
        filtered = []
        for msg in messages:
            subject = (msg.get("subject") or "").lower()
            preview = (msg.get("bodyPreview") or "").lower()
            text = f"{subject} {preview}"
            
            for kw in kw_list:
                if kw.lower() in text:
                    filtered.append(msg)
                    break
        
        return filtered
    
    def extract_plain_text_from_body(self, body: dict) -> str:
        """
        Extract plain text from message body.
        
        Args:
            body: Body object with contentType and content
            
        Returns:
            Plain text content
        """
        content_type = body.get("contentType", "text")
        content = body.get("content", "")
        
        if content_type == "html":
            # Simple HTML to text conversion
            import re
            # Remove script and style elements
            text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Decode HTML entities
            import html
            text = html.unescape(text)
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        
        return content
    
    def detect_network_from_email(self, sender_email: str, subject: str, body_preview: str) -> Optional[str]:
        """
        Detect which expert network an email is from.
        
        Args:
            sender_email: Sender's email address
            subject: Email subject
            body_preview: Email body preview
            
        Returns:
            Network name (alphasights, guidepoint, glg, etc.) or None
        """
        text = f"{sender_email} {subject} {body_preview}".lower()
        
        network_patterns = {
            "alphasights": ["alphasights", "alpha-sights"],
            "guidepoint": ["guidepoint", "guide-point"],
            "glg": ["glg", "gerson lehrman"],
            "tegus": ["tegus"],
            "thirdbridge": ["thirdbridge", "third bridge", "third-bridge"],
        }
        
        for network, patterns in network_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return network
        
        return None


# Singleton instance
outlook_service = OutlookService()
