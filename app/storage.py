import os
import json
from datetime import datetime, timezone

# Load DATA_DIR from environment, fallback to a local 'data' folder
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))

def init_storage():
    """Ensure the base data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

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
