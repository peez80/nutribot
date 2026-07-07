import os
import json
from unittest.mock import patch, mock_open, MagicMock

# New test for user storage initialization
@patch('app.storage.os.makedirs')
def test_init_user_storage(mock_makedirs):
    from app.storage import init_user_storage
    init_user_storage("testuser")
    
    # Check that it creates sessions and uploads directories for the user
    calls = [call.args[0] for call in mock_makedirs.call_args_list]
    assert any("testuser" in path and "sessions" in path for path in calls)
    assert any("testuser" in path and "uploads" in path for path in calls)

@patch('app.storage.os.makedirs')
@patch('app.storage.datetime')
@patch('builtins.open', new_callable=mock_open)
def test_save_entry(mock_file, mock_datetime, mock_makedirs):
    from app.storage import save_entry
    # Setup mocks
    mock_now = MagicMock()
    mock_now.strftime.side_effect = lambda fmt: "2026-07" if fmt == "%Y-%m" else "2026-07-06T120000Z"
    mock_now.isoformat.return_value = "2026-07-06T12:00:00+00:00"
    mock_datetime.now.return_value = mock_now
    
    # Test execution
    username = "testuser"
    entry_type = "meal"
    raw_input = "Ich habe einen Apfel gegessen."
    structured_data = {"food": "Apfel"}
    
    filepath = save_entry(username, entry_type, raw_input, structured_data)
    
    # Assertions
    mock_makedirs.assert_called_once()
    assert mock_makedirs.call_args[0][0].endswith(os.path.join("testuser", "2026-07")) or "testuser" in mock_makedirs.call_args[0][0]
    
    assert "testuser" in filepath
    assert filepath.endswith("2026-07-06T120000Z_meal.json")
    
    # Verify file was written
    mock_file.assert_called_once_with(filepath, "w", encoding="utf-8")
    
    # Verify content
    handle = mock_file()
    written_data = "".join([call.args[0] for call in handle.write.call_args_list])
    
    loaded_data = json.loads(written_data)
    assert loaded_data["type"] == "meal"
    assert loaded_data["timestamp"] == "2026-07-06T12:00:00+00:00"
    assert loaded_data["raw_input"] == raw_input
    assert loaded_data["data"] == structured_data

@patch('app.storage.os.path.exists')
@patch('app.storage.uuid.uuid4')
@patch('app.storage.datetime')
@patch('builtins.open', new_callable=mock_open)
def test_create_session(mock_file, mock_datetime, mock_uuid, mock_exists):
    from app.storage import create_session
    mock_uuid.return_value.hex = "12345"
    mock_exists.return_value = True
    
    mock_now = MagicMock()
    mock_now.isoformat.return_value = "2026-07-06T12:00:00+00:00"
    mock_datetime.now.return_value = mock_now
    
    username = "testuser"
    session_id = create_session(username, "Test Chat")
    
    assert session_id == "12345"
    mock_file.assert_called_once()
    assert "testuser" in mock_file.call_args[0][0]
    assert mock_file.call_args[0][0].endswith("session_12345.json")
    
    handle = mock_file()
    written_data = "".join([call.args[0] for call in handle.write.call_args_list])
    loaded_data = json.loads(written_data)
    
    assert loaded_data["id"] == "12345"
    assert loaded_data["title"] == "Test Chat"
    assert loaded_data["history"] == []

@patch('app.storage.os.path.exists')
@patch('app.storage.os.listdir')
@patch('app.storage.os.path.isfile')
@patch('builtins.open', new_callable=mock_open)
def test_get_sessions(mock_file, mock_isfile, mock_listdir, mock_exists):
    from app.storage import get_sessions
    
    mock_exists.return_value = True
    mock_listdir.return_value = ["session_1.json", "session_2.json", "other.txt"]
    mock_isfile.return_value = True
    
    session1 = json.dumps({"id": "1", "title": "A", "created_at": "2026-07-06T12:00:00+00:00", "history": []})
    session2 = json.dumps({"id": "2", "title": "B", "created_at": "2026-07-07T12:00:00+00:00", "history": []})
    
    mock_file.side_effect = [
        mock_open(read_data=session1).return_value,
        mock_open(read_data=session2).return_value
    ]
    
    username = "testuser"
    sessions = get_sessions(username)
    
    assert len(sessions) == 2
    assert sessions[0]["id"] == "2"
    assert sessions[1]["id"] == "1"
    assert "testuser" in mock_exists.call_args[0][0]

@patch('builtins.open', new_callable=mock_open)
@patch('app.storage.os.path.exists')
def test_get_session_history(mock_exists, mock_file):
    from app.storage import get_session_history
    mock_exists.return_value = True
    
    session_data = json.dumps({
        "id": "123",
        "title": "Chat",
        "created_at": "2026-07-06T12:00:00+00:00",
        "history": [{"text": "Hi", "is_user": True}]
    })
    mock_file.return_value.read.return_value = session_data
    
    history = get_session_history("testuser", "123")
    
    assert len(history) == 1
    assert history[0]["text"] == "Hi"
    assert "testuser" in mock_exists.call_args[0][0]

@patch('builtins.open', new_callable=mock_open)
@patch('app.storage.os.path.exists')
def test_save_session_message(mock_exists, mock_file):
    from app.storage import save_session_message
    mock_exists.return_value = True
    
    session_data = json.dumps({
        "id": "123",
        "title": "Chat",
        "created_at": "2026-07-06T12:00:00+00:00",
        "history": []
    })
    
    mock_file.return_value.read.return_value = session_data
    
    save_session_message("testuser", "123", {"text": "Hello", "is_user": True})
    
    handle = mock_file()
    written_data = "".join([call.args[0] for call in handle.write.call_args_list])
    loaded_data = json.loads(written_data)
    
    assert len(loaded_data["history"]) == 1
    assert loaded_data["history"][0]["text"] == "Hello"

@patch('builtins.open', new_callable=mock_open)
@patch('app.storage.os.path.exists')
def test_update_session_title(mock_exists, mock_file):
    from app.storage import update_session_title
    mock_exists.return_value = True
    
    session_data = json.dumps({
        "id": "123",
        "title": "Neuer Chat",
        "created_at": "2026-07-06T12:00:00+00:00",
        "history": []
    })
    
    mock_file.return_value.read.return_value = session_data
    
    update_session_title("testuser", "123", "New Title")
    
    handle = mock_file()
    written_data = "".join([call.args[0] for call in handle.write.call_args_list])
    loaded_data = json.loads(written_data)
    
    assert loaded_data["title"] == "New Title"

@patch('app.storage.os.path.exists')
@patch('app.storage.os.remove')
def test_delete_session(mock_remove, mock_exists):
    from app.storage import delete_session
    mock_exists.return_value = True
    
    delete_session("testuser", "123")
    
    mock_exists.assert_called_once()
    mock_remove.assert_called_once()
    assert "testuser" in mock_remove.call_args[0][0]
    assert mock_remove.call_args[0][0].endswith("session_123.json")

@patch('builtins.open', new_callable=mock_open)
@patch('app.storage.os.path.exists')
def test_get_session_prompt(mock_exists, mock_file):
    from app.storage import get_session_prompt
    mock_exists.return_value = True
    
    session_data = json.dumps({
        "id": "123",
        "system_prompt": "You are a chef."
    })
    mock_file.return_value.read.return_value = session_data
    
    prompt = get_session_prompt("testuser", "123")
    assert prompt == "You are a chef."

@patch('builtins.open', new_callable=mock_open)
@patch('app.storage.os.path.exists')
def test_get_session_prompt_fallback(mock_exists, mock_file):
    from app.storage import get_session_prompt
    mock_exists.return_value = True
    
    session_data = json.dumps({
        "id": "123"
    })
    mock_file.return_value.read.return_value = session_data
    
    prompt = get_session_prompt("testuser", "123")
    assert prompt == ""

@patch('builtins.open', new_callable=mock_open)
@patch('app.storage.os.path.exists')
def test_update_session_prompt(mock_exists, mock_file):
    from app.storage import update_session_prompt
    mock_exists.return_value = True
    
    session_data = json.dumps({
        "id": "123",
        "system_prompt": ""
    })
    
    mock_file.return_value.read.return_value = session_data
    
    update_session_prompt("testuser", "123", "New Prompt")
    
    handle = mock_file()
    written_data = "".join([call.args[0] for call in handle.write.call_args_list])
    loaded_data = json.loads(written_data)
    
    assert loaded_data["system_prompt"] == "New Prompt"
