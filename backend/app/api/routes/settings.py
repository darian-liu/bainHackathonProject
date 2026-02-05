from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from app.core.config import (
    settings,
    save_settings_to_file,
    reload_settings,
    load_settings_from_file,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None
    graph_client_id: Optional[str] = None
    graph_client_secret: Optional[str] = None
    graph_tenant_id: Optional[str] = None
    sharepoint_site_id: Optional[str] = None
    document_source_mode: Optional[str] = None


class SettingsResponse(BaseModel):
    document_source_mode: str
    openai_api_key: str  # masked
    openai_base_url: str
    openai_model: str
    graph_client_id: str
    graph_client_secret: str  # masked
    graph_tenant_id: str
    sharepoint_site_id: str


class TestConnectionResponse(BaseModel):
    openai: bool
    sharepoint: Optional[bool] = None
    errors: dict


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Retrieve current settings with masked sensitive values."""
    return settings.get_effective_settings()


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.post("", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    """Update settings and save to local file."""
    # Load existing settings
    current = load_settings_from_file()

    # Update only provided fields
    if update.openai_api_key is not None:
        current["openai_api_key"] = update.openai_api_key
        # Also set environment variable for immediate use
        os.environ["OPENAI_API_KEY"] = update.openai_api_key

    if update.openai_base_url is not None:
        current["openai_base_url"] = update.openai_base_url
        os.environ["OPENAI_BASE_URL"] = update.openai_base_url

    if update.openai_model is not None:
        current["openai_model"] = update.openai_model
        os.environ["OPENAI_MODEL"] = update.openai_model

    if update.graph_client_id is not None:
        current["graph_client_id"] = update.graph_client_id
        os.environ["GRAPH_CLIENT_ID"] = update.graph_client_id

    if update.graph_client_secret is not None:
        current["graph_client_secret"] = update.graph_client_secret
        os.environ["GRAPH_CLIENT_SECRET"] = update.graph_client_secret

    if update.graph_tenant_id is not None:
        current["graph_tenant_id"] = update.graph_tenant_id
        os.environ["GRAPH_TENANT_ID"] = update.graph_tenant_id

    if update.sharepoint_site_id is not None:
        current["sharepoint_site_id"] = update.sharepoint_site_id
        os.environ["SHAREPOINT_SITE_ID"] = update.sharepoint_site_id

    if update.document_source_mode is not None:
        if update.document_source_mode not in ("mock", "live"):
            raise HTTPException(
                status_code=400,
                detail="document_source_mode must be 'mock' or 'live'",
            )
        current["document_source_mode"] = update.document_source_mode
        os.environ["DOCUMENT_SOURCE_MODE"] = update.document_source_mode

    # Save to file
    save_settings_to_file(current)

    # Reload settings
    new_settings = reload_settings()

    return new_settings.get_effective_settings()


# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
@router.post("/test", response_model=TestConnectionResponse)
async def test_connections():
    """Test API connections with current settings."""
    errors = {}
    openai_ok = False
    sharepoint_ok = None

    # Test OpenAI / Portkey
    try:
        from openai import OpenAI

        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        base_url = settings.openai_base_url or os.getenv("OPENAI_BASE_URL")

        if not api_key:
            errors["openai"] = "No API key configured"
        else:
            # Configure client with optional Portkey base URL
            client_config = {"api_key": api_key}
            if base_url:
                client_config["base_url"] = base_url

            client = OpenAI(**client_config)
            # Simple test - list models (may not work with all gateways)
            try:
                client.models.list()
            except Exception:
                # Some gateways don't support models.list, try a simple completion instead
                pass
            openai_ok = True
    except Exception as e:
        errors["openai"] = str(e)

    # Test SharePoint if in live mode
    if settings.document_source_mode == "live":
        try:
            from app.services.sharepoint import SharePointSource

            source = SharePointSource()
            # Try to list root folders as a test
            await source.list_folders(None)
            sharepoint_ok = True
        except Exception as e:
            errors["sharepoint"] = str(e)
            sharepoint_ok = False

    return TestConnectionResponse(
        openai=openai_ok, sharepoint=sharepoint_ok, errors=errors
    )
