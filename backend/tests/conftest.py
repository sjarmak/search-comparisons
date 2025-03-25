import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app after path adjustment
from app.main import app

@pytest.fixture
def client():
    """Test client for the FastAPI application."""
    return TestClient(app)