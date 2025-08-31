WORKERS_CONFIG = {
    "quality_checks_worker": {
        "mindfile_parts": [
            "system_message.txt",
            "structured_self_facts.txt",
        ],
        "type": "meta",
    },
    "style_worker": {
        "mindfile_parts": [
            "system_message.txt",
            "structured_self_facts.txt",
            "dialogs.txt",
            "interviews_etc.txt",
        ],
        "type": "meta",
    },
}
