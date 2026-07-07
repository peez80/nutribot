import pytest
import subprocess
import json
from unittest.mock import patch, MagicMock
from app.agy_client import AgyClient

@pytest.fixture
def client():
    return AgyClient(executable_path="dummy_agy")

@patch("app.agy_client.os.path.exists")
@patch("app.agy_client.os.listdir")
def test_is_authenticated_via_dir(mock_listdir, mock_exists, client):
    # Setup mock to return true for dir exists and has content
    mock_exists.return_value = True
    mock_listdir.return_value = ["credentials.json"]
    
    assert client.is_authenticated() == True
    
@patch("app.agy_client.os.path.exists")
@patch("app.agy_client.subprocess.run")
def test_is_authenticated_via_cli(mock_run, mock_exists, client):
    # Setup mock: dir doesn't exist, but CLI runs fine
    def mock_exists_side_effect(path):
        if "antigravity-cli" in path:
            return False
        return True
    mock_exists.side_effect = mock_exists_side_effect
    
    mock_run.return_value = MagicMock(returncode=0)
    
    assert client.is_authenticated() == True
    mock_run.assert_called_once()

@patch("app.agy_client.subprocess.Popen")
def test_get_login_url_success(mock_popen, client):
    # Setup a mock process that yields a URL
    mock_process = MagicMock()
    mock_process.stdout.readline.side_effect = [
        "Please visit this URL to login:\n",
        "https://antigravity.google/auth?code=xyz\n",
        "Enter code:\n",
        ""
    ]
    mock_popen.return_value = mock_process
    
    url = client.get_login_url()
    
    assert url == "https://antigravity.google/auth?code=xyz"
    mock_popen.assert_called_once()

@patch("app.agy_client.subprocess.run")
def test_process_message_success(mock_run, client):
    # Mock a successful run returning valid JSON
    expected_response = {
        "type": "meal",
        "data": {"food": "Apfel"},
        "reply": "Apfel notiert!"
    }
    
    # Sometimes it wraps in markdown
    mock_run.return_value = MagicMock(
        stdout=f"```json\n{json.dumps(expected_response)}\n```\n",
        returncode=0
    )
    
    context = [{"is_user": True, "text": "Hallo"}]
    message = "Ein Apfel."
    
    result = client.process_message(context, message)
    
    assert result == expected_response
    mock_run.assert_called_once()
    
    # Check if prompt formatting was correct
    args, kwargs = mock_run.call_args
    assert "--prompt" in args[0]
    prompt_arg = args[0][args[0].index("--prompt") + 1]
    assert "User: Hallo" in prompt_arg
    assert "User: Ein Apfel." in prompt_arg

@patch("app.agy_client.subprocess.run")
def test_process_message_with_multiple_images(mock_run, client):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({"type": "meal", "data": {}, "reply": "ok"}),
        returncode=0
    )
    
    result = client.process_message([], "Essen", ["/tmp/image1.jpg", "/tmp/image2.jpg"])
    
    assert result["reply"] == "ok"
    
    # Verify image paths are included in prompt
    args, kwargs = mock_run.call_args
    prompt_arg = args[0][args[0].index("--prompt") + 1]
    assert "/tmp/image1.jpg" in prompt_arg
    assert "/tmp/image2.jpg" in prompt_arg

@patch("app.agy_client.subprocess.run")
def test_process_message_json_error(mock_run, client):
    # Mock CLI returning garbage instead of JSON
    mock_run.return_value = MagicMock(
        stdout="Something went wrong",
        returncode=0
    )
    
    result = client.process_message([], "Test")
    
    assert result["type"] == "unknown"
    assert "Something went wrong" in result["data"]["raw_output"]
