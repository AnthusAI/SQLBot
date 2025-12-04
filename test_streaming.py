#!/usr/bin/env python3
"""
Test script to reproduce and fix the streaming issue
"""
import requests
import json
import time
from sseclient import SSEClient

BASE_URL = "http://127.0.0.1:5000"

def test_streaming():
    """Test the complete streaming flow"""
    print("=" * 80)
    print("STREAMING TEST")
    print("=" * 80)

    # Step 1: Create a session
    print("\n1. Creating session...")
    response = requests.post(f"{BASE_URL}/api/sessions", json={})
    if response.status_code != 200:
        print(f"❌ Failed to create session: {response.status_code}")
        print(response.text)
        return False

    session_data = response.json()
    print(f"✓ Session created: {session_data['session_id']}")

    # Step 2: Start listening to SSE events
    print("\n2. Connecting to SSE stream...")
    sse_url = f"{BASE_URL}/events"

    # Step 3: Send a query
    print("\n3. Sending query: 'hello'")
    query_response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "hello"},
        timeout=5
    )

    if query_response.status_code != 200:
        print(f"❌ Failed to send query: {query_response.status_code}")
        print(query_response.text)
        return False

    print(f"✓ Query accepted: {query_response.json()}")

    # Step 4: Listen for SSE events
    print("\n4. Listening for SSE events (10 second timeout)...")
    print("-" * 80)

    try:
        client = SSEClient(sse_url)
        event_count = 0

        for msg in client.events():
            if msg.event == 'keepalive':
                continue

            event_count += 1
            print(f"\n[Event {event_count}] Type: {msg.event}")

            if msg.data:
                try:
                    data = json.loads(msg.data)
                    if msg.event == 'message':
                        content = data.get('content', '')
                        # Truncate long messages
                        if len(content) > 200:
                            print(f"Content: {content[:200]}...")
                        else:
                            print(f"Content: {content}")
                    else:
                        print(f"Data: {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    print(f"Data: {msg.data}")

            # Stop after query_complete
            if msg.event == 'query_complete':
                print("\n✓ Received query_complete event")
                break

            # Timeout after 10 events
            if event_count >= 10:
                print("\n⚠ Stopping after 10 events")
                break

    except Exception as e:
        print(f"\n❌ SSE Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("-" * 80)
    print(f"\n✓ Test complete! Received {event_count} events")
    return True


if __name__ == "__main__":
    # Install sseclient if needed
    try:
        import sseclient
    except ImportError:
        print("Installing sseclient-py...")
        import subprocess
        subprocess.check_call(["pip", "install", "sseclient-py"])
        from sseclient import SSEClient

    success = test_streaming()
    exit(0 if success else 1)
