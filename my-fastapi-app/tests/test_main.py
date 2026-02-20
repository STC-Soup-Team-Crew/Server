from unittest.mock import AsyncMock, patch
from io import BytesIO

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---- Existing tests (fixed assertions) ----

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to my FastAPI application!"}


# ---- Image upload endpoint tests ----

def _make_test_image(filename="test.png", content_type="image/png", size=128):
    """Return a tuple suitable for TestClient file uploads."""
    return ("file", (filename, BytesIO(b"\x89PNG" + b"\x00" * size), content_type))


def test_upload_image_unsupported_type():
    """Non-image content types should be rejected with 400."""
    file = ("file", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))
    response = client.post("/api/v1/upload-image/", files=[file])
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@patch("app.api.v1.endpoints.settings")
def test_upload_image_no_api_url(mock_settings):
    """If EXTERNAL_API_URL is not configured, return 500."""
    mock_settings.external_api_url = ""
    mock_settings.external_api_key = ""
    response = client.post("/api/v1/upload-image/", files=[_make_test_image()])
    assert response.status_code == 500
    assert "not configured" in response.json()["detail"]


@patch("app.api.v1.endpoints.httpx.AsyncClient")
@patch("app.api.v1.endpoints.settings")
def test_upload_image_success(mock_settings, mock_async_client_cls):
    """Happy path: image is forwarded and external API JSON is returned."""
    mock_settings.external_api_url = "https://api.example.com/analyze"
    mock_settings.external_api_key = "test-key"

    # Mock the async context-manager and its .post()
    mock_response = AsyncMock()
    mock_response.json.return_value = {"label": "cat", "confidence": 0.97}
    mock_response.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client

    response = client.post("/api/v1/upload-image/", files=[_make_test_image()])
    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "cat"
    assert data["confidence"] == 0.97