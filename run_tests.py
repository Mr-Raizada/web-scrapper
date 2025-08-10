#!/usr/bin/env python3
"""
Test runner for the Web Scraper Test API
"""

import subprocess
import sys
import os

def run_tests():
    """Run the pytest tests"""
    print("🧪 Running Web Scraper Tests")
    print("=" * 40)
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"])
    
    # Run tests
    print("🚀 Starting tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "--asyncio-mode=auto"
    ])
    
    if result.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    return result.returncode

def run_specific_test(test_name):
    """Run a specific test"""
    print(f"🧪 Running specific test: {test_name}")
    print("=" * 40)
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        f"tests/test_scraping.py::{test_name}",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])
    
    return result.returncode

def run_quick_tests():
    """Run only quick tests (skip slow ones)"""
    print("⚡ Running quick tests only...")
    print("=" * 40)
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-m", "not slow"
    ])
    
    return result.returncode

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "quick":
            return run_quick_tests()
        elif command == "specific" and len(sys.argv) > 2:
            return run_specific_test(sys.argv[2])
        else:
            print("Usage:")
            print("  python run_tests.py          # Run all tests")
            print("  python run_tests.py quick    # Run quick tests only")
            print("  python run_tests.py specific TestClassName::test_method  # Run specific test")
            return 1
    else:
        return run_tests()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 