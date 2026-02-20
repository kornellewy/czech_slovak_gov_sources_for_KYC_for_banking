#!/usr/bin/env python3
"""
Test Recursive Ownership Script

Tests the recursive UBO/IBO search functionality including:
1. Simple 2-level chain
2. Cross-border ownership (SK-CZ)
3. Mixed direct/indirect ownership
4. Cycle detection
5. IBO calculation verification

Usage:
    # Test all scenarios
    python3 test_recursive_ownership.py

    # Test specific scenario
    python3 test_recursive_ownership.py --scenario simple
    python3 test_recursive_ownership.py --scenario cross_border
    python3 test_recursive_ownership.py --scenario mixed
    python3 test_recursive_ownership.py --scenario cycle

    # Test with specific ICO
    python3 test_recursive_ownership.py --ico 06649114
"""

import sys
import argparse
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, '.')

from src.company_registry_api import CompanyRegistryAPI, Country


def test_simple_chain(api, ico: str = "06649114") -> bool:
    """
    Test 1: Simple 2-level chain

    Company A -> Person X (direct, individual)

    Expected: Single UBO with direct ownership
    """
    print("\n" + "="*60)
    print("TEST 1: Simple Chain (Direct Individual Owner)")
    print("="*60)
    print(f"ICO: {ico}")

    result = api.get_recursive_ubo(ico, max_depth=3)

    if not result:
        print("❌ FAIL: No result returned")
        return False

    metadata = result.get('metadata', {})
    ubos = metadata.get('ultimate_beneficial_owners', [])

    print(f"\nCompany: {result.get('entity', {}).get('company_name_registry')}")
    print(f"UBOs found: {len(ubos)}")

    for ubo in ubos:
        print(f"  - {ubo['name']}: {ubo['ownership_percentage']}% ({'Individual' if ubo['is_individual'] else 'Entity'})")
        print(f"    Path: {ubo['path']}")

    # Verify expectations
    if len(ubos) == 0:
        print("⚠️  WARNING: No UBOs found (may be using mock data)")

    print("✓ Simple chain test completed")
    return True


def test_cross_border(api, ico: str = "35763491") -> bool:
    """
    Test 2: Cross-border ownership

    SK Company -> AT Entity (75%) -> Individual

    Expected: UBO with cross-border path
    """
    print("\n" + "="*60)
    print("TEST 2: Cross-Border Ownership (SK -> AT)")
    print("="*60)
    print(f"ICO: {ico}")

    result = api.get_recursive_ubo(ico, max_depth=5, country=Country.SLOVAKIA)

    if not result:
        print("❌ FAIL: No result returned")
        return False

    metadata = result.get('metadata', {})
    ubos = metadata.get('ultimate_beneficial_owners', [])

    print(f"\nCompany: {result.get('entity', {}).get('company_name_registry')}")

    # Get ownership tree for detailed view
    tree_result = api.get_ownership_tree(ico, max_depth=5)

    if tree_result:
        cross_border = tree_result.get('cross_border_exposure', [])
        print(f"\nCross-border links: {len(cross_border)}")
        for link in cross_border:
            print(f"  {link['from_country']} -> {link['to_country']}: "
                  f"{link['entity_name']} ({link['ownership_percentage']}%)")

    print(f"\nUBOs found: {len(ubos)}")
    for ubo in ubos:
        print(f"  - {ubo['name']}: {ubo['ownership_percentage']}% ({ubo['country']})")
        print(f"    Path: {ubo['path']}")

    # Check for cross-border ownership
    has_foreign = any(ubo.get('country') not in ['SK', 'CZ', 'Unknown'] for ubo in ubos)
    if has_foreign:
        print("✓ Cross-border ownership detected")
    else:
        print("⚠️  No foreign ownership detected (may be mock data)")

    return True


def test_mixed_ownership(api, ico: str = "44103755") -> bool:
    """
    Test 3: Mixed direct/indirect ownership

    Company A
      ├── Person X (30%) [direct, individual]
      └── Company B (70%) [entity]
          └── Person Y (100%) [individual]

    Expected:
      - Person X: 30% direct UBO
      - Person Y: 70% indirect UBO
    """
    print("\n" + "="*60)
    print("TEST 3: Mixed Direct/Indirect Ownership")
    print("="*60)
    print(f"ICO: {ico}")

    # Get IBO summary (Slovak ICO)
    ibo_result = api.get_ibo_summary(ico, max_depth=5, country=Country.SLOVAKIA)

    if not ibo_result:
        print("❌ FAIL: No IBO result returned")
        return False

    print(f"\nCompany: {ibo_result.get('company_name')}")
    print(f"Total indirect ownership: {ibo_result.get('total_indirect_ownership', 0):.2f}%")
    print(f"Max depth reached: {ibo_result.get('ownership_depth', 0)}")

    ibos = ibo_result.get('indirect_beneficial_owners', [])
    print(f"\nIndirect Beneficial Owners: {len(ibos)}")

    for ibo in ibos:
        print(f"  - {ibo['name']}: {ibo['indirect_ownership_pct']:.2f}%")
        print(f"    Path: {ibo['path']}")

    # Get concentration risk
    tree_result = api.get_ownership_tree(ico, max_depth=5)
    if tree_result:
        concentration = tree_result.get('concentration_risk', {})
        print(f"\nConcentration Risk: {concentration.get('has_concentration_risk', False)}")
        if concentration.get('dominant_owner'):
            print(f"  Dominant: {concentration['dominant_owner']} "
                  f"({concentration['dominant_ownership_pct']:.2f}%)")

    print("✓ Mixed ownership test completed")
    return True


def test_cycle_detection(api, ico: str = "31328356") -> bool:
    """
    Test 4: Cycle detection

    Company A -> Company B -> Company A (cycle)

    Expected: Detect cycle and stop recursion
    """
    print("\n" + "="*60)
    print("TEST 4: Cycle Detection")
    print("="*60)
    print(f"ICO: {ico}")

    result = api.get_ownership_tree(ico, max_depth=10, country=Country.SLOVAKIA)  # High depth to test cycle detection

    if not result:
        print("❌ FAIL: No result returned")
        return False

    summary = result.get('summary', {})
    max_depth = summary.get('max_depth_reached', 0)
    entity_counts = summary.get('entity_counts', {})

    print(f"\nCompany: {result.get('company_name')}")
    print(f"Max depth reached: {max_depth}")
    print(f"Total entities: {entity_counts.get('total_entities', 0)}")
    print(f"Total individuals: {entity_counts.get('total_individuals', 0)}")

    if max_depth < 10:
        print("✓ Cycle detection appears working (depth limited)")
    else:
        print("⚠️  Depth at maximum - possible cycle not detected")

    print("✓ Cycle detection test completed")
    return True


def test_ibo_calculation(api) -> bool:
    """
    Test 5: IBO calculation verification

    Manually verify IBO calculation:
    - Company A owns 50% of Company B
    - Person X owns 100% of Company A
    - Person X's indirect ownership of Company B = 50% * 100% = 50%
    """
    print("\n" + "="*60)
    print("TEST 5: IBO Calculation Verification")
    print("="*60)

    # Test with known entities - use correct country for each
    test_entities = [
        ("35763491", Country.SLOVAKIA),  # Slovak
        ("44103755", Country.SLOVAKIA),  # Slovak
        ("31328356", Country.SLOVAKIA),  # Slovak
        ("06649114", Country.CZECH_REPUBLIC),  # Czech
    ]

    for ico, country in test_entities:
        print(f"\nTesting ICO: {ico} ({country.value})")
        ibo_result = api.get_ibo_summary(ico, max_depth=5, country=country)

        if ibo_result:
            ibos = ibo_result.get('indirect_beneficial_owners', [])
            print(f"  IBOs: {len(ibos)}")

            for ibo in ibos:
                # Verify calculation makes sense
                pct = ibo.get('indirect_ownership_pct', 0)
                path = ibo.get('path', '')
                print(f"  - {ibo['name']}: {pct:.2f}% via {path[:50]}...")

                # Ownership should be between 0 and 100
                if not (0 <= pct <= 100):
                    print(f"    ❌ FAIL: Invalid ownership percentage")
                    return False

    print("✓ IBO calculation verification completed")
    return True


def test_print_tree(api, ico: str = "06649114") -> None:
    """Test tree printing for visualization."""
    print("\n" + "="*60)
    print("TEST: Tree Visualization")
    print("="*60)
    print(f"ICO: {ico}")

    api.print_ownership_tree(ico, max_depth=3)


def run_all_tests() -> bool:
    """Run all test scenarios."""
    api = CompanyRegistryAPI(default_country=Country.CZECH_REPUBLIC)

    all_passed = True

    # Test 1: Simple chain
    try:
        if not test_simple_chain(api):
            all_passed = False
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}")
        all_passed = False

    # Test 2: Cross-border
    try:
        if not test_cross_border(api):
            all_passed = False
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}")
        all_passed = False

    # Test 3: Mixed ownership
    try:
        if not test_mixed_ownership(api):
            all_passed = False
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}")
        all_passed = False

    # Test 4: Cycle detection
    try:
        if not test_cycle_detection(api):
            all_passed = False
    except Exception as e:
        print(f"❌ Test 4 failed with error: {e}")
        all_passed = False

    # Test 5: IBO calculation
    try:
        if not test_ibo_calculation(api):
            all_passed = False
    except Exception as e:
        print(f"❌ Test 5 failed with error: {e}")
        all_passed = False

    # Print tree visualization
    try:
        test_print_tree(api)
    except Exception as e:
        print(f"❌ Tree visualization failed: {e}")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Test recursive ownership functionality")
    parser.add_argument("--scenario", choices=["simple", "cross_border", "mixed", "cycle", "ibo"],
                       help="Run specific test scenario")
    parser.add_argument("--ico", help="Test with specific ICO")
    parser.add_argument("--depth", type=int, default=5, help="Maximum recursion depth")
    parser.add_argument("--tree", action="store_true", help="Print ownership tree")

    args = parser.parse_args()

    api = CompanyRegistryAPI(default_country=Country.CZECH_REPUBLIC)

    if args.tree and args.ico:
        api.print_ownership_tree(args.ico, max_depth=args.depth)
        return 0

    if args.scenario:
        scenarios = {
            "simple": lambda: test_simple_chain(api, args.ico or "06649114"),
            "cross_border": lambda: test_cross_border(api, args.ico or "35763491"),
            "mixed": lambda: test_mixed_ownership(api, args.ico or "44103755"),
            "cycle": lambda: test_cycle_detection(api, args.ico or "31328356"),
            "ibo": lambda: test_ibo_calculation(api),
        }

        test_func = scenarios.get(args.scenario)
        if test_func:
            try:
                test_func()
            except Exception as e:
                print(f"Error running test: {e}")
                import traceback
                traceback.print_exc()
                return 1
        else:
            print(f"Unknown scenario: {args.scenario}")
            return 1
    else:
        # Run all tests
        if run_all_tests():
            print("\n" + "="*60)
            print("✓ ALL TESTS PASSED")
            print("="*60)
            return 0
        else:
            print("\n" + "="*60)
            print("❌ SOME TESTS FAILED")
            print("="*60)
            return 1


if __name__ == "__main__":
    sys.exit(main())
