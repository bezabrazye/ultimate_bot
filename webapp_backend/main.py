# webapp_backend/main.py
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware # For CORS if your TMA is hosted separately
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import logging

# Project imports for DB and Service
from config.settings import settings
from database.db import MongoDB
from database.repositories import UserRepository
from services.webapp_service import WebAppService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Telegram Mini App Backend",
    description="Backend for handling Telegram Mini App data (IP, InitData etc.)",
    version="1.0.0",
)

# CORS Middleware for development
# Allows calls from any origin (*), useful for local testing or if TMA is on different domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust to specific origins in production, e.g., ["https://your-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB connection and service initialization
mongo_db_instance = MongoDB()
@app.on_event("startup")
async def startup_event():
    await mongo_db_instance.connect()
    app.extra["user_repo"] = UserRepository(mongo_db_instance.db)
    app.extra["webapp_service"] = WebAppService(app.extra["user_repo"])
    logger.info("FastAPI backend started.")

@app.on_event("shutdown")
async def shutdown_event():
    await mongo_db_instance.close()
    logger.info("FastAPI backend shut down.")

# Mount static files – this serves your index.html and any other static assets
# __file__ gives path to main.py, so parent.parent is ultimate_bot/
current_dir = os.path.dirname(os.path.abspath(__file__))
tma_app_path = os.path.join(current_dir, "tma_app")
app.mount(settings.WEBAPP_FRONTEND_PATH, StaticFiles(directory=tma_app_path, html=True), name="tma_app")
logger.info(f"Serving static files from {tma_app_path} at {settings.WEBAPP_FRONTEND_PATH}")

class WebAppAuthData(BaseModel):
    initData: str

@app.post("/api/v1/webapp/auth")
async def process_webapp_auth(data: WebAppAuthData, request: Request):
    """
    Receives initData from Telegram Mini App and processes it.
    Also captures the client's IP address.
    """
    client_ip = request.client.host # Get the client's IP address
    if not client_ip:
        logger.warning(f"Could not get client IP for initData request.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not determine client IP.")

    webapp_service: WebAppService = app.extra["webapp_service"]
    
    success = await webapp_service.process_webapp_auth_data(data.initData, client_ip)

    if success:
        return {"status": "success", "message": "User data updated successfully."}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to process WebApp data.")

@app.get("/heartbeat")
async def heartbeat():
    """Simple endpoint to check if the server is running."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# To run this file: uvicorn main:app --reload --port 8000
# From the webapp_backend directory.