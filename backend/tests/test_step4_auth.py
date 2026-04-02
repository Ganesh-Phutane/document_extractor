"""
tests/test_step4_auth.py
────────────────────────
Automated test for Step 4: Auth / Login.
Checks Register -> Login -> Me flow.
"""
import requests
import time
import subprocess
import os
import signal

# Configuration
BASE_URL = "http://127.0.0.1:8005"


TEST_USER = {
    "email": f"auth_test_{int(time.time())}@example.com",
    "password": "strongpassword123"
}

def test_auth_flow():
    print("🚀 Starting Auth Flow Test...")

    # 1. Register
    print(f"--- 1. Registering user: {TEST_USER['email']} ---")
    resp = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
    if resp.status_code == 201:
        print("✅ Registration successful")
    else:
        print(f"❌ Registration failed: {resp.status_code} - {resp.text}")
        return

    # 2. Login
    print("--- 2. Logging in ---")
    resp = requests.post(f"{BASE_URL}/auth/login", json=TEST_USER)
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        print("✅ Login successful, token received")
    else:
        print(f"❌ Login failed: {resp.status_code} - {resp.text}")
        return

    # 3. Access Protected Route (/auth/me)
    print("--- 3. Fetching /auth/me ---")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if resp.status_code == 200:
        user_data = resp.json()
        print(f"✅ /auth/me successful: Welcome {user_data['email']}")
    else:
        print(f"❌ /auth/me failed: {resp.status_code} - {resp.text}")
        return

    # 4. Access Protected Route without token
    print("--- 4. Accessing /auth/me without token (should fail) ---")
    resp = requests.get(f"{BASE_URL}/auth/me")
    if resp.status_code == 401:
        print("✅ Unauthenticated access rejected as expected")
    else:
        print(f"❌ Security failure: Unauthenticated access returned {resp.status_code}")
        return

    print("\n🎉 ALL AUTH TESTS PASSED!")

if __name__ == "__main__":
    # Usually we'd start the server here, but we assume it's already running or we start it briefly
    # For this environment, I'll assume I need to start it in the background
    test_auth_flow()
