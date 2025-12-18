from fastapi.testclient import TestClient
from python.web.app import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_get_active_rules():
    response = client.get("/api/rules/active")
    # Even if it falls back to default, it should return 200
    assert response.status_code == 200
    assert "risk_management" in response.json()

def test_simulate_rules_no_draft():
    # Might fail if file exists, but generally checks endpoint reachability
    response = client.post("/simulate")
    # 200 if logic runs, or 4xx if validation fails, or custom error
    # Based on code: returns {"error": ...} or result dict
    assert response.status_code == 200

def test_actions_execute():
    response = client.post("/api/actions/execute?action_type=test")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
