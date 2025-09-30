"""Tests for staking API endpoints."""
import requests
import os
from dotenv import load_dotenv

# Load environment
load_dotenv("/workspace/repo/backend/.env")

BASE_URL = "http://localhost:8001/api"

def test_auth_and_staking():
    """Test complete auth flow and staking endpoints."""

    # Test signup
    print("Testing signup...")
    signup_data = {
        "email": f"test_user_{os.urandom(4).hex()}@example.com",
        "password": "testpassword123",
        "username": "testuser"
    }

    response = requests.post(f"{BASE_URL}/auth/signup", json=signup_data)
    print(f"Signup response: {response.status_code}")
    assert response.status_code == 200, f"Signup failed: {response.text}"

    data = response.json()
    assert data["success"] == True, f"Signup not successful: {data}"
    assert "token" in data, "Token missing in signup response"

    token = data["token"]
    print(f"✓ Signup successful, token received")

    # Test login
    print("\nTesting login...")
    login_data = {
        "email": signup_data["email"],
        "password": signup_data["password"]
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Login response: {response.status_code}")
    assert response.status_code == 200, f"Login failed: {response.text}"

    data = response.json()
    assert data["success"] == True, f"Login not successful: {data}"
    assert "token" in data, "Token missing in login response"
    print(f"✓ Login successful")

    # Set headers with token
    headers = {"Authorization": f"Bearer {token}"}

    # Test staking overview
    print("\nTesting staking overview...")
    response = requests.get(f"{BASE_URL}/staking/overview", headers=headers)
    print(f"Overview response: {response.status_code}")
    assert response.status_code == 200, f"Overview failed: {response.text}"

    data = response.json()
    assert data["success"] == True, "Overview not successful"
    assert "data" in data, "Data missing in overview response"

    overview = data["data"]
    assert "total_staked_value" in overview, "total_staked_value missing"
    assert "total_rewards_earned" in overview, "total_rewards_earned missing"
    assert "average_apy" in overview, "average_apy missing"
    assert overview["total_staked_value"] > 0, "total_staked_value should be > 0"
    print(f"✓ Overview: Staked=${overview['total_staked_value']:.2f}, Rewards=${overview['total_rewards_earned']:.2f}, APY={overview['average_apy']:.2f}%")

    # Test staking assets
    print("\nTesting staking assets...")
    response = requests.get(f"{BASE_URL}/staking/assets", headers=headers)
    print(f"Assets response: {response.status_code}")
    assert response.status_code == 200, f"Assets failed: {response.text}"

    data = response.json()
    assert data["success"] == True, "Assets not successful"
    assert "data" in data, "Data missing in assets response"
    assert len(data["data"]) > 0, "Should have at least one asset"

    asset = data["data"][0]
    assert "asset_name" in asset, "asset_name missing"
    assert "amount_staked" in asset, "amount_staked missing"
    assert "apy" in asset, "apy missing"
    print(f"✓ Assets: Found {len(data['data'])} staked assets")

    # Test rewards history
    print("\nTesting rewards history...")
    response = requests.get(f"{BASE_URL}/staking/rewards-history?days=7", headers=headers)
    print(f"Rewards response: {response.status_code}")
    assert response.status_code == 200, f"Rewards failed: {response.text}"

    data = response.json()
    assert data["success"] == True, "Rewards not successful"
    assert "data" in data, "Data missing in rewards response"
    assert len(data["data"]) == 7, "Should have 7 days of rewards"
    print(f"✓ Rewards: Found {len(data['data'])} reward entries")

    # Test performance data
    print("\nTesting performance data...")
    response = requests.get(f"{BASE_URL}/staking/performance?days=7", headers=headers)
    print(f"Performance response: {response.status_code}")
    assert response.status_code == 200, f"Performance failed: {response.text}"

    data = response.json()
    assert data["success"] == True, "Performance not successful"
    assert "data" in data, "Data missing in performance response"
    assert len(data["data"]) == 7, "Should have 7 days of performance"
    print(f"✓ Performance: Found {len(data['data'])} performance entries")

    # Test unauthorized access
    print("\nTesting unauthorized access...")
    response = requests.get(f"{BASE_URL}/staking/overview")
    assert response.status_code == 401, "Should return 401 for unauthorized access"
    print(f"✓ Unauthorized access properly rejected")

    print("\n✅ All staking API tests passed!")

if __name__ == "__main__":
    try:
        test_auth_and_staking()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
