import requests
import sys
import json
import io
from datetime import datetime

class WhatsAppBulkMessengerTester:
    def __init__(self, base_url="https://easywasend-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.user_token = None
        self.test_user_id = None
        self.test_user_email = None
        self.test_template_id = None
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
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

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
        """Test admin login with correct credentials"""
        # Try adminpassword first (from test_result.md)
        success, response = self.run_test(
            "Admin Login (adminpassword)",
            "POST",
            "auth/login",
            200,
            data={"email": "bizchatapi@gmail.com", "password": "adminpassword"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   Admin token obtained: {self.admin_token[:20]}...")
            return True
        
        # Try admin123 (from code default)
        success, response = self.run_test(
            "Admin Login (admin123)",
            "POST",
            "auth/login",
            200,
            data={"email": "bizchatapi@gmail.com", "password": "admin123"}
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

    def test_password_change(self):
        """Test password change functionality"""
        if not self.admin_token:
            print("❌ Skipping - No admin token")
            return False

        # Test with wrong current password
        success, response = self.run_test(
            "Password Change (Wrong Current)",
            "POST",
            "auth/change-password",
            400,  # Should fail with wrong current password
            data={"currentPassword": "wrongpassword", "newPassword": "newpass123"},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if not success:
            return False

        # Test with correct current password
        success, response = self.run_test(
            "Password Change (Correct)",
            "POST",
            "auth/change-password",
            200,
            data={"currentPassword": "adminpassword", "newPassword": "newpass123"},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if success:
            # Change it back
            self.run_test(
                "Password Change (Revert)",
                "POST",
                "auth/change-password",
                200,
                data={"currentPassword": "newpass123", "newPassword": "adminpassword"},
                headers={'Authorization': f'Bearer {self.admin_token}'}
            )
        
        return success

    def test_super_admin_protection(self):
        """Test super admin protection (cannot pause/delete bizchatapi@gmail.com)"""
        if not self.admin_token:
            print("❌ Skipping - No admin token")
            return False

        # Get admin user ID
        success, response = self.run_test(
            "Get Admin Profile for Protection Test",
            "GET",
            "auth/me",
            200,
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if not success or 'id' not in response:
            return False
        
        admin_user_id = response['id']

        # Try to pause super admin (should fail)
        success, response = self.run_test(
            "Try Pause Super Admin (Should Fail)",
            "PUT",
            f"users/{admin_user_id}/pause",
            403,  # Should fail with 403
            data={"isPaused": True},
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        if not success:
            return False

        # Try to delete super admin (should fail)
        success, response = self.run_test(
            "Try Delete Super Admin (Should Fail)",
            "DELETE",
            f"users/{admin_user_id}",
            403,  # Should fail with 403
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        return success

    def test_upload_media_image(self):
        """Test media upload - image"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        # Create a simple test image (1x1 pixel PNG)
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xac\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        
        success, response = self.run_test(
            "Upload Image Media",
            "POST",
            "upload/media?media_type=image",
            200,
            files={'file': ('test.png', png_data, 'image/png')},
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success and 'url' in response:
            print(f"   Image uploaded: {response['url']}")
        
        return success

    def test_upload_media_document(self):
        """Test media upload - document"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        # Create a simple test PDF content
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
        
        success, response = self.run_test(
            "Upload Document Media",
            "POST",
            "upload/media?media_type=document",
            200,
            files={'file': ('test.pdf', pdf_content, 'application/pdf')},
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success and 'url' in response:
            print(f"   Document uploaded: {response['url']}")
        
        return success

    def test_create_saved_template_with_media(self):
        """Test creating saved template with media fields"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        template_data = {
            "name": "Test Template with Image",
            "templateName": "test_template",
            "templateLanguage": "en",
            "field1": "Hello {name}",
            "field2": "Welcome to our service",
            "field3": "Thank you for choosing us",
            "header_image": "https://easywasend-1.preview.emergentagent.com/uploads/images/test.jpg"
        }

        success, response = self.run_test(
            "Create Saved Template with Media",
            "POST",
            "saved-templates",
            200,
            data=template_data,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success and 'templateId' in response:
            self.test_template_id = response['templateId']
            print(f"   Template created: {self.test_template_id}")
        
        return success

    def test_get_saved_templates(self):
        """Test getting saved templates"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        success, response = self.run_test(
            "Get Saved Templates",
            "GET",
            "saved-templates",
            200,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success and 'templates' in response:
            print(f"   Found {len(response['templates'])} templates")
        
        return success

    def test_get_saved_template_by_id(self):
        """Test getting specific saved template"""
        if not self.user_token or not self.test_template_id:
            print("❌ Skipping - No user token or template ID")
            return False

        success, response = self.run_test(
            "Get Saved Template by ID",
            "GET",
            f"saved-templates/{self.test_template_id}",
            200,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        if success:
            print(f"   Template name: {response.get('name', 'N/A')}")
            print(f"   Has image: {'Yes' if response.get('header_image') else 'No'}")
        
        return success

    def test_update_saved_template(self):
        """Test updating saved template"""
        if not self.user_token or not self.test_template_id:
            print("❌ Skipping - No user token or template ID")
            return False

        update_data = {
            "name": "Updated Test Template",
            "templateName": "test_template_updated",
            "templateLanguage": "en",
            "field1": "Updated Hello {name}",
            "field2": "Updated welcome message",
            "header_video": "https://easywasend-1.preview.emergentagent.com/uploads/videos/test.mp4"
        }

        success, response = self.run_test(
            "Update Saved Template",
            "PUT",
            f"saved-templates/{self.test_template_id}",
            200,
            data=update_data,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        return success

    def test_create_template_with_location(self):
        """Test creating template with location data"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        template_data = {
            "name": "Location Template",
            "templateName": "location_template",
            "templateLanguage": "en",
            "field1": "Visit our store",
            "location_latitude": "22.5726",
            "location_longitude": "88.3639",
            "location_name": "Our Store",
            "location_address": "123 Main Street, Kolkata, India"
        }

        success, response = self.run_test(
            "Create Template with Location",
            "POST",
            "saved-templates",
            200,
            data=template_data,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        return success

    def test_send_message_with_media(self):
        """Test sending message with media (without actually sending)"""
        if not self.user_token:
            print("❌ Skipping - No user token")
            return False

        # This will fail because user doesn't have BizChat token configured
        # But we can test the API structure
        message_data = {
            "campaignName": "Test Campaign with Media",
            "templateName": "test_template",
            "recipients": [
                {
                    "phone": "+1234567890",
                    "name": "Test User",
                    "field_1": "Hello Test",
                    "field_2": "Welcome"
                }
            ],
            "header_image": "https://easywasend-1.preview.emergentagent.com/uploads/images/test.jpg"
        }

        success, response = self.run_test(
            "Send Message with Media (Expected to Fail - No BizChat Token)",
            "POST",
            "messages/send",
            400,  # Expected to fail due to missing BizChat token
            data=message_data,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        return success

    def test_delete_saved_template(self):
        """Test deleting saved template"""
        if not self.user_token or not self.test_template_id:
            print("❌ Skipping - No user token or template ID")
            return False

        success, response = self.run_test(
            "Delete Saved Template",
            "DELETE",
            f"saved-templates/{self.test_template_id}",
            200,
            headers={'Authorization': f'Bearer {self.user_token}'}
        )
        
        return success

def main():
    print("🚀 Starting WhatsApp Bulk Messenger API Tests")
    print("=" * 60)
    
    tester = WhatsAppBulkMessengerTester()
    
    # Authentication Tests
    print("\n📋 AUTHENTICATION & ADMIN TESTS")
    print("-" * 40)
    tester.test_admin_login()
    tester.test_admin_me()
    tester.test_password_change()
    tester.test_super_admin_protection()
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
    
    # Media Upload Tests
    print("\n📁 MEDIA UPLOAD TESTS")
    print("-" * 30)
    tester.test_upload_media_image()
    tester.test_upload_media_document()
    
    # Template Management Tests
    print("\n📄 TEMPLATE MANAGEMENT TESTS")
    print("-" * 35)
    tester.test_create_saved_template_with_media()
    tester.test_get_saved_templates()
    tester.test_get_saved_template_by_id()
    tester.test_update_saved_template()
    tester.test_create_template_with_location()
    
    # Campaign Tests
    print("\n📊 CAMPAIGN TESTS")
    print("-" * 30)
    tester.test_get_campaigns()
    tester.test_send_message_with_media()
    
    # File Upload Tests
    print("\n📋 RECIPIENT UPLOAD TESTS")
    print("-" * 30)
    tester.test_upload_recipients()
    
    # Cleanup Tests
    print("\n🧹 CLEANUP TESTS")
    print("-" * 20)
    tester.test_delete_saved_template()
    
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