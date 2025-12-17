#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import WhatsAppBulkMessengerTester

def main():
    print("🚀 Testing NEW FEATURES - December 2024")
    print("=" * 60)
    
    tester = WhatsAppBulkMessengerTester()
    
    # Login first
    print("\n📋 AUTHENTICATION")
    print("-" * 20)
    if not tester.test_admin_login():
        print("❌ Failed to login as admin")
        return 1
    
    # NEW FEATURE TESTS
    print("\n🆕 NEW FEATURE TESTS - DECEMBER 2024")
    print("-" * 45)
    
    test_results = []
    
    # Test 1: Scheduled Campaign Daily Limit Bypass
    result1 = tester.test_scheduled_campaign_future_date_daily_limit_bypass()
    test_results.append(("Scheduled Campaign Daily Limit Bypass", result1))
    
    # Test 2: Message Sending Performance Verification
    result2 = tester.test_message_sending_performance_verification()
    test_results.append(("Message Sending Performance Verification", result2))
    
    # Test 3: Same-Day Limit Enforcement (for comparison)
    result3 = tester.test_scheduled_campaign_same_day_limit_enforcement()
    test_results.append(("Same-Day Scheduled Campaign Limit Enforcement", result3))
    
    # Print Results
    print("\n" + "=" * 60)
    print("📊 NEW FEATURE TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nTests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed / total * 100):.1f}%")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())