import threading
from typing import Tuple, Optional
from utils.dataset_files import refresh_local_mindfile_data
from utils.mindfile import get_system_message_and_context, Mindfile
from config import REPO_URL, DATASET_LOCAL_DIR_PATH, REFRESH_EVERY_N_REQUESTS

class MindDataManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        if MindDataManager._instance is not None:
            raise RuntimeError("Use get_instance() instead")
        self._request_counter = 0
        self._system_message: Optional[str] = None
        self._context: Optional[str] = None
        self._files_dict: dict[str, str] = {}
        self._counter_lock = threading.Lock()
        self._refresh_data()

    @classmethod
    def get_instance(cls) -> 'MindDataManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _refresh_data(self) -> None:
        """Refresh the mind data from the repository."""
        print("Refreshing mind data...")
        try:
            self._files_dict = refresh_local_mindfile_data(REPO_URL, DATASET_LOCAL_DIR_PATH)
            if not self._files_dict:
                # If refresh returns nothing, and we have no old data, it's a critical failure.
                if not self._system_message:
                    raise RuntimeError("Initial mind data load failed: no files found.")
                else:
                    # If we have old data, just warn and continue with it.
                    print("Warning: Mind data refresh resulted in no files. Using stale data.")
                    return # Skip updating system_message and context
            
            self._system_message, self._context = get_system_message_and_context(self._files_dict)
            
            with self._counter_lock:
                self._request_counter = 0
        except Exception as e:
            # If refresh fails and we don't have any data yet, raise the error
            if self._system_message is None or self._context is None:
                raise RuntimeError(f"Initial mind data load failed: {str(e)}")
            # Otherwise, keep the old data and just log the error
            print(f"Warning: Mind data refresh failed: {str(e)}")

    def get_current_data(self) -> Tuple[str, str]:
        """Get the current system message and context, refreshing if needed."""
        with self._counter_lock:
            self._request_counter += 1
            print(f"Request counter for refreshing mind data: {self._request_counter}")
            should_refresh = self._request_counter >= REFRESH_EVERY_N_REQUESTS

        if should_refresh:
            self._refresh_data()

        if self._system_message is None or self._context is None:
            raise RuntimeError("Mind data not properly initialized")
        
        #tokens_num = count_tokens(self._context)
        #print(f"Chars num in context: {len(self._context)}")
        #print(f"Tokens number in context: {tokens_num}")
        #if is_token_limit_of_text_exceeded(self._context):
        #    print("Token limit exceeded")

        return self._system_message, self._context

    def get_mindfile(self) -> Mindfile:
        """
        Returns a Mindfile instance created from the current data.
        This is the preferred way to access mindfile contents for new features.
        """
        if not self._files_dict:
            # This should not happen if the instance is properly initialized.
            raise RuntimeError("Mind data files not available.")
        return Mindfile(self._files_dict)

    def force_refresh(self) -> None:
        """Force a refresh of the mind data."""
        self._refresh_data() 