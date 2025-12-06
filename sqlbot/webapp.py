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
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_from_directory, send_file

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


@app.route('/<filename>')
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


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get current DBT profile information including connection status, schema, and macros."""
    global current_service

    # Check if session is active
    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.schema import SchemaLoader
        from sqlbot.core.dbt_service import get_dbt_service
        from sqlbot.core.config import SQLBotConfig
        import glob

        # Get DBT service using the profile from the session
        # Note: safeguard_mode (True=safe) is the opposite of dangerous (True=dangerous)
        safeguard_mode = current_service.context.get('safeguard_mode', True)
        config = SQLBotConfig(
            profile=current_service.profile,
            dangerous=not safeguard_mode,  # dangerous is opposite of safeguard
            preview_mode=current_service.context.get('preview_mode', False)
        )
        dbt_service = get_dbt_service(config)

        # Get basic profile configuration
        config_info = dbt_service.get_dbt_config_info()
        profile_name = config_info.get('profile_name', 'Unknown')
        profiles_dir = config_info.get('profiles_dir', '')
        is_using_local_dbt = config_info.get('is_using_local_dbt', False)

        # Get connection status via dbt debug
        debug_result = dbt_service.debug()
        connection_ok = debug_result.get('connection_ok', False)

        connection_status = {
            'status': 'connected' if connection_ok else 'disconnected',
            'error': debug_result.get('error'),
            'last_checked': datetime.now().isoformat() + 'Z'
        }

        # Get schema information
        schema_info = {
            'sources_count': 0,
            'tables_count': 0,
            'location': None,
            'content': None
        }

        try:
            schema_loader = SchemaLoader(profile_name)
            profile_paths = schema_loader.get_profile_paths()

            # Try to find schema files
            for profile_path in profile_paths:
                schema_path = profile_path / 'models' / 'schema.yml'
                if schema_path.exists():
                    schema_info['location'] = str(schema_path)
                    # Load and count sources/tables
                    import yaml
                    with open(schema_path, 'r') as f:
                        schema_content = f.read()
                        schema_info['content'] = schema_content
                        schema_data = yaml.safe_load(schema_content)
                        if schema_data and 'sources' in schema_data:
                            sources = schema_data['sources']
                            schema_info['sources_count'] = len(sources)
                            # Count total tables across all sources
                            for source in sources:
                                if 'tables' in source:
                                    schema_info['tables_count'] += len(source['tables'])
                    break
        except Exception as e:
            print(f"Error loading schema info: {e}")

        # Get macros information
        macros_info = {
            'count': 0,
            'location': None,
            'available': [],
            'files': []
        }

        try:
            # Check for macros in profile-specific directory
            for profile_path in [Path(f'.sqlbot/profiles/{profile_name}/macros'), Path(f'profiles/{profile_name}/macros')]:
                if profile_path.exists():
                    macros_info['location'] = str(profile_path)
                    # List .sql files in macros directory
                    macro_files = list(profile_path.glob('*.sql'))
                    macros_info['count'] = len(macro_files)
                    macros_info['available'] = [f.stem for f in macro_files]

                    # Read contents of each macro file
                    for macro_file in macro_files:
                        try:
                            with open(macro_file, 'r') as f:
                                macros_info['files'].append({
                                    'name': macro_file.stem,
                                    'filename': macro_file.name,
                                    'content': f.read()
                                })
                        except Exception as e:
                            print(f"Error reading macro file {macro_file}: {e}")
                    break
        except Exception as e:
            print(f"Error loading macros info: {e}")

        # Build response
        profile_data = {
            'profile_name': profile_name,
            'connection': connection_status,
            'config': {
                'profiles_dir': profiles_dir,
                'is_using_local_dbt': is_using_local_dbt
            },
            'schema': schema_info,
            'macros': macros_info
        }

        return jsonify(profile_data)

    except Exception as e:
        return jsonify({
            'error': f'Failed to get profile information: {str(e)}'
        }), 500


@app.route('/api/files/schema', methods=['GET'])
def get_schema_file():
    """Get schema file content."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.file_security import FileSecurityValidator

        profile_name = current_service.profile
        validator = FileSecurityValidator(profile_name)

        # Get validated schema path
        schema_path = validator.validate_schema_path()

        # Check if file exists
        if not schema_path.exists():
            return jsonify({
                'location': str(schema_path),
                'content': ''
            })

        # Read file content
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'location': str(schema_path),
            'content': content
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to get schema file: {str(e)}'
        }), 500


@app.route('/api/files/schema', methods=['PUT'])
def update_schema_file():
    """Update schema file with validation."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.file_security import FileSecurityValidator
        from sqlbot.core.file_validation import FileValidator

        # Get content from request
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content in request body'}), 400

        content = data['content']

        # Validate schema file (size, YAML syntax, DBT structure)
        is_valid, error_message = FileValidator.validate_schema_file(content)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_message
            }), 400

        # Get validated path
        profile_name = current_service.profile
        validator = FileSecurityValidator(profile_name)
        schema_path = validator.validate_schema_path()

        # Create parent directories if needed
        validator.create_directory_if_needed(schema_path)

        # Write atomically (temp file → rename)
        temp_path = schema_path.with_suffix('.tmp')
        temp_path.write_text(content, encoding='utf-8')
        temp_path.rename(schema_path)

        return jsonify({
            'success': True,
            'location': str(schema_path)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update schema file: {str(e)}'
        }), 500


@app.route('/api/files/macros', methods=['GET'])
def list_macro_files():
    """List all macro files."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.file_security import FileSecurityValidator

        profile_name = current_service.profile
        validator = FileSecurityValidator(profile_name)

        # List all macro files
        macro_files = validator.list_macro_files()

        # Convert to response format
        files_data = []
        for macro_path in macro_files:
            files_data.append({
                'name': macro_path.stem,  # Filename without extension
                'filename': macro_path.name  # Full filename with .sql
            })

        return jsonify({
            'files': files_data
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to list macro files: {str(e)}'
        }), 500


@app.route('/api/files/macros/<filename>', methods=['GET'])
def get_macro_file(filename):
    """Get specific macro file."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.file_security import FileSecurityValidator

        profile_name = current_service.profile
        validator = FileSecurityValidator(profile_name)

        # Validate and get macro path
        macro_path = validator.validate_macro_path(filename)

        # Check if file exists
        if not macro_path.exists():
            return jsonify({
                'error': f'Macro file not found: {filename}'
            }), 404

        # Read file content
        with open(macro_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({
            'filename': filename,
            'content': content
        })

    except ValueError as e:
        # Security validation error
        return jsonify({
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': f'Failed to get macro file: {str(e)}'
        }), 500


@app.route('/api/files/macros/<filename>', methods=['PUT'])
def update_macro_file(filename):
    """Update existing macro file."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.file_security import FileSecurityValidator
        from sqlbot.core.file_validation import FileValidator

        # Get content from request
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content in request body'}), 400

        content = data['content']

        # Validate macro file (size, SQL syntax - returns warnings)
        is_valid, warning_message = FileValidator.validate_macro_file(content)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': warning_message
            }), 400

        # Get validated path
        profile_name = current_service.profile
        validator = FileSecurityValidator(profile_name)
        macro_path = validator.validate_macro_path(filename)

        # Check if file exists
        if not macro_path.exists():
            return jsonify({
                'success': False,
                'error': f'Macro file not found: {filename}'
            }), 404

        # Write atomically (temp file → rename)
        temp_path = macro_path.with_suffix('.tmp')
        temp_path.write_text(content, encoding='utf-8')
        temp_path.rename(macro_path)

        return jsonify({
            'success': True,
            'location': str(macro_path),
            'warning': warning_message  # Include warnings if any
        })

    except ValueError as e:
        # Security validation error
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update macro file: {str(e)}'
        }), 500


@app.route('/api/files/macros/<filename>', methods=['POST'])
def create_macro_file(filename):
    """Create new macro file."""
    global current_service

    if not current_service:
        return jsonify({'error': 'No active session'}), 400

    try:
        from sqlbot.core.file_security import FileSecurityValidator
        from sqlbot.core.file_validation import FileValidator

        # Get content from request
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Missing content in request body'}), 400

        content = data['content']

        # Validate macro file (size, SQL syntax - returns warnings)
        is_valid, warning_message = FileValidator.validate_macro_file(content)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': warning_message
            }), 400

        # Get validated path
        profile_name = current_service.profile
        validator = FileSecurityValidator(profile_name)
        macro_path = validator.validate_macro_path(filename)

        # Check if file already exists
        if macro_path.exists():
            return jsonify({
                'success': False,
                'error': f'Macro file already exists: {filename}. Use PUT to update it.'
            }), 409

        # Create parent directories if needed
        validator.create_directory_if_needed(macro_path)

        # Write file
        macro_path.write_text(content, encoding='utf-8')

        return jsonify({
            'success': True,
            'location': str(macro_path),
            'warning': warning_message  # Include warnings if any
        }), 201

    except ValueError as e:
        # Security validation error
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create macro file: {str(e)}'
        }), 500


@app.route('/api/sessions/<session_id>/query_results', methods=['GET'])
def get_query_results(session_id):
    """Get query results for a session from QueryResultList."""
    from sqlbot.core.query_result_list import get_query_result_list

    try:
        result_list = get_query_result_list(session_id)
        all_results = result_list.get_all_results()

        # Convert to JSON-serializable format
        results_data = []
        for entry in reversed(all_results):  # Newest first
            results_data.append({
                'index': entry.index,
                'timestamp': entry.timestamp.isoformat(),
                'query_text': entry.query_text,
                'success': entry.result.success,
                'row_count': entry.result.row_count,
                'columns': entry.result.columns,
                'data': entry.result.data if entry.result.success else None,
                'error': entry.result.error,
                'execution_time': entry.result.execution_time
            })

        return jsonify({'results': results_data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>/query_results/<int:query_index>/export/<format>', methods=['GET'])
def export_query_result(session_id, query_index, format):
    """Export query result to file and trigger download."""
    from sqlbot.core.export import DataExporter

    # Validate format
    valid_formats = ['csv', 'excel', 'parquet', 'hdf5']
    if format not in valid_formats:
        return jsonify({'error': f'Invalid format. Must be one of: {valid_formats}'}), 400

    try:
        # Create exports directory in session folder
        exports_dir = Path.home() / '.sqlbot_sessions' / session_id / 'exports'
        exports_dir.mkdir(parents=True, exist_ok=True)

        # Export the query result
        exporter = DataExporter(session_id)
        result = exporter.export_by_index(
            index=query_index,
            format=format,
            location=str(exports_dir)
        )

        if not result['success']:
            return jsonify({'error': result['error']}), 400

        # MIME types and extensions
        mime_types = {
            'csv': 'text/csv',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'parquet': 'application/octet-stream',
            'hdf5': 'application/x-hdf'
        }

        extensions = {
            'csv': 'csv',
            'excel': 'xlsx',
            'parquet': 'parquet',
            'hdf5': 'h5'
        }

        # Send file for download
        return send_file(
            result['file_path'],
            mimetype=mime_types[format],
            as_attachment=True,
            download_name=f"query_{query_index}.{extensions[format]}"
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
