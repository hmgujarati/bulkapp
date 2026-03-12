"""
Chatbot Lead Qualification API Tests
Tests for: Settings, Categories, Products, Questions, Leads, Stats endpoints
"""
import pytest
import requests
import os
import io
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials
ADMIN_EMAIL = "bizchatapi@gmail.com"
ADMIN_PASSWORD = "adminpassword"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code}")
    return response.json().get("token")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestChatbotSettings:
    """Chatbot Settings endpoint tests"""

    def test_get_settings_returns_default(self, api_client):
        """GET /api/chatbot/settings - Returns default settings for new/existing user"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify required fields exist
        assert "isActive" in data
        assert "greetingMessage" in data
        assert "completionMessage" in data
        assert "followUpDelayMinutes" in data
        assert "maxFollowUps" in data
        assert "followUpMessage" in data
        assert "notifyMainNumber" in data

    def test_update_settings(self, api_client):
        """PUT /api/chatbot/settings - Update chatbot settings"""
        update_data = {
            "isActive": True,
            "greetingMessage": "TEST greeting message",
            "completionMessage": "TEST completion message",
            "followUpDelayMinutes": 30,
            "maxFollowUps": 3,
            "followUpMessage": "TEST follow-up message",
            "notifyMainNumber": True,
            "mainNotifyPhone": "919876543210"
        }
        response = api_client.put(f"{BASE_URL}/api/chatbot/settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update persisted
        get_response = api_client.get(f"{BASE_URL}/api/chatbot/settings")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["isActive"] == True
        assert data["greetingMessage"] == "TEST greeting message"
        assert data["followUpDelayMinutes"] == 30


class TestChatbotCategories:
    """Category CRUD endpoint tests"""

    def test_get_categories_empty_or_list(self, api_client):
        """GET /api/chatbot/categories - Returns categories list"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "categories" in data
        assert isinstance(data["categories"], list)

    def test_create_category(self, api_client):
        """POST /api/chatbot/categories - Create a category"""
        category_data = {
            "name": f"TEST_Category_{uuid.uuid4().hex[:8]}",
            "description": "Test category description",
            "employeePhone": "919876543210",
            "employeeName": "Test Employee"
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/categories", json=category_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "message" in data
        return data["id"]

    def test_create_and_get_category_persisted(self, api_client):
        """POST then GET - Verify category was persisted"""
        # Create
        category_data = {
            "name": f"TEST_Persist_{uuid.uuid4().hex[:8]}",
            "description": "Persistence test"
        }
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/categories", json=category_data)
        assert create_response.status_code == 200
        category_id = create_response.json()["id"]
        
        # Get and verify
        get_response = api_client.get(f"{BASE_URL}/api/chatbot/categories")
        assert get_response.status_code == 200
        categories = get_response.json()["categories"]
        found = any(c["id"] == category_id for c in categories)
        assert found, "Created category not found in list"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/chatbot/categories/{category_id}")

    def test_update_category(self, api_client):
        """PUT /api/chatbot/categories/{id} - Update a category"""
        # First create
        category_data = {"name": f"TEST_Update_{uuid.uuid4().hex[:8]}"}
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/categories", json=category_data)
        assert create_response.status_code == 200
        category_id = create_response.json()["id"]
        
        # Update
        update_data = {"name": "TEST_Updated_Name", "description": "Updated description"}
        update_response = api_client.put(f"{BASE_URL}/api/chatbot/categories/{category_id}", json=update_data)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify update
        get_response = api_client.get(f"{BASE_URL}/api/chatbot/categories")
        categories = get_response.json()["categories"]
        updated_cat = next((c for c in categories if c["id"] == category_id), None)
        assert updated_cat is not None
        assert updated_cat["name"] == "TEST_Updated_Name"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/chatbot/categories/{category_id}")

    def test_delete_category(self, api_client):
        """DELETE /api/chatbot/categories/{id} - Delete a category"""
        # Create first
        category_data = {"name": f"TEST_Delete_{uuid.uuid4().hex[:8]}"}
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/categories", json=category_data)
        assert create_response.status_code == 200
        category_id = create_response.json()["id"]
        
        # Delete
        delete_response = api_client.delete(f"{BASE_URL}/api/chatbot/categories/{category_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        
        # Verify deleted
        get_response = api_client.get(f"{BASE_URL}/api/chatbot/categories")
        categories = get_response.json()["categories"]
        found = any(c["id"] == category_id for c in categories)
        assert not found, "Deleted category still in list"

    def test_delete_nonexistent_category(self, api_client):
        """DELETE /api/chatbot/categories/{id} - Returns 404 for non-existent"""
        response = api_client.delete(f"{BASE_URL}/api/chatbot/categories/nonexistent-id-12345")
        assert response.status_code == 404


class TestChatbotProducts:
    """Product CRUD endpoint tests"""

    @pytest.fixture
    def test_category(self, api_client):
        """Create a test category for products"""
        category_data = {"name": f"TEST_ProdCat_{uuid.uuid4().hex[:8]}"}
        response = api_client.post(f"{BASE_URL}/api/chatbot/categories", json=category_data)
        category_id = response.json()["id"]
        yield category_id
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/chatbot/categories/{category_id}")

    def test_get_products_empty_or_list(self, api_client):
        """GET /api/chatbot/products - Returns products list"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert "totalPages" in data

    def test_create_product(self, api_client, test_category):
        """POST /api/chatbot/products - Create a product"""
        product_data = {
            "categoryId": test_category,
            "name": f"TEST_Product_{uuid.uuid4().hex[:8]}",
            "description": "Test product description",
            "price": "999"
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/products", json=product_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "message" in data

    def test_create_product_invalid_category(self, api_client):
        """POST /api/chatbot/products - Returns 404 for invalid category"""
        product_data = {
            "categoryId": "invalid-category-id",
            "name": "Test Product",
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/products", json=product_data)
        assert response.status_code == 404

    def test_get_products_with_filters(self, api_client, test_category):
        """GET /api/chatbot/products - Filter by category and search"""
        # Create a product first
        product_data = {
            "categoryId": test_category,
            "name": "TEST_FilterProd_Unique123",
        }
        api_client.post(f"{BASE_URL}/api/chatbot/products", json=product_data)
        
        # Filter by category
        response = api_client.get(f"{BASE_URL}/api/chatbot/products", params={"category_id": test_category})
        assert response.status_code == 200
        
        # Filter by search
        response = api_client.get(f"{BASE_URL}/api/chatbot/products", params={"search": "FilterProd"})
        assert response.status_code == 200

    def test_update_product(self, api_client, test_category):
        """PUT /api/chatbot/products/{id} - Update a product"""
        # Create
        product_data = {"categoryId": test_category, "name": "TEST_UpdProd"}
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/products", json=product_data)
        product_id = create_response.json()["id"]
        
        # Update
        update_data = {"name": "TEST_UpdatedProduct", "price": "1999"}
        update_response = api_client.put(f"{BASE_URL}/api/chatbot/products/{product_id}", json=update_data)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"

    def test_delete_product(self, api_client, test_category):
        """DELETE /api/chatbot/products/{id} - Delete a product"""
        # Create
        product_data = {"categoryId": test_category, "name": "TEST_DelProd"}
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/products", json=product_data)
        product_id = create_response.json()["id"]
        
        # Delete
        delete_response = api_client.delete(f"{BASE_URL}/api/chatbot/products/{product_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"

    def test_bulk_upload_products(self, api_client):
        """POST /api/chatbot/products/bulk-upload - Upload CSV with products"""
        csv_content = """Category,Product Name,Description,Price
TEST_BulkCat,TEST_BulkProd1,Description 1,100
TEST_BulkCat,TEST_BulkProd2,Description 2,200
TEST_BulkCat2,TEST_BulkProd3,Description 3,300
"""
        files = {"file": ("products.csv", csv_content, "text/csv")}
        # Need to remove Content-Type header for file upload
        session = requests.Session()
        session.headers.update({"Authorization": api_client.headers["Authorization"]})
        
        response = session.post(f"{BASE_URL}/api/chatbot/products/bulk-upload", files=files)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "created" in data
        assert data["created"] >= 3

        # Cleanup - delete the created categories (which cascades to products)
        categories_response = api_client.get(f"{BASE_URL}/api/chatbot/categories")
        for cat in categories_response.json()["categories"]:
            if cat["name"].startswith("TEST_BulkCat"):
                api_client.delete(f"{BASE_URL}/api/chatbot/categories/{cat['id']}")


class TestChatbotQuestions:
    """Flow Questions endpoint tests"""

    @pytest.fixture
    def test_category_for_questions(self, api_client):
        """Create a test category for questions"""
        category_data = {"name": f"TEST_QCat_{uuid.uuid4().hex[:8]}"}
        response = api_client.post(f"{BASE_URL}/api/chatbot/categories", json=category_data)
        category_id = response.json()["id"]
        yield category_id
        api_client.delete(f"{BASE_URL}/api/chatbot/categories/{category_id}")

    def test_get_questions_for_category(self, api_client, test_category_for_questions):
        """GET /api/chatbot/questions/{category_id} - Returns questions list"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/questions/{test_category_for_questions}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "questions" in data
        assert isinstance(data["questions"], list)

    def test_create_question_text_type(self, api_client, test_category_for_questions):
        """POST /api/chatbot/questions - Create text type question"""
        question_data = {
            "categoryId": test_category_for_questions,
            "questionText": "TEST: What is your name?",
            "questionType": "text",
            "isRequired": True
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=question_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data

    def test_create_question_button_type(self, api_client, test_category_for_questions):
        """POST /api/chatbot/questions - Create button type question with options"""
        question_data = {
            "categoryId": test_category_for_questions,
            "questionText": "TEST: What is your budget?",
            "questionType": "button",
            "options": ["Under 10K", "10K-50K", "Above 50K"],
            "isRequired": True
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=question_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_create_question_list_type(self, api_client, test_category_for_questions):
        """POST /api/chatbot/questions - Create list type question"""
        question_data = {
            "categoryId": test_category_for_questions,
            "questionText": "TEST: Which city are you from?",
            "questionType": "list",
            "options": ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata"],
            "isRequired": True
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=question_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_create_question_invalid_category(self, api_client):
        """POST /api/chatbot/questions - Returns 404 for invalid category"""
        question_data = {
            "categoryId": "invalid-cat-id",
            "questionText": "Test question",
            "questionType": "text"
        }
        response = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=question_data)
        assert response.status_code == 404

    def test_update_question(self, api_client, test_category_for_questions):
        """PUT /api/chatbot/questions/{id} - Update a question"""
        # Create
        question_data = {
            "categoryId": test_category_for_questions,
            "questionText": "TEST: Original question",
            "questionType": "text"
        }
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=question_data)
        question_id = create_response.json()["id"]
        
        # Update
        update_data = {"questionText": "TEST: Updated question text"}
        update_response = api_client.put(f"{BASE_URL}/api/chatbot/questions/{question_id}", json=update_data)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"

    def test_delete_question(self, api_client, test_category_for_questions):
        """DELETE /api/chatbot/questions/{id} - Delete a question"""
        # Create
        question_data = {
            "categoryId": test_category_for_questions,
            "questionText": "TEST: Delete me",
            "questionType": "text"
        }
        create_response = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=question_data)
        question_id = create_response.json()["id"]
        
        # Delete
        delete_response = api_client.delete(f"{BASE_URL}/api/chatbot/questions/{question_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"

    def test_reorder_questions(self, api_client, test_category_for_questions):
        """PUT /api/chatbot/questions/reorder/{category_id} - Reorder questions"""
        # Create 3 questions
        q_ids = []
        for i in range(3):
            q_data = {
                "categoryId": test_category_for_questions,
                "questionText": f"TEST: Question {i+1}",
                "questionType": "text",
                "sortOrder": i
            }
            resp = api_client.post(f"{BASE_URL}/api/chatbot/questions", json=q_data)
            q_ids.append(resp.json()["id"])
        
        # Reorder (reverse)
        reversed_ids = list(reversed(q_ids))
        reorder_response = api_client.put(
            f"{BASE_URL}/api/chatbot/questions/reorder/{test_category_for_questions}",
            json=reversed_ids
        )
        assert reorder_response.status_code == 200, f"Expected 200, got {reorder_response.status_code}: {reorder_response.text}"


class TestChatbotLeads:
    """Leads endpoint tests"""

    def test_get_leads_list(self, api_client):
        """GET /api/chatbot/leads - Returns leads list with stats"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/leads")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
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

    def test_get_leads_with_filters(self, api_client):
        """GET /api/chatbot/leads - Filter by status and search"""
        # Filter by status
        response = api_client.get(f"{BASE_URL}/api/chatbot/leads", params={"status": "new"})
        assert response.status_code == 200
        
        # Filter by search
        response = api_client.get(f"{BASE_URL}/api/chatbot/leads", params={"search": "test"})
        assert response.status_code == 200

    def test_update_lead_status_nonexistent(self, api_client):
        """PUT /api/chatbot/leads/{id} - Returns 404 for non-existent lead"""
        response = api_client.put(f"{BASE_URL}/api/chatbot/leads/nonexistent-lead-id", json={"status": "contacted"})
        assert response.status_code == 404

    def test_delete_lead_nonexistent(self, api_client):
        """DELETE /api/chatbot/leads/{id} - Returns 404 for non-existent lead"""
        response = api_client.delete(f"{BASE_URL}/api/chatbot/leads/nonexistent-lead-id")
        assert response.status_code == 404

    def test_export_leads_csv(self, api_client):
        """GET /api/chatbot/leads/export - Export leads as CSV"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/leads/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify CSV response
        assert "text/csv" in response.headers.get("Content-Type", "")


class TestChatbotStats:
    """Stats endpoint tests"""

    def test_get_stats(self, api_client):
        """GET /api/chatbot/stats - Returns chatbot statistics"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "categories" in data
        assert "products" in data
        assert "totalLeads" in data
        assert "activeConversations" in data
        
        # Verify types
        assert isinstance(data["categories"], int)
        assert isinstance(data["products"], int)
        assert isinstance(data["totalLeads"], int)
        assert isinstance(data["activeConversations"], int)


class TestChatbotCleanup:
    """Cleanup test data"""

    def test_cleanup_test_categories(self, api_client):
        """Cleanup any remaining TEST_ prefixed categories"""
        response = api_client.get(f"{BASE_URL}/api/chatbot/categories")
        if response.status_code == 200:
            for cat in response.json().get("categories", []):
                if cat["name"].startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/chatbot/categories/{cat['id']}")
        assert True  # Always pass - cleanup is best effort
