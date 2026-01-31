import json
import re

def parse_vision_response(raw: str) -> dict:
    """Parses the raw response from the vision model to extract JSON data.

    Args:
        raw (str): The raw string response from the model.

    Returns:
        dict: The parsed JSON data or an error message.
    """
    # Extract JSON from the response
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        json_str = json_match.group()
        
        # Try parsing as-is first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # If that fails, try fixing unquoted time values like 2:27 or 55:00
        try:
            fixed_str = re.sub(r':\s*(\d+:\d+)(?=[,}\s])', r': "\1"', json_str)
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": raw}
    else:
        return {"error": "No JSON found in response", "raw": raw}