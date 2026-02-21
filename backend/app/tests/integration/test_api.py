"""
Integration tests for the Negotiation API.

Run with: pytest tests/test_api.py -v
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_session_request():
    """Sample request for creating a session."""
    return {
        "product": {
            "product_id": "TEST-001",
            "product_name": "Test Widget",
            "base_price": 100.00,
            "cost_price": 60.00,
            "min_acceptable_price": 75.00,
            "max_loss_percentage": 0,
        },
        "inventory": {
            "available_quantity": 100,
            "requested_quantity": 10,
            "inventory_pressure": "medium",
            "sales_frequency": "medium",
        },
        "strategy": {
            "mode": "MAX_PROFIT",
            "urgency": "medium",
            "relationship_priority": "medium",
            "max_rounds": 5,
        },
    }


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_returns_ok(self, client):
        """Health endpoint should return 200."""
        response = client.get("/api/v1/negotiate/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestCreateSession:
    """Tests for session creation."""
    
    def test_create_session_success(self, client, sample_session_request):
        """Creating a session should return session ID and initial offer."""
        response = client.post(
            "/api/v1/negotiate/sessions",
            json=sample_session_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "initial_offer" in data
        assert "message" in data
        assert float(data["initial_offer"]) > 0
    
    def test_create_session_validation_error(self, client):
        """Invalid request should return 422."""
        response = client.post(
            "/api/v1/negotiate/sessions",
            json={
                "product": {
                    "product_id": "TEST-001",
                    # Missing required fields
                },
            },
        )
        
        assert response.status_code == 422
        assert "error" in response.json()


class TestNegotiationFlow:
    """Tests for complete negotiation flow."""
    
    def test_complete_negotiation_accept(self, client, sample_session_request):
        """Test a complete negotiation that ends in acceptance."""
        # Create session
        create_response = client.post(
            "/api/v1/negotiate/sessions",
            json=sample_session_request,
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]
        initial_offer = float(create_response.json()["initial_offer"])
        
        # Submit an offer at the initial price (should accept)
        turn_response = client.post(
            f"/api/v1/negotiate/sessions/{session_id}/turns",
            json={
                "offered_price": initial_offer,
                "message": "I accept your price",
            },
        )
        
        assert turn_response.status_code == 200
        data = turn_response.json()
        
        assert data["pricing"]["decision"] == "accept"
        assert data["status"] == "accepted"
        assert data["can_continue"] is False
    
    def test_negotiation_counter_offer(self, client, sample_session_request):
        """Test that low offers receive counter-offers."""
        # Create session
        create_response = client.post(
            "/api/v1/negotiate/sessions",
            json=sample_session_request,
        )
        session_id = create_response.json()["session_id"]
        
        # Submit a low offer
        turn_response = client.post(
            f"/api/v1/negotiate/sessions/{session_id}/turns",
            json={
                "offered_price": 80.00,  # Below initial offer
                "message": "Can you do better?",
            },
        )
        
        assert turn_response.status_code == 200
        data = turn_response.json()
        
        # Should get a counter offer
        assert data["pricing"]["decision"] in ["counter", "accept"]
        if data["pricing"]["decision"] == "counter":
            assert data["pricing"]["counter_offer_price"] is not None
    
    def test_get_session_status(self, client, sample_session_request):
        """Test getting session status."""
        # Create session
        create_response = client.post(
            "/api/v1/negotiate/sessions",
            json=sample_session_request,
        )
        session_id = create_response.json()["session_id"]
        
        # Get session
        get_response = client.get(f"/api/v1/negotiate/sessions/{session_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["session_id"] == session_id
        assert data["status"] == "active"
    
    def test_end_session_early(self, client, sample_session_request):
        """Test ending a session early."""
        # Create session
        create_response = client.post(
            "/api/v1/negotiate/sessions",
            json=sample_session_request,
        )
        session_id = create_response.json()["session_id"]
        
        # End session
        delete_response = client.delete(
            f"/api/v1/negotiate/sessions/{session_id}?reason=buyer_walked"
        )
        
        assert delete_response.status_code == 200
        data = delete_response.json()
        
        assert data["status"] == "buyer_walked"


class TestConstraintEnforcement:
    """Tests for constraint enforcement."""
    
    def test_below_minimum_triggers_violation(self, client, sample_session_request):
        """Offer below minimum should be flagged."""
        # Create session
        create_response = client.post(
            "/api/v1/negotiate/sessions",
            json=sample_session_request,
        )
        session_id = create_response.json()["session_id"]
        
        # Submit offer below minimum (75.00)
        turn_response = client.post(
            f"/api/v1/negotiate/sessions/{session_id}/turns",
            json={
                "offered_price": 50.00,  # Way below minimum
                "message": "Best I can do",
            },
        )
        
        assert turn_response.status_code == 200
        data = turn_response.json()
        
        # Should flag constraint violation
        assert data["pricing"]["within_constraints"] is False
        assert len(data["pricing"]["constraint_violations"]) > 0
