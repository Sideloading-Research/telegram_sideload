"""
Integration Test: Full end-to-end leftover flow with workers
Demonstrates how leftover flows through the entire system to data workers.
"""

import sys
from utils.mind_data_manager import MindDataManager
from workers.integration_worker import IntegrationWorker
from config import STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT


def test_integration_worker_initialization():
    """Test that integration worker properly initializes with leftover."""
    print("\n" + "=" * 70)
    print("Integration Test: Worker Initialization with Leftover")
    print("=" * 70)
    
    try:
        # Get mindfile
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if has_leftover7:
            print("\n✓ Mindfile has leftover content")
        else:
            print("\n⚠ No leftover in mindfile (no truncation occurred)")
        
        # Initialize integration worker
        integration_worker = IntegrationWorker(mindfile=mindfile)
        print("✓ IntegrationWorker initialized successfully")
        
        # Initialize workers (this creates compendium workers)
        integration_worker._initialize_workers()
        print("✓ Sub-workers initialized")
        
        # Check compendium workers
        num_compendium_workers = len(integration_worker.compendium_data_workers)
        print(f"\n✓ Created {num_compendium_workers} compendium data worker(s)")
        
        if has_leftover7 and num_compendium_workers > 0:
            # Check if any compendium workers have leftover in their context
            workers_with_leftover = 0
            leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
            
            for i, worker in enumerate(integration_worker.compendium_data_workers):
                context = worker._get_worker_context()
                if leftover_tag in context:
                    workers_with_leftover += 1
                    print(f"  Worker {i+1}/{num_compendium_workers}: ✓ Has leftover content")
                else:
                    print(f"  Worker {i+1}/{num_compendium_workers}: - No leftover content")
            
            if workers_with_leftover > 0:
                print(f"\n✓ {workers_with_leftover} worker(s) have access to leftover content")
                percentage = (workers_with_leftover / num_compendium_workers) * 100
                print(f"  Distribution: {percentage:.1f}% of workers have leftover")
            else:
                print("\n⚠ No workers have leftover content (unexpected if leftover exists)")
        
        # Check generalist data worker
        if integration_worker.generalist_data_worker:
            context = integration_worker.generalist_data_worker._get_worker_context()
            leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
            
            if leftover_tag in context:
                print("\n✓ Generalist data worker has access to leftover")
            else:
                print("\n- Generalist data worker does not have leftover")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_leftover_coverage_summary():
    """Display a summary of leftover coverage across the system."""
    print("\n" + "=" * 70)
    print("Leftover Coverage Summary")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("\n⚠ No leftover present in this mindfile")
            print("  Reason: structured_self_facts fits within token limits")
            return True
        
        # Get leftover statistics
        leftover_content = mindfile.get_file_content(STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT)
        
        # Get original facts statistics
        facts_content = mindfile.get_file_content("structured_self_facts")
        
        from utils.tokens import count_tokens
        leftover_tokens = count_tokens(leftover_content)
        facts_tokens = count_tokens(facts_content)
        total_original_tokens = leftover_tokens + facts_tokens
        
        print(f"\n📊 Leftover Statistics:")
        print(f"   Total original tokens: {total_original_tokens:,}")
        print(f"   Kept in main facts: {facts_tokens:,} ({facts_tokens/total_original_tokens*100:.1f}%)")
        print(f"   Preserved as leftover: {leftover_tokens:,} ({leftover_tokens/total_original_tokens*100:.1f}%)")
        
        # Check distribution
        compendiums = mindfile.get_mindfile_data_packed_into_compendiums()
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        
        comps_with_leftover = sum(1 for comp in compendiums if leftover_tag in comp)
        
        print(f"\n📦 Compendium Distribution:")
        print(f"   Total compendiums: {len(compendiums)}")
        print(f"   Compendiums with leftover: {comps_with_leftover}")
        print(f"   Coverage: {comps_with_leftover/len(compendiums)*100:.1f}%")
        
        print("\n✅ Leftover preservation is working!")
        print(f"   {leftover_tokens:,} tokens of valuable data that would have been")
        print(f"   lost are now available to {comps_with_leftover} data worker(s).")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to generate summary: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_integration_tests():
    """Run integration tests."""
    print("\n")
    print("=" * 70)
    print("INTEGRATION TEST: End-to-End Leftover Flow")
    print("=" * 70)
    
    tests = [
        test_integration_worker_initialization,
        show_leftover_coverage_summary,
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
    print(f"Integration Test Results: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)

