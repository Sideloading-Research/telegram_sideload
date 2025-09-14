from abc import ABC, abstractmethod
from worker_config import WORKERS_CONFIG

class BaseWorker(ABC):
    def __init__(self, worker_name: str, custom_display_name: str | None = None):
        if worker_name not in WORKERS_CONFIG:
            raise ValueError(f"Worker '{worker_name}' not found in WORKERS_CONFIG.")
        
        self.worker_name = worker_name
        self.display_name = custom_display_name if custom_display_name is not None else worker_name
        self.config = WORKERS_CONFIG[worker_name]
        self.mindfile_parts = self.config["mindfile_parts"]

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
            return result
        finally:
            print(f"{log_prefix}--- {self.display_name} Finished ---\n")

    @abstractmethod
    def _process(self, *args, **kwargs):
        """
        Main method to be implemented by each worker.
        It will take specific arguments depending on the worker's role.
        """
        pass
