from app.services.parser import parse_vision_response

class TestParseVisionResponse:
  def test_parses_clean_json(self):
    """Model returns properly formatted JSON."""
    raw = '{"workout_type": "Indoor Cycle", "duration": "55:00"}'
    result = parse_vision_response(raw)
    assert result == {
      "workout_type": "Indoor Cycle",
      "duration": "55:00"
    }

  def test_handles_unquoted_time_values(self):
    """Model returns time values without quotes."""
    raw = '{"pace": 2:27, "duration": 55:00}'
    result = parse_vision_response(raw)
    assert result == {
        "pace": "2:27",
        "duration": "55:00"
    }

  def test_extracts_json_from_markdown(self):
    """Model wraps JSON in ``` json blocks"""
    raw = '```json\n{"workout_type": "Run", "distance": 5.0}\n```'
    result = parse_vision_response(raw)
    assert result == {
      "workout_type": "Run",
      "distance": 5.0
    }

  def test_handles_no_json_found(self):
    """Model returns prose instead of JSON."""
    raw = "The workout was great today!"
    result = parse_vision_response(raw)
    assert result == {
      "error": "No JSON found in response",
      "raw": raw
    }

  def test_handles_empty_response(self):
    """Model returns an empty response."""
    raw = ""
    result = parse_vision_response(raw)
    assert result == {
      "error": "No JSON found in response",
      "raw": raw
    }