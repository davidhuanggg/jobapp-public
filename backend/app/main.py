from fastapi import FastAPI
from app.db.database import Base, engine
from app.api import router as api_router
from app.db import models  # ensures all models are registered

app = FastAPI()
app.include_router(api_router)

# Create all tables
Base.metadata.create_all(bind=engine)

