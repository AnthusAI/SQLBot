"""
Shared message formatting logic for QBot interfaces

This module provides consistent message formatting across both text mode and Textual interface.
"""

import json
from typing import Optional


class MessageSymbols:
    """Unicode symbols for message progression across interfaces"""
    # User input progression
    INPUT_PROMPT = "◁"      # U+25C1 White left-pointing triangle - for input prompt
    USER_MESSAGE = "◀"      # U+25C0 Black left-pointing triangle - for submitted user message
    
    # AI response progression  
    AI_THINKING = "▷"       # U+25B7 White right-pointing triangle - for thinking indicator
    AI_RESPONSE = "▶"       # U+25B6 Black right-pointing triangle - for AI responses
    
    # Tool calls and results
    TOOL_CALL = "▽"         # U+25BD White down-pointing triangle - for tool calls
    TOOL_RESULT = "▼"       # U+25BC Black down-pointing triangle - for tool results
    SYSTEM = "◦"            # White bullet for system messages
    ERROR = "▪"             # Black square for errors
    
    # Legacy aliases for backward compatibility
    USER = USER_MESSAGE     # Alias for existing code
    THINKING = AI_THINKING  # Alias for existing code


def _extract_text_from_json(text: str) -> str:
    """
    Extract clean text from JSON response format.
    
    Args:
        text: Text that might be JSON format
        
    Returns:
        Clean text content
    """
    if not text or not text.strip():
        return text
    
    text = text.strip()
    
    # Check if this looks like JSON
    if text.startswith('{') and text.endswith('}'):
        try:
            import json
            # Handle single quotes in JSON
            json_text = text.replace("'", '"')
            data = json.loads(json_text)
            
            if isinstance(data, dict):
                # Look for text content in various formats
                if 'text' in data:
                    return data['text']
                elif 'content' in data:
                    return data['content']
                elif 'message' in data:
                    return data['message']
        except (json.JSONDecodeError, Exception):
            # If JSON parsing fails, return original text
            pass
    
    # Handle concatenated JSON objects
    if '}{' in text:
        try:
            import json
            # Split concatenated JSON objects and extract text from each
            json_parts = []
            current_part = ""
            brace_count = 0
            
            for char in text:
                current_part += char
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_parts.append(current_part)
                        current_part = ""
            
            # Extract text from each JSON part
            text_parts = []
            for json_part in json_parts:
                json_part_fixed = json_part.replace("'", '"')
                try:
                    data = json.loads(json_part_fixed)
                    if isinstance(data, dict) and 'text' in data:
                        text_parts.append(data['text'])
                except (json.JSONDecodeError, Exception):
                    continue
            
            if text_parts:
                return ' '.join(text_parts)
        except Exception:
            pass
    
    # If not JSON or parsing failed, return original text
    return text


def _format_response_with_tool_calls(raw_response: str) -> str:
    """
    Format LLM response that contains tool calls in the correct conversation flow.
    
    Args:
        raw_response: Response containing "--- Query Details ---" section
        
    Returns:
        Formatted response with tool calls and results displayed in chronological order
    """
    # Split the response into main response and tool details
    parts = raw_response.split("--- Query Details ---")
    main_response = parts[0].strip()
    tool_details = parts[1].strip() if len(parts) > 1 else ""
    
    formatted_lines = []
    
    # Parse and format tool calls FIRST (chronological order)
    if tool_details:
        # Split tool details into individual queries
        queries = []
        current_query = ""
        current_result = ""
        in_result = False
        
        for line in tool_details.split('\n'):
            line = line.strip()
            if line.startswith('Query:'):
                # Save previous query if exists
                if current_query:
                    queries.append((current_query, current_result.strip()))
                # Start new query
                current_query = line[6:].strip()  # Remove "Query:" prefix
                current_result = ""
                in_result = False
            elif line.startswith('Result:'):
                in_result = True
                current_result = line[7:].strip()  # Remove "Result:" prefix
            elif in_result and line:
                current_result += f" {line}"
        
        # Don't forget the last query
        if current_query:
            queries.append((current_query, current_result.strip()))
        
        # Format each tool call and result in sequence
        for query, result in queries:
            if query:
                # Show tool call
                formatted_lines.append(f"{MessageSymbols.TOOL_CALL} {query}")
                
                # Show tool result (truncated for readability)
                if result and len(result.strip()) > 0:
                    # Truncate long results but show meaningful preview
                    if len(result) > 150:
                        result_preview = result[:150] + "..."
                    else:
                        result_preview = result
                    formatted_lines.append(f"{MessageSymbols.TOOL_RESULT} {result_preview}")
    
    # Then show the main AI response (final analysis/summary)
    if main_response:
        # Parse JSON if the main response is in JSON format
        parsed_main_response = _extract_text_from_json(main_response)
        formatted_lines.append(f"{MessageSymbols.AI_RESPONSE} {parsed_main_response}")
    
    return "\n".join(formatted_lines)


def format_llm_response(raw_response: str) -> str:
    """
    Format LLM response by parsing JSON and extracting meaningful content.
    Also handles tool calls and formats them with appropriate symbols.
    
    Args:
        raw_response: Raw response from LLM (may be JSON or plain text)
        
    Returns:
        Formatted response string with appropriate symbols
    """
    if not raw_response or not raw_response.strip():
        return f"{MessageSymbols.AI_RESPONSE} No response"
    
    # Debug: Check what the raw response looks like
    # print(f"DEBUG: Raw response length: {len(raw_response)}")
    # print(f"DEBUG: Contains Query Details: {'--- Query Details ---' in raw_response}")
    # if len(raw_response) < 1000:
    #     print(f"DEBUG: Raw response: {repr(raw_response)}")
    # else:
    #     print(f"DEBUG: Raw response preview: {repr(raw_response[:500])}...")
    
    # Check if response contains tool call details
    if "--- Query Details ---" in raw_response:
        # Since we now have real-time tool display, just show the main AI response
        parts = raw_response.split("--- Query Details ---")
        main_response = parts[0].strip()
        if main_response:
            # Parse JSON if the main response is in JSON format
            parsed_main_response = _extract_text_from_json(main_response)
            return f"{MessageSymbols.AI_RESPONSE} {parsed_main_response}"
        else:
            return f"{MessageSymbols.AI_RESPONSE} No response"
    
    # Continue with existing logic for responses without tool calls
    
    
    # Check if this looks like JSON
    response_str = raw_response.strip()
    if response_str.startswith('{') or response_str.startswith('['):
        # Handle concatenated JSON objects (common with GPT-5 responses)
        if response_str.count('}{') > 0:
            # Split concatenated JSON objects
            json_parts = []
            current_part = ""
            brace_count = 0
            
            for char in response_str:
                current_part += char
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Complete JSON object
                        json_parts.append(current_part)
                        current_part = ""
            
            # Process each JSON part
            text_parts = []
            tool_calls = []
            
            for json_part in json_parts:
                try:
                    # Convert single quotes to double quotes for valid JSON
                    json_part_fixed = json_part.replace("'", '"')
                    data = json.loads(json_part_fixed)
                    if isinstance(data, dict):
                        # Check for text content
                        if 'text' in data:
                            text_parts.append(data['text'])
                        elif 'type' in data and data['type'] == 'text' and 'text' in data:
                            text_parts.append(data['text'])
                        # Check for tool calls
                        elif 'id' in data and 'name' in data:
                            tool_name = data.get('name', 'Database Query')
                            tool_args = data.get('args', {})
                            
                            tool_display = f"Calling {tool_name}"
                            if tool_args and isinstance(tool_args, dict):
                                args_preview = ', '.join([f"{k}={str(v)[:30]}..." if len(str(v)) > 30 else f"{k}={v}" for k, v in tool_args.items()])
                                tool_display += f" with {args_preview}"
                            
                            tool_calls.append(f"{MessageSymbols.TOOL_CALL} {tool_display}")
                except json.JSONDecodeError:
                    continue
            
            # Return the formatted result
            if text_parts:
                combined_text = ' '.join(text_parts)
                return f"{MessageSymbols.AI_RESPONSE} {combined_text}"
            elif tool_calls:
                return '\n'.join(tool_calls)
            else:
                return f"{MessageSymbols.AI_RESPONSE} [Structured Response]"
        
        try:
            # Try to parse as JSON
            if response_str.startswith('['):
                # Handle array of response objects
                response_data = json.loads(response_str)
                if isinstance(response_data, list) and len(response_data) > 0:
                    # Look for text content in the array
                    text_parts = []
                    tool_calls = []
                    
                    for item in response_data:
                        if isinstance(item, dict):
                            # Check if this is a tool call
                            if 'id' in item and 'name' in item:
                                tool_name = item.get('name', 'Database Query')
                                tool_args = item.get('args', {})
                                
                                # Format tool call
                                tool_display = f"Calling {tool_name}"
                                if tool_args and isinstance(tool_args, dict):
                                    args_preview = ', '.join([f"{k}={str(v)[:30]}..." if len(str(v)) > 30 else f"{k}={v}" for k, v in tool_args.items()])
                                    tool_display += f" with {args_preview}"
                                
                                tool_calls.append(f"{MessageSymbols.TOOL_CALL} {tool_display}")
                            
                            # Check for text content
                            elif 'text' in item:
                                text_parts.append(item['text'])
                            elif 'type' in item and item['type'] == 'text' and 'text' in item:
                                text_parts.append(item['text'])
                    
                    # Combine results
                    result_parts = []
                    if text_parts:
                        combined_text = ' '.join(text_parts)
                        result_parts.append(f"{MessageSymbols.AI_RESPONSE} {combined_text}")
                    
                    result_parts.extend(tool_calls)
                    
                    if result_parts:
                        return '\n'.join(result_parts)
                    else:
                        return f"{MessageSymbols.AI_RESPONSE} [Structured Response]"
            
            else:
                # Handle single JSON object - try with proper quote replacement
                try:
                    # First try direct parsing (in case it's already valid JSON)
                    response_data = json.loads(response_str)
                except json.JSONDecodeError:
                    # Try with quote replacement for Python dict-style strings
                    try:
                        # Use ast.literal_eval for Python dict strings with single quotes
                        import ast
                        response_data = ast.literal_eval(response_str)
                    except (ValueError, SyntaxError):
                        # Last resort: simple quote replacement (may break on quotes in content)
                        response_str_fixed = response_str.replace("'", '"')
                        response_data = json.loads(response_str_fixed)
                
                if isinstance(response_data, dict):
                    # Check if this is a tool call
                    if 'id' in response_data and 'name' in response_data:
                        tool_name = response_data.get('name', 'Database Query')
                        tool_args = response_data.get('args', {})
                        
                        # Format tool call
                        tool_display = f"Calling {tool_name}"
                        if tool_args and isinstance(tool_args, dict):
                            args_preview = ', '.join([f"{k}={str(v)[:30]}..." if len(str(v)) > 30 else f"{k}={v}" for k, v in tool_args.items()])
                            tool_display += f" with {args_preview}"
                        
                        return f"{MessageSymbols.TOOL_CALL} {tool_display}"
                    
                    # Check for text content - handle type='text' case specifically
                    if response_data.get('type') == 'text' and 'text' in response_data:
                        return f"{MessageSymbols.AI_RESPONSE} {response_data['text']}"
                    
                    # Check for text content in various fields
                    for field in ['content', 'text', 'message', 'output', 'response']:
                        if field in response_data and response_data[field]:
                            return f"{MessageSymbols.AI_RESPONSE} {response_data[field]}"
                    
                    # Fallback for unrecognized JSON structure
                    return f"{MessageSymbols.AI_RESPONSE} [Structured Response]"
                        
        except json.JSONDecodeError:
            # Not valid JSON, treat as plain text
            pass
    
    # Plain text response
    return f"{MessageSymbols.AI_RESPONSE} {response_str}"


