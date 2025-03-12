#!/usr/bin/env python3
"""
Script to run all tests for the Montreal Parking Finder.
"""

import unittest
import os
import sys
import argparse

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def main():
    """
    Main entry point for running tests.
    """
    parser = argparse.ArgumentParser(
        description='Run tests for the Montreal Parking Finder'
    )
    
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Run tests in verbose mode'
    )
    
    parser.add_argument(
        '--module', '-m', 
        help='Run tests for a specific module (e.g., parser, distance)'
    )
    
    args = parser.parse_args()
    
    # Discover and run tests
    if args.module:
        test_pattern = f'test_{args.module}.py'
    else:
        test_pattern = 'test_*.py'
    
    test_suite = unittest.defaultTestLoader.discover('tests', pattern=test_pattern)
    
    test_runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = test_runner.run(test_suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
