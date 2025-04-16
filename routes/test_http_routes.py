#!/usr/bin/env python3
"""
Simple test script to verify HTTP routes are working
"""
import requests
import time
import sys

def test_route(url, name):
    """Test a route and print result"""
    try:
        print(f"Testing {name} route: {url}")
        response = requests.get(url, timeout=5)
        print(f"Response code: {response.status_code}")
        print(f"Response: {response.text[:100]}")
        print("-" * 40)
        return True
    except Exception as e:
        print(f"Error testing {name} route: {e}")
        print("-" * 40)
        return False

def main():
    """Test all routes"""
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5)
    
    # Base URL
    base_url = "http://localhost:5000"
    
    # Test routes
    routes = [
        ("health-check", "/health-check"),
        ("basic-test", "/basic-test"),
        ("diagnostic", "/diagnostic"),
        ("backtest", "/backtest")
    ]
    
    success = 0
    total = len(routes)
    
    for name, path in routes:
        if test_route(f"{base_url}{path}", name):
            success += 1
    
    print(f"Results: {success}/{total} routes working")
    
    if success == total:
        print("All routes are working correctly!")
        return 0
    else:
        print("Some routes are not working properly.")
        return 1

if __name__ == "__main__":
    sys.exit(main())