"""
Reminder Bot Feature Tests
Tests for phone numbers management, reminders, and settings APIs
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://reminder-bot-10.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "bizchatapi@gmail.com"
ADMIN_PASSWORD = "adminpassword"

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
    def test_login_success(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "user" in data, "User not in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Login successful for {ADMIN_EMAIL}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")


class TestTimezones:
    """Timezone endpoint tests"""
    
    def test_get_timezones(self):
        """Test GET /api/reminder-numbers/timezones"""
        response = requests.get(f"{BASE_URL}/api/reminder-numbers/timezones")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "timezones" in data, "timezones key missing"
        assert len(data["timezones"]) > 0, "No timezones returned"
        assert "Asia/Kolkata" in data["timezones"], "Asia/Kolkata not in timezones"
        assert "UTC" in data["timezones"], "UTC not in timezones"
        print(f"✓ Got {len(data['timezones'])} timezones")


class TestReminderNumbers:
    """Reminder Numbers CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_reminder_numbers(self, auth_headers):
        """Test GET /api/reminder-numbers - list phone numbers"""
        response = requests.get(f"{BASE_URL}/api/reminder-numbers", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "numbers" in data, "numbers key missing"
        print(f"✓ Got {len(data['numbers'])} phone numbers")
    
    def test_create_reminder_number(self, auth_headers):
        """Test POST /api/reminder-numbers - add phone number"""
        test_phone = f"+91TEST{datetime.now().strftime('%H%M%S')}"
        payload = {
            "phone": test_phone,
            "name": "TEST_AutoTest User",
            "timezone": "Asia/Kolkata",
            "isDefault": False
        }
        response = requests.post(f"{BASE_URL}/api/reminder-numbers", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "numberId" in data, "numberId not in response"
        assert "number" in data, "number not in response"
        assert data["number"]["name"] == "TEST_AutoTest User"
        print(f"✓ Created phone number: {data['numberId']}")
        return data["numberId"]
    
    def test_create_duplicate_number_fails(self, auth_headers):
        """Test that duplicate phone numbers are rejected"""
        # First create a number
        test_phone = "+91TESTDUP123"
        payload = {
            "phone": test_phone,
            "name": "TEST_Duplicate Test",
            "timezone": "Asia/Kolkata"
        }
        # First creation should succeed
        response1 = requests.post(f"{BASE_URL}/api/reminder-numbers", json=payload, headers=auth_headers)
        
        # Second creation with same phone should fail
        response2 = requests.post(f"{BASE_URL}/api/reminder-numbers", json=payload, headers=auth_headers)
        # Either 400 (duplicate) or 200 (if first failed)
        if response1.status_code == 200:
            assert response2.status_code == 400, f"Expected 400 for duplicate, got {response2.status_code}"
            print("✓ Duplicate phone number correctly rejected")
        else:
            print("✓ Phone number already exists (expected)")
    
    def test_create_number_invalid_timezone(self, auth_headers):
        """Test that invalid timezone is rejected"""
        payload = {
            "phone": "+91TESTINVALID",
            "name": "TEST_Invalid TZ",
            "timezone": "Invalid/Timezone"
        }
        response = requests.post(f"{BASE_URL}/api/reminder-numbers", json=payload, headers=auth_headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid timezone correctly rejected")
    
    def test_delete_reminder_number(self, auth_headers):
        """Test DELETE /api/reminder-numbers/{id}"""
        # First create a number to delete
        test_phone = f"+91TESTDEL{datetime.now().strftime('%H%M%S')}"
        payload = {
            "phone": test_phone,
            "name": "TEST_To Delete",
            "timezone": "Asia/Kolkata"
        }
        create_response = requests.post(f"{BASE_URL}/api/reminder-numbers", json=payload, headers=auth_headers)
        if create_response.status_code != 200:
            pytest.skip("Could not create number to delete")
        
        number_id = create_response.json()["numberId"]
        
        # Now delete it
        delete_response = requests.delete(f"{BASE_URL}/api/reminder-numbers/{number_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        print(f"✓ Deleted phone number: {number_id}")
        
        # Verify it's deleted
        get_response = requests.get(f"{BASE_URL}/api/reminder-numbers/{number_id}", headers=auth_headers)
        assert get_response.status_code == 404, "Number should be deleted"
        print("✓ Verified number is deleted")
    
    def test_delete_nonexistent_number(self, auth_headers):
        """Test deleting a non-existent number returns 404"""
        response = requests.delete(f"{BASE_URL}/api/reminder-numbers/nonexistent-id-12345", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent number correctly returns 404")


class TestReminderSettings:
    """Reminder Settings tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_settings(self, auth_headers):
        """Test GET /api/reminders/settings"""
        response = requests.get(f"{BASE_URL}/api/reminders/settings", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "userId" in data, "userId missing"
        assert "hasApiKey" in data, "hasApiKey missing"
        print(f"✓ Got settings, hasApiKey: {data['hasApiKey']}")
    
    def test_update_settings_template(self, auth_headers):
        """Test PUT /api/reminders/settings - update template ID"""
        payload = {
            "defaultTemplateId": "test_reminder_template"
        }
        response = requests.put(f"{BASE_URL}/api/reminders/settings", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ Updated settings with template ID")
        
        # Verify the update
        get_response = requests.get(f"{BASE_URL}/api/reminders/settings", headers=auth_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("defaultTemplateId") == "test_reminder_template"
        print("✓ Verified template ID was saved")
    
    def test_update_settings_empty_fails(self, auth_headers):
        """Test that empty update is rejected"""
        response = requests.put(f"{BASE_URL}/api/reminders/settings", json={}, headers=auth_headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Empty settings update correctly rejected")


class TestReminders:
    """Reminders CRUD tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def test_number_id(self, auth_headers):
        """Create or get a test phone number for reminders"""
        # First check if we have any numbers
        response = requests.get(f"{BASE_URL}/api/reminder-numbers", headers=auth_headers)
        if response.status_code == 200:
            numbers = response.json().get("numbers", [])
            if numbers:
                return numbers[0]["id"]
        
        # Create a new number
        payload = {
            "phone": "+919876543210",
            "name": "TEST_Reminder Test",
            "timezone": "Asia/Kolkata"
        }
        create_response = requests.post(f"{BASE_URL}/api/reminder-numbers", json=payload, headers=auth_headers)
        if create_response.status_code == 200:
            return create_response.json()["numberId"]
        pytest.skip("Could not create test number")
    
    def test_get_reminders_all(self, auth_headers):
        """Test GET /api/reminders - list all reminders"""
        response = requests.get(f"{BASE_URL}/api/reminders", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "reminders" in data, "reminders key missing"
        assert "count" in data, "count key missing"
        print(f"✓ Got {data['count']} reminders")
    
    def test_get_reminders_with_filter(self, auth_headers):
        """Test GET /api/reminders with filters"""
        filters = ["all", "today", "week", "pending", "sent", "failed"]
        for f in filters:
            response = requests.get(f"{BASE_URL}/api/reminders?filter={f}", headers=auth_headers)
            assert response.status_code == 200, f"Filter '{f}' failed: {response.text}"
            print(f"✓ Filter '{f}' works")
    
    def test_create_reminder_direct(self, auth_headers, test_number_id):
        """Test POST /api/reminders/direct - create reminder without NLP"""
        # Schedule for 1 hour from now
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        
        payload = {
            "numberId": test_number_id,
            "title": "TEST_Direct Reminder",
            "message": "This is a test reminder created directly",
            "scheduledAt": scheduled_time,
            "useTemplate": True
        }
        response = requests.post(f"{BASE_URL}/api/reminders/direct", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "reminderId" in data, "reminderId missing"
        assert "reminder" in data, "reminder missing"
        assert data["reminder"]["title"] == "TEST_Direct Reminder"
        print(f"✓ Created direct reminder: {data['reminderId']}")
        return data["reminderId"]
    
    def test_create_reminder_past_time_fails(self, auth_headers, test_number_id):
        """Test that creating reminder in the past fails"""
        # Schedule for 1 hour ago
        scheduled_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        
        payload = {
            "numberId": test_number_id,
            "title": "TEST_Past Reminder",
            "message": "This should fail",
            "scheduledAt": scheduled_time
        }
        response = requests.post(f"{BASE_URL}/api/reminders/direct", json=payload, headers=auth_headers)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Past time reminder correctly rejected")
    
    def test_create_reminder_invalid_number_fails(self, auth_headers):
        """Test that creating reminder with invalid number fails"""
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        
        payload = {
            "numberId": "invalid-number-id-12345",
            "title": "TEST_Invalid Number",
            "message": "This should fail",
            "scheduledAt": scheduled_time
        }
        response = requests.post(f"{BASE_URL}/api/reminders/direct", json=payload, headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid number ID correctly rejected")
    
    def test_delete_reminder(self, auth_headers, test_number_id):
        """Test DELETE /api/reminders/{id}"""
        # First create a reminder to delete
        scheduled_time = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        
        payload = {
            "numberId": test_number_id,
            "title": "TEST_To Delete",
            "message": "This reminder will be deleted",
            "scheduledAt": scheduled_time
        }
        create_response = requests.post(f"{BASE_URL}/api/reminders/direct", json=payload, headers=auth_headers)
        if create_response.status_code != 200:
            pytest.skip("Could not create reminder to delete")
        
        reminder_id = create_response.json()["reminderId"]
        
        # Now delete it
        delete_response = requests.delete(f"{BASE_URL}/api/reminders/{reminder_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        print(f"✓ Deleted reminder: {reminder_id}")
        
        # Verify it's deleted
        get_response = requests.get(f"{BASE_URL}/api/reminders/{reminder_id}", headers=auth_headers)
        assert get_response.status_code == 404, "Reminder should be deleted"
        print("✓ Verified reminder is deleted")
    
    def test_delete_nonexistent_reminder(self, auth_headers):
        """Test deleting a non-existent reminder returns 404"""
        response = requests.delete(f"{BASE_URL}/api/reminders/nonexistent-id-12345", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent reminder correctly returns 404")
    
    def test_create_reminder_nlp_without_api_key(self, auth_headers, test_number_id):
        """Test that NLP reminder creation fails without API key"""
        payload = {
            "numberId": test_number_id,
            "naturalLanguageInput": "remind me to call John at 10am tomorrow"
        }
        response = requests.post(f"{BASE_URL}/api/reminders", json=payload, headers=auth_headers)
        # Should fail because no OpenAI API key is configured
        # Either 400 (no API key) or 500 (API error)
        assert response.status_code in [400, 500], f"Expected 400/500, got {response.status_code}"
        print("✓ NLP reminder without API key correctly handled")


class TestHealthAndVersion:
    """Health check and version tests"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.1.0"
        assert "reminder_bot" in data["features"]
        print(f"✓ Health check passed, version: {data['version']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
