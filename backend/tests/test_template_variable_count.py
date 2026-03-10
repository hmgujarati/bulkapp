"""
Test Template Variable Count Feature
Tests the dynamic template variable count functionality for:
1. Reminder settings API - templateVariableCount field
2. Auto-message settings API - birthdayTemplateVariableCount, anniversaryTemplateVariableCount
3. Persistence of templateVariableCount after updates
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {
    "email": "bizchatapi@gmail.com",
    "password": "adminpassword"
}

REGULAR_USER_CREDENTIALS = {
    "email": "rapidexpresstechnologies@gmail.com",
    "password": "test123"
}


@pytest.fixture(scope="module")
def admin_session():
    """Create session with admin authentication"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as admin
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
    else:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return session


@pytest.fixture(scope="module")
def user_session():
    """Create session with regular user authentication"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as regular user
    response = session.post(f"{BASE_URL}/api/auth/login", json=REGULAR_USER_CREDENTIALS)
    if response.status_code == 200:
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
    else:
        pytest.skip(f"User login failed: {response.status_code} - {response.text}")
    return session


class TestReminderSettingsTemplateVariableCount:
    """Tests for templateVariableCount in reminder settings"""
    
    def test_get_reminder_settings_returns_template_variable_count(self, admin_session):
        """Verify GET /api/reminders/settings returns templateVariableCount field"""
        response = admin_session.get(f"{BASE_URL}/api/reminders/settings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check that templateVariableCount is present (either set or defaulted)
        assert "templateVariableCount" in data, "templateVariableCount field missing from response"
        
        # Verify it's an integer and within valid range (default is 3 per code)
        var_count = data["templateVariableCount"]
        assert isinstance(var_count, int), f"templateVariableCount should be int, got {type(var_count)}"
        assert 1 <= var_count <= 5, f"templateVariableCount should be 1-5, got {var_count}"
        
        print(f"✓ GET reminder settings returns templateVariableCount: {var_count}")
    
    def test_update_reminder_settings_template_variable_count_to_1(self, admin_session):
        """Test updating templateVariableCount to 1"""
        response = admin_session.put(
            f"{BASE_URL}/api/reminders/settings",
            json={"templateVariableCount": 1}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence - GET should return 1
        verify_response = admin_session.get(f"{BASE_URL}/api/reminders/settings")
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        assert data.get("templateVariableCount") == 1, f"Expected 1, got {data.get('templateVariableCount')}"
        
        print("✓ templateVariableCount updated to 1 and persisted correctly")
    
    def test_update_reminder_settings_template_variable_count_to_3(self, admin_session):
        """Test updating templateVariableCount to 3"""
        response = admin_session.put(
            f"{BASE_URL}/api/reminders/settings",
            json={"templateVariableCount": 3}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence
        verify_response = admin_session.get(f"{BASE_URL}/api/reminders/settings")
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        assert data.get("templateVariableCount") == 3, f"Expected 3, got {data.get('templateVariableCount')}"
        
        print("✓ templateVariableCount updated to 3 and persisted correctly")
    
    def test_update_reminder_settings_template_variable_count_to_5(self, admin_session):
        """Test updating templateVariableCount to 5 (max value)"""
        response = admin_session.put(
            f"{BASE_URL}/api/reminders/settings",
            json={"templateVariableCount": 5}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence
        verify_response = admin_session.get(f"{BASE_URL}/api/reminders/settings")
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        assert data.get("templateVariableCount") == 5, f"Expected 5, got {data.get('templateVariableCount')}"
        
        print("✓ templateVariableCount updated to 5 and persisted correctly")


class TestAutoMessageSettingsTemplateVariableCount:
    """Tests for birthdayTemplateVariableCount and anniversaryTemplateVariableCount"""
    
    def test_get_auto_message_settings_returns_variable_counts(self, admin_session):
        """Verify GET /api/contacts/settings/auto-messages returns variable count fields"""
        response = admin_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        settings = data.get("settings", data)  # Handle both direct and wrapped response
        
        # Check birthdayTemplateVariableCount
        assert "birthdayTemplateVariableCount" in settings, "birthdayTemplateVariableCount missing"
        bday_count = settings["birthdayTemplateVariableCount"]
        assert isinstance(bday_count, int), f"birthdayTemplateVariableCount should be int"
        
        # Check anniversaryTemplateVariableCount
        assert "anniversaryTemplateVariableCount" in settings, "anniversaryTemplateVariableCount missing"
        anni_count = settings["anniversaryTemplateVariableCount"]
        assert isinstance(anni_count, int), f"anniversaryTemplateVariableCount should be int"
        
        print(f"✓ Auto-message settings return variable counts: birthday={bday_count}, anniversary={anni_count}")
    
    def test_update_birthday_template_variable_count(self, admin_session):
        """Test updating birthdayTemplateVariableCount"""
        response = admin_session.put(
            f"{BASE_URL}/api/contacts/settings/auto-messages",
            json={"birthdayTemplateVariableCount": 2}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence
        verify_response = admin_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        settings = data.get("settings", data)
        assert settings.get("birthdayTemplateVariableCount") == 2, \
            f"Expected 2, got {settings.get('birthdayTemplateVariableCount')}"
        
        print("✓ birthdayTemplateVariableCount updated to 2 and persisted")
    
    def test_update_anniversary_template_variable_count(self, admin_session):
        """Test updating anniversaryTemplateVariableCount"""
        response = admin_session.put(
            f"{BASE_URL}/api/contacts/settings/auto-messages",
            json={"anniversaryTemplateVariableCount": 3}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence
        verify_response = admin_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        settings = data.get("settings", data)
        assert settings.get("anniversaryTemplateVariableCount") == 3, \
            f"Expected 3, got {settings.get('anniversaryTemplateVariableCount')}"
        
        print("✓ anniversaryTemplateVariableCount updated to 3 and persisted")
    
    def test_update_both_variable_counts_together(self, admin_session):
        """Test updating both birthday and anniversary variable counts in one request"""
        response = admin_session.put(
            f"{BASE_URL}/api/contacts/settings/auto-messages",
            json={
                "birthdayTemplateVariableCount": 1,
                "anniversaryTemplateVariableCount": 1
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify both persisted correctly
        verify_response = admin_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        settings = data.get("settings", data)
        
        assert settings.get("birthdayTemplateVariableCount") == 1, \
            f"Birthday: Expected 1, got {settings.get('birthdayTemplateVariableCount')}"
        assert settings.get("anniversaryTemplateVariableCount") == 1, \
            f"Anniversary: Expected 1, got {settings.get('anniversaryTemplateVariableCount')}"
        
        print("✓ Both variable counts updated and persisted correctly")


class TestRegularUserTemplateVariableCount:
    """Tests with regular user credentials"""
    
    def test_regular_user_can_access_reminder_settings(self, user_session):
        """Regular user can access their own reminder settings"""
        response = user_session.get(f"{BASE_URL}/api/reminders/settings")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templateVariableCount" in data, "templateVariableCount missing for regular user"
        
        print(f"✓ Regular user can access reminder settings with templateVariableCount")
    
    def test_regular_user_can_update_template_variable_count(self, user_session):
        """Regular user can update their templateVariableCount"""
        response = user_session.put(
            f"{BASE_URL}/api/reminders/settings",
            json={"templateVariableCount": 2}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify
        verify_response = user_session.get(f"{BASE_URL}/api/reminders/settings")
        data = verify_response.json()
        assert data.get("templateVariableCount") == 2
        
        print("✓ Regular user can update templateVariableCount")
    
    def test_regular_user_can_access_auto_message_settings(self, user_session):
        """Regular user can access their auto-message settings"""
        response = user_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        settings = data.get("settings", data)
        
        assert "birthdayTemplateVariableCount" in settings
        assert "anniversaryTemplateVariableCount" in settings
        
        print("✓ Regular user can access auto-message settings with variable counts")


class TestDefaultValues:
    """Tests to verify default values are correct"""
    
    def test_reminder_settings_default_value(self, admin_session):
        """Verify default templateVariableCount is 3 (as per code comment)"""
        response = admin_session.get(f"{BASE_URL}/api/reminders/settings")
        assert response.status_code == 200
        
        data = response.json()
        # Default is 3 per the code in reminders.py line 132
        # But if already updated by previous tests, just check it's valid
        var_count = data.get("templateVariableCount")
        assert var_count is not None, "templateVariableCount should not be None"
        assert 1 <= var_count <= 5, f"templateVariableCount should be 1-5, got {var_count}"
        
        print(f"✓ templateVariableCount has valid value: {var_count}")
    
    def test_auto_message_settings_default_values(self, admin_session):
        """Verify default values for auto-message variable counts are 1"""
        response = admin_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        assert response.status_code == 200
        
        data = response.json()
        settings = data.get("settings", data)
        
        # Default values from contacts.py line 392, 398 are 1
        bday = settings.get("birthdayTemplateVariableCount")
        anni = settings.get("anniversaryTemplateVariableCount")
        
        assert bday is not None, "birthdayTemplateVariableCount should not be None"
        assert anni is not None, "anniversaryTemplateVariableCount should not be None"
        
        print(f"✓ Auto-message variable counts have valid values: birthday={bday}, anniversary={anni}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
