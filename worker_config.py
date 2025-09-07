WORKERS_CONFIG = {
    "quality_checks_worker": {
        "mindfile_parts": [
            "system_message",
            "structured_self_facts",
        ],
        "type": "meta",
    },
    "integration_worker": {
        "mindfile_parts": [
            "system_message",
            "structured_self_facts",
            "internal_assets:this_architecture_description",
        ],
        "type": "meta",
    },
    "style_worker": {
        "mindfile_parts": [
            "system_message",
            "structured_self_facts",
            "dialogs",
            "interviews_etc",
        ],
        "type": "meta",
    },
    "data_worker": {
        "mindfile_parts": [
            "system_message",
            "structured_self_facts",
            "structured_memories",
            "consumed_media_list",
            "dialogs",
            "interviews_etc",
            "writings_non_fiction",
            "dreams",
            "writings_fiction"
        ],
        "type": "data",
    }
}
