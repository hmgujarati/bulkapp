#!/usr/bin/env python3
"""
Test authentication and file upload as specified in the review request
"""
import requests
import sys

def test_auth_and_upload():
    base_url = "https://easywasend-1.preview.emergentagent.com"
    
    print("🔐 Testing Authentication Flow")
    print("=" * 40)
    
    # Step 1: Login with specified credentials
    print("1. Testing login with bizchatapi@gmail.com / adminpassword")
    login_url = f"{base_url}/api/auth/login"
    login_data = {
        "email": "bizchatapi@gmail.com",
        "password": "adminpassword"
    }
    
    try:
        response = requests.post(login_url, json=login_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            token = result['token']
            print(f"✅ Login successful")
            print(f"   Token: {token[:30]}...")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False
    
    print(f"\n📁 Testing File Upload with Authentication")
    print("=" * 50)
    
    # Step 2: Test file upload with different sizes and media types
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test cases as specified in review request
    test_cases = [
        {
            "name": "Small Image (2MB) - Should Succeed",
            "media_type": "image",
            "size_mb": 2.0,
            "expected_status": 200,
            "filename": "small_image.png",
            "mime_type": "image/png"
        },
        {
            "name": "Large Image (6MB) - Should Fail",
            "media_type": "image", 
            "size_mb": 6.0,
            "expected_status": 400,
            "filename": "large_image.png",
            "mime_type": "image/png"
        },
        {
            "name": "Small Video (8MB) - Should Succeed",
            "media_type": "video",
            "size_mb": 8.0,
            "expected_status": 200,
            "filename": "small_video.mp4",
            "mime_type": "video/mp4"
        },
        {
            "name": "Large Video (20MB) - Should Fail",
            "media_type": "video",
            "size_mb": 20.0,
            "expected_status": 400,
            "filename": "large_video.mp4",
            "mime_type": "video/mp4"
        },
        {
            "name": "Small Document (3MB) - Should Succeed",
            "media_type": "document",
            "size_mb": 3.0,
            "expected_status": 200,
            "filename": "small_doc.pdf",
            "mime_type": "application/pdf"
        },
        {
            "name": "Large Document (15MB) - Should Fail",
            "media_type": "document",
            "size_mb": 15.0,
            "expected_status": 400,
            "filename": "large_doc.pdf",
            "mime_type": "application/pdf"
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        
        # Create test file data
        size_bytes = int(test_case['size_mb'] * 1024 * 1024)
        file_data = b'X' * size_bytes  # Simple file content
        
        # Upload file
        upload_url = f"{base_url}/api/upload/media"
        files = {
            'file': (test_case['filename'], file_data, test_case['mime_type'])
        }
        params = {'media_type': test_case['media_type']}
        
        try:
            response = requests.post(upload_url, files=files, headers=headers, params=params, timeout=60)
            
            print(f"   File size: {test_case['size_mb']}MB")
            print(f"   Media type: {test_case['media_type']}")
            print(f"   Expected: {test_case['expected_status']}")
            print(f"   Actual: {response.status_code}")
            
            if response.status_code == test_case['expected_status']:
                print(f"   ✅ PASSED")
                passed_tests += 1
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   Upload URL: {result.get('url', 'N/A')}")
                elif response.status_code == 400:
                    result = response.json()
                    print(f"   Error: {result.get('detail', 'N/A')}")
            else:
                print(f"   ❌ FAILED")
                print(f"   Response: {response.text[:150]}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
    
    print(f"\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"=" * 50)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print(f"🎉 ALL TESTS PASSED - File size limits working correctly!")
        return True
    else:
        print(f"❌ Some tests failed")
        return False

def main():
    success = test_auth_and_upload()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())