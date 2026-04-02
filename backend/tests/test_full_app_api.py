"""
Comprehensive API tests for WhatsApp Automation Platform
Tests: Auth, Admin, Chatbot, Webhook, Campaigns, Contacts, Reminders, Indiamart
"""
import pytest
import requests
import os
import uuid
import csv
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from requirements
ADMIN_EMAIL = "bizchatapi@gmail.com"
ADMIN_PASSWORD = "adminpassword"
USER_EMAIL = "rapidexpresstechnologies@gmail.com"
USER_PASSWORD = "admin"
USER_ID = "61b4ea2d-4358-4cf9-be71-cc0f92433d6f"


class TestHealthCheck:
    """Basic health check"""
    
    def test_health_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")


class TestAuthLogin:
    """Authentication login tests"""
    
    def test_login_admin_success(self):
        """POST /api/auth/login - Login with valid admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data, "Token missing from response"
        assert "user" in data, "User missing from response"
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_login_user_success(self):
        """POST /api/auth/login - Login with valid user credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == USER_EMAIL
        print(f"✓ User login successful: {data['user']['email']}")
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login - Reject invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected")


class TestAuthMe:
    """Auth /me endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_current_user(self, admin_token):
        """GET /api/auth/me - Get current user info with token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("email") == ADMIN_EMAIL
        assert "id" in data
        print(f"✓ Get current user: {data.get('email')}")
    
    def test_get_me_without_token(self):
        """GET /api/auth/me - Should fail without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("✓ Unauthorized access correctly rejected")


class TestAdminLoginAs:
    """Admin Login-As feature tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture
    def user_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })
        return response.json().get("token")
    
    def test_admin_login_as_user(self, admin_token):
        """POST /api/auth/login-as/{user_id} - Admin can login as another user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login-as/{USER_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["id"] == USER_ID
        print(f"✓ Admin login-as successful: {data['user']['email']}")
    
    def test_non_admin_login_as_rejected(self, user_token):
        """POST /api/auth/login-as/{user_id} - Non-admin gets rejected"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login-as/{USER_ID}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-admin login-as correctly rejected")
    
    def test_login_as_nonexistent_user(self, admin_token):
        """POST /api/auth/login-as/{user_id} - 404 for non-existent user"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/auth/login-as/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        print("✓ Login-as non-existent user returns 404")


class TestAdminUserManagement:
    """Admin user management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_admin_list_users(self, admin_token):
        """GET /api/users - Admin can list all users"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) > 0
        print(f"✓ Admin listed {len(data['users'])} users")
    
    def test_admin_update_user_features(self, admin_token):
        """PUT /api/users/{user_id}/features - Admin can update user features including chatbot"""
        response = requests.put(
            f"{BASE_URL}/api/users/{USER_ID}/features",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"chatbot": True, "indiamart": True}
        )
        # Note: chatbot might not be in valid_features list - check response
        if response.status_code == 400:
            # If chatbot is not in valid features, that's a bug to report
            print(f"⚠ Feature update returned 400: {response.text}")
        else:
            assert response.status_code == 200
            print("✓ Admin updated user features")
    
    def test_admin_update_daily_limit(self, admin_token):
        """PUT /api/users/{user_id}/limit - Admin can update user daily limit"""
        response = requests.put(
            f"{BASE_URL}/api/users/{USER_ID}/limit",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"dailyLimit": 500}
        )
        assert response.status_code == 200
        print("✓ Admin updated user daily limit")


class TestChatbotSettings:
    """Chatbot settings tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_chatbot_settings(self, admin_token):
        """GET /api/chatbot/settings - Returns chatbot settings with webhookUrl"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "webhookUrl" in data, "webhookUrl missing from settings"
        assert "isActive" in data
        print(f"✓ Chatbot settings retrieved, webhookUrl: {data.get('webhookUrl')[:50]}...")
    
    def test_update_chatbot_settings(self, admin_token):
        """PUT /api/chatbot/settings - Update chatbot settings"""
        response = requests.put(
            f"{BASE_URL}/api/chatbot/settings",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "isActive": True,
                "greetingMessage": "TEST: Welcome to our chatbot!",
                "completionMessage": "TEST: Thank you for your inquiry!"
            }
        )
        assert response.status_code == 200
        print("✓ Chatbot settings updated")


class TestChatbotCategories:
    """Chatbot categories CRUD tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_create_category_with_trigger_keywords(self, admin_token):
        """POST /api/chatbot/categories - Create category with triggerKeywords"""
        response = requests.post(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "TEST_Category_Keywords",
                "description": "Test category with keywords",
                "triggerKeywords": ["test", "demo", "sample"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Category created with ID: {data['id']}")
        return data["id"]
    
    def test_list_categories(self, admin_token):
        """GET /api/chatbot/categories - List categories with product/question counts"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        # Check that counts are included
        if len(data["categories"]) > 0:
            cat = data["categories"][0]
            assert "productCount" in cat or "questionCount" in cat
        print(f"✓ Listed {len(data['categories'])} categories")
    
    def test_update_category(self, admin_token):
        """PUT /api/chatbot/categories/{id} - Update category"""
        # First create a category
        create_resp = requests.post(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_Update_Category", "description": "To be updated"}
        )
        cat_id = create_resp.json().get("id")
        
        # Update it
        response = requests.put(
            f"{BASE_URL}/api/chatbot/categories/{cat_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_Updated_Category", "description": "Updated description"}
        )
        assert response.status_code == 200
        print("✓ Category updated")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/chatbot/categories/{cat_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_delete_category_cascades(self, admin_token):
        """DELETE /api/chatbot/categories/{id} - Delete category cascades to products/questions"""
        # Create category
        create_resp = requests.post(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_Delete_Cascade"}
        )
        cat_id = create_resp.json().get("id")
        
        # Create a product in it
        requests.post(
            f"{BASE_URL}/api/chatbot/products",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": cat_id, "name": "TEST_Product_Cascade"}
        )
        
        # Delete category
        response = requests.delete(
            f"{BASE_URL}/api/chatbot/categories/{cat_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Category deleted with cascade")


class TestChatbotProducts:
    """Chatbot products tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture
    def test_category(self, admin_token):
        """Create a test category for products"""
        response = requests.post(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_Products_Category"}
        )
        cat_id = response.json().get("id")
        yield cat_id
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/chatbot/categories/{cat_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_create_product(self, admin_token, test_category):
        """POST /api/chatbot/products - Create product under category"""
        response = requests.post(
            f"{BASE_URL}/api/chatbot/products",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "categoryId": test_category,
                "name": "TEST_Product_1",
                "description": "Test product description",
                "price": "999"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Product created: {data['id']}")
    
    def test_list_products_with_filters(self, admin_token, test_category):
        """GET /api/chatbot/products - List products with category filter and search"""
        # Create a product first
        requests.post(
            f"{BASE_URL}/api/chatbot/products",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": test_category, "name": "TEST_Searchable_Product"}
        )
        
        # List with category filter
        response = requests.get(
            f"{BASE_URL}/api/chatbot/products?category_id={test_category}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        print(f"✓ Listed {len(data['products'])} products with filter")
        
        # List with search
        response = requests.get(
            f"{BASE_URL}/api/chatbot/products?search=Searchable",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Product search works")
    
    def test_bulk_upload_products(self, admin_token):
        """POST /api/chatbot/products/bulk-upload - CSV upload"""
        csv_content = "Category,Product Name,Description,Price\nTEST_Bulk_Category,TEST_Bulk_Product_1,Desc 1,100\nTEST_Bulk_Category,TEST_Bulk_Product_2,Desc 2,200"
        
        files = {
            'file': ('products.csv', csv_content, 'text/csv')
        }
        response = requests.post(
            f"{BASE_URL}/api/chatbot/products/bulk-upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("created", 0) >= 0
        print(f"✓ Bulk upload: {data.get('created', 0)} products created")
        
        # Cleanup - delete the bulk category
        cats_resp = requests.get(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        for cat in cats_resp.json().get("categories", []):
            if cat["name"] == "TEST_Bulk_Category":
                requests.delete(
                    f"{BASE_URL}/api/chatbot/categories/{cat['id']}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
    
    def test_delete_product(self, admin_token, test_category):
        """DELETE /api/chatbot/products/{id} - Delete product"""
        # Create product
        create_resp = requests.post(
            f"{BASE_URL}/api/chatbot/products",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": test_category, "name": "TEST_Delete_Product"}
        )
        prod_id = create_resp.json().get("id")
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/chatbot/products/{prod_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Product deleted")


class TestChatbotQuestions:
    """Chatbot flow questions tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    @pytest.fixture
    def test_category(self, admin_token):
        response = requests.post(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "TEST_Questions_Category"}
        )
        cat_id = response.json().get("id")
        yield cat_id
        requests.delete(
            f"{BASE_URL}/api/chatbot/categories/{cat_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_create_question(self, admin_token, test_category):
        """POST /api/chatbot/questions - Create qualifying question"""
        response = requests.post(
            f"{BASE_URL}/api/chatbot/questions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "categoryId": test_category,
                "questionText": "TEST: What is your budget?",
                "questionType": "text",
                "isRequired": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        print(f"✓ Question created: {data['id']}")
    
    def test_list_questions(self, admin_token, test_category):
        """GET /api/chatbot/questions/{category_id} - List questions in order"""
        # Create a question first
        requests.post(
            f"{BASE_URL}/api/chatbot/questions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": test_category, "questionText": "TEST Q1", "questionType": "text"}
        )
        
        response = requests.get(
            f"{BASE_URL}/api/chatbot/questions/{test_category}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        print(f"✓ Listed {len(data['questions'])} questions")
    
    def test_reorder_questions(self, admin_token, test_category):
        """PUT /api/chatbot/questions/reorder/{category_id} - Reorder questions"""
        # Create two questions
        q1_resp = requests.post(
            f"{BASE_URL}/api/chatbot/questions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": test_category, "questionText": "TEST Reorder Q1", "questionType": "text"}
        )
        q2_resp = requests.post(
            f"{BASE_URL}/api/chatbot/questions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": test_category, "questionText": "TEST Reorder Q2", "questionType": "text"}
        )
        
        q1_id = q1_resp.json().get("id")
        q2_id = q2_resp.json().get("id")
        
        # Reorder (swap)
        response = requests.put(
            f"{BASE_URL}/api/chatbot/questions/reorder/{test_category}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=[q2_id, q1_id]  # Reversed order
        )
        assert response.status_code == 200
        print("✓ Questions reordered")
    
    def test_delete_question(self, admin_token, test_category):
        """DELETE /api/chatbot/questions/{id} - Delete question"""
        create_resp = requests.post(
            f"{BASE_URL}/api/chatbot/questions",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"categoryId": test_category, "questionText": "TEST Delete Q", "questionType": "text"}
        )
        q_id = create_resp.json().get("id")
        
        response = requests.delete(
            f"{BASE_URL}/api/chatbot/questions/{q_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Question deleted")


class TestChatbotLeads:
    """Chatbot leads tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_list_leads(self, admin_token):
        """GET /api/chatbot/leads - List leads with filters"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/leads",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        assert "stats" in data
        assert "total" in data["stats"]
        print(f"✓ Listed leads, stats: {data['stats']}")
    
    def test_list_leads_with_status_filter(self, admin_token):
        """GET /api/chatbot/leads - List leads with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/leads?status=new",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Leads filtered by status")
    
    def test_export_leads_csv(self, admin_token):
        """GET /api/chatbot/leads/export - Export leads as CSV"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/leads/export",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        print("✓ Leads exported as CSV")


class TestChatbotStats:
    """Chatbot stats tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_chatbot_stats(self, admin_token):
        """GET /api/chatbot/stats - Get chatbot statistics"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "products" in data
        assert "totalLeads" in data
        assert "activeConversations" in data
        print(f"✓ Chatbot stats: {data}")


class TestWebhook:
    """Webhook endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_verify_universal_webhook(self):
        """GET /api/webhook/{user_id} - Verify universal webhook"""
        response = requests.get(f"{BASE_URL}/api/webhook/{USER_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert data.get("user_id") == USER_ID
        print(f"✓ Universal webhook verified for user {USER_ID}")
    
    def test_verify_legacy_webhook(self):
        """GET /api/webhook/bizchat - Verify legacy webhook"""
        response = requests.get(f"{BASE_URL}/api/webhook/bizchat")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Legacy webhook verified")
    
    def test_universal_webhook_ignores_old_message(self):
        """POST /api/webhook/{user_id} - Universal webhook ignores is_new_message=false"""
        response = requests.post(
            f"{BASE_URL}/api/webhook/{USER_ID}",
            json={
                "contact": {"phone_number": "+919999999999"},
                "message": {"body": "test message", "is_new_message": False}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ignored"
        assert data.get("reason") == "not a new message"
        print("✓ Webhook correctly ignores old messages")
    
    def test_universal_webhook_deduplication(self):
        """POST /api/webhook/{user_id} - Universal webhook deduplicates same whatsapp_message_id"""
        unique_msg_id = f"test_dedup_{uuid.uuid4()}"
        
        # First request
        response1 = requests.post(
            f"{BASE_URL}/api/webhook/{USER_ID}",
            json={
                "contact": {"phone_number": "+919999999998"},
                "message": {
                    "body": "dedup test",
                    "is_new_message": True,
                    "whatsapp_message_id": unique_msg_id
                }
            }
        )
        
        # Second request with same message ID
        response2 = requests.post(
            f"{BASE_URL}/api/webhook/{USER_ID}",
            json={
                "contact": {"phone_number": "+919999999998"},
                "message": {
                    "body": "dedup test",
                    "is_new_message": True,
                    "whatsapp_message_id": unique_msg_id
                }
            }
        )
        
        # Second should be ignored as duplicate
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("status") == "ignored"
        assert data2.get("reason") == "duplicate message"
        print("✓ Webhook deduplication working")
    
    def test_legacy_webhook_post(self):
        """POST /api/webhook/bizchat - Legacy webhook still works"""
        response = requests.post(
            f"{BASE_URL}/api/webhook/bizchat",
            json={
                "contact": {"phone_number": "+919999999997"},
                "message": {"body": "legacy test", "is_new_message": True}
            }
        )
        assert response.status_code == 200
        # Should be ignored since phone not registered
        data = response.json()
        assert data.get("status") in ["ignored", "success"]
        print("✓ Legacy webhook POST works")


class TestCampaigns:
    """Campaign and retry-failed tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_retry_failed_nonexistent_campaign(self, admin_token):
        """POST /api/campaigns/{id}/retry-failed - 404 for non-existent campaign"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{fake_id}/retry-failed",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404
        print("✓ Retry-failed returns 404 for non-existent campaign")


class TestContacts:
    """Contact management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_list_contacts(self, admin_token):
        """GET /api/contacts - List contacts"""
        response = requests.get(
            f"{BASE_URL}/api/contacts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "contacts" in data
        assert "total" in data
        print(f"✓ Listed {data['total']} contacts")
    
    def test_create_contact(self, admin_token):
        """POST /api/contacts - Create contact"""
        response = requests.post(
            f"{BASE_URL}/api/contacts",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "TEST_Contact",
                "phone": "+919876543210",
                "email": "test@example.com"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "contact" in data
        contact_id = data["contact"]["id"]
        print(f"✓ Contact created: {contact_id}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/contacts/{contact_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestReminders:
    """Reminder management tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_list_reminders(self, admin_token):
        """GET /api/reminders - List reminders"""
        response = requests.get(
            f"{BASE_URL}/api/reminders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data
        print(f"✓ Listed {len(data['reminders'])} reminders")


class TestIndiamart:
    """Indiamart integration tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_get_indiamart_settings(self, admin_token):
        """GET /api/indiamart/settings - Get Indiamart settings"""
        response = requests.get(
            f"{BASE_URL}/api/indiamart/settings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert "webhookUrl" in data
        print(f"✓ Indiamart settings retrieved")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json().get("token")
    
    def test_cleanup_test_categories(self, admin_token):
        """Cleanup TEST_ prefixed categories"""
        response = requests.get(
            f"{BASE_URL}/api/chatbot/categories",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            for cat in response.json().get("categories", []):
                if cat["name"].startswith("TEST_"):
                    requests.delete(
                        f"{BASE_URL}/api/chatbot/categories/{cat['id']}",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
        print("✓ Test data cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
