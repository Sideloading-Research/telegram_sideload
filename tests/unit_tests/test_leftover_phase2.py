"""
Phase 2 Test Script: Compendium Distribution and Integration
Tests that leftover content is properly distributed across compendiums
and reaches data workers correctly.
"""

import sys
from utils.mind_data_manager import MindDataManager
from config import STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT


def test_compendium_generation():
    """Test that compendiums are generated with leftover included."""
    print("\n" + "=" * 70)
    print("Test 1: Compendium Generation")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        # Generate compendiums (this will trigger logging)
        compendiums = mindfile.get_mindfile_data_packed_into_compendiums()
        
        print(f"\n✓ Generated {len(compendiums)} compendium(s)")
        
        # Check for leftover in files_dict
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if has_leftover7:
            print("✓ Leftover is present in files_dict")
            
            # Check which compendiums contain leftover
            leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
            compendiums_with_leftover = []
            
            for i, comp in enumerate(compendiums):
                if leftover_tag in comp:
                    compendiums_with_leftover.append(i)
            
            if compendiums_with_leftover:
                print(f"✓ Leftover found in {len(compendiums_with_leftover)} compendium(s)")
                print(f"  Compendium indices: {compendiums_with_leftover}")
            else:
                print("✗ Leftover NOT found in any compendium (unexpected!)")
                return False
        else:
            print("⚠ No leftover present (no truncation needed)")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entries_include_leftover():
    """Test that entries include leftover content."""
    print("\n" + "=" * 70)
    print("Test 2: Entries Include Leftover")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("⚠ No leftover present, skipping entry check")
            return True
        
        # Get entries
        entries = mindfile.get_entries()
        print(f"\n✓ Generated {len(entries)} entries")
        
        # Check how many entries contain leftover
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        entries_with_leftover = 0
        
        for entry in entries:
            if leftover_tag in entry.text:
                entries_with_leftover += 1
        
        if entries_with_leftover > 0:
            percentage = (entries_with_leftover / len(entries)) * 100
            print(f"✓ Leftover found in {entries_with_leftover} entries ({percentage:.1f}%)")
        else:
            print("✗ Leftover NOT found in any entry (unexpected!)")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_context_includes_leftover():
    """Test that full mindfile content includes leftover."""
    print("\n" + "=" * 70)
    print("Test 3: Full Context Includes Leftover")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("⚠ No leftover present, skipping context check")
            return True
        
        # Get full mindfile content
        full_content = mindfile.get_full_mindfile_content()
        
        print(f"\n✓ Full content length: {len(full_content):,} chars")
        
        # Check if leftover is in full content
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        
        if leftover_tag in full_content:
            # Calculate approximate leftover size in full content
            start_pos = full_content.find(leftover_tag)
            end_tag = f"</mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
            end_pos = full_content.find(end_tag)
            
            if start_pos != -1 and end_pos != -1:
                leftover_size = end_pos - start_pos
                print(f"✓ Leftover is present in full content (~{leftover_size:,} chars)")
            else:
                print("✓ Leftover is present in full content")
        else:
            print("✗ Leftover NOT found in full content (unexpected!)")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_worker_can_access_leftover():
    """Test that data workers can access leftover through mindfile."""
    print("\n" + "=" * 70)
    print("Test 4: Data Worker Leftover Access")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("⚠ No leftover present, skipping worker access check")
            return True
        
        # Try to access leftover as a data worker would
        leftover_content = mindfile.get_file_content(STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT)
        
        if leftover_content:
            print(f"✓ Data worker can access leftover ({len(leftover_content):,} chars)")
            
            # Verify it's actual content, not empty
            if len(leftover_content) > 100:
                print("✓ Leftover content is substantial")
            else:
                print("⚠ Leftover content seems very small")
        else:
            print("✗ Data worker cannot access leftover (empty content)")
            return False
        
        # Test getting context with leftover included
        from worker_config import WORKERS_CONFIG
        data_worker_parts = WORKERS_CONFIG["data_worker"]["mindfile_parts"]
        data_worker_parts_optional = WORKERS_CONFIG["data_worker"]["mindfile_parts_optional"]
        all_parts = data_worker_parts + data_worker_parts_optional
        
        context = mindfile.get_context(all_parts)
        
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        if leftover_tag in context:
            print("✓ Leftover is included in data worker context")
        else:
            print("⚠ Leftover not in context (may be missing from files_dict)")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_leftover_distribution_stats():
    """Display detailed statistics about leftover distribution."""
    print("\n" + "=" * 70)
    print("Test 5: Leftover Distribution Statistics")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("⚠ No leftover present, no statistics to display")
            return True
        
        # Get leftover size from file
        leftover_content = mindfile.get_file_content(STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT)
        leftover_size = len(leftover_content)
        
        # Get compendiums
        compendiums = mindfile.get_mindfile_data_packed_into_compendiums()
        
        # Analyze distribution
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        compendiums_with_leftover = []
        total_leftover_in_comps = 0
        
        for i, comp in enumerate(compendiums):
            if leftover_tag in comp:
                compendiums_with_leftover.append(i)
                # Count occurrences
                total_leftover_in_comps += comp.count(leftover_tag)
        
        print(f"\nLeftover Statistics:")
        print(f"  Original leftover file size: {leftover_size:,} chars")
        print(f"  Total compendiums: {len(compendiums)}")
        print(f"  Compendiums with leftover: {len(compendiums_with_leftover)}")
        
        if len(compendiums_with_leftover) > 0:
            coverage = (len(compendiums_with_leftover) / len(compendiums)) * 100
            print(f"  Coverage: {coverage:.1f}% of compendiums contain leftover")
            print(f"  Distribution: Leftover split across {len(compendiums_with_leftover)} worker(s)")
            
            print(f"\n✓ Leftover successfully distributed!")
        else:
            print("\n⚠ Leftover not found in compendiums")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n")
    print("=" * 70)
    print("Phase 2 Tests: Compendium Distribution and Integration")
    print("=" * 70)
    
    tests = [
        test_compendium_generation,
        test_entries_include_leftover,
        test_full_context_includes_leftover,
        test_data_worker_can_access_leftover,
        test_leftover_distribution_stats,
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
    success = run_all_tests()
    sys.exit(0 if success else 1)

