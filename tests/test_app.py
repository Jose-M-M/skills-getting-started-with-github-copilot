"""Tests for the Mergington High School API endpoints"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have activities
        assert len(data) > 0
        
        # Check that Chess Club exists and has correct structure
        assert "Chess Club" in data
        assert "description" in data["Chess Club"]
        assert "schedule" in data["Chess Club"]
        assert "max_participants" in data["Chess Club"]
        assert "participants" in data["Chess Club"]
    
    def test_get_activities_returns_correct_data_types(self, client):
        """Test that activities have correct data types"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity_success(self, client):
        """Test successful signup for an existing activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Chess Club"
        
        # Verify the student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "duplicate@mergington.edu"
        activity = "Programming Class"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert data["detail"] == "Student is already signed up"
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Art%20Studio/signup?email=artist@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Art Studio" in data["message"]
    
    def test_multiple_students_can_signup(self, client):
        """Test that multiple different students can sign up for the same activity"""
        activity = "Drama Club"
        email1 = "actor1@mergington.edu"
        email2 = "actor2@mergington.edu"
        
        # First student signs up
        response1 = client.post(f"/activities/{activity}/signup?email={email1}")
        assert response1.status_code == 200
        
        # Second student signs up
        response2 = client.post(f"/activities/{activity}/signup?email={email2}")
        assert response2.status_code == 200
        
        # Verify both are in the participants list
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email1 in activities_data[activity]["participants"]
        assert email2 in activities_data[activity]["participants"]
    
    def test_signup_preserves_existing_participants(self, client):
        """Test that signing up a new student doesn't remove existing participants"""
        activity = "Basketball Team"
        
        # Get initial participants
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity]["participants"].copy()
        
        # Sign up a new student
        new_email = "newplayer@mergington.edu"
        client.post(f"/activities/{activity}/signup?email={new_email}")
        
        # Verify all original participants are still there
        final_response = client.get("/activities")
        final_participants = final_response.json()[activity]["participants"]
        
        for participant in initial_participants:
            assert participant in final_participants
        assert new_email in final_participants


class TestActivityConstraints:
    """Tests for activity business logic and constraints"""
    
    def test_all_activities_have_required_fields(self, client):
        """Test that all activities have the required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"{activity_name} missing {field}"
    
    def test_participants_count_does_not_exceed_max(self, client):
        """Test that no activity has more participants than max_participants"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            participants_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            assert participants_count <= max_participants, \
                f"{activity_name} has {participants_count} participants but max is {max_participants}"
