import requests
import sys
import json
from datetime import datetime

class WhatsAppBulkMessengerTester:
    def __init__(self, base_url="https://whatsapp-bulk-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.test_user_id = None
        self.test_user_email = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for file uploads
                    test_headers.pop('Content-Type', None)
                    response = requests.post(url, files=files, headers=test_headers, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@masswhatsapp.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   Admin token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def test_admin_me(self):
        """Test getting admin profile"""
        if not self.admin_token:
            print("❌ Skipping - No admin token")
            return False
        
        success, response = self.run_test(
            "Get Admin Profile",
            "GET",
            "auth/me",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        return success

    def test_create_user(self):
        """Test creating a new user"""
        if not self.admin_token:
            print("❌ Skipping - No admin token")
            return False

        timestamp = datetime.now().strftime("%H%M%S")
        self.test_user_email = f"testuser{timestamp}@example.com"
        user_data = {
            "email": self.test_user_email,
            "password": "testpass123",
            "firstName": "Test",
            "lastName": "User",
            "role": "user"
        }

        success, response = self.run_test(
            "Create User",
            "POST",
            "auth/register",
            200,
            data=user_data,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success and 'userId' in response:
            self.test_user_id = response['userId']
            print(f"   Created user ID: {self.test_user_id}")
            print(f"   Created user email: {self.test_user_email}")
            return True
        return False

    def test_user_login(self):
        """Test user login"""
        if not self.test_user_id or not self.test_user_email:
            print("❌ Skipping - No test user created")
            return False

        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": self.test_user_email, "password": "testpass123"}
        )
        
        if success and 'token' in response:
            self.user_token = response['token']
            print(f"   User token obtained: {self.user_token[:20]}...")
            return True
        return False

    def test_get_users(self):
        """Test getting all users (admin only)"""
        if not self.admin_token:
            print("❌ Skipping - No admin token")
            return False

        success, response = self.run_test(
            "Get All Users",
            "GET",
            "users",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success and 'users' in response:
            print(f"   Found {len(response['users'])} users")
        return success

    def test_pause_user(self):
        """Test pausing a user"""
        if not self.admin_token or not self.test_user_id:
            print("❌ Skipping - No admin token or test user")
            return False

        success, response = self.run_test(
            "Pause User",
            "PUT",
            f"users/{self.test_user_id}/pause",
            200,
            data={"isPaused": True},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        return success

    def test_update_user_limit(self):
        """Test updating user daily limit"""
        if not self.admin_token or not self.test_user_id:
            print("❌ Skipping - No admin token or test user")
            return False

        success, response = self.run_test(
            "Update User Limit",
            "PUT",
            f"users/{self.test_user_id}/limit",
            200,
            data={"dailyLimit": 500},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        return success

    def test_unpause_user(self):
        """Test unpausing a user"""
        if not self.admin_token or not self.test_user_id:
            print("❌ Skipping - No admin token or test user")
            return False

        success, response = self.run_test(
            "Unpause User",
            "PUT",
            f"users/{self.test_user_id}/pause",
            200,
            data={"isPaused": False},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        return success

    def test_get_templates_no_token(self):
        """Test getting templates without BizChat token"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        success, response = self.run_test(
            "Get Templates (No BizChat Token)",
            "GET",
            "templates",
            400,  # Should fail with 400 when no token configured
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        return success

    def test_update_user_profile(self):
        """Test updating user profile"""
        if not self.user_token or not self.test_user_id:
            print("❌ Skipping - No user token or test user")
            return False

        success, response = self.run_test(
            "Update User Profile",
            "PUT",
            f"users/{self.test_user_id}",
            200,
            data={"firstName": "Updated", "lastName": "Name"},
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        return success

    def test_get_campaigns(self):
        """Test getting campaigns"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        success, response = self.run_test(
            "Get Campaigns",
            "GET",
            "campaigns",
            200,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success and 'campaigns' in response:
            print(f"   Found {len(response['campaigns'])} campaigns")
        return success

    def test_upload_recipients(self):
        """Test uploading recipients file"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        # Create a simple CSV content
        csv_content = "phone,name\n+1234567890,John Doe\n+9876543210,Jane Smith"
        
        success, response = self.run_test(
            "Upload Recipients File",
            "POST",
            "messages/upload",
            200,
            files={'file': ('test.csv', csv_content, 'text/csv')},
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success and 'recipients' in response:
            print(f"   Uploaded {len(response['recipients'])} recipients")
        return success

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        success, response = self.run_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,  # Should fail with 401
            data={"email": "invalid@example.com", "password": "wrongpass"}
        )
        return success

    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        success, response = self.run_test(
            "Unauthorized Access",
            "GET",
            "users",
            403,  # Should fail with 403 (Not authenticated)
        )
        return success

def main():
    print("🚀 Starting WhatsApp Bulk Messenger API Tests")
    print("=" * 60)
    
    tester = WhatsAppBulkMessengerTester()
    
    # Authentication Tests
    print("\n📋 AUTHENTICATION TESTS")
    print("-" * 30)
    tester.test_admin_login()
    tester.test_admin_me()
    tester.test_invalid_login()
    tester.test_unauthorized_access()
    
    # User Management Tests
    print("\n👥 USER MANAGEMENT TESTS")
    print("-" * 30)
    tester.test_create_user()
    tester.test_user_login()
    tester.test_get_users()
    tester.test_pause_user()
    tester.test_update_user_limit()
    tester.test_unpause_user()
    tester.test_update_user_profile()
    
    # Template Tests
    print("\n📄 TEMPLATE TESTS")
    print("-" * 30)
    tester.test_get_templates_no_token()
    
    # Campaign Tests
    print("\n📊 CAMPAIGN TESTS")
    print("-" * 30)
    tester.test_get_campaigns()
    
    # File Upload Tests
    print("\n📁 FILE UPLOAD TESTS")
    print("-" * 30)
    tester.test_upload_recipients()
    
    # Print Results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if tester.failed_tests:
        print("\n❌ FAILED TESTS:")
        for i, test in enumerate(tester.failed_tests, 1):
            print(f"{i}. {test['test']}")
            if 'error' in test:
                print(f"   Error: {test['error']}")
            else:
                print(f"   Expected: {test['expected']}, Got: {test['actual']}")
                print(f"   Response: {test['response']}")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())