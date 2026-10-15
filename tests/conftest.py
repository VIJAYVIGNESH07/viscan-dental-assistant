import os
os.environ["GROQ_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.conversation_service import SESSIONS


@pytest.fixture()
def client():
    SESSIONS.clear()
    with TestClient(app) as test_client:
        yield test_client
