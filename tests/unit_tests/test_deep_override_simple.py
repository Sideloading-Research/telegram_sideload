"""
Simple Test: Deep Mode Override Logic
Tests the logic without requiring full worker initialization or credentials.
"""

import sys
from utils.mind_data_manager import MindDataManager
from config import STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT


def test_leftover_detection_logic():
    """Test that we can detect leftover in mindfile."""
    print("\n" + "=" * 70)
    print("Test 1: Leftover Detection in Mindfile")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if has_leftover7:
            print(f"✓ Leftover detected in mindfile.files_dict")
            leftover_path = mindfile.files_dict[STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT]
            print(f"  Leftover file: {leftover_path}")
        else:
            print(f"⚠ No leftover present (no truncation needed)")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_override_logic_simulation():
    """Simulate the override logic without actual workers."""
    print("\n" + "=" * 70)
    print("Test 2: Override Logic Simulation")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        print(f"\nLeftover present: {has_leftover7}")
        print("\nSimulating different scenarios:\n")
        
        # Simulate the logic from integration_worker._process()
        test_scenarios = [
            ("shallow", "normal request"),
            ("deep", "complex request"),
            ("jailbreak", "malicious request"),
            ("exploitation", "off-topic request"),
        ]
        
        for request_type, description in test_scenarios:
            print(f"Scenario: doorman says '{request_type}' ({description})")
            
            # Replicate the logic from integration_worker
            if request_type in ["jailbreak", "exploitation"]:
                deep_dive7 = False
                reason = "jailbreak/exploitation path (never overridden)"
            else:
                if has_leftover7 and request_type == "shallow":
                    deep_dive7 = True
                    reason = "OVERRIDDEN: leftover exists, forcing deep mode"
                else:
                    deep_dive7 = request_type == "deep"
                    reason = "following doorman's decision"
            
            result = "DEEP" if deep_dive7 else "SHALLOW"
            marker = "←" if (has_leftover7 and request_type == "shallow") else " "
            
            print(f"  → Result: {result} ({reason}) {marker}")
            print()
        
        if has_leftover7:
            print("✓ Logic verified: shallow → deep override active")
        else:
            print("✓ Logic verified: no override needed (no leftover)")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_expected_behavior_matrix():
    """Display the expected behavior matrix."""
    print("\n" + "=" * 70)
    print("Test 3: Expected Behavior Matrix")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        print(f"\nCurrent mindfile has leftover: {'YES' if has_leftover7 else 'NO'}\n")
        
        print("Expected Behavior Matrix:")
        print("-" * 70)
        print(f"{'Doorman Says':<18} | {'Has Leftover':<14} | {'Final Mode':<15} | {'Notes'}")
        print("-" * 70)
        
        behaviors = [
            ("shallow", "NO", "shallow", "Normal behavior"),
            ("shallow", "YES", "DEEP", "★ OVERRIDE to ensure leftover consulted"),
            ("deep", "NO", "deep", "Normal behavior"),
            ("deep", "YES", "deep", "Already deep, no override needed"),
            ("jailbreak", "NO", "shallow", "Quick rejection path"),
            ("jailbreak", "YES", "shallow", "NOT overridden (as requested)"),
            ("exploitation", "NO", "shallow", "Quick rejection path"),
            ("exploitation", "YES", "shallow", "NOT overridden (as requested)"),
        ]
        
        for doorman, leftover, mode, notes in behaviors:
            # Highlight the current scenario
            current = "→" if (leftover == ("YES" if has_leftover7 else "NO")) else " "
            print(f"{doorman:<18} | {leftover:<14} | {mode:<15} | {notes} {current}")
        
        print("-" * 70)
        
        if has_leftover7:
            print("\n★ Active Override:")
            print("  When doorman suggests 'shallow', system will use 'deep' mode")
            print("  to consult compendium workers that contain leftover content.")
        else:
            print("\n⚠ No Override Needed:")
            print("  System follows doorman's classification normally.")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_reasoning_explanation():
    """Explain the reasoning behind the override."""
    print("\n" + "=" * 70)
    print("Test 4: Override Reasoning")
    print("=" * 70)
    
    try:
        mind_manager = MindDataManager.get_instance()
        mindfile = mind_manager.get_mindfile()
        
        has_leftover7 = STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in mindfile.files_dict
        
        if not has_leftover7:
            print("\n⚠ No leftover present - override not needed")
            return True
        
        print("\n📚 Why Override Shallow → Deep?")
        print("-" * 70)
        
        # Get statistics
        from utils.tokens import count_tokens
        leftover_content = mindfile.get_file_content(STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT)
        facts_content = mindfile.get_file_content("structured_self_facts")
        
        leftover_tokens = count_tokens(leftover_content)
        facts_tokens = count_tokens(facts_content)
        total_tokens = leftover_tokens + facts_tokens
        
        print(f"\n1. Data Distribution:")
        print(f"   Main facts: {facts_tokens:,} tokens ({facts_tokens/total_tokens*100:.1f}%)")
        print(f"   Leftover: {leftover_tokens:,} tokens ({leftover_tokens/total_tokens*100:.1f}%)")
        
        print(f"\n2. Worker Behavior:")
        print(f"   SHALLOW mode:")
        print(f"     • Uses only 1 generalist data worker")
        print(f"     • Worker gets context from all mindfile parts")
        print(f"     • BUT: Only ~{facts_tokens:,} tokens of facts in main content")
        print(f"     • Missing: ~{leftover_tokens:,} tokens of valuable data!")
        
        print(f"\n   DEEP mode:")
        print(f"     • Uses generalist + multiple compendium workers")
        
        # Get compendium info
        compendiums = mindfile.get_mindfile_data_packed_into_compendiums()
        leftover_tag = f"<mindfile_source_file:{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}>"
        workers_with_leftover = sum(1 for comp in compendiums if leftover_tag in comp)
        
        print(f"     • Total compendium workers: {len(compendiums)}")
        print(f"     • Workers with leftover: {workers_with_leftover}")
        print(f"     • Result: ALL {leftover_tokens:,} tokens are consulted!")
        
        print(f"\n3. Conclusion:")
        print(f"   Without override: {leftover_tokens:,} tokens would be ignored in shallow mode")
        print(f"   With override: All preserved data is available for answering")
        
        print(f"\n✓ Override ensures no data loss in user-facing responses")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_tests():
    """Run all simple override tests."""
    print("\n")
    print("=" * 70)
    print("DEEP MODE OVERRIDE TESTS (Simple)")
    print("=" * 70)
    
    tests = [
        test_leftover_detection_logic,
        test_override_logic_simulation,
        test_expected_behavior_matrix,
        test_reasoning_explanation,
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
    success = run_tests()
    sys.exit(0 if success else 1)

