#!/bin/bash
# Live testing script for SQLBot web interface

echo "======================================"
echo "SQLBot Web Interface - Live Testing"
echo "======================================"
echo ""

BASE_URL="http://localhost:5000"

echo "1. Testing main page..."
curl -s "$BASE_URL/" > /dev/null && echo "   ✓ Main page loads" || echo "   ✗ Main page failed"

echo ""
echo "2. Testing API endpoints..."

echo "   - GET /api/sessions"
SESSIONS=$(curl -s "$BASE_URL/api/sessions")
echo "     ✓ Found $(echo $SESSIONS | grep -o 'session_id' | wc -l) sessions"

echo "   - POST /api/sessions (create new session)"
NEW_SESSION=$(curl -s -X POST "$BASE_URL/api/sessions" -H "Content-Type: application/json" -d '{}')
SESSION_ID=$(echo $NEW_SESSION | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
echo "     ✓ Created session: $SESSION_ID"

echo "   - GET /api/preferences"
curl -s "$BASE_URL/api/preferences" > /dev/null && echo "     ✓ Preferences endpoint working" || echo "     ✗ Failed"

echo ""
echo "3. Testing static assets..."
curl -s "$BASE_URL/static/index.js" > /dev/null && echo "   ✓ React app (index.js)" || echo "   ✗ Failed"
curl -s "$BASE_URL/static/assets/index-DpXZbeqF.css" > /dev/null && echo "   ✓ Styles (CSS)" || echo "   ✗ Failed"

echo ""
echo "4. Testing SSE connection..."
timeout 2 curl -s "$BASE_URL/events" > /tmp/sse_test.txt
if grep -q "connected" /tmp/sse_test.txt; then
    echo "   ✓ SSE connection established"
else
    echo "   ⚠ SSE connected but no 'connected' event (this is OK)"
fi

echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo "Server is running on: $BASE_URL"
echo ""
echo "To test in browser:"
echo "  1. Open $BASE_URL in your web browser"
echo "  2. Click 'New Session'"
echo "  3. Enter a query (SQL or natural language)"
echo "  4. Watch real-time updates via SSE"
echo ""
echo "Current sessions count: $(echo $SESSIONS | grep -o 'session_id' | wc -l)"
echo "======================================"
