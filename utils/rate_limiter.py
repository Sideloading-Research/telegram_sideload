import os
import time
from typing import Tuple
from config import GLOBAL_RATE_LIMIT_REQUESTS_PER_MINUTE

RATE_LIMIT_FILE_PATH = "TEMP_DATA/global_request_timestamps.txt"
WARNING_TIMESTAMP_FILE_PATH = "TEMP_DATA/rate_limit_warning_timestamp.txt"

def is_global_rate_limited() -> Tuple[bool, bool]:
    """
    Checks if the global rate limit has been exceeded.
    Returns a tuple: (is_limited, should_send_warning)
    
    is_limited: True if too many requests, False otherwise.
    should_send_warning: True if we should warn the user (only happens once per minute).
    
    Also records the current request timestamp if not limited.
    
    NOTE ON CONCURRENCY:
    This function performs synchronous file I/O. In a standard asyncio event loop 
    (single-threaded), this blocks the loop, ensuring atomic execution. 
    This prevents race conditions between concurrent requests because no context 
    switch can occur during the read-check-write cycle.
    
    This is safe for a single-process bot. If running with multiple processes (workers),
    file locking would be required.

    NOTE ON SELF-CLEANING:
    This function automatically prunes the timestamp file. Every time it runs, it reads the file,
    keeps only timestamps from the last 60 seconds (discarding older ones), and rewrites the file.
    This ensures the file size stays small (bounded by the rate limit) and doesn't grow indefinitely.
    """
    current_time = time.time()
    valid_timestamps = []
    
    # Ensure directory exists
    dir_name = os.path.dirname(RATE_LIMIT_FILE_PATH)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    # Read existing timestamps
    if os.path.exists(RATE_LIMIT_FILE_PATH):
        try:
            with open(RATE_LIMIT_FILE_PATH, 'r') as f:
                for line in f:
                    try:
                        timestamp = float(line.strip())
                        # Keep only timestamps within the last 60 seconds
                        if current_time - timestamp < 60:
                            valid_timestamps.append(timestamp)
                    except ValueError:
                        continue # Skip malformed lines
        except Exception as e:
            print(f"Error reading rate limit file: {e}")
            pass
            
    # Check limit BEFORE appending current. 
    if len(valid_timestamps) >= GLOBAL_RATE_LIMIT_REQUESTS_PER_MINUTE:
        # Rate limit exceeded. Check if we should warn.
        should_warn = False
        last_warning_time = 0.0
        
        if os.path.exists(WARNING_TIMESTAMP_FILE_PATH):
            try:
                with open(WARNING_TIMESTAMP_FILE_PATH, 'r') as f:
                    content = f.read().strip()
                    if content:
                        last_warning_time = float(content)
            except Exception as e:
                print(f"Error reading warning timestamp: {e}")
        
        # Warn if no warning sent in the last 60 seconds
        if current_time - last_warning_time > 60:
            should_warn = True
            try:
                with open(WARNING_TIMESTAMP_FILE_PATH, 'w') as f:
                    f.write(str(current_time))
            except Exception as e:
                print(f"Error writing warning timestamp: {e}")
                
        return True, should_warn
        
    # Add current timestamp
    valid_timestamps.append(current_time)
    
    # Write back to file
    try:
        with open(RATE_LIMIT_FILE_PATH, 'w') as f:
            for timestamp in valid_timestamps:
                f.write(f"{timestamp}\n")
    except Exception as e:
        print(f"Error writing rate limit file: {e}")
        
    return False, False
