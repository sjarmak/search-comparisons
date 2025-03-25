import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.core.config import get_settings, EnvironmentType
from app.core.environment import initialize_environment, apply_platform_specific_fixes
from app.api.routes import router

# Add after the CORS middleware setup
app.include_router(router, prefix=get_settings().API_PREFIX)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Determine environment (can be overridden at runtime)
ENV = os.getenv("APP_ENVIRONMENT", "local").lower()

# Load appropriate .env file
env_files = {
    "local": ".env.local",
    "development": ".env.dev",
    "production": ".env.prod",
}

# Try to load the environment-specific .env file first, then fall back to .env
if ENV in env_files and os.path.exists(env_files[ENV]):
    load_dotenv(env_files[ENV])
else:
    load_dotenv()  # Default to .env

# Apply platform-specific fixes
apply_platform_specific_fixes()

# Initialize environment
initialize_environment()

# Create FastAPI app
app = FastAPI(
    title="Search Engine Comparator",
    description="API for comparing search engine results",
    version="1.0.0",
    debug=get_settings().DEBUG,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "environment": get_settings().ENVIRONMENT}