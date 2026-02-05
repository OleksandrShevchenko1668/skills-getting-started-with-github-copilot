import pytest
from fastapi import HTTPException


class TestRoot:
    """Tests for the root endpoint."""
    
    def test_root_redirects(self, client):
        """Test that GET / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for the GET /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert "Chess Club" in activities
        assert "Programming Class" in activities
        assert "Gym Class" in activities
        assert len(activities) == 9
    
    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_chess_club_initial_participants(self, client):
        """Test that Chess Club has initial participants."""
        response = client.get("/activities")
        activities = response.json()
        
        chess_club = activities["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_new_participant(self, client):
        """Test signing up a new participant for an activity."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant to the activity list."""
        # Sign up a new participant
        client.post(
            "/activities/Tennis Club/signup",
            params={"email": "tennis_player@mergington.edu"}
        )
        
        # Verify the participant was added
        response = client.get("/activities")
        activities = response.json()
        assert "tennis_player@mergington.edu" in activities["Tennis Club"]["participants"]
    
    def test_signup_duplicate_participant_fails(self, client):
        """Test that signing up the same participant twice fails."""
        email = "michael@mergington.edu"
        
        # First signup should work
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        # Since michael is already in Chess Club, this should fail
        assert response1.status_code == 400
        data = response1.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a non-existent activity fails."""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_same_student_different_activities(self, client):
        """Test that a student can sign up for multiple activities."""
        email = "multi_student@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Tennis Club
        response2 = client.post(
            "/activities/Tennis Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify student is in both activities
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Tennis Club"]["participants"]


class TestUnsignup:
    """Tests for the DELETE /activities/{activity_name}/unsignup endpoint."""
    
    def test_unsignup_removes_participant(self, client):
        """Test that unsignup removes the participant."""
        email = "michael@mergington.edu"
        
        # Verify participant is in Chess Club
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Chess Club"]["participants"]
        initial_count = len(activities["Chess Club"]["participants"])
        
        # Remove participant
        response = client.delete(
            "/activities/Chess Club/unsignup",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        
        # Verify participant is no longer in Chess Club
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == initial_count - 1
    
    def test_unsignup_nonexistent_participant_fails(self, client):
        """Test that removing a non-existent participant fails."""
        response = client.delete(
            "/activities/Chess Club/unsignup",
            params={"email": "nonexistent@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unsignup_nonexistent_activity_fails(self, client):
        """Test that removing from a non-existent activity fails."""
        response = client.delete(
            "/activities/Nonexistent Activity/unsignup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_unsignup_after_signup(self, client):
        """Test signing up and then removing."""
        email = "temp_student@mergington.edu"
        activity = "Robotics Club"
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify signup was successful
        response = client.get("/activities")
        activities = response.json()
        assert email in activities[activity]["participants"]
        
        # Remove
        response = client.delete(
            f"/activities/{activity}/unsignup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify removal was successful
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities[activity]["participants"]


class TestIntegration:
    """Integration tests combining multiple endpoints."""
    
    def test_full_signup_workflow(self, client):
        """Test the complete signup workflow."""
        email = "workflow_student@mergington.edu"
        
        # Get initial state
        response = client.get("/activities")
        initial_activities = response.json()
        initial_art_count = len(initial_activities["Art Club"]["participants"])
        
        # Sign up for Art Club
        response = client.post(
            "/activities/Art Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Art Club"]["participants"]
        assert len(activities["Art Club"]["participants"]) == initial_art_count + 1
        
        # Remove from Art Club
        response = client.delete(
            "/activities/Art Club/unsignup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities["Art Club"]["participants"]
        assert len(activities["Art Club"]["participants"]) == initial_art_count
    
    def test_multiple_students_signup(self, client):
        """Test multiple students signing up for the same activity."""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        activity = "Drama Club"
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up multiple students
        for student in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": student}
            )
            assert response.status_code == 200
        
        # Verify all students are signed up
        response = client.get("/activities")
        activities = response.json()
        for student in students:
            assert student in activities[activity]["participants"]
        assert len(activities[activity]["participants"]) == initial_count + 3
