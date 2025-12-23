import json
import os
import hashlib
import streamlit as st

USERS_FILE = ".users.json"
HISTORY_DIR = "user_history"

# --- USER MANAGEMENT ---

def _load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def _save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def _hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    users = _load_users()
    if username not in users:
        return False
    return users[username] == _hash_pw(password)

def sign_up(username, password):
    users = _load_users()
    if username in users:
        return False # Already exists
    
    users[username] = _hash_pw(password)
    _save_users(users)
    return True

# --- HISTORY MANAGEMENT ---

def get_history_file(username):
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    return os.path.join(HISTORY_DIR, f"{username}.json")

def load_user_history(username):
    """Returns (sessions, current_id) tuple"""
    filepath = get_history_file(username)
    if not os.path.exists(filepath):
        # Default fresh state
        import uuid
        init_id = str(uuid.uuid4())
        return {init_id: []}, init_id
    
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return data.get("sessions", {}), data.get("current_id", "")
    except:
         import uuid
         init_id = str(uuid.uuid4())
         return {init_id: []}, init_id

def save_user_history(username, sessions, current_id, pinned_sessions):
    """Saves complete session state"""
    data = {
        "sessions": sessions,
        "current_id": current_id,
        "pinned_sessions": list(pinned_sessions)
    }
    with open(get_history_file(username), "w") as f:
        json.dump(data, f)
        
def load_pinned(username):
    filepath = get_history_file(username)
    if not os.path.exists(filepath): return set()
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return set(data.get("pinned_sessions", []))
    except:
        return set()
