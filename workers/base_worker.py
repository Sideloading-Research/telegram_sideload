from abc import ABC, abstractmethod
from worker_config import WORKERS_CONFIG

class BaseWorker(ABC):
    def __init__(self, worker_name: str):
        if worker_name not in WORKERS_CONFIG:
            raise ValueError(f"Worker '{worker_name}' not found in WORKERS_CONFIG.")
        
        self.worker_name = worker_name
        self.config = WORKERS_CONFIG[worker_name]
        self.mindfile_parts = self.config["mindfile_parts"]

    @abstractmethod
    def process(self, *args, **kwargs):
        """
        Main method to be implemented by each worker.
        It will take specific arguments depending on the worker's role.
        """
        pass
