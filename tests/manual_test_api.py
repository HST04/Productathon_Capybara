"""Manual test script for API endpoints.

This script demonstrates how to test the API endpoints manually.
Run the FastAPI server first: uvicorn app.main:app --reload

Then run this script: python tests/manual_test_api.py
"""

import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health check endpoint."""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200


def test_list_leads():
    """Test list leads endpoint."""
    print("\n=== Testing List Leads ===")
    response = requests.get(f"{BASE_URL}/api/leads/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total leads: {data['total']}")
        print(f"Returned: {len(data['leads'])} leads")
    else:
        print(f"Error: {response.text}")


def test_list_leads_with_filters():
    """Test list leads with filters."""
    print("\n=== Testing List Leads with Filters ===")
    params = {
        "priority": "high",
        "limit": 10
    }
    response = requests.get(f"{BASE_URL}/api/leads/", params=params)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"High priority leads: {len(data['leads'])}")


def test_get_lead_dossier(lead_id: str):
    """Test get lead dossier endpoint."""
    print(f"\n=== Testing Get Lead Dossier ({lead_id}) ===")
    response = requests.get(f"{BASE_URL}/api/leads/{lead_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Company: {data['company']['name']}")
        print(f"Score: {data['lead']['score']}")
        print(f"Priority: {data['lead']['priority']}")
        print(f"Products: {len(data['products'])}")
    else:
        print(f"Error: {response.text}")


def test_submit_feedback(lead_id: str):
    """Test submit feedback endpoint."""
    print(f"\n=== Testing Submit Feedback ({lead_id}) ===")
    payload = {
        "feedback_type": "accepted",
        "notes": "Good lead, will follow up",
        "submitted_by": "test_officer"
    }
    response = requests.post(
        f"{BASE_URL}/api/leads/{lead_id}/feedback",
        json=payload
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Feedback submitted: {data['feedback_type']}")
    else:
        print(f"Error: {response.text}")


def test_list_sources():
    """Test list sources endpoint."""
    print("\n=== Testing List Sources ===")
    response = requests.get(f"{BASE_URL}/api/sources/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total sources: {data['total']}")
        print(f"Returned: {len(data['sources'])} sources")


def test_dashboard_stats():
    """Test dashboard statistics endpoint."""
    print("\n=== Testing Dashboard Stats ===")
    response = requests.get(f"{BASE_URL}/api/dashboard/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total leads: {data['total_leads']}")
        print(f"Conversion rate: {data['conversion_rate']}%")
        print(f"Leads by priority: {data['leads_by_priority']}")
        print(f"Top sources: {len(data['top_sources'])}")
    else:
        print(f"Error: {response.text}")


def test_get_company(company_id: str):
    """Test get company endpoint."""
    print(f"\n=== Testing Get Company ({company_id}) ===")
    response = requests.get(f"{BASE_URL}/api/companies/{company_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Company: {data['name']}")
        print(f"Industry: {data.get('industry', 'N/A')}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    print("=" * 60)
    print("HPCL Lead Intelligence Agent - API Manual Tests")
    print("=" * 60)
    print("\nMake sure the API server is running:")
    print("  uvicorn app.main:app --reload")
    print("\nNote: Some tests may fail if database is empty.")
    print("=" * 60)
    
    try:
        # Basic tests
        test_health()
        test_list_leads()
        test_list_sources()
        test_dashboard_stats()
        
        # Tests requiring data (will fail if DB is empty)
        # Uncomment and replace with actual IDs from your database
        # test_get_lead_dossier("your-lead-uuid-here")
        # test_submit_feedback("your-lead-uuid-here")
        # test_get_company("your-company-uuid-here")
        
        print("\n" + "=" * 60)
        print("Tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API server.")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
