from abc import ABC, abstractmethod
from worker_config import WORKERS_CONFIG
from config import MAX_TELEGRAM_MESSAGE_LEN

class BaseWorker(ABC):
    def __init__(self, worker_name: str, custom_display_name: str | None = None):
        if worker_name not in WORKERS_CONFIG:
            raise ValueError(f"Worker '{worker_name}' not found in WORKERS_CONFIG.")
        
        self.worker_name = worker_name
        self.display_name = custom_display_name if custom_display_name is not None else worker_name
        self.config = WORKERS_CONFIG[worker_name]
        self.mindfile_parts = self.config.get("mindfile_parts", []) + self.config.get(
            "mindfile_parts_optional", []
        )
        self.mindfile = None  # Set by child class __init__
        
        # Diagnostics support (opt-in via collect_diagnostics7)
        self.collect_diagnostics7 = True
        self._diag_events = []
    
    def get_worker_system_message(self, additional_prompt: str | None = None) -> str:
        """
        Gets the system message for this worker from mindfile.
        
        This ensures workers load their system message explicitly from mindfile
        based on worker_config, not from conversation history.
        
        Args:
            additional_prompt: Optional prompt to append (e.g., user_info_prompt)
            
        Returns:
            System message string
        """
        if not self.mindfile:
            raise RuntimeError(f"Worker {self.worker_name} has no mindfile set")
        
        system_message = self.mindfile.get_system_message()
        if additional_prompt:
            system_message += "\n\n" + additional_prompt
        return system_message
    
    def get_worker_context(self) -> str:
        """
        Gets the context for this worker from mindfile based on worker_config.
        
        This ensures workers load their context explicitly from mindfile
        according to their mindfile_parts configuration, not from conversation history.
        
        Returns:
            Context string (automatically excludes system_message to prevent duplication)
        """
        if not self.mindfile:
            raise RuntimeError(f"Worker {self.worker_name} has no mindfile set")
        
        return self.mindfile.get_context(self.mindfile_parts)

    def process(self, *args, **kwargs):
        """
        A wrapper around the main `_process` method to handle logging.
        """
        # Integration worker is the top-level orchestrator
        # log_prefix = "#" if self.worker_name == "integration_worker" else "##"
        log_prefix = "#"
        
        print(f"\n{log_prefix}--- Running {self.display_name} ---")
        try:
            result = self._process(*args, **kwargs)
            if isinstance(result, str) and len(result) > MAX_TELEGRAM_MESSAGE_LEN:
                print(
                    f"# Worker {self.display_name} result is too long ({len(result)} chars), truncating to {MAX_TELEGRAM_MESSAGE_LEN} chars."
                )
                result = result[-MAX_TELEGRAM_MESSAGE_LEN:]
            return result
        finally:
            print(f"{log_prefix}--- {self.display_name} Finished ---\n")

    def record_diag_event(self, event: str, details: str | None = None) -> None:
        if not self.collect_diagnostics7:
            return
        try:
            self._diag_events.append({"event": event, "details": details})
        except Exception:
            # Avoid diagnostics failures impacting main flow
            pass

    def get_diag_events(self) -> list[dict]:
        return list(self._diag_events)

    def clear_diag_events(self) -> None:
        self._diag_events = []

    def print_diag_events(self) -> None:
        if not self._diag_events:
            return
        print("Self-diagnostics:")
        for evt in self._diag_events:
            event = evt.get("event")
            details = evt.get("details")
            if details:
                print(f"- {event}: {details}")
            else:
                print(f"- {event}")

    @abstractmethod
    def _process(self, *args, **kwargs):
        """
        Main method to be implemented by each worker.
        It will take specific arguments depending on the worker's role.
        """
        pass
