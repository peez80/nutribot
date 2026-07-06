import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import app *after* any env setup if needed, but it's safe here
from app.main import app

client = TestClient(app)

def test_index_route(tmp_path):
    # Testing index route when static/index.html is mocked
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=lambda: "<html>Mock</html>"))))):
        response = client.get("/")
        assert response.status_code == 200
        assert "Mock" in response.text

@patch("app.main.agy_client")
@patch("app.main.save_entry")
def test_chat_endpoint_text_only(mock_save_entry, mock_agy_client):
    # Mock the response from agy client
    mock_response = {
        "type": "meal",
        "data": {"food": "Pizza"},
        "reply": "Pizza wurde erfasst."
    }
    mock_agy_client.process_message.return_value = mock_response
    
    response = client.post("/api/chat", data={"message": "Ich habe Pizza gegessen"})
    
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["reply"] == "Pizza wurde erfasst."
    assert json_resp["parsed"]["type"] == "meal"
    
    # Verify save_entry was called
    mock_save_entry.assert_called_once_with("meal", "Ich habe Pizza gegessen", {"food": "Pizza"})
    
    # Verify agy_client was called correctly (image_path should be None)
    mock_agy_client.process_message.assert_called_once()
    args, kwargs = mock_agy_client.process_message.call_args
    assert args[1] == "Ich habe Pizza gegessen"
    assert args[2] is None  # image_path
    
@patch("app.main.agy_client")
@patch("app.main.save_entry")
def test_chat_endpoint_with_image(mock_save_entry, mock_agy_client):
    mock_response = {
        "type": "meal",
        "data": {"food": "Pizza"},
        "reply": "Bild der Pizza wurde erfasst."
    }
    mock_agy_client.process_message.return_value = mock_response
    
    # Create a dummy image file
    files = {'image': ('test.jpg', b'dummy_image_data', 'image/jpeg')}
    data = {'message': 'Hier ist mein Essen'}
    
    response = client.post("/api/chat", data=data, files=files)
    
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["reply"] == "Bild der Pizza wurde erfasst."
    
    # Check that process_message was called with a path
    mock_agy_client.process_message.assert_called_once()
    args, kwargs = mock_agy_client.process_message.call_args
    assert args[1] == "Hier ist mein Essen"
    assert args[2] is not None
    assert args[2].endswith(".jpg")

@patch("app.main.agy_client")
def test_auth_endpoints(mock_agy_client):
    mock_agy_client.is_authenticated.return_value = True
    mock_agy_client.get_login_url.return_value = "https://mock.login"
    mock_agy_client.submit_auth_code.return_value = True
    
    resp_status = client.get("/api/auth/status")
    assert resp_status.status_code == 200
    assert resp_status.json() == {"authenticated": True}
    
    resp_start = client.post("/api/auth/start")
    assert resp_start.status_code == 200
    assert resp_start.json() == {"url": "https://mock.login"}
    
    resp_verify = client.post("/api/auth/verify", json={"code": "12345"})
    assert resp_verify.status_code == 200
    assert resp_verify.json() == {"success": True}
