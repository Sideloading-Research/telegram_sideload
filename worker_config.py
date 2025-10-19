# Worker-specific mindfile parts and worker types.
# This is the "single source of truth" for per-worker configuration.
from config import WORKERS_OBLIGATORY_PARTS


WORKER_SPECIFIC_PARTS = {
    "quality_checks_worker": {
        "mindfile_parts": [],
        "type": "meta",
    },
    "integration_worker": {
        "mindfile_parts": ["internal_assets:this_architecture_description"],
        "type": "meta",
    },
    "style_worker": {
        "mindfile_parts": ["dialogs", "interviews_etc"],
        "type": "meta",
    },
    "doorman_worker": {
        "mindfile_parts": [],
        "type": "meta",
    },
    "data_worker": {
        "mindfile_parts": [
            "structured_memories",
            "consumed_media_list",
            "dialogs",
            "interviews_etc",
            "writings_non_fiction",
            "dreams",
            "writings_fiction",
        ],
        "type": "data",
    },
}

# Dynamically build the final WORKERS_CONFIG.
# This allows for easy addition of new workers and obligatory sources
# without duplicating the obligatory sources for each worker.
WORKERS_CONFIG = {}
for worker_name, specs in WORKER_SPECIFIC_PARTS.items():
    WORKERS_CONFIG[worker_name] = {
        "mindfile_parts": WORKERS_OBLIGATORY_PARTS + specs["mindfile_parts"],
        "type": specs["type"],
    }