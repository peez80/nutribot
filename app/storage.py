import os
import json
import uuid
from datetime import datetime, timezone

# Load DATA_DIR from environment, fallback to a local 'data' folder
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))

def init_storage():
    """Ensure the base data directory and subdirectories exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "sessions"), exist_ok=True)

def save_entry(entry_type: str, raw_input: str, structured_data: dict) -> str:
    """
    Saves an entry (meal or symptom) to a JSON file.
    Groups by YYYY-MM folder and prefixes filename with ISO timestamp.
    """
    now = datetime.now(timezone.utc)
    month_dir = now.strftime("%Y-%m")
    timestamp_str = now.strftime("%Y-%m-%dT%H%M%SZ")
    
    # Create the month directory
    target_dir = os.path.join(DATA_DIR, month_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    # Construct filename
    filename = f"{timestamp_str}_{entry_type}.json"
    filepath = os.path.join(target_dir, filename)
    
    # Prepare data payload
    payload = {
        "type": entry_type,
        "timestamp": now.isoformat(),
        "raw_input": raw_input,
        "data": structured_data
    }
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    return filepath

# --- Session Management ---

def get_session_filepath(session_id: str) -> str:
    return os.path.join(DATA_DIR, "sessions", f"session_{session_id}.json")

def create_session(title: str = "Neuer Chat") -> str:
    session_id = uuid.uuid4().hex
    filepath = get_session_filepath(session_id)
    
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

def get_sessions() -> list:
    sessions_dir = os.path.join(DATA_DIR, "sessions")
    if not os.path.exists(sessions_dir):
        return []
        
    sessions = []
    for filename in os.listdir(sessions_dir):
        if filename.startswith("session_") and filename.endswith(".json"):
            filepath = os.path.join(sessions_dir, filename)
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

def get_session_history(session_id: str) -> list:
    filepath = get_session_filepath(session_id)
    if not os.path.exists(filepath):
        return []
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("history", [])
    except Exception:
        return []

def save_session_message(session_id: str, message: dict):
    filepath = get_session_filepath(session_id)
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

def update_session_title(session_id: str, new_title: str):
    filepath = get_session_filepath(session_id)
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

def delete_session(session_id: str):
    filepath = get_session_filepath(session_id)
    if os.path.exists(filepath):
        os.remove(filepath)

def get_session_prompt(session_id: str) -> str:
    filepath = get_session_filepath(session_id)
    if not os.path.exists(filepath):
        return ""
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("system_prompt", "")
    except Exception:
        return ""

def update_session_prompt(session_id: str, prompt: str):
    filepath = get_session_filepath(session_id)
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
