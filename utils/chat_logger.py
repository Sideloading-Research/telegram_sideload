import os
import json
import shutil
from datetime import datetime

# Define the directory for chat logs
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT_LOGS_DIR = os.path.join(PROJECT_ROOT, "TEMP_DATA", "chat_logs")

def _ensure_log_dir_exists():
    if not os.path.exists(CHAT_LOGS_DIR):
        os.makedirs(CHAT_LOGS_DIR, exist_ok=True)

def _get_log_path(conversation_key: str) -> str:
    # Sanitize key to be safe for filenames (though keys are usually ints or simple strings)
    safe_key = "".join(c for c in conversation_key if c.isalnum() or c in ('-', '_'))
    return os.path.join(CHAT_LOGS_DIR, f"{safe_key}.jsonl")

def append_message(conversation_key: str, role: str, content: str):
    """
    Appends a message to the conversation log file.
    """
    _ensure_log_dir_exists()
    file_path = _get_log_path(conversation_key)
    
    message_entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content
    }
    
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(message_entry, ensure_ascii=False) + "\n")

def load_chat_history(conversation_key: str, limit: int = 50) -> list[dict]:
    """
    Loads the last N messages from the conversation log.
    Returns a list of dicts with 'role' and 'content'.
    """
    file_path = _get_log_path(conversation_key)
    if not os.path.exists(file_path):
        return []
    
    messages = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Take the last 'limit' lines
        relevant_lines = lines[-limit:] if limit > 0 else lines
        
        for line in relevant_lines:
            if line.strip():
                try:
                    data = json.loads(line)
                    # Extract only needed fields for the conversation context
                    messages.append({
                        "role": data.get("role"),
                        "content": data.get("content")
                    })
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"Error loading chat history for {conversation_key}: {e}")
        return []
        
    return messages

def archive_chat_log(conversation_key: str):
    """
    Renames the current log file to an archive name with a timestamp.
    Used when resetting a conversation.
    """
    file_path = _get_log_path(conversation_key)
    if not os.path.exists(file_path):
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # safe_key is re-derived here, or we could just use basename
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    archive_filename = f"{name}_archive_{timestamp}{ext}"
    archive_path = os.path.join(CHAT_LOGS_DIR, archive_filename)
    
    try:
        shutil.move(file_path, archive_path)
        print(f"Archived chat log for {conversation_key} to {archive_filename}")
    except Exception as e:
        print(f"Error archiving chat log for {conversation_key}: {e}")

