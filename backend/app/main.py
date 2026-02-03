from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.api.routes import data_room
from app.api import websocket
from app.core.config import settings

app = FastAPI(
    title="Bain Productivity Tool API",
    version="1.0.0",
    description="Backend API for the Bain Productivity Tool"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(data_room.router, prefix="/api")
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
