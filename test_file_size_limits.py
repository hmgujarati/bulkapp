#!/usr/bin/env python3
"""
Focused test for file size limits in WhatsApp Bulk Messenger
"""
import requests
import sys

class FileSizeLimitTester:
    def __init__(self, base_url="https://easywasend-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def login(self):
        """Login to get authentication token"""
        url = f"{self.base_url}/api/auth/login"
        data = {"email": "bizchatapi@gmail.com", "password": "adminpassword"}
        
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                self.token = result['token']
                print(f"✅ Login successful, token obtained")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False

    def create_test_file(self, size_mb, file_type="image"):
        """Create a test file of specified size in MB"""
        size_bytes = int(size_mb * 1024 * 1024)
        
        if file_type == "image":
            # Create a minimal PNG header + data to reach desired size
            png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x02\x00\x00\x00\x90wS\xde'
            # Fill the rest with dummy data to reach target size
            remaining_size = size_bytes - len(png_header) - 12  # 12 bytes for IEND chunk
            dummy_data = b'A' * max(0, remaining_size)
            iend_chunk = b'\x00\x00\x00\x00IEND\xaeB`\x82'
            return png_header + dummy_data + iend_chunk
        
        elif file_type == "video":
            # Create a minimal MP4-like file
            mp4_header = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom'
            remaining_size = size_bytes - len(mp4_header)
            dummy_data = b'V' * max(0, remaining_size)
            return mp4_header + dummy_data
        
        elif file_type == "document":
            # Create a minimal PDF
            pdf_header = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Size 1\n>>\nstartxref\n%%EOF\n'
            remaining_size = size_bytes - len(pdf_header)
            dummy_data = b'D' * max(0, remaining_size)
            return pdf_header + dummy_data
        
        return b'X' * size_bytes

    def run_test(self, name, media_type, file_size_mb, expected_status, file_extension):
        """Run a single file upload test"""
        if not self.token:
            print(f"❌ Skipping {name} - No token")
            return False

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        # Create test file
        file_data = self.create_test_file(file_size_mb, media_type)
        filename = f"test_{file_size_mb}mb.{file_extension}"
        
        # Determine MIME type
        mime_types = {
            "image": "image/png",
            "video": "video/mp4", 
            "document": "application/pdf"
        }
        mime_type = mime_types.get(media_type, "application/octet-stream")
        
        url = f"{self.base_url}/api/upload/media?media_type={media_type}"
        headers = {'Authorization': f'Bearer {self.token}'}
        files = {'file': (filename, file_data, mime_type)}
        
        try:
            response = requests.post(url, files=files, headers=headers, timeout=30)
            
            print(f"   File size: {file_size_mb}MB")
            print(f"   Expected status: {expected_status}")
            print(f"   Actual status: {response.status_code}")
            
            if response.status_code == expected_status:
                self.tests_passed += 1
                print(f"✅ PASSED")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   Upload URL: {result.get('url', 'N/A')}")
                elif response.status_code == 400:
                    result = response.json()
                    print(f"   Error message: {result.get('detail', 'N/A')}")
                
                return True
            else:
                print(f"❌ FAILED")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False
                
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False

    def run_all_tests(self):
        """Run all file size limit tests"""
        print("🚀 Starting File Size Limit Tests")
        print("=" * 50)
        
        if not self.login():
            return False
        
        # Image tests (5MB limit)
        print(f"\n📸 IMAGE TESTS (5MB limit)")
        print("-" * 30)
        self.run_test("Image Under Limit", "image", 2.0, 200, "png")
        self.run_test("Image At Limit", "image", 5.0, 200, "png")
        self.run_test("Image Over Limit", "image", 6.0, 400, "png")
        
        # Video tests (16MB limit)
        print(f"\n🎥 VIDEO TESTS (16MB limit)")
        print("-" * 30)
        self.run_test("Video Under Limit", "video", 10.0, 200, "mp4")
        self.run_test("Video At Limit", "video", 16.0, 200, "mp4")
        self.run_test("Video Over Limit", "video", 18.0, 400, "mp4")
        
        # Document tests (10MB limit)
        print(f"\n📄 DOCUMENT TESTS (10MB limit)")
        print("-" * 30)
        self.run_test("Document Under Limit", "document", 5.0, 200, "pdf")
        self.run_test("Document At Limit", "document", 10.0, 200, "pdf")
        self.run_test("Document Over Limit", "document", 12.0, 400, "pdf")
        
        # Print Results
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS")
        print("=" * 50)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                print(f"{i}. {test['test']}")
                if 'error' in test:
                    print(f"   Error: {test['error']}")
                else:
                    print(f"   Expected: {test['expected']}, Got: {test['actual']}")
                    print(f"   Response: {test['response']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = FileSizeLimitTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())