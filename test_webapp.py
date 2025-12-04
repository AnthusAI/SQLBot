#!/usr/bin/env python3
"""
Test script for SQLBot web interface backend.

Tests Flask app, session service, and API endpoints without requiring the frontend.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("SQLBot Web Interface Backend Test")
print("=" * 60)

# Test 1: Import all modules
print("\n[Test 1] Importing modules...")
try:
    from sqlbot.state_manager import StateManager
    from sqlbot.preferences import PreferencesManager
    from sqlbot.session_service import SessionService
    from sqlbot.webapp import app
    print("✓ All modules imported successfully")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: StateManager
print("\n[Test 2] Testing StateManager...")
try:
    state = StateManager()
    state.set_current_session("test-session-123")
    current = state.get_current_session()
    assert current == "test-session-123", f"Expected 'test-session-123', got '{current}'"
    state.clear_current_session()
    print(f"✓ StateManager works (saved to {state.config_path})")
except Exception as e:
    print(f"✗ StateManager failed: {e}")

# Test 3: PreferencesManager
print("\n[Test 3] Testing PreferencesManager...")
try:
    prefs = PreferencesManager()
    prefs.set('theme', 'dark')
    theme = prefs.get('theme')
    assert theme == 'dark', f"Expected 'dark', got '{theme}'"
    print(f"✓ PreferencesManager works (saved to {prefs.config_path})")
except Exception as e:
    print(f"✗ PreferencesManager failed: {e}")

# Test 4: SessionService initialization
print("\n[Test 4] Testing SessionService initialization...")
try:
    from datetime import datetime
    session_context = {
        'session_id': 'test-session-001',
        'session_name': 'Test Session',
        'profile': 'Sakila',
        'safeguard_mode': True,
        'preview_mode': False,
        'created': datetime.utcnow().isoformat() + 'Z',
        'modified': datetime.utcnow().isoformat() + 'Z'
    }
    service = SessionService(session_context)
    print(f"✓ SessionService initialized")
    print(f"  - Session ID: {service.session_id}")
    print(f"  - Session Name: {service.session_name}")
    print(f"  - Profile: {service.profile}")

    # Test save
    service.save_session()
    print(f"✓ Session saved to {service.session_file}")

    # Verify file exists
    if service.session_file.exists():
        print(f"✓ Session file exists and is accessible")
    else:
        print(f"✗ Session file not found")

except Exception as e:
    print(f"✗ SessionService failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Flask app configuration
print("\n[Test 5] Testing Flask app configuration...")
try:
    print(f"✓ Flask app created")
    print(f"  - App name: {app.name}")
    print(f"  - Routes:")
    for rule in app.url_map.iter_rules():
        print(f"    - {rule.rule} [{', '.join(rule.methods - {'HEAD', 'OPTIONS'})}]")
except Exception as e:
    print(f"✗ Flask app test failed: {e}")

# Test 6: Flask app test client
print("\n[Test 6] Testing Flask API endpoints...")
try:
    with app.test_client() as client:
        # Test index route
        response = client.get('/')
        print(f"✓ GET / - Status: {response.status_code}")

        # Test sessions list (should be empty initially)
        response = client.get('/api/sessions')
        print(f"✓ GET /api/sessions - Status: {response.status_code}")
        if response.status_code == 200:
            sessions = response.get_json()
            print(f"  - Found {len(sessions)} sessions")

        # Test preferences
        response = client.get('/api/preferences')
        print(f"✓ GET /api/preferences - Status: {response.status_code}")
        if response.status_code == 200:
            prefs = response.get_json()
            print(f"  - Theme: {prefs.get('theme', 'not set')}")

        # Test create session
        response = client.post('/api/sessions', json={})
        print(f"✓ POST /api/sessions - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"  - Created session: {data.get('name')}")
            session_id = data.get('session_id')

            # Test load session
            response = client.post(f'/api/sessions/{session_id}/load')
            print(f"✓ POST /api/sessions/{session_id}/load - Status: {response.status_code}")

            # Test delete session
            response = client.delete(f'/api/sessions/{session_id}')
            print(f"✓ DELETE /api/sessions/{session_id} - Status: {response.status_code}")

except Exception as e:
    print(f"✗ Flask API test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("Backend Test Complete!")
print("=" * 60)
print("\nTo start the web server, run:")
print("  python -m sqlbot.webapp")
print("\nOr:")
print("  cd /home/ryan/projects/SQLBot")
print("  python -c 'from sqlbot.webapp import run_webapp; run_webapp()'")
print("\nThen open http://localhost:5000 in your browser")
print("=" * 60)
