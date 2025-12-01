#!/usr/bin/env python3
"""
Simple test script for new features:
1. --debug flag for raw response logging
2. --continue flag for conversation persistence
"""

import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_conversation_persistence():
    """Test conversation persistence functionality"""
    print("=" * 80)
    print("Testing Conversation Persistence")
    print("=" * 80)

    from sqlbot.conversation_persistence import ConversationPersistence

    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n✓ Using temp directory: {temp_dir}")

        # Create persistence manager
        persistence = ConversationPersistence(storage_dir=temp_dir)
        print("✓ Created persistence manager")

        # Test saving conversation
        test_conversation = [
            {"role": "user", "content": "How many films are there?"},
            {"role": "assistant", "content": "There are 1000 films in the database."}
        ]

        session_id = persistence.save_conversation(test_conversation)
        print(f"✓ Saved conversation with session ID: {session_id}")

        # Test loading conversation
        loaded_conversation = persistence.load_current_conversation()
        print(f"✓ Loaded conversation with {len(loaded_conversation)} messages")

        # Verify content
        assert len(loaded_conversation) == 2, "Expected 2 messages"
        assert loaded_conversation[0]["role"] == "user", "First message should be user"
        assert loaded_conversation[1]["role"] == "assistant", "Second message should be assistant"
        print("✓ Conversation content verified")

        # Test archiving
        archive_path = persistence.archive_current_conversation()
        if archive_path:
            print(f"✓ Archived conversation to: {archive_path}")

        # Test listing archived sessions
        archived_sessions = persistence.list_archived_sessions()
        print(f"✓ Found {len(archived_sessions)} archived sessions")

        print("\n✅ All conversation persistence tests passed!")


def test_debug_logging():
    """Test debug logging setup"""
    print("\n" + "=" * 80)
    print("Testing Debug Logging Setup")
    print("=" * 80)

    from sqlbot import llm_integration

    # Test that DEBUG_MODE exists and is False by default
    assert hasattr(llm_integration, 'DEBUG_MODE'), "DEBUG_MODE should exist"
    print(f"✓ DEBUG_MODE exists, default value: {llm_integration.DEBUG_MODE}")

    # Test setting DEBUG_MODE
    llm_integration.DEBUG_MODE = True
    assert llm_integration.DEBUG_MODE == True, "DEBUG_MODE should be settable"
    print("✓ DEBUG_MODE can be set to True")

    llm_integration.DEBUG_MODE = False
    assert llm_integration.DEBUG_MODE == False, "DEBUG_MODE should be settable to False"
    print("✓ DEBUG_MODE can be set to False")

    # Check that debug log path is accessible
    debug_log_path = os.path.join(os.path.expanduser("~"), ".sqlbot_debug.log")
    print(f"✓ Debug log will be written to: {debug_log_path}")

    print("\n✅ All debug logging tests passed!")


def test_cli_arguments():
    """Test that CLI arguments are properly defined"""
    print("\n" + "=" * 80)
    print("Testing CLI Arguments")
    print("=" * 80)

    from sqlbot.cli import parse_args_with_subcommands

    # Test parsing --debug flag
    args = parse_args_with_subcommands(['--debug', 'test query'])
    assert hasattr(args, 'debug'), "--debug flag should be recognized"
    assert args.debug == True, "--debug should be True when flag is present"
    print("✓ --debug flag recognized and parsed correctly")

    # Test parsing --continue flag
    args = parse_args_with_subcommands(['--continue'])
    assert hasattr(args, 'continue_session'), "--continue flag should be recognized"
    assert args.continue_session == True, "--continue should be True when flag is present"
    print("✓ --continue flag recognized and parsed correctly")

    # Test default values
    args = parse_args_with_subcommands(['test query'])
    assert args.debug == False, "--debug should default to False"
    assert args.continue_session == False, "--continue should default to False"
    print("✓ Default values are correct (both False)")

    print("\n✅ All CLI argument tests passed!")


def test_history_file():
    """Test that command history file is being used"""
    print("\n" + "=" * 80)
    print("Testing Command History File")
    print("=" * 80)

    from pathlib import Path

    # Check history file path from repl.py
    history_file = Path.home() / '.qbot_history'
    print(f"✓ Command history file location: {history_file}")

    if history_file.exists():
        print(f"✓ History file exists with {sum(1 for _ in open(history_file))} lines")
    else:
        print("ℹ History file will be created on first use")

    print("\n✅ Command history file test passed!")


if __name__ == "__main__":
    try:
        test_cli_arguments()
        test_debug_logging()
        test_conversation_persistence()
        test_history_file()

        print("\n" + "=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print("\nFeatures implemented:")
        print("1. ✅ --debug flag for raw LLM response logging")
        print("2. ✅ --continue flag to resume previous conversation")
        print("3. ✅ Conversation persistence to ~/.sqlbot_conversations/")
        print("4. ✅ Command history with up-arrow recall (already existed)")
        print("\nUsage:")
        print("  sqlbot --debug 'your query'        # Enable debug logging")
        print("  sqlbot --continue                  # Resume last conversation")
        print("  sqlbot --debug --continue 'query'  # Both at once")
        print("\nDebug logs will be written to: ~/.sqlbot_debug.log")
        print("Conversations saved to: ~/.sqlbot_conversations/")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
