"""
Shared message formatting logic for SQLBot interfaces

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
    
    # Status messages
    SUCCESS = "✔"           # U+2714 Check mark - for success messages (safeguard passes)
    ERROR = "✖"             # U+2716 Heavy multiplication X - for error messages
    SYSTEM = "◦"            # White bullet for system messages
    
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
            import ast
            import re
            
            # First try to parse as valid JSON (double quotes)
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # If that fails, try to parse as Python dict (single quotes)
                try:
                    # Use ast.literal_eval which handles Python dict syntax better
                    data = ast.literal_eval(text)
                except (ValueError, SyntaxError):
                    # Try regex extraction for complex cases with nested quotes
                    try:
                        # More robust regex patterns for text extraction
                        # Look for 'text': 'content' but handle escaped quotes and newlines
                        text_patterns = [
                            r"'text'\s*:\s*'([^']*(?:\\'[^']*)*)'",  # Handle escaped quotes
                            r'"text"\s*:\s*"([^"]*(?:\\"[^"]*)*)"',  # Handle double quotes
                            r"'text'\s*:\s*'(.*?)'(?=\s*[,}])",     # Non-greedy match
                            r'"text"\s*:\s*"(.*?)"(?=\s*[,}])',     # Non-greedy match double quotes
                        ]
                        
                        for pattern in text_patterns:
                            text_match = re.search(pattern, text, re.DOTALL)
                            if text_match:
                                # Unescape any escaped quotes
                                extracted = text_match.group(1)
                                extracted = extracted.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n')
                                return extracted
                        
                        # Look for other content patterns
                        content_patterns = [
                            r"'(?:content|message)'\s*:\s*'([^']*(?:\\'[^']*)*)'",
                            r'"(?:content|message)"\s*:\s*"([^"]*(?:\\"[^"]*)*)"',
                        ]
                        
                        for pattern in content_patterns:
                            content_match = re.search(pattern, text, re.DOTALL)
                            if content_match:
                                extracted = content_match.group(1)
                                extracted = extracted.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n')
                                return extracted
                        
                        # If no patterns match, return original
                        return text
                    except Exception:
                        return text
            
            if isinstance(data, dict):
                # Look for text content in various formats
                if 'text' in data:
                    return data['text']
                elif 'content' in data:
                    return data['content']
                elif 'message' in data:
                    return data['message']
        except (json.JSONDecodeError, ValueError, SyntaxError, Exception):
            # If JSON parsing fails, return original text
            pass
    
    # Handle concatenated JSON objects - simple approach using regex
    if '}{' in text:
        try:
            import re
            # Use regex to find all JSON objects that contain 'text' field
            # Look for patterns like {'type': 'text', 'text': '...'} or {'text': '...'}
            text_patterns = [
                r"\{'type'\s*:\s*'text'[^}]*'text'\s*:\s*'([^']*(?:\\'[^']*)*)'\s*[^}]*\}",
                r"\{'text'\s*:\s*'([^']*(?:\\'[^']*)*)'\s*[^}]*\}",
                r'\{"type"\s*:\s*"text"[^}]*"text"\s*:\s*"([^"]*(?:\\"[^"]*)*)"\s*[^}]*\}',
                r'\{"text"\s*:\s*"([^"]*(?:\\"[^"]*)*)"\s*[^}]*\}',
            ]
            
            for pattern in text_patterns:
                matches = re.findall(pattern, text, re.DOTALL)
                if matches:
                    # Unescape quotes and join all text matches
                    extracted_texts = []
                    for match in matches:
                        cleaned = match.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n')
                        extracted_texts.append(cleaned)
                    if extracted_texts:
                        return ' '.join(extracted_texts)
        except Exception:
            pass
    
    # If not JSON or parsing failed, return original text with newline cleanup
    return text.replace('\\n', '\n') if isinstance(text, str) else text


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
    
    # Check if this is already formatted (starts with a message symbol)
    response_str = raw_response.strip()
    if (response_str.startswith(MessageSymbols.AI_RESPONSE) or 
        response_str.startswith(MessageSymbols.TOOL_CALL) or 
        response_str.startswith(MessageSymbols.TOOL_RESULT)):
        return response_str
    
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
                return f"{MessageSymbols.AI_RESPONSE} Response received but could not be formatted properly."
        
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
                        return f"{MessageSymbols.AI_RESPONSE} Response received but could not be formatted properly."
            
            else:
                # Handle single JSON object - use the improved extraction function
                extracted_text = _extract_text_from_json(response_str)
                if extracted_text != response_str:
                    # Successfully extracted text content
                    return f"{MessageSymbols.AI_RESPONSE} {extracted_text}"
                
                # If extraction didn't find content but JSON is valid, treat as plain text
                try:
                    # Check if it's valid JSON but just doesn't have extractable content
                    import ast
                    try:
                        json.loads(response_str)
                        # Valid JSON but no extractable content - treat as plain text
                        return f"{MessageSymbols.AI_RESPONSE} {response_str}"
                    except json.JSONDecodeError:
                        try:
                            ast.literal_eval(response_str)
                            # Valid Python dict but no extractable content - treat as plain text
                            return f"{MessageSymbols.AI_RESPONSE} {response_str}"
                        except (ValueError, SyntaxError):
                            pass
                except Exception:
                    pass
                
                # If extraction failed, try the old parsing approach for tool calls
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
                        # If all parsing fails, return as plain text
                        return f"{MessageSymbols.AI_RESPONSE} {response_str}"
                
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
                    
                    # Fallback for unrecognized JSON structure
                    return f"{MessageSymbols.AI_RESPONSE} Response received but could not be formatted properly."
                        
        except json.JSONDecodeError:
            # Not valid JSON, treat as plain text
            pass
    
    # Plain text response
    return f"{MessageSymbols.AI_RESPONSE} {response_str}"


