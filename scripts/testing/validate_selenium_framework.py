#!/usr/bin/env python3
"""
Selenium Testing Framework Validation Script

This script validates that the selenium testing framework is properly set up
and all components are working correctly.
"""

import sys
import subprocess
import importlib
import os
from pathlib import Path

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message, status="INFO"):
    color = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "ERROR": Colors.RED,
        "WARNING": Colors.YELLOW
    }.get(status, Colors.BLUE)
    print(f"{color}[{status}]{Colors.END} {message}")

def check_python_packages():
    """Check if required Python packages are installed."""
    print_status("Checking Python packages...")
    
    required_packages = [
        "pytest",
        "selenium", 
        "requests"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print_status(f"✓ {package}", "SUCCESS")
        except ImportError:
            print_status(f"✗ {package} not found", "ERROR")
            missing_packages.append(package)
    
    if missing_packages:
        print_status(f"Missing packages: {', '.join(missing_packages)}", "ERROR")
        return False
    
    print_status("All required packages installed", "SUCCESS")
    return True

def check_test_structure():
    """Check if test directory structure is correct."""
    print_status("Checking test directory structure...")
    
    project_root = Path(__file__).parent.parent.parent
    expected_files = [
        "tests/selenium/__init__.py",
        "tests/selenium/conftest.py",
        "pytest.ini"
    ]
    
    missing_files = []
    
    for file_path in expected_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_status(f"✓ {file_path}", "SUCCESS")
        else:
            print_status(f"✗ {file_path} not found", "ERROR")
            missing_files.append(file_path)
    
    if missing_files:
        print_status(f"Missing files: {len(missing_files)}", "ERROR")
        return False
    
    print_status("Test structure is correct", "SUCCESS")
    return True

def main():
    """Main validation function."""
    print_status("=== Selenium Testing Framework Validation ===", "INFO")
    print()
    
    checks = [
        ("Python Packages", check_python_packages),
        ("Test Structure", check_test_structure),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print_status(f"Running {check_name} check...", "INFO")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print_status(f"✗ {check_name} check failed with exception: {str(e)}", "ERROR")
            results.append((check_name, False))
        print()
    
    # Summary
    print_status("=== Validation Summary ===", "INFO")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "PASS" if result else "FAIL"
        color = "SUCCESS" if result else "ERROR"
        print_status(f"{check_name}: {status}", color)
    
    print()
    print_status(f"Overall: {passed}/{total} checks passed", 
                "SUCCESS" if passed == total else "ERROR")
    
    if passed == total:
        print_status("🎉 Selenium testing framework is ready!", "SUCCESS")
        return True
    else:
        print_status("❌ Some checks failed. Please fix the issues above.", "ERROR")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)