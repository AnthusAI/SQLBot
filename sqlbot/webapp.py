"""
Flask web application for SQLBot.

Provides a modern web interface with real-time updates via Server-Sent Events (SSE).
Modeled after DeckBot's architecture.
"""

import os
import json
import time
import uuid
import threading
from queue import Queue, Empty
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory

from sqlbot.session_service import SessionService
from sqlbot.state_manager import StateManager
from sqlbot.preferences import PreferencesManager
from sqlbot.interfaces.banner import get_interactive_banner_content

app = Flask(__name__)

# Global service instance (single user for now)
current_service: Optional[SessionService] = None

# Event queues for SSE (one per client connection)
event_queues: List[Queue] = []
event_queues_lock = threading.Lock()


@app.route('/')
def index():
    """Serve main web interface."""
    # Serve the built React app directly from static directory
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, 'index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (React build output)."""
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, filename)


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Serve assets (CSS, JS) from build output."""
    static_dir = os.path.join(os.path.dirname(__file__), 'static', 'assets')
    return send_from_directory(static_dir, filename)


@app.route('/<path:filename>')
def serve_root_files(filename):
    """Serve root-level files (vite.svg, etc) from build output."""
    # Only serve specific files, not all paths (to avoid conflicts with API routes)
    if filename in ['vite.svg', 'index.js']:
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, filename)
    # If not a known static file, return 404
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all saved sessions."""
    sessions_dir = Path.home() / '.sqlbot_sessions'
    sessions_dir.mkdir(exist_ok=True)

    sessions = []
    for session_file in sessions_dir.glob('*.json'):
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                # Return metadata only
                sessions.append({
                    'session_id': session_data['session_id'],
                    'name': session_data['name'],
                    'created': session_data['created'],
                    'modified': session_data['modified'],
                    'query_count': len(session_data.get('queries', []))
                })
        except Exception as e:
            print(f"Error loading session {session_file}: {e}")
            continue

    # Sort by modified date (newest first)
    sessions.sort(key=lambda s: s['modified'], reverse=True)

    return jsonify(sessions)


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new session."""
    global current_service

    # Auto-generate session name from timestamp
    now = datetime.now()
    session_name = now.strftime("Session %Y-%m-%d %H:%M")
    session_id = str(uuid.uuid4())

    # Get profile from request or environment
    data = request.json or {}
    profile = data.get('profile', os.getenv('DBT_PROFILE_NAME'))

    # Create session context
    session_context = {
        'session_id': session_id,
        'session_name': session_name,
        'profile': profile,
        'safeguard_mode': True,  # Enable by default
        'preview_mode': False,
        'created': now.isoformat() + 'Z',
        'modified': now.isoformat() + 'Z'
    }

    # Create session service
    current_service = SessionService(session_context)

    # Subscribe to events to broadcast via SSE
    current_service.subscribe(_broadcast_event)

    # Save initial session to disk
    current_service.save_session()

    # Update state manager
    state_manager = StateManager()
    state_manager.set_current_session(session_id)

    return jsonify({
        'session_id': session_id,
        'name': session_name,
        'created': session_context['created']
    })


@app.route('/api/sessions/<session_id>/load', methods=['POST'])
def load_session(session_id):
    """Load an existing session."""
    global current_service

    sessions_dir = Path.home() / '.sqlbot_sessions'
    session_file = sessions_dir / f"{session_id}.json"

    if not session_file.exists():
        return jsonify({'error': 'Session not found'}), 404

    try:
        with open(session_file, 'r') as f:
            session_data = json.load(f)

        # Create session context
        session_context = {
            'session_id': session_data['session_id'],
            'session_name': session_data['name'],
            'profile': session_data.get('config', {}).get('profile'),
            'safeguard_mode': session_data.get('config', {}).get('safeguard_mode', True),
            'preview_mode': session_data.get('config', {}).get('preview_mode', False),
            'created': session_data['created'],
            'modified': session_data['modified']
        }

        # Create session service
        current_service = SessionService(session_context)

        # Restore queries
        current_service.queries = session_data.get('queries', [])

        # Restore conversation history
        conversation_history = session_data.get('conversation_history', {})
        if conversation_history and 'messages' in conversation_history:
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

            for msg_data in conversation_history['messages']:
                msg_type = msg_data.get('type')
                content = msg_data.get('content', '')

                # Recreate the appropriate message type
                if msg_type == 'HumanMessage':
                    current_service.conversation_manager.history.add_message(HumanMessage(content=content))
                elif msg_type == 'AIMessage':
                    current_service.conversation_manager.history.add_message(AIMessage(content=content))
                elif msg_type == 'SystemMessage':
                    current_service.conversation_manager.history.add_message(SystemMessage(content=content))

        # Subscribe to events
        current_service.subscribe(_broadcast_event)

        # Update state manager
        state_manager = StateManager()
        state_manager.set_current_session(session_id)

        return jsonify({
            'session': session_context,
            'queries': current_service.queries,
            'conversation_history': session_data.get('conversation_history', {})
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session."""
    sessions_dir = Path.home() / '.sqlbot_sessions'
    session_file = sessions_dir / f"{session_id}.json"

    if not session_file.exists():
        return jsonify({'error': 'Session not found'}), 404

    try:
        os.remove(session_file)

        # Clear state if this was the current session
        state_manager = StateManager()
        if state_manager.get_current_session() == session_id:
            state_manager.clear_current_session()

        return jsonify({'message': 'Session deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/query', methods=['POST'])
def execute_query():
    """Execute a query (SQL, natural language, or slash command)."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    data = request.json
    query_text = data.get('query')

    if not query_text:
        return jsonify({'error': 'Query text required'}), 400

    # Execute query in background (results come via SSE)
    current_service.execute_query(query_text)

    return jsonify({'message': 'Query started'})


@app.route('/events')
def events():
    """
    Server-Sent Events endpoint for real-time updates.

    Streams events to the client as they occur.
    """
    import sys

    def event_stream():
        # Create a queue for this client
        queue = Queue()

        # Register queue for broadcasting
        with event_queues_lock:
            event_queues.append(queue)
            print(f"[SSE] Client connected. Total queues: {len(event_queues)}", file=sys.stderr)

        try:
            # Send initial connected event
            yield f"event: connected\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"

            # Stream events from queue
            while True:
                try:
                    # Block for up to 15 seconds, then send keepalive
                    # Shorter timeout means more frequent keepalives = more stable connection
                    event_type, data = queue.get(timeout=15)
                    event_data = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    print(f"[SSE] Sending event: {event_type}", file=sys.stderr)
                    yield event_data
                except Empty:
                    # Send keepalive comment to prevent timeout
                    print(f"[SSE] Sending keepalive", file=sys.stderr)
                    yield ": keepalive\n\n"

        except GeneratorExit:
            # Client disconnected
            pass
        finally:
            # Unregister queue
            with event_queues_lock:
                if queue in event_queues:
                    event_queues.remove(queue)
                print(f"[SSE] Client disconnected. Total queues: {len(event_queues)}", file=sys.stderr)

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )


@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """Get user preferences."""
    prefs = PreferencesManager()
    return jsonify(prefs.get_all())


@app.route('/api/preferences/theme', methods=['GET'])
def get_theme():
    """Get theme preference."""
    prefs = PreferencesManager()
    theme = prefs.get('theme', 'system')
    return jsonify({'value': theme})


@app.route('/api/preferences/theme', methods=['POST'])
def set_theme():
    """Set theme preference."""
    data = request.json
    theme = data.get('value')

    if theme not in ['light', 'dark', 'system']:
        return jsonify({'error': 'Invalid theme'}), 400

    prefs = PreferencesManager()
    prefs.set('theme', theme)

    return jsonify({'message': 'Theme updated'})


@app.route('/api/intro', methods=['GET'])
def get_intro():
    """Get intro banner message for new sessions."""
    profile = os.getenv('DBT_PROFILE')
    llm_model = os.getenv('SQLBOT_LLM_MODEL', 'gpt-5')
    llm_available = True  # Assume LLM is available in webapp mode

    banner_content = get_interactive_banner_content(
        profile=profile,
        llm_model=llm_model,
        llm_available=llm_available
    )

    return jsonify({'content': banner_content})


def _broadcast_event(event_type: str, data: Any):
    """
    Broadcast an event to all connected SSE clients.

    Args:
        event_type: Type of event
        data: Event data
    """
    with event_queues_lock:
        for queue in event_queues:
            try:
                queue.put((event_type, data))
            except Exception as e:
                print(f"Error broadcasting to client: {e}")


def run_webapp(host='127.0.0.1', port=5000):
    """
    Run the Flask web application.

    Args:
        host: Host to bind to (default: localhost only)
        port: Port to listen on (default: 5000)
    """
    print(f"Starting SQLBot web interface on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    app.run(host=host, port=port, threaded=True)


if __name__ == '__main__':
    run_webapp()
