from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # Document source
    document_source_mode: str = "mock"
    
    # OpenAI
    openai_api_key: str = ""
    
    # MS Graph (for live mode)
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant_id: str = ""
    sharepoint_site_id: str = ""
    
    # Server
    backend_port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173"]
    
    # Agent
    use_simple_agent: bool = False
    
    class Config:
        env_file = ".env"
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Handle CORS_ORIGINS as JSON string from env
        import os
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            try:
                self.cors_origins = json.loads(cors_env)
            except json.JSONDecodeError:
                pass


settings = Settings()
