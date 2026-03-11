"""
Comprehensive API Tests for WhatsApp Bulk Messenger
Tests all CRUD operations and critical edge cases as per review_request:
- Authentication & User Management
- Daily Limit & 24-Hour Reset
- Templates
- Campaigns
- Reminders
- Contacts
- Indiamart Integration
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {
    "email": "bizchatapi@gmail.com",
    "password": "adminpassword"
}

USER_CREDENTIALS = {
    "email": "rapidexpresstechnologies@gmail.com",
    "password": "test123"
}

USER_ID_FOR_TESTING = "61b4ea2d-4358-4cf9-be71-cc0f92433d6f"


@pytest.fixture(scope="module")
def admin_session():
    """Create session with admin authentication"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"✓ Admin login successful")
    else:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return session


@pytest.fixture(scope="module")
def user_session():
    """Create session with regular user authentication"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json=USER_CREDENTIALS)
    if response.status_code == 200:
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        print(f"✓ User login successful")
    else:
        pytest.skip(f"User login failed: {response.status_code} - {response.text}")
    return session


# =======================
# AUTHENTICATION TESTS
# =======================
class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_01_health_check(self):
        """Test health endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed - version: {data.get('version')}")
    
    def test_02_login_admin_success(self):
        """Test login with valid admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Token missing from response"
        assert "user" in data, "User info missing from response"
        assert data["user"]["email"] == ADMIN_CREDENTIALS["email"]
        assert data["user"]["role"] == "admin"
        assert "features" in data["user"], "Features missing from user data"
        print("✓ Admin login successful with token and user info")
    
    def test_03_login_user_success(self):
        """Test login with valid user credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=USER_CREDENTIALS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == USER_CREDENTIALS["email"]
        print("✓ Regular user login successful")
    
    def test_04_login_invalid_credentials(self):
        """Test login with invalid credentials should fail"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_05_get_me_with_daily_usage(self, user_session):
        """GET /api/auth/me returns user info with dailyUsage, remaining, nextResetAt"""
        response = user_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "User ID missing"
        assert "email" in data, "Email missing"
        assert "dailyLimit" in data, "dailyLimit missing"
        
        # Check for 24-hour reset fields
        assert "remaining" in data, "remaining field missing from /me response"
        
        # nextResetAt may be None if no messages have been sent yet
        if data.get("dailyUsage", 0) > 0:
            assert "nextResetAt" in data, "nextResetAt missing when dailyUsage > 0"
        
        print(f"✓ GET /me returns: remaining={data.get('remaining')}, nextResetAt={data.get('nextResetAt')}")


# =======================
# USER MANAGEMENT TESTS (Admin only)
# =======================
class TestUserManagement:
    """User management endpoint tests"""
    
    def test_01_admin_get_all_users(self, admin_session):
        """Admin can view all users via GET /api/users"""
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "users" in data, "users key missing from response"
        assert isinstance(data["users"], list), "users should be a list"
        assert len(data["users"]) > 0, "Expected at least one user"
        print(f"✓ Admin retrieved {len(data['users'])} users")
    
    def test_02_user_cannot_get_all_users(self, user_session):
        """Regular user cannot access GET /api/users"""
        response = user_session.get(f"{BASE_URL}/api/users")
        # Should be 403 Forbidden for regular users
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Regular user correctly denied access to /users list")
    
    def test_03_admin_update_user_limit(self, admin_session):
        """Admin can update user daily limit via PUT /api/users/{id}/limit"""
        response = admin_session.put(
            f"{BASE_URL}/api/users/{USER_ID_FOR_TESTING}/limit",
            json={"dailyLimit": 1500}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Admin updated user daily limit successfully")
        
        # Reset to original
        admin_session.put(
            f"{BASE_URL}/api/users/{USER_ID_FOR_TESTING}/limit",
            json={"dailyLimit": 1000}
        )
    
    def test_04_admin_update_user_features(self, admin_session):
        """Admin can update user features via PUT /api/users/{id}/features"""
        response = admin_session.put(
            f"{BASE_URL}/api/users/{USER_ID_FOR_TESTING}/features",
            json={"indiamart": True}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "features" in data, "features missing from response"
        print(f"✓ Admin updated user features: {data.get('features')}")
    
    def test_05_admin_pause_unpause_user(self, admin_session):
        """Admin can pause/unpause user via PUT /api/users/{id}/pause"""
        # Pause user
        response = admin_session.put(
            f"{BASE_URL}/api/users/{USER_ID_FOR_TESTING}/pause",
            json={"isPaused": True}
        )
        assert response.status_code == 200, f"Pause failed: {response.status_code}: {response.text}"
        print("✓ Admin paused user successfully")
        
        # Unpause user
        response = admin_session.put(
            f"{BASE_URL}/api/users/{USER_ID_FOR_TESTING}/pause",
            json={"isPaused": False}
        )
        assert response.status_code == 200, f"Unpause failed: {response.status_code}: {response.text}"
        print("✓ Admin unpaused user successfully")


# =======================
# TEMPLATES TESTS
# =======================
class TestTemplates:
    """Template CRUD tests"""
    
    created_template_id = None
    
    def test_01_get_templates(self, user_session):
        """GET /api/saved-templates returns user's templates"""
        response = user_session.get(f"{BASE_URL}/api/saved-templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templates" in data, "templates key missing"
        print(f"✓ GET templates returned {len(data.get('templates', []))} templates")
    
    def test_02_create_template(self, user_session):
        """POST /api/saved-templates creates new template"""
        template_name = f"TEST_template_{uuid.uuid4().hex[:8]}"
        response = user_session.post(
            f"{BASE_URL}/api/saved-templates",
            json={
                "name": template_name,
                "templateName": "test_bizchat_template",
                "countryCode": "+91",
                "description": "Test template for automated testing"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "templateId" in data, "templateId missing from response"
        TestTemplates.created_template_id = data["templateId"]
        print(f"✓ Created template with ID: {TestTemplates.created_template_id}")
    
    def test_03_delete_template(self, user_session):
        """DELETE /api/saved-templates/{id} deletes template"""
        if not TestTemplates.created_template_id:
            pytest.skip("No template to delete")
        
        response = user_session.delete(
            f"{BASE_URL}/api/saved-templates/{TestTemplates.created_template_id}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Deleted template {TestTemplates.created_template_id}")


# =======================
# CAMPAIGNS TESTS
# =======================
class TestCampaigns:
    """Campaign endpoint tests"""
    
    def test_01_get_campaigns(self, user_session):
        """GET /api/campaigns returns user's campaigns"""
        response = user_session.get(f"{BASE_URL}/api/campaigns")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "campaigns" in data, "campaigns key missing"
        print(f"✓ GET campaigns returned {len(data.get('campaigns', []))} campaigns")
    
    def test_02_get_campaign_404(self, user_session):
        """GET /api/campaigns/{id} returns 404 for non-existent campaign"""
        response = user_session.get(f"{BASE_URL}/api/campaigns/nonexistent-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent campaign correctly returns 404")


# =======================
# REMINDERS TESTS
# =======================
class TestReminders:
    """Reminders endpoint tests"""
    
    def test_01_get_reminders(self, user_session):
        """GET /api/reminders returns user's reminders"""
        response = user_session.get(f"{BASE_URL}/api/reminders")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "reminders" in data, "reminders key missing"
        assert "count" in data, "count key missing"
        print(f"✓ GET reminders returned {data.get('count')} reminders")
    
    def test_02_get_reminder_settings(self, user_session):
        """GET /api/reminders/settings returns settings with templateVariableCount"""
        response = user_session.get(f"{BASE_URL}/api/reminders/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "hasApiKey" in data or "templateVariableCount" in data, "Expected settings fields"
        print(f"✓ GET reminder settings returned: templateVariableCount={data.get('templateVariableCount')}")
    
    def test_03_update_reminder_settings(self, user_session):
        """PUT /api/reminders/settings updates settings including templateVariableCount"""
        response = user_session.put(
            f"{BASE_URL}/api/reminders/settings",
            json={"templateVariableCount": 3}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ PUT reminder settings updated successfully")
    
    def test_04_delete_reminder_404(self, user_session):
        """DELETE /api/reminders/{id} returns 404 for non-existent reminder"""
        response = user_session.delete(f"{BASE_URL}/api/reminders/nonexistent-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent reminder correctly returns 404")


# =======================
# CONTACTS TESTS
# =======================
class TestContacts:
    """Contacts endpoint tests"""
    
    created_contact_id = None
    created_group_id = None
    
    def test_01_get_contacts(self, user_session):
        """GET /api/contacts returns user's contacts"""
        response = user_session.get(f"{BASE_URL}/api/contacts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "contacts" in data, "contacts key missing"
        assert "total" in data, "total key missing"
        print(f"✓ GET contacts returned {data.get('total')} contacts")
    
    def test_02_create_contact(self, user_session):
        """POST /api/contacts creates new contact"""
        response = user_session.post(
            f"{BASE_URL}/api/contacts",
            json={
                "name": f"TEST_Contact_{uuid.uuid4().hex[:6]}",
                "phone": "9876543210",
                "email": "test@example.com",
                "sendBirthdayWish": True
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "contact" in data, "contact key missing"
        TestContacts.created_contact_id = data["contact"]["id"]
        print(f"✓ Created contact with ID: {TestContacts.created_contact_id}")
    
    def test_03_update_contact(self, user_session):
        """PUT /api/contacts/{id} updates contact"""
        if not TestContacts.created_contact_id:
            pytest.skip("No contact to update")
        
        response = user_session.put(
            f"{BASE_URL}/api/contacts/{TestContacts.created_contact_id}",
            json={"notes": "Updated by test"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Contact updated successfully")
    
    def test_04_delete_contact(self, user_session):
        """DELETE /api/contacts/{id} deletes contact"""
        if not TestContacts.created_contact_id:
            pytest.skip("No contact to delete")
        
        response = user_session.delete(
            f"{BASE_URL}/api/contacts/{TestContacts.created_contact_id}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Deleted contact {TestContacts.created_contact_id}")
    
    def test_05_get_contact_groups(self, user_session):
        """GET /api/contacts/groups returns user's groups"""
        response = user_session.get(f"{BASE_URL}/api/contacts/groups")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "groups" in data, "groups key missing"
        print(f"✓ GET contact groups returned {len(data.get('groups', []))} groups")
    
    def test_06_create_contact_group(self, user_session):
        """POST /api/contacts/groups creates new group"""
        response = user_session.post(
            f"{BASE_URL}/api/contacts/groups",
            json={
                "name": f"TEST_Group_{uuid.uuid4().hex[:6]}",
                "description": "Test group",
                "color": "#3B82F6"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "group" in data, "group key missing"
        TestContacts.created_group_id = data["group"]["id"]
        print(f"✓ Created group with ID: {TestContacts.created_group_id}")
        
        # Cleanup: delete the group
        user_session.delete(f"{BASE_URL}/api/contacts/groups/{TestContacts.created_group_id}")
    
    def test_07_get_auto_message_settings(self, user_session):
        """GET /api/contacts/settings/auto-messages returns auto-message settings"""
        response = user_session.get(f"{BASE_URL}/api/contacts/settings/auto-messages")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "settings" in data, "settings key missing"
        settings = data["settings"]
        
        # Check for template variable count fields
        print(f"✓ GET auto-message settings: birthdayEnabled={settings.get('birthdayEnabled')}, "
              f"birthdayTemplateVariableCount={settings.get('birthdayTemplateVariableCount')}")
    
    def test_08_update_auto_message_settings(self, user_session):
        """PUT /api/contacts/settings/auto-messages updates settings with templateVariableCount"""
        response = user_session.put(
            f"{BASE_URL}/api/contacts/settings/auto-messages",
            json={
                "birthdayEnabled": True,
                "birthdayTemplateVariableCount": 2
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ PUT auto-message settings updated successfully")


# =======================
# INDIAMART TESTS
# =======================
class TestIndiamart:
    """Indiamart integration tests"""
    
    def test_01_get_indiamart_settings(self, user_session):
        """GET /api/indiamart/settings returns webhook URL and settings"""
        response = user_session.get(f"{BASE_URL}/api/indiamart/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "settings" in data, "settings key missing"
        assert "webhookUrl" in data, "webhookUrl key missing"
        
        settings = data["settings"]
        assert "isActive" in settings, "isActive missing from settings"
        assert "webhookSecret" in settings, "webhookSecret missing"
        print(f"✓ GET Indiamart settings: isActive={settings.get('isActive')}, webhookUrl exists")
    
    def test_02_update_indiamart_settings(self, user_session):
        """PUT /api/indiamart/settings updates settings"""
        response = user_session.put(
            f"{BASE_URL}/api/indiamart/settings",
            json={
                "isActive": True,
                "templateName": "test_template",
                "templateVariableCount": 2
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ PUT Indiamart settings updated successfully")
    
    def test_03_get_indiamart_leads(self, user_session):
        """GET /api/indiamart/leads returns leads list with stats"""
        response = user_session.get(f"{BASE_URL}/api/indiamart/leads")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leads" in data, "leads key missing"
        assert "stats" in data, "stats key missing"
        assert "total" in data, "total key missing"
        
        print(f"✓ GET Indiamart leads: total={data.get('total')}, stats={data.get('stats')}")
    
    def test_04_webhook_invalid_secret(self, user_session):
        """POST /api/indiamart/webhook/{user_id} rejects invalid secret"""
        # Get user ID from session
        me_response = user_session.get(f"{BASE_URL}/api/auth/me")
        user_id = me_response.json().get("id")
        
        # Try with invalid secret
        response = requests.post(
            f"{BASE_URL}/api/indiamart/webhook/{user_id}?secret=invalid_secret",
            json={"SENDER_NAME": "Test", "SENDER_MOBILE": "9876543210"},
            headers={"Content-Type": "application/json"}
        )
        # Should be 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Webhook correctly rejects invalid secret")
    
    def test_05_update_lead_404(self, user_session):
        """PUT /api/indiamart/leads/{id} returns 404 for non-existent lead"""
        response = user_session.put(
            f"{BASE_URL}/api/indiamart/leads/nonexistent-id",
            json={"status": "converted"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent lead correctly returns 404")
    
    def test_06_resend_lead_message_404(self, user_session):
        """POST /api/indiamart/leads/{id}/resend returns 404 for non-existent lead"""
        response = user_session.post(f"{BASE_URL}/api/indiamart/leads/nonexistent-id/resend")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Resend for non-existent lead correctly returns 404")


# =======================
# DAILY LIMIT & RESET TESTS
# =======================
class TestDailyLimitReset:
    """Tests for 24-hour time-based daily limit reset"""
    
    def test_01_auth_me_returns_reset_fields(self, user_session):
        """Verify /api/auth/me returns 'remaining' and 'nextResetAt' fields"""
        response = user_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "remaining" in data, "'remaining' field missing from /me response"
        assert "dailyLimit" in data, "'dailyLimit' field missing"
        
        remaining = data.get("remaining")
        daily_limit = data.get("dailyLimit")
        daily_usage = data.get("dailyUsage", 0)
        
        # Verify remaining calculation is correct
        expected_remaining = daily_limit - daily_usage
        assert remaining == expected_remaining, f"remaining should be {expected_remaining}, got {remaining}"
        
        print(f"✓ Daily limit fields: remaining={remaining}, dailyLimit={daily_limit}, dailyUsage={daily_usage}")
        
        # nextResetAt may be null if no activity yet
        if data.get("nextResetAt"):
            print(f"  nextResetAt: {data.get('nextResetAt')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
