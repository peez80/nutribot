import os
import json
import uuid
import shutil
from datetime import datetime, timezone

# Load DATA_DIR from environment, fallback to a local 'data' folder
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))

def init_storage():
    """Ensure the base data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "config"), exist_ok=True)

def init_user_storage(username: str):
    """Ensure the subdirectories for a specific user exist."""
    user_dir = os.path.join(DATA_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(os.path.join(user_dir, "sessions"), exist_ok=True)

def init_session_storage(username: str, session_id: str):
    """Ensure the subdirectories for a specific session exist."""
    session_dir = os.path.join(DATA_DIR, username, "sessions", session_id)
    os.makedirs(session_dir, exist_ok=True)
    os.makedirs(os.path.join(session_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(session_dir, "data"), exist_ok=True)


# --- Session Management ---

def get_session_filepath(username: str, session_id: str) -> str:
    # Basic protection against path traversal
    safe_session_id = os.path.basename(session_id)
    return os.path.join(DATA_DIR, username, "sessions", safe_session_id, "session.json")

def create_session(username: str, title: str = "Neuer Chat") -> str:
    init_user_storage(username)
    session_id = uuid.uuid4().hex
    init_session_storage(username, session_id)
    filepath = get_session_filepath(username, session_id)
    
    session_data = {
        "id": session_id,
        "title": title,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "history": [],
        "system_prompt": ""
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)
        
    return session_id

def get_sessions(username: str) -> list:
    sessions_dir = os.path.join(DATA_DIR, username, "sessions")
    if not os.path.exists(sessions_dir):
        return []
        
    sessions = []
    for dirname in os.listdir(sessions_dir):
        dir_path = os.path.join(sessions_dir, dirname)
        if os.path.isdir(dir_path):
            filepath = os.path.join(dir_path, "session.json")
            if os.path.isfile(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        sessions.append({
                            "id": data.get("id"),
                            "title": data.get("title", "Chat"),
                            "created_at": data.get("created_at", "")
                        })
                except Exception:
                    continue
                    
    # Sort newest first
    sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return sessions

def get_session_history(username: str, session_id: str) -> list:
    filepath = get_session_filepath(username, session_id)
    if not os.path.exists(filepath):
        return []
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("history", [])
    except Exception:
        return []

def save_session_message(username: str, session_id: str, message: dict):
    filepath = get_session_filepath(username, session_id)
    if not os.path.exists(filepath):
        return
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        data["history"].append(message)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def update_session_title(username: str, session_id: str, new_title: str):
    filepath = get_session_filepath(username, session_id)
    if not os.path.exists(filepath):
        return
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        data["title"] = new_title
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def delete_session(username: str, session_id: str):
    filepath = get_session_filepath(username, session_id)
    session_dir = os.path.dirname(filepath)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)

def get_session_prompt(username: str, session_id: str) -> str:
    filepath = get_session_filepath(username, session_id)
    if not os.path.exists(filepath):
        return ""
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("system_prompt", "")
    except Exception:
        return ""

def update_session_prompt(username: str, session_id: str, prompt: str):
    filepath = get_session_filepath(username, session_id)
    if not os.path.exists(filepath):
        return
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        data["system_prompt"] = prompt
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
