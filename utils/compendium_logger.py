"""
Logging utilities for compendium distribution and leftover tracking.
Provides visibility into how leftover content is distributed among workers.
"""

from config import STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT


def log_files_being_packed(files_dict: dict[str, str]):
    """Logs which files are being packed into compendiums."""
    print("\n--- Files being packed into compendiums ---")
    
    has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in files_dict
    
    for filename in sorted(files_dict.keys()):
        if filename == STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT:
            print(f"  ✓ {filename} (LEFTOVER)")
        else:
            print(f"  • {filename}")
    
    if has_leftover7:
        print("→ Leftover will be distributed among compendiums")
    else:
        print("→ No leftover (no truncation occurred)")
    
    print("-------------------------------------------\n")
    
    return has_leftover7


def log_entry_sources(entries: list):
    """Logs which source files contributed to entries."""
    source_files = set()
    leftover_entries_count = 0
    
    for entry in entries:
        # Try to detect if entry contains leftover content
        # The entry text includes source tags, so we can check for leftover tags
        if STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in entry.text:
            leftover_entries_count += 1
    
    total_entries = len(entries)
    
    if leftover_entries_count > 0:
        print(f"\n--- Entry distribution ---")
        print(f"Total entries: {total_entries}")
        print(f"Entries containing leftover: {leftover_entries_count}")
        print(f"Leftover presence: {leftover_entries_count}/{total_entries} entries")
        print("-------------------------\n")


def log_compendium_distribution(compendiums: list[str], files_dict: dict[str, str]):
    """
    Logs detailed information about compendium distribution,
    especially tracking leftover content.
    """
    total_compendiums = len(compendiums)
    
    if total_compendiums == 0:
        print("No compendiums created (empty mindfile)")
        return
    
    has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in files_dict
    
    print("\n" + "=" * 70)
    print(f"COMPENDIUM DISTRIBUTION REPORT")
    print("=" * 70)
    
    print(f"\nTotal compendiums created: {total_compendiums}")
    
    if not has_leftover7:
        print("\nNo leftover content (no truncation occurred)")
        print("=" * 70 + "\n")
        return
    
    # Analyze which compendiums contain leftover
    leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
    compendiums_with_leftover = []
    
    for i, comp in enumerate(compendiums):
        if leftover_tag in comp:
            compendiums_with_leftover.append(i)
    
    leftover_count = len(compendiums_with_leftover)
    
    print(f"\nLeftover distribution:")
    print(f"  Compendiums containing leftover: {leftover_count}/{total_compendiums}")
    
    if leftover_count > 0:
        percentage = (leftover_count / total_compendiums) * 100
        print(f"  Distribution rate: {percentage:.1f}%")
        print(f"  Compendium indices with leftover: {compendiums_with_leftover}")
        
        # Calculate leftover sizes in each compendium
        leftover_sizes = []
        for i in compendiums_with_leftover:
            comp = compendiums[i]
            # Count chars between leftover tags (rough estimate)
            start_pos = comp.find(leftover_tag)
            end_tag = f"</mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
            end_pos = comp.find(end_tag)
            
            if start_pos != -1 and end_pos != -1:
                leftover_chunk_size = end_pos - start_pos
                leftover_sizes.append(leftover_chunk_size)
        
        if leftover_sizes:
            total_leftover_chars = sum(leftover_sizes)
            avg_leftover_per_comp = total_leftover_chars / len(leftover_sizes)
            print(f"\n  Leftover size statistics:")
            print(f"    Total leftover distributed: {total_leftover_chars:,} chars")
            print(f"    Average per compendium: {avg_leftover_per_comp:,.0f} chars")
            print(f"    Min chunk: {min(leftover_sizes):,} chars")
            print(f"    Max chunk: {max(leftover_sizes):,} chars")
    
    print("\n" + "=" * 70 + "\n")


def log_worker_leftover_access(worker_name: str, context: str):
    """
    Logs whether a worker's context includes leftover content.
    Useful for debugging which workers receive leftover.
    """
    leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
    has_leftover7 = leftover_tag in context
    
    if has_leftover7:
        # Count approximate size
        start_pos = context.find(leftover_tag)
        end_tag = f"</mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        end_pos = context.find(end_tag)
        
        if start_pos != -1 and end_pos != -1:
            leftover_size = end_pos - start_pos
            print(f"  [{worker_name}] ✓ Has leftover content (~{leftover_size:,} chars)")
        else:
            print(f"  [{worker_name}] ✓ Has leftover content (size unknown)")
    else:
        print(f"  [{worker_name}] - No leftover content")

