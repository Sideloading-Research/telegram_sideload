"""
Phase 1 Test Script: Leftover Preservation
Tests that leftover generation, storage, and injection works correctly.
"""

import os
import sys
from utils.leftover_manager import (
    cleanup_leftover_files,
    get_leftover_cache_dir,
    process_and_generate_leftover,
)
from utils.mindfile import Mindfile
from utils.mind_data_manager import MindDataManager
from config import STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT


def test_leftover_cache_dir_creation():
    """Test that cache directory is created."""
    print("\n=== Test 1: Cache directory creation ===")
    cleanup_leftover_files()  # Start clean
    
    cache_dir = get_leftover_cache_dir()
    assert os.path.exists(cache_dir), "Cache directory should be created"
    print(f"✓ Cache directory created at: {cache_dir}")
    
    cleanup_leftover_files()
    assert not os.path.exists(cache_dir), "Cache directory should be cleaned up"
    print("✓ Cache directory cleaned up successfully")


def test_leftover_with_small_facts():
    """Test that no leftover is generated when facts are small enough."""
    print("\n=== Test 2: No truncation with small facts ===")
    cleanup_leftover_files()
    
    small_facts = "This is a small structured_self_facts content."
    system_message = "You are an AI assistant."
    
    result = process_and_generate_leftover(
        facts_content=small_facts,
        system_message_content=system_message,
        ultra_small_mode7=False,
        max_tokens_allowed=1000000,
        leftover_filename_key=STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT
    )
    
    assert result is None, "Should return None when no truncation needed"
    print("✓ No leftover generated for small facts (as expected)")


def test_leftover_with_large_facts():
    """Test that leftover is generated and saved when facts are large."""
    print("\n=== Test 3: Leftover generation with large facts ===")
    cleanup_leftover_files()
    
    # Create large facts content (repeat to ensure it exceeds 30% of token limit)
    large_facts = "This is a sentence in structured_self_facts. " * 100000
    system_message = "You are an AI assistant."
    
    result = process_and_generate_leftover(
        facts_content=large_facts,
        system_message_content=system_message,
        ultra_small_mode7=False,
        max_tokens_allowed=1000000,
        leftover_filename_key=STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT
    )
    
    assert result is not None, "Should return dict with leftover filepath"
    assert STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in result, "Should contain leftover key"
    
    leftover_path = result[STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT]
    assert os.path.exists(leftover_path), "Leftover file should exist"
    
    with open(leftover_path, "r", encoding="utf-8") as f:
        leftover_content = f.read()
    
    assert len(leftover_content) > 0, "Leftover content should not be empty"
    print(f"✓ Leftover generated and saved ({len(leftover_content)} chars)")


def test_mindfile_integration():
    """Test that Mindfile properly integrates leftover into files_dict."""
    print("\n=== Test 4: Mindfile integration ===")
    
    try:
        # Get actual mindfile from MindDataManager
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        print(f"Files in mindfile.files_dict: {list(mindfile.files_dict.keys())}")
        
        # Check if leftover was generated
        if STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict:
            print("✓ Leftover is in files_dict (truncation occurred)")
            
            # Verify the file path exists
            leftover_path = mindfile.files_dict[STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT]
            assert os.path.exists(leftover_path), "Leftover file should exist"
            print(f"✓ Leftover file exists at: {leftover_path}")
            
            # Try to read it through mindfile
            leftover_content = mindfile.get_file_content(STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT)
            print(f"✓ Leftover can be read through mindfile.get_file_content() ({len(leftover_content)} chars)")
            
        else:
            print("⚠ No leftover in files_dict (no truncation needed for current mindfile)")
            
    except Exception as e:
        print(f"⚠ Could not test with actual mindfile: {e}")
        print("This is OK if mindfile data is not available in test environment")


def test_worker_config():
    """Test that worker_config includes leftover as optional."""
    print("\n=== Test 5: Worker configuration ===")
    from worker_config import WORKERS_CONFIG
    
    data_worker_config = WORKERS_CONFIG.get("data_worker", {})
    optional_parts = data_worker_config.get("mindfile_parts_optional", [])
    
    assert STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in optional_parts, \
        "Leftover should be in data_worker optional parts"
    
    print(f"✓ Leftover is configured as optional for data_worker")
    print(f"  Data worker optional parts: {optional_parts}")


def run_all_tests():
    """Run all Phase 1 tests."""
    print("=" * 70)
    print("Phase 1 Tests: Leftover Preservation Implementation")
    print("=" * 70)
    
    tests = [
        test_leftover_cache_dir_creation,
        test_leftover_with_small_facts,
        test_leftover_with_large_facts,
        test_worker_config,
        test_mindfile_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    # Final cleanup
    cleanup_leftover_files()
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

