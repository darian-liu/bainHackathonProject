from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

from app.api.routes import data_room, settings, expert_networks, outlook
from app.api import websocket
from app.core.config import settings as app_settings
from app.db.database import connect_db, disconnect_db

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Bain Productivity Tool API",
    version="1.0.0",
    description="Backend API for the Bain Productivity Tool"
)

# Attach limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# TODO: [SECURITY] Add authentication middleware before production deployment
# See: https://fastapi.tiangolo.com/tutorial/security/
# Options to consider:
# - OAuth2 with JWT tokens
# - API key authentication
# - Session-based authentication

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_room.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(expert_networks.router, prefix="/api")
app.include_router(outlook.router, prefix="/api")
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "name": "Bain Productivity Tool API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    """Connect to database on startup."""
    await connect_db()


@app.on_event("shutdown")
async def shutdown():
    """Disconnect from database on shutdown."""
    await disconnect_db()
