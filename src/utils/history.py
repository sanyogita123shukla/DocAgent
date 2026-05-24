import os
import json
from uuid import uuid4
from datetime import datetime

SESSION_FILE = "data/sessions.json"

def _ensure_dir():
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    if not os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "w") as f:
            json.dump([], f)

def get_sessions():
    """Returns a list of sessions ordered by newest first."""
    _ensure_dir()
    with open(SESSION_FILE, "r") as f:
        try:
            sessions = json.load(f)
            # Sort by timestamp descending
            sessions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return sessions
        except json.JSONDecodeError:
            return []

def create_session(title="New Chat"):
    """Creates a new session and returns its ID."""
    _ensure_dir()
    session_id = str(uuid4())
    session_metadata = {
        "id": session_id,
        "title": title,
        "timestamp": datetime.now().isoformat()
    }
    
    sessions = get_sessions()
    sessions.append(session_metadata)
    
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=4)
        
    return session_id

def update_session_title(session_id, title):
    """Updates the title of a specific session."""
    sessions = get_sessions()
    for s in sessions:
        if s["id"] == session_id:
            s["title"] = title
            break
            
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=4)
