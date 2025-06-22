# webapp_backend/startup.py
import uvicorn
import os
from fastapi import FastAPI

app = FastAPI()
# Adjust sys.path to include the project root for imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def start_webapp_backend():
    """Function to start the FastAPI web app."""
    # Ensure environment variables are loaded if running directly without dotenv
    # For this project, assume .env is loaded by pydantic-settings
    
    # Get config (optional check)
    from config.settings import settings
    print(f"Starting WebApp backend with base URL: {settings.WEBAPP_BASE_URL} and Frontend Path: {settings.WEBAPP_FRONTEND_PATH}")

    uvicorn.run(
        "webapp_backend.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True # Set to False for production
    )

if __name__ == "__main__":
    start_webapp_backend()
    
@app.get("/")
async def root():
    return {"message": "Backend работает успешно!"}
