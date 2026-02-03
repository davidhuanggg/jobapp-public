from fastapi import FastAPI
from app.db.database import Base, engine
from app.api import router as api_router
from app.db import models  # ensures all models are registered
from app.api_ingestion import router as ingest_router

app = FastAPI()
app.include_router(api_router)
app.include_router(ingest_router)

# Create all tables
Base.metadata.create_all(bind=engine)

