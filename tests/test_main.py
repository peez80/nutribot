import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

def test_index_route(tmp_path):
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=lambda: "<html>Mock</html>"))))):
        response = client.get("/")
        assert response.status_code == 200
        assert "Mock" in response.text

@patch("app.main.create_session")
def test_create_session_endpoint(mock_create):
    mock_create.return_value = "sess-123"
    response = client.post("/api/sessions")
    assert response.status_code == 200
    assert response.json() == {"id": "sess-123", "title": "Neuer Chat"}
    mock_create.assert_called_once_with("Neuer Chat")

@patch("app.main.get_sessions")
def test_get_sessions_endpoint(mock_get):
    mock_get.return_value = [{"id": "1", "title": "Chat 1"}]
    response = client.get("/api/sessions")
    assert response.status_code == 200
    assert response.json() == [{"id": "1", "title": "Chat 1"}]

@patch("app.main.get_session_history")
def test_get_history_endpoint(mock_history):
    mock_history.return_value = [{"text": "Hi", "is_user": True, "image_urls": []}]
    response = client.get("/api/sessions/sess-123/history")
    assert response.status_code == 200
    assert response.json() == [{"text": "Hi", "is_user": True, "image_urls": []}]

@patch("app.main.agy_client")
@patch("app.main.save_entry")
@patch("app.main.get_session_history")
@patch("app.main.save_session_message")
@patch("app.main.get_sessions")
@patch("app.main.update_session_title")
def test_chat_endpoint_text_only(mock_update_title, mock_get_sessions, mock_save_msg, mock_get_history, mock_save_entry, mock_agy_client):
    mock_get_history.return_value = []
    # Mock get_sessions to return a session with "Neuer Chat" title to test auto-rename
    mock_get_sessions.return_value = [{"id": "sess-123", "title": "Neuer Chat"}]
    
    mock_response = {
        "type": "meal",
        "data": {"food": "Pizza"},
        "reply": "Pizza wurde erfasst.",
        "context_truncated": False
    }
    mock_agy_client.process_message.return_value = mock_response
    
    response = client.post("/api/sessions/sess-123/chat", data={"message": "Ich habe Pizza gegessen"})
    
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["reply"] == "Pizza wurde erfasst."
    assert json_resp["parsed"]["type"] == "meal"
    
    # Verify save_entry was called
    mock_save_entry.assert_called_once_with("meal", "Ich habe Pizza gegessen", {"food": "Pizza"})
    
    # Verify agy_client was called
    mock_agy_client.process_message.assert_called_once()
    args, kwargs = mock_agy_client.process_message.call_args
    assert args[1] == "Ich habe Pizza gegessen"
    assert args[2] == []  # image_paths
    
    # Verify title update
    mock_update_title.assert_called_once_with("sess-123", "Ich habe Pizza gegessen")
    
    # Verify messages saved
    assert mock_save_msg.call_count == 2
    user_msg_call = mock_save_msg.call_args_list[0][0][1]
    assert user_msg_call["text"] == "Ich habe Pizza gegessen"
    assert user_msg_call["is_user"] is True

@patch("app.main.agy_client")
@patch("app.main.save_entry")
@patch("app.main.get_session_history")
@patch("app.main.save_session_message")
@patch("app.main.get_sessions")
def test_chat_endpoint_with_image(mock_get_sessions, mock_save_msg, mock_get_history, mock_save_entry, mock_agy_client):
    mock_get_history.return_value = []
    mock_get_sessions.return_value = [{"id": "sess-123", "title": "Existing Chat"}] # No rename

    mock_response = {
        "type": "meal",
        "data": {"food": "Pizza"},
        "reply": "Bild der Pizza wurde erfasst."
    }
    mock_agy_client.process_message.return_value = mock_response
    
    files = [('images', ('test.jpg', b'dummy_image_data', 'image/jpeg'))]
    data = {'message': 'Hier ist mein Essen'}
    
    response = client.post("/api/sessions/sess-123/chat", data=data, files=files)
    
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["reply"] == "Bild der Pizza wurde erfasst."
    
    mock_agy_client.process_message.assert_called_once()
    args, kwargs = mock_agy_client.process_message.call_args
    assert len(args[2]) == 1
    assert args[2][0].endswith(".jpg")

@patch("app.main.get_sessions")
def test_chat_endpoint_too_many_images(mock_get_sessions):
    mock_get_sessions.return_value = [{"id": "sess-123", "title": "Chat"}]
    files = []
    for i in range(6):
        files.append(('images', (f'test{i}.jpg', b'data', 'image/jpeg')))
    
    response = client.post("/api/sessions/sess-123/chat", data={'message': 'Zu viele'}, files=files)
    
    assert response.status_code == 400
    assert response.json()["error"] == "Maximal 5 Bilder erlaubt"

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

@patch("app.main.delete_session")
@patch("app.main.get_sessions")
def test_delete_session_endpoint(mock_get_sessions, mock_delete_session):
    mock_get_sessions.return_value = [{"id": "sess-123", "title": "Test"}]
    
    response = client.delete("/api/sessions/sess-123")
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_delete_session.assert_called_once_with("sess-123")
    
    # Test not found
    response = client.delete("/api/sessions/unknown")
    assert response.status_code == 404
