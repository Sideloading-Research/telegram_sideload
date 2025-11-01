# Leftover Preservation System

## Overview

The leftover preservation system prevents data loss when `structured_self_facts` exceeds token limits. Instead of discarding the excess content, the system preserves it, distributes it to data workers, and ensures it's consulted when answering user questions.

## The Problem

Large mindfiles often have `structured_self_facts` that exceed token limits:
- **Token limit**: Configured as 30% of the LLM's context window
- **Large files**: Can be 3-4x larger than the limit
- **Previous behavior**: Excess content was truncated and lost forever
- **Result**: Up to 60-70% of facts data was unavailable to the bot

## The Solution

A three-phase system that:
1. **Preserves** the truncated content as "leftover"
2. **Distributes** leftover across multiple data workers via compendiums
3. **Ensures usage** by auto-upgrading shallow mode to deep mode when leftover exists

## How It Works

### Phase 1: Leftover Generation

When `Mindfile` is initialized:

```
1. Read structured_self_facts file
2. Check if it exceeds configured token limit (30% of context window)
3. If YES:
   - Truncate to the limit (kept in main facts)
   - Save remainder to cache file
   - Inject leftover into files_dict as virtual file
```

**Example with large file:**
- Main facts: ~32% of original (within limit)
- Leftover: ~68% of original ← **Preserved!**

### Phase 2: Distribution

Leftover is treated like any other mindfile part:

```
1. Leftover included in get_full_mindfile_content()
2. Split into entries by get_entries()
3. Packed into compendiums by bin packing algorithm
4. Distributed to multiple DataWorker instances
```

**Example distribution:**
- Total compendiums: 12
- Compendiums with leftover: 2
- Coverage: 16.7%

This is optimal - leftover is large so it consolidates into fewer chunks, and those 2 workers have complete access to all leftover content.

### Phase 3: Automatic Deep Mode Override

The critical final piece - ensuring leftover is actually **used**:

```python
if request_type in ["jailbreak", "exploitation"]:
    use_shallow_mode()  # Fast rejection path
else:
    if has_leftover and doorman_says_shallow:
        use_deep_mode()  # Override to consult all workers!
    else:
        follow_doorman_decision()
```

**Behavior Matrix:**

| Doorman Classification | Has Leftover | Final Mode | Reasoning |
|----------------------|--------------|------------|-----------|
| shallow | NO | shallow | Normal behavior |
| **shallow** | **YES** | **DEEP** | **Override to ensure leftover consulted** |
| deep | YES/NO | deep | Already using all workers |
| jailbreak | YES/NO | shallow | Fast rejection (never override) |
| exploitation | YES/NO | shallow | Fast rejection (never override) |

## Real-World Impact

### Real-World Example

**Data Distribution (typical large mindfile):**
- Total structured_self_facts: ~930k tokens
- Main content: ~300k tokens (32%, within configured limit)
- Leftover: ~630k tokens (68%)

**Without Leftover Preservation:**
- Deep mode: Uses ~300k tokens (all available within limit)
- Shallow mode: Uses ~300k tokens (all available within limit)
- **Lost**: ~630k tokens of valuable biographical data (~68%)

**With Leftover Preservation:**
- Deep mode: Uses ~930k tokens (100% of original)
- Shallow mode: Auto-upgraded to deep → ~930k tokens (100%)
- **Lost**: Nothing!

### User Experience Impact

**Before:**
```
User: "What did you write about consciousness in 2015?"
Doorman: "shallow" (seems straightforward)
System: Uses 1 generalist worker with partial facts (only main content)
Bot: "I'm not certain, I don't have detailed records from that period."
```

**After:**
```
User: "What did you write about consciousness in 2015?"
Doorman: "shallow" (seems straightforward)
System: "Leftover detected: forcing deep mode"
System: Polls multiple workers including those with leftover content
Bot: "Yes, in 2015 I wrote extensively about consciousness in [detailed answer with specific references]"
```

## Implementation Details

### File Structure

**New Modules:**
- `utils/leftover_manager.py` - Core leftover logic
- `utils/compendium_logger.py` - Logging and visibility

**Modified Files:**
- `utils/mindfile.py` - Leftover injection
- `workers/integration_worker.py` - Deep mode override
- `worker_config.py` - Data worker configuration
- `config.py` - Constants

### Cache Directory

Location: `.telegram_sideload_cache/`
- Created automatically when leftover is generated
- Contains: `structured_self_facts_leftover.txt`
- Cleaned up on each data refresh
- Ignored by git

### Configuration

**No configuration needed!** The system works automatically:

```python
# In config.py
STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT = "structured_self_facts_leftover"

# In worker_config.py
"data_worker": {
    "mindfile_parts_optional": [
        # ... other optional parts ...
        "structured_self_facts_leftover",  # Automatically included
    ],
}
```

## Logging and Visibility

### When Leftover is Generated

```
Truncation detected: 934381 tokens > configured token limit
Leftover statistics:
  Original: 934381 tokens (100%)
  Truncated: 299991 tokens (32.1%)
  Leftover: 634390 tokens (67.9%)
Leftover saved to: .telegram_sideload_cache/structured_self_facts_leftover.txt
Leftover injected into files_dict as 'structured_self_facts_leftover'
```

### During Compendium Creation

```
--- Files being packed into compendiums ---
  • dialogs
  • structured_memories
  • structured_self_facts
  ✓ structured_self_facts_leftover (LEFTOVER)
  • system_message
→ Leftover will be distributed among compendiums
-------------------------------------------

======================================================================
COMPENDIUM DISTRIBUTION REPORT
======================================================================

Total compendiums created: 12

Leftover distribution:
  Compendiums containing leftover: 2/12
  Distribution rate: 16.7%
  Compendium indices with leftover: [7, 8]
======================================================================
```

### When Override Occurs

```
Doorman classification: shallow
Leftover detected: forcing deep mode to ensure all preserved data is consulted
```

## Benefits

✅ **Zero data loss**: All truncated content is preserved and used  
✅ **Automatic**: No configuration or manual intervention needed  
✅ **Intelligent**: Only activates when truncation occurs  
✅ **Efficient**: Minimal performance overhead  
✅ **Transparent**: Clear logging at every step  
✅ **Complete**: From generation → distribution → usage  

## Performance

- **Leftover generation**: Happens once during Mindfile initialization
- **Distribution**: Leverages existing compendium packing algorithm
- **Override check**: Simple dictionary lookup (negligible)
- **Deep mode**: Already in use for complex queries, now also for simple ones when needed

**Net impact**: Virtually no performance cost, massive accuracy improvement!

## Testing

The system includes comprehensive test coverage:

```bash
# Phase 1: Generation and storage
python3 test_leftover_phase1.py

# Phase 2: Distribution and integration  
python3 test_leftover_phase2.py
python3 test_leftover_workers.py

# Phase 3: Deep mode override
python3 test_deep_override_simple.py
```

All tests verify:
- Leftover detection and generation
- Cache file creation and cleanup
- Injection into files_dict
- Distribution to compendium workers
- Access by data workers
- Override logic correctness

## Technical Deep Dive

### Leftover Generation Algorithm

```python
def process_and_generate_leftover(facts_content, system_message_content, ...):
    # Calculate token limit dynamically
    # Default: 30% of MAX_TOKENS_ALLOWED_IN_REQUEST
    # Can be stricter in ultra-small context window mode
    token_limit = calculate_truncation_limit(
        system_message_content,
        ultra_small_mode7,
        max_tokens_allowed
    )
    
    # Check if truncation is needed
    if count_tokens(facts_content) > token_limit:
        # Truncate at token boundary
        truncated = truncate_text_by_tokens(facts_content, token_limit)
        
        # Extract leftover
        leftover = facts_content[len(truncated):].strip()
        
        # Save to cache file
        leftover_path = write_leftover_to_file(leftover)
        
        # Return filepath mapping for injection
        return {leftover_key: leftover_path}
    
    return None  # No truncation needed
```

### Injection into Mindfile

```python
class Mindfile:
    def __init__(self, files_dict):
        self.files_dict = files_dict.copy()  # Allow modification
        self._validate_required_files()
        self._process_and_inject_leftover()  # Early injection!
```

By injecting early in `__init__`, leftover flows through all subsequent processing:
- `get_full_mindfile_content()` includes it
- `get_entries()` splits it  
- `get_mindfile_data_packed_into_compendiums()` distributes it
- Data workers receive it automatically

### Override Logic

```python
class IntegrationWorker:
    def _has_leftover(self) -> bool:
        return STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in self.mindfile.files_dict
    
    def _process(self, messages_history, raw_user_message):
        request_type = self.doorman_worker.process(...)
        
        if request_type in ["jailbreak", "exploitation"]:
            deep_dive7 = False  # Never override security paths
        else:
            has_leftover7 = self._has_leftover()
            
            if has_leftover7 and request_type == "shallow":
                print("Leftover detected: forcing deep mode...")
                deep_dive7 = True  # Override!
            else:
                deep_dive7 = request_type == "deep"
        
        # Use deep_dive7 to determine worker polling strategy
        answers = self.poll_data_workers(..., deep_dive7=deep_dive7)
```

## Troubleshooting

### No leftover generated

**This is normal if:**
- Your `structured_self_facts` fits within the configured token limit (typically 30% of context window)
- The limit is calculated dynamically based on `MAX_TOKENS_ALLOWED_IN_REQUEST` in `config.py`

**Check:**
- Look for "No truncation needed" message in logs
- Verify file size: `count_tokens()` on your facts file

### Leftover not in compendiums

**Unlikely but check:**
- Verify leftover is in `mindfile.files_dict`
- Check `worker_config.py` includes leftover in optional parts
- Look for error messages during compendium generation

### Cache directory issues

**Solution:**
- Ensure write permissions in project directory
- Verify `.telegram_sideload_cache/` is in `.gitignore`
- Manual cleanup: `from utils.leftover_manager import cleanup_leftover_files; cleanup_leftover_files()`

## Future Enhancements (Optional)

Potential improvements not currently needed:
- Smart truncation at sentence boundaries (currently truncates at token boundary)
- Configurable minimum leftover size threshold
- Multiple leftover tiers (primary, secondary)
- Compression for very large leftovers
- Real-time metrics dashboard

## Summary

The leftover preservation system is a complete solution that:

1. **Detects** when structured_self_facts exceeds limits
2. **Preserves** the excess content instead of discarding it
3. **Distributes** leftover to multiple workers via compendiums
4. **Ensures usage** by auto-upgrading to deep mode when needed

**Result**: Zero data loss, better answers, fully automatic operation.

In typical scenarios with large mindfiles, this system prevents **60-70% of biographical data from being lost**, dramatically improving the bot's ability to answer questions accurately and completely.

