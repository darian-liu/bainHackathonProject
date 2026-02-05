"""Outlook connection database queries."""

from datetime import datetime
from typing import Optional
import databases
import secrets


async def get_active_connection(db: databases.Database) -> Optional[dict]:
    """Get the active Outlook connection (only one allowed)."""
    query = """
        SELECT * FROM OutlookConnection 
        WHERE is_active = 1 
        ORDER BY created_at DESC 
        LIMIT 1
    """
    row = await db.fetch_one(query)
    
    if not row:
        return None
    
    return {
        "id": row["id"],
        "userEmail": row["user_email"],
        "accessToken": row["access_token"],
        "refreshToken": row["refresh_token"],
        "tokenExpiresAt": row["token_expires_at"],
        "lastConnectedAt": row["last_connected_at"],
        "lastTestAt": row["last_test_at"],
        "isActive": bool(row["is_active"]),
        "allowedSenderDomains": row["allowed_sender_domains"],
        "lastSyncAt": row["last_sync_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


async def create_or_update_connection(
    db: databases.Database,
    user_email: str,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime,
    allowed_sender_domains: Optional[str] = None,
) -> dict:
    """Create or update the Outlook connection. Only one active connection allowed."""
    now = datetime.utcnow()
    
    # Deactivate any existing connections first
    await db.execute("UPDATE OutlookConnection SET is_active = 0, updated_at = :now", {"now": now})
    
    # Create new connection
    connection_id = secrets.token_urlsafe(16)
    
    query = """
        INSERT INTO OutlookConnection (
            id, user_email, access_token, refresh_token, token_expires_at,
            last_connected_at, is_active, allowed_sender_domains, created_at, updated_at
        ) VALUES (
            :id, :user_email, :access_token, :refresh_token, :token_expires_at,
            :last_connected_at, 1, :allowed_sender_domains, :created_at, :updated_at
        )
    """
    
    await db.execute(query, {
        "id": connection_id,
        "user_email": user_email,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": token_expires_at.isoformat(),
        "last_connected_at": now.isoformat(),
        "allowed_sender_domains": allowed_sender_domains,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    })
    
    return {
        "id": connection_id,
        "userEmail": user_email,
        "tokenExpiresAt": token_expires_at.isoformat(),
        "lastConnectedAt": now.isoformat(),
        "isActive": True,
        "allowedSenderDomains": allowed_sender_domains,
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat(),
    }


async def update_tokens(
    db: databases.Database,
    connection_id: str,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime,
) -> bool:
    """Update tokens for an existing connection (after refresh)."""
    now = datetime.utcnow()
    
    query = """
        UPDATE OutlookConnection 
        SET access_token = :access_token,
            refresh_token = :refresh_token,
            token_expires_at = :token_expires_at,
            updated_at = :updated_at
        WHERE id = :id
    """
    
    result = await db.execute(query, {
        "id": connection_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": token_expires_at.isoformat(),
        "updated_at": now.isoformat(),
    })
    
    return result > 0


async def update_test_timestamp(db: databases.Database, connection_id: str) -> bool:
    """Update the last_test_at timestamp."""
    now = datetime.utcnow()
    
    query = """
        UPDATE OutlookConnection 
        SET last_test_at = :last_test_at, updated_at = :updated_at
        WHERE id = :id
    """
    
    result = await db.execute(query, {
        "id": connection_id,
        "last_test_at": now.isoformat(),
        "updated_at": now.isoformat(),
    })
    
    return result > 0


async def update_sync_timestamp(db: databases.Database, connection_id: str) -> bool:
    """Update the last_sync_at timestamp (for future email scanning)."""
    now = datetime.utcnow()
    
    query = """
        UPDATE OutlookConnection 
        SET last_sync_at = :last_sync_at, updated_at = :updated_at
        WHERE id = :id
    """
    
    result = await db.execute(query, {
        "id": connection_id,
        "last_sync_at": now.isoformat(),
        "updated_at": now.isoformat(),
    })
    
    return result > 0


async def deactivate_connection(db: databases.Database, connection_id: str) -> bool:
    """Deactivate a connection and clear tokens."""
    now = datetime.utcnow()
    
    query = """
        UPDATE OutlookConnection 
        SET is_active = 0, 
            access_token = '',
            refresh_token = '',
            updated_at = :updated_at
        WHERE id = :id
    """
    
    result = await db.execute(query, {
        "id": connection_id,
        "updated_at": now.isoformat(),
    })
    
    return result > 0


async def deactivate_all_connections(db: databases.Database) -> int:
    """Deactivate all connections and clear tokens."""
    now = datetime.utcnow()
    
    query = """
        UPDATE OutlookConnection 
        SET is_active = 0, 
            access_token = '',
            refresh_token = '',
            updated_at = :updated_at
        WHERE is_active = 1
    """
    
    result = await db.execute(query, {"updated_at": now.isoformat()})
    return result
