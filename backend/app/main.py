import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env relative to this file so it works regardless of CWD.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Base, engine, _run_migrations
from app.api import router as api_router
from app.db import models  # ensures all models are registered

logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Create all tables, then apply any additive column migrations.
Base.metadata.create_all(bind=engine)
_run_migrations()

# Log which job-board providers are active so startup issues are obvious.
from app.services.job_board_client import _enabled_providers
_active = _enabled_providers()
_log.info("Job board providers enabled at startup: %s", _active or ["(none — no API keys found)"])

