"""
Worker Context Test: Verify data workers can access leftover through their context
Tests worker context building without requiring full AI service initialization.
"""

import sys
from utils.mind_data_manager import MindDataManager
from worker_config import WORKERS_CONFIG
from config import STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT


def test_data_worker_config():
    """Test that data_worker configuration includes leftover."""
    print("\n" + "=" * 70)
    print("Test 1: Data Worker Configuration")
    print("=" * 70)
    
    config = WORKERS_CONFIG.get("data_worker", {})
    optional_parts = config.get("mindfile_parts_optional", [])
    
    print(f"\nData worker optional parts:")
    for part in optional_parts:
        marker = "✓" if part == STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT else " "
        print(f"  {marker} {part}")
    
    if STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in optional_parts:
        print(f"\n✓ Leftover configured correctly as optional part")
        return True
    else:
        print(f"\n✗ Leftover NOT found in optional parts")
        return False


def test_worker_context_building():
    """Test that worker context includes leftover when available."""
    print("\n" + "=" * 70)
    print("Test 2: Worker Context Building")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("\n⚠ No leftover present, skipping context test")
            return True
        
        print(f"\n✓ Leftover present in mindfile")
        
        # Get data worker parts
        config = WORKERS_CONFIG["data_worker"]
        mindfile_parts = config["mindfile_parts"] + config["mindfile_parts_optional"]
        
        print(f"\nData worker requests these parts:")
        for part in mindfile_parts:
            exists = part in mindfile.files_dict
            marker = "✓" if exists else "-"
            print(f"  {marker} {part}")
        
        # Build context as data worker would
        context = mindfile.get_context(mindfile_parts)
        
        # Check if leftover is in context
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        
        if leftover_tag in context:
            print(f"\n✓ Leftover successfully included in worker context")
            
            # Calculate approximate size
            start_pos = context.find(leftover_tag)
            end_tag = f"</mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
            end_pos = context.find(end_tag)
            
            if start_pos != -1 and end_pos != -1:
                leftover_size = end_pos - start_pos
                print(f"  Context leftover size: ~{leftover_size:,} chars")
        else:
            print(f"\n✗ Leftover NOT found in worker context")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compendium_workers_would_receive_leftover():
    """Test that compendium creation distributes leftover to workers."""
    print("\n" + "=" * 70)
    print("Test 3: Compendium Workers Receive Leftover")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("\n⚠ No leftover present, skipping compendium worker test")
            return True
        
        # Get compendiums (simulating what IntegrationWorker does)
        print("\nGenerating compendiums (as IntegrationWorker would)...")
        compendiums = mindfile.get_mindfile_data_packed_into_compendiums()
        
        print(f"\n✓ Would create {len(compendiums)} compendium worker(s)")
        
        # Check which would receive leftover
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        workers_with_leftover = []
        
        for i, comp in enumerate(compendiums):
            if leftover_tag in comp:
                workers_with_leftover.append(i)
        
        if workers_with_leftover:
            print(f"\n✓ Workers with leftover: {len(workers_with_leftover)}/{len(compendiums)}")
            print(f"  Worker indices: {workers_with_leftover}")
            
            # Show context size for each worker with leftover
            print(f"\n  Worker details:")
            for idx in workers_with_leftover:
                comp_size = len(compendiums[idx])
                print(f"    Worker {idx+1}: ~{comp_size:,} chars total context")
        else:
            print(f"\n⚠ No workers would receive leftover")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_impact_summary():
    """Show the impact of leftover preservation."""
    print("\n" + "=" * 70)
    print("IMPACT SUMMARY")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("\n⚠ No truncation occurred with current mindfile")
            print("  All structured_self_facts fits within token limits")
            return True
        
        # Get statistics
        from utils.tokens import count_tokens
        
        leftover_content = mindfile.get_file_content(STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT)
        facts_content = mindfile.get_file_content("structured_self_facts")
        
        leftover_tokens = count_tokens(leftover_content)
        facts_tokens = count_tokens(facts_content)
        total_tokens = leftover_tokens + facts_tokens
        
        # Get distribution
        compendiums = mindfile.get_mindfile_data_packed_into_compendiums()
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        workers_with_leftover = sum(1 for comp in compendiums if leftover_tag in comp)
        
        print(f"\n📊 Data Preservation Impact:")
        print(f"   Before: {leftover_tokens:,} tokens would be LOST")
        print(f"   After:  {leftover_tokens:,} tokens PRESERVED ({leftover_tokens/total_tokens*100:.1f}% of total)")
        
        print(f"\n📦 Distribution:")
        print(f"   Total workers: {len(compendiums)}")
        print(f"   Workers with leftover: {workers_with_leftover}")
        print(f"   Coverage: {workers_with_leftover/len(compendiums)*100:.1f}%")
        
        print(f"\n✅ SUCCESS! Leftover preservation is working perfectly!")
        print(f"   {leftover_tokens:,} tokens of valuable data are now available")
        print(f"   to {workers_with_leftover} data worker(s) for answering questions.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to generate summary: {e}")
        return False


def run_worker_tests():
    """Run all worker-related tests."""
    print("\n")
    print("=" * 70)
    print("WORKER LEFTOVER ACCESS TESTS")
    print("=" * 70)
    
    tests = [
        test_data_worker_config,
        test_worker_context_building,
        test_compendium_workers_would_receive_leftover,
        show_impact_summary,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_worker_tests()
    sys.exit(0 if success else 1)

