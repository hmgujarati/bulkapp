"""
Test suite for the Simplified Chatbot System
Tests the new Flow-based model (replacing Category->Product->Flow)

Collections used:
- chatbot_settings: Global settings per user
- chatbot_flows: NEW - replaces chatbot_categories + chatbot_flow_questions + chatbot_products
- chatbot_conversations: Active chat sessions
- chatbot_leads: Completed conversations
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://whatsapp-lead-flow.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "bizchatapi@gmail.com"
ADMIN_PASSWORD = "adminpassword"
USER_EMAIL = "rapidexpresstechnologies@gmail.com"
USER_PASSWORD = "admin"


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful")
    
    def test_user_login(self):
        """Test regular user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"✓ User login successful")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Admin login failed")


@pytest.fixture(scope="module")
def user_token():
    """Get user auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("User login failed")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin auth headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def user_headers(user_token):
    """User auth headers"""
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}


class TestChatbotSettings:
    """Test chatbot settings API - GET/PUT /api/chatbot/settings"""
    
    def test_get_settings_returns_webhook_url(self, user_headers):
        """GET /api/chatbot/settings returns settings with webhookUrl"""
        response = requests.get(f"{BASE_URL}/api/chatbot/settings", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "webhookUrl" in data, "Settings should include webhookUrl"
        assert "isActive" in data
        assert "followUpDelayMinutes" in data
        assert "maxFollowUps" in data
        assert "followUpMessage" in data
        
        # Verify webhookUrl format
        assert "/api/webhook/" in data["webhookUrl"], f"webhookUrl should contain /api/webhook/, got: {data['webhookUrl']}"
        print(f"✓ GET /api/chatbot/settings returns webhookUrl: {data['webhookUrl']}")
    
    def test_update_settings(self, user_headers):
        """PUT /api/chatbot/settings updates settings"""
        update_data = {
            "isActive": True,
            "defaultNotifyPhone": "919876543210",
            "followUpDelayMinutes": 20,
            "maxFollowUps": 3,
            "followUpMessage": "TEST: Would you like to continue?"
        }
        
        response = requests.put(f"{BASE_URL}/api/chatbot/settings", json=update_data, headers=user_headers)
        assert response.status_code == 200
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/chatbot/settings", headers=user_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["isActive"] == True
        assert data["defaultNotifyPhone"] == "919876543210"
        assert data["followUpDelayMinutes"] == 20
        assert data["maxFollowUps"] == 3
        print(f"✓ PUT /api/chatbot/settings updates correctly")


class TestChatbotFlowsCRUD:
    """Test chatbot flows CRUD - /api/chatbot/flows"""
    
    test_flow_id = None
    
    def test_create_flow(self, user_headers):
        """POST /api/chatbot/flows creates a flow with all fields"""
        flow_data = {
            "name": "TEST_WhatsApp API Inquiry",
            "triggerKeywords": ["api", "whatsapp", "pricing"],
            "greetingMessage": "Hello! Thanks for your interest in our WhatsApp API service.",
            "completionMessage": "Thank you! Our team will contact you within 24 hours.",
            "questions": [
                {
                    "questionText": "What is your name?",
                    "questionType": "text",
                    "options": []
                },
                {
                    "questionText": "What is your company name?",
                    "questionType": "text",
                    "options": []
                },
                {
                    "questionText": "What is your expected monthly message volume?",
                    "questionType": "button",
                    "options": ["< 10,000", "10,000 - 50,000", "> 50,000"]
                },
                {
                    "questionText": "Which features interest you?",
                    "questionType": "list",
                    "options": ["Bulk Messaging", "Chatbot", "Templates", "Analytics", "API Integration"]
                }
            ],
            "notifyPhone": "919876543210"
        }
        
        response = requests.post(f"{BASE_URL}/api/chatbot/flows", json=flow_data, headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["message"] == "Flow created"
        TestChatbotFlowsCRUD.test_flow_id = data["id"]
        print(f"✓ POST /api/chatbot/flows created flow with id: {data['id']}")
    
    def test_get_all_flows(self, user_headers):
        """GET /api/chatbot/flows returns all flows"""
        response = requests.get(f"{BASE_URL}/api/chatbot/flows", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "flows" in data
        assert isinstance(data["flows"], list)
        
        # Find our test flow
        test_flows = [f for f in data["flows"] if f.get("name", "").startswith("TEST_")]
        assert len(test_flows) > 0, "Should find at least one TEST_ flow"
        
        flow = test_flows[0]
        assert "triggerKeywords" in flow
        assert "questions" in flow
        assert "greetingMessage" in flow
        assert "completionMessage" in flow
        print(f"✓ GET /api/chatbot/flows returns {len(data['flows'])} flows")
    
    def test_get_single_flow(self, user_headers):
        """GET /api/chatbot/flows/{flow_id} returns single flow"""
        if not TestChatbotFlowsCRUD.test_flow_id:
            pytest.skip("No test flow created")
        
        response = requests.get(f"{BASE_URL}/api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id}", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == TestChatbotFlowsCRUD.test_flow_id
        assert data["name"] == "TEST_WhatsApp API Inquiry"
        assert len(data["triggerKeywords"]) == 3
        assert len(data["questions"]) == 4
        
        # Verify question types
        assert data["questions"][0]["questionType"] == "text"
        assert data["questions"][2]["questionType"] == "button"
        assert data["questions"][3]["questionType"] == "list"
        print(f"✓ GET /api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id} returns correct flow")
    
    def test_update_flow(self, user_headers):
        """PUT /api/chatbot/flows/{flow_id} updates a flow"""
        if not TestChatbotFlowsCRUD.test_flow_id:
            pytest.skip("No test flow created")
        
        update_data = {
            "name": "TEST_Updated Flow Name",
            "triggerKeywords": ["api", "whatsapp", "pricing", "demo"],
            "isActive": False
        }
        
        response = requests.put(
            f"{BASE_URL}/api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id}",
            json=update_data,
            headers=user_headers
        )
        assert response.status_code == 200
        
        # Verify update persisted
        get_response = requests.get(
            f"{BASE_URL}/api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id}",
            headers=user_headers
        )
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["name"] == "TEST_Updated Flow Name"
        assert len(data["triggerKeywords"]) == 4
        assert data["isActive"] == False
        print(f"✓ PUT /api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id} updates correctly")
    
    def test_get_nonexistent_flow_returns_404(self, user_headers):
        """GET /api/chatbot/flows/{flow_id} returns 404 for nonexistent flow"""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/chatbot/flows/{fake_id}", headers=user_headers)
        assert response.status_code == 404
        print(f"✓ GET /api/chatbot/flows/{fake_id} returns 404")


class TestChatbotLeads:
    """Test chatbot leads API - /api/chatbot/leads"""
    
    def test_get_leads_with_filters(self, user_headers):
        """GET /api/chatbot/leads with filters (status, flow_id, search, page)"""
        # Test basic get
        response = requests.get(f"{BASE_URL}/api/chatbot/leads", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "leads" in data
        assert "total" in data
        assert "page" in data
        assert "totalPages" in data
        assert "stats" in data
        
        # Verify stats structure
        stats = data["stats"]
        assert "total" in stats
        assert "new" in stats
        assert "qualified" in stats
        assert "contacted" in stats
        print(f"✓ GET /api/chatbot/leads returns {data['total']} leads with stats")
    
    def test_get_leads_with_status_filter(self, user_headers):
        """GET /api/chatbot/leads?status=new filters by status"""
        response = requests.get(f"{BASE_URL}/api/chatbot/leads?status=new", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        # All returned leads should have status=new
        for lead in data["leads"]:
            assert lead["status"] == "new", f"Expected status 'new', got '{lead['status']}'"
        print(f"✓ GET /api/chatbot/leads?status=new filters correctly")
    
    def test_get_leads_with_pagination(self, user_headers):
        """GET /api/chatbot/leads?page=1&limit=5 paginates correctly"""
        response = requests.get(f"{BASE_URL}/api/chatbot/leads?page=1&limit=5", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert len(data["leads"]) <= 5
        print(f"✓ GET /api/chatbot/leads pagination works")
    
    def test_update_lead_status(self, user_headers):
        """PUT /api/chatbot/leads/{lead_id} updates lead status"""
        # First get a lead
        response = requests.get(f"{BASE_URL}/api/chatbot/leads", headers=user_headers)
        if response.status_code != 200 or len(response.json().get("leads", [])) == 0:
            pytest.skip("No leads available to test update")
        
        lead = response.json()["leads"][0]
        lead_id = lead["id"]
        
        # Update status
        update_response = requests.put(
            f"{BASE_URL}/api/chatbot/leads/{lead_id}",
            json={"status": "contacted", "notes": "TEST: Called customer"},
            headers=user_headers
        )
        assert update_response.status_code == 200
        print(f"✓ PUT /api/chatbot/leads/{lead_id} updates status")
    
    def test_update_nonexistent_lead_returns_404(self, user_headers):
        """PUT /api/chatbot/leads/{lead_id} returns 404 for nonexistent lead"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/chatbot/leads/{fake_id}",
            json={"status": "contacted"},
            headers=user_headers
        )
        assert response.status_code == 404
        print(f"✓ PUT /api/chatbot/leads/{fake_id} returns 404")


class TestChatbotLeadsExport:
    """Test chatbot leads export - GET /api/chatbot/leads/export"""
    
    def test_export_leads_csv(self, user_headers):
        """GET /api/chatbot/leads/export returns CSV"""
        response = requests.get(f"{BASE_URL}/api/chatbot/leads/export", headers=user_headers)
        assert response.status_code == 200
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        # Check content disposition
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert "chatbot_leads.csv" in content_disp
        
        # Verify CSV has headers
        content = response.text
        assert "Phone" in content
        assert "Name" in content
        assert "Flow" in content
        assert "Status" in content
        print(f"✓ GET /api/chatbot/leads/export returns valid CSV")


class TestChatbotStats:
    """Test chatbot stats API - GET /api/chatbot/stats"""
    
    def test_get_stats(self, user_headers):
        """GET /api/chatbot/stats returns totalFlows, activeFlows, totalLeads, activeConversations"""
        response = requests.get(f"{BASE_URL}/api/chatbot/stats", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields
        assert "totalFlows" in data
        assert "activeFlows" in data
        assert "totalLeads" in data
        assert "activeConversations" in data
        
        # Verify types
        assert isinstance(data["totalFlows"], int)
        assert isinstance(data["activeFlows"], int)
        assert isinstance(data["totalLeads"], int)
        assert isinstance(data["activeConversations"], int)
        
        print(f"✓ GET /api/chatbot/stats returns: totalFlows={data['totalFlows']}, activeFlows={data['activeFlows']}, totalLeads={data['totalLeads']}, activeConversations={data['activeConversations']}")


class TestRetryFailedEndpoint:
    """Test retry failed messages endpoint - POST /api/messages/campaigns/{id}/retry-failed"""
    
    def test_retry_failed_nonexistent_campaign_returns_404(self, user_headers):
        """POST /api/messages/campaigns/{id}/retry-failed returns 404 for nonexistent campaign"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/messages/campaigns/{fake_id}/retry-failed",
            headers=user_headers
        )
        # Should return 404, not a routing error
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        print(f"✓ POST /api/messages/campaigns/{fake_id}/retry-failed returns 404 (not routing error)")


class TestCleanup:
    """Cleanup test data"""
    
    def test_delete_test_flow(self, user_headers):
        """DELETE /api/chatbot/flows/{flow_id} deletes a flow"""
        if not TestChatbotFlowsCRUD.test_flow_id:
            pytest.skip("No test flow to delete")
        
        response = requests.delete(
            f"{BASE_URL}/api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id}",
            headers=user_headers
        )
        assert response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(
            f"{BASE_URL}/api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id}",
            headers=user_headers
        )
        assert get_response.status_code == 404
        print(f"✓ DELETE /api/chatbot/flows/{TestChatbotFlowsCRUD.test_flow_id} deleted successfully")
    
    def test_cleanup_all_test_flows(self, user_headers):
        """Cleanup any remaining TEST_ flows"""
        response = requests.get(f"{BASE_URL}/api/chatbot/flows", headers=user_headers)
        if response.status_code == 200:
            flows = response.json().get("flows", [])
            for flow in flows:
                if flow.get("name", "").startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/chatbot/flows/{flow['id']}", headers=user_headers)
                    print(f"  Cleaned up flow: {flow['name']}")
        print(f"✓ Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
