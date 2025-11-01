# Admin Commands

This document outlines the admin commands available in the bot for development and testing purposes.

## Data Source Switching

You can dynamically switch the mindfile data source between the default source and a smaller, local test dataset. This is useful for quick testing without needing to modify configuration files or restart the bot.

### Switch to Test Mode

To switch to the quick test dataset, send the following message to the bot:

```
admin:test
```

The bot will activate the test mode and start using the data from the `tests/test_data/smaller_versions_of_dataset/300k` directory. It will confirm the switch with the message: "quick test mode activated".

### Switch Back to Normal Mode

To switch back to the default data source, send the following message:

```
admin:norm
```

The bot will revert to the original data source configuration (either the remote repository or the `LOCAL_MINDFILE_DIR_PATH` you specified in `config.py`). It will confirm the switch with the message: "normal mode activated".
