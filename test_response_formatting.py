#!/usr/bin/env python3
"""
Test script to verify response formatting handles GPT-5 Responses API format
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_gpt5_responses_format():
    """Test formatting of GPT-5 Responses API format (list of dicts)"""
    print("=" * 80)
    print("Testing GPT-5 Responses API Format Handling")
    print("=" * 80)

    from sqlbot.interfaces.message_formatter import format_llm_response

    # Test case 1: Single reasoning + text block (the problematic format)
    test_response_1 = """[{'id': 'rs_0a4655ef646046df0068ffb6ad17e081959668dfff7bd35b02', 'summary': [], 'type': 'reasoning'}, {'type': 'text', 'text': "1) Understood—you're looking for actual scorecards, not vwForm.\\n\\n2) Approach: Queried dbo.scorecards (via {{ source('call_criteria','scorecards') }}) for case-insensitive matches of \\"sanmar\\" in description/short_name/appname.\\n\\n3) Query executed.\\n\\n4) Result: No scorecards matched \\"sanmar\\" (including variants \\"san mar\\" and \\"san-mar\\").\\n\\n5) Next steps:\\n- Want me to search other scorecard-related tables (e.g., wtd_scorecards, outbound_scorecards) for the same term?\\n- Or confirm the exact naming (e.g., \\"San Mar,\\" \\"SanMar,\\" client/group names) so I can broaden the search to related metadata (scorecard_groups, etc.).", 'annotations': [], 'id': 'msg_0a4655ef646046df0068ffb6b40ddc81959db9bc547bd730b5'}]"""

    print("\n1. Testing GPT-5 format with reasoning + text blocks:")
    print("-" * 80)

    formatted = format_llm_response(test_response_1)

    # Check that it doesn't show raw JSON
    assert not formatted.startswith("[{"), "Should not start with raw JSON list"
    assert "'id':" not in formatted, "Should not contain raw dict keys"
    assert "'type': 'reasoning'" not in formatted, "Should not show reasoning blocks"

    # Check that it extracted the text properly
    assert "▶" in formatted or "Understood" in formatted, "Should have AI response symbol or content"
    assert "looking for actual scorecards" in formatted, "Should contain the actual text content"

    print(f"✓ Formatted correctly (length: {len(formatted)} chars)")
    print(f"Preview: {formatted[:200]}...")

    # Test case 2: Multiple text blocks
    test_response_2 = """[{'id': 'rs_123', 'type': 'reasoning'}, {'type': 'text', 'text': 'First response.', 'id': 'msg_1'}, {'type': 'text', 'text': 'Second response.', 'id': 'msg_2'}]"""

    print("\n2. Testing multiple text blocks:")
    print("-" * 80)

    formatted = format_llm_response(test_response_2)

    assert "First response" in formatted, "Should contain first text block"
    assert "Second response" in formatted, "Should contain second text block"
    assert "'type': 'reasoning'" not in formatted, "Should not show reasoning"

    print(f"✓ Formatted correctly")
    print(f"Content: {formatted}")

    # Test case 3: Plain text (should still work)
    test_response_3 = "This is a plain text response without JSON."

    print("\n3. Testing plain text fallback:")
    print("-" * 80)

    formatted = format_llm_response(test_response_3)

    assert "plain text response" in formatted, "Should preserve plain text"
    assert "▶" in formatted, "Should have AI response symbol"

    print(f"✓ Formatted correctly")
    print(f"Content: {formatted}")

    print("\n" + "=" * 80)
    print("✅ All response formatting tests passed!")
    print("=" * 80)
    print("\nVerified:")
    print("- GPT-5 Responses API format (list with reasoning + text blocks) ✓")
    print("- Reasoning blocks are filtered out ✓")
    print("- Text content is extracted properly ✓")
    print("- Multiple text blocks are combined ✓")
    print("- Plain text still works ✓")
    print("- No raw JSON displayed ✓")


if __name__ == "__main__":
    try:
        test_gpt5_responses_format()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
