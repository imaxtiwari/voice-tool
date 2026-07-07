"""Main entry point for Voice Tool sidecar FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sidecar import config
from sidecar.edit_log import init_db
from sidecar.health import router as health_router
from sidecar.rewrite import router as rewrite_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    # 1. Load config (done automatically via config module import)
    # 2. Initialize SQLite edit log database
    init_db()
    # 3. Log startup message
    print(f"Voice Tool sidecar starting on port {config.SIDECAR_PORT}")
    yield
    # Shutdown tasks (if any)

app = FastAPI(lifespan=lifespan)

# Add CORS middleware with regex for localhost and chrome extension origins
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"^(https?://localhost(:\d+)?|chrome-extension://.*)$",
)

# Register routes
app.include_router(health_router)
app.include_router(rewrite_router)
