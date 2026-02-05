from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
from pathlib import Path
import json
import os


SETTINGS_FILE = Path(__file__).parent.parent.parent / "settings.json"


def load_settings_from_file() -> dict:
    """Load settings from JSON file if exists."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_settings_to_file(settings: dict) -> None:
    """Save settings to JSON file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


class Settings(BaseSettings):
    # Document source
    document_source_mode: str = "mock"

    # OpenAI / Portkey
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"  # Faster model for extraction, 3-5x faster than gpt-4o

    # MS Graph (for live mode)
    graph_client_id: str = ""
    graph_client_secret: str = ""
    graph_tenant_id: str = ""
    sharepoint_site_id: str = ""

    # Legacy aliases for MS Graph (maps azure_* to graph_*)
    azure_client_id: str = Field(default="", alias="azure_client_id")
    azure_client_secret: str = Field(default="", alias="azure_client_secret")
    azure_tenant_id: str = Field(default="", alias="azure_tenant_id")

    # Personal Outlook Integration
    outlook_client_id: str = ""
    outlook_client_secret: str = ""
    outlook_redirect_uri: str = "http://localhost:8000/api/outlook/callback"
    outlook_allowed_sender_domains: str = ""  # Comma-separated, for future email scanning
    outlook_network_keywords: str = ""  # Comma-separated, for future network detection

    # Server
    backend_port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173"]

    # Agent
    use_simple_agent: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"
        populate_by_name = True

    def __init__(self, **kwargs):
        # Load from settings file first
        file_settings = load_settings_from_file()

        # Merge: kwargs > file_settings > env vars (handled by pydantic)
        merged = {**file_settings, **kwargs}

        super().__init__(**merged)

        # Handle CORS_ORIGINS as JSON string from env
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            try:
                self.cors_origins = json.loads(cors_env)
            except json.JSONDecodeError:
                pass

        # Map legacy azure_* names to graph_* if graph_* not set
        if not self.graph_client_id and self.azure_client_id:
            self.graph_client_id = self.azure_client_id
        if not self.graph_client_secret and self.azure_client_secret:
            self.graph_client_secret = self.azure_client_secret
        if not self.graph_tenant_id and self.azure_tenant_id:
            self.graph_tenant_id = self.azure_tenant_id

    def get_effective_settings(self) -> dict:
        """Get current effective settings (for API response)."""
        return {
            "document_source_mode": self.document_source_mode,
            "openai_api_key": self._mask_key(self.openai_api_key),
            "openai_base_url": self.openai_base_url,
            "openai_model": self.openai_model,
            "graph_client_id": self.graph_client_id,
            "graph_client_secret": self._mask_key(self.graph_client_secret),
            "graph_tenant_id": self.graph_tenant_id,
            "sharepoint_site_id": self.sharepoint_site_id,
            "outlook_client_id": self.outlook_client_id,
            "outlook_client_secret": self._mask_key(self.outlook_client_secret),
            "outlook_redirect_uri": self.outlook_redirect_uri,
            "outlook_allowed_sender_domains": self.outlook_allowed_sender_domains,
            "outlook_network_keywords": self.outlook_network_keywords,
        }

    def _mask_key(self, key: str) -> str:
        """Mask a secret key for display."""
        if not key:
            return ""
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + "*" * (len(key) - 8) + key[-4:]


def reload_settings() -> "Settings":
    """Reload settings from file and environment."""
    global settings
    settings = Settings()
    return settings


settings = Settings()
