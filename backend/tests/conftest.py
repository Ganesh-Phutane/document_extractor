# tests/conftest.py
# Shared pytest fixtures — populated in Step 3 and beyond.
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI test client — use this in all route tests."""
    with TestClient(app) as c:
        yield c
