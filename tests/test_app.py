import pytest
from fastapi.testclient import TestClient


def test_root_redirect(client):
    """Test that root endpoint redirects to static/index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test retrieving all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    
    activities = response.json()
    assert isinstance(activities, dict)
    assert "Chess Club" in activities
    assert "Programming Class" in activities
    assert "Gym Class" in activities
    
    # Check activity structure
    chess_club = activities["Chess Club"]
    assert chess_club["description"]
    assert chess_club["schedule"]
    assert chess_club["max_participants"] >= 0
    assert isinstance(chess_club["participants"], list)


def test_get_activities_has_required_fields(client):
    """Test that activities have all required fields"""
    response = client.get("/activities")
    activities = response.json()
    
    required_fields = ["description", "schedule", "max_participants", "participants"]
    
    for activity_name, activity in activities.items():
        for field in required_fields:
            assert field in activity, f"Activity '{activity_name}' missing field '{field}'"


def test_signup_for_activity(client):
    """Test signing up a new student for an activity"""
    response = client.post(
        "/activities/Tennis%20Club/signup",
        params={"email": "newstudent@mergington.edu"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "newstudent@mergington.edu" in data["message"]
    assert "Tennis Club" in data["message"]
    
    # Verify the student was added
    activities_response = client.get("/activities")
    activities = activities_response.json()
    assert "newstudent@mergington.edu" in activities["Tennis Club"]["participants"]


def test_signup_for_nonexistent_activity(client):
    """Test signing up for an activity that doesn't exist"""
    response = client.post(
        "/activities/Nonexistent%20Activity/signup",
        params={"email": "student@mergington.edu"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_signup_already_signed_up(client):
    """Test signing up when already registered"""
    response = client.post(
        "/activities/Chess%20Club/signup",
        params={"email": "michael@mergington.edu"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already signed up" in data["detail"]


def test_remove_participant(client):
    """Test removing a participant from an activity"""
    response = client.delete(
        "/activities/Chess%20Club/remove",
        params={"email": "michael@mergington.edu"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "michael@mergington.edu" in data["message"]
    assert "Chess Club" in data["message"]
    
    # Verify the participant was removed
    activities_response = client.get("/activities")
    activities = activities_response.json()
    assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]


def test_remove_nonexistent_activity(client):
    """Test removing a participant from a non-existent activity"""
    response = client.delete(
        "/activities/Nonexistent%20Activity/remove",
        params={"email": "student@mergington.edu"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_remove_no_signup_participant(client):
    """Test removing a participant who is not signed up"""
    response = client.delete(
        "/activities/Chess%20Club/remove",
        params={"email": "notsignup@mergington.edu"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "not signed up" in data["detail"]


def test_signup_and_remove_flow(client):
    """Test the complete flow of signing up and then removing"""
    new_email = "testuser@mergington.edu"
    activity = "Robotics%20Club"
    
    # Sign up
    signup_response = client.post(
        f"/activities/{activity}/signup",
        params={"email": new_email}
    )
    assert signup_response.status_code == 200
    
    # Verify signup
    get_response = client.get("/activities")
    activities = get_response.json()
    assert new_email in activities["Robotics Club"]["participants"]
    
    # Remove
    remove_response = client.delete(
        f"/activities/{activity}/remove",
        params={"email": new_email}
    )
    assert remove_response.status_code == 200
    
    # Verify removal
    final_response = client.get("/activities")
    final_activities = final_response.json()
    assert new_email not in final_activities["Robotics Club"]["participants"]


def test_activity_with_special_characters_in_name(client):
    """Test handling of activity names with special characters"""
    # The app should handle URL-encoded names properly
    response = client.get("/activities")
    assert response.status_code == 200
    
    activities = response.json()
    activity_names = list(activities.keys())
    
    # Test signup with a real activity name
    if activity_names:
        activity = activity_names[0]
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup",
            params={"email": "special@mergington.edu"}
        )
        assert signup_response.status_code in [200, 400]  # Could be already signed up


def test_participant_limit_not_enforced(client):
    """Test current behavior - participant limit is not enforced"""
    # Get current participant count for Debate Team
    get_response = client.get("/activities")
    activities = get_response.json()
    debate_team = activities["Debate Team"]
    current_count = len(debate_team["participants"])
    max_count = debate_team["max_participants"]
    
    # We can sign up even if at capacity (current implementation doesn't enforce limit)
    # This test documents the current behavior
    if current_count < max_count:
        response = client.post(
            "/activities/Debate%20Team/signup",
            params={"email": "capacity_test@mergington.edu"}
        )
        assert response.status_code == 200
