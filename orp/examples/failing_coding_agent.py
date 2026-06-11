#!/usr/bin/env python3
"""Example failing coding agent — simulates a buggy agent for ORP testing"""

import sys


def fix_authentication():
    """Simulates fixing an auth bug — but misses the anonymous user path"""
    # This "fix" only covers logged-in users
    print("Fixing authentication controller...")
    print("Added null check for authenticated user")
    print("Running tests...")
    print("pytest: 34 passed, 1 failed")
    print("FAILED tests/test_anonymous_access.py::test_anonymous_user_get_name")
    sys.exit(1)


def fix_with_tests_first():
    """Alternative strategy: write tests first, then fix"""
    print("Step 1: Writing anonymous user regression test...")
    print("tests/test_anonymous_access.py written")
    print("Step 2: Running test to confirm failure...")
    print("FAILED as expected — test reproduces the bug")
    print("Step 3: Fixing the implementation...")
    print("Added null check for anonymous user")
    print("Step 4: Running all tests...")
    print("pytest: 35 passed, 0 failed")
    print("All tests pass!")
    sys.exit(0)


if __name__ == "__main__":
    # By default, simulate the failing path
    mode = sys.argv[1] if len(sys.argv) > 1 else "failing"
    if mode == "failing":
        fix_authentication()
    else:
        fix_with_tests_first()
