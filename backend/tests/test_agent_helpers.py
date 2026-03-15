"""
Zero-mock unit tests for agent helper functions that have no I/O.

Tests _parse_json_response — the JSON fence-stripping logic that sits between
every Gemini API call and the rest of the pipeline.  If this breaks, every
feature breaks silently.
"""

import json
import pytest
from agent import _parse_json_response

VALID_OBJ = {"scene_summary": "A detective finds a letter.", "beat_map": {"tension": 70}}


# ---------------------------------------------------------------------------
# Happy-path variants
# ---------------------------------------------------------------------------

class TestParseJsonResponseHappyPath:
    def test_plain_json_no_fences(self):
        text = json.dumps(VALID_OBJ)
        result = _parse_json_response(text)
        assert result == VALID_OBJ

    def test_json_fence_with_language_tag(self):
        text = f"```json\n{json.dumps(VALID_OBJ)}\n```"
        result = _parse_json_response(text)
        assert result == VALID_OBJ

    def test_json_fence_without_language_tag(self):
        text = f"```\n{json.dumps(VALID_OBJ)}\n```"
        result = _parse_json_response(text)
        assert result == VALID_OBJ

    def test_leading_trailing_whitespace(self):
        text = f"  \n  {json.dumps(VALID_OBJ)}  \n  "
        result = _parse_json_response(text)
        assert result == VALID_OBJ

    def test_fenced_with_leading_trailing_whitespace(self):
        text = f"  ```json\n{json.dumps(VALID_OBJ)}\n```  "
        result = _parse_json_response(text)
        assert result == VALID_OBJ

    def test_nested_json_object(self):
        """Deep nested structure must parse without modification."""
        obj = {
            "panels": [
                {"panel_number": 1, "dialogue": "Hello", "beat_map": {"tension": 80}},
                {"panel_number": 2, "dialogue": "[SILENCE]"},
            ]
        }
        text = json.dumps(obj)
        assert _parse_json_response(text) == obj


# ---------------------------------------------------------------------------
# Real-world Gemini edge cases
# ---------------------------------------------------------------------------

class TestParseJsonResponseGeminiEdgeCases:
    def test_trailing_prose_after_closing_fence(self):
        """
        Gemini sometimes appends explanatory text after the closing ```.
        The old implementation would include this in the parsed text → JSONDecodeError.
        The fixed rfind-based approach handles this correctly.
        """
        obj = {"key": "value"}
        text = f"```json\n{json.dumps(obj)}\n```\nHere is the JSON I generated for you."
        result = _parse_json_response(text)
        assert result == obj

    def test_multiple_closing_fences_uses_last(self):
        """
        If the JSON content itself mentions ``` (e.g. in a code example inside dialogue),
        rfind finds the LAST ``` which is the real closing fence.
        """
        obj = {"dialogue": "refer to ```this```", "number": 1}
        text = f"```json\n{json.dumps(obj)}\n```"
        result = _parse_json_response(text)
        assert result["number"] == 1

    def test_fenced_with_extra_blank_lines(self):
        """Blank lines inside fences must be preserved for JSON parsing."""
        obj = {"a": 1}
        text = f"```json\n\n{json.dumps(obj)}\n\n```"
        result = _parse_json_response(text)
        assert result == obj


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestParseJsonResponseErrors:
    def test_malformed_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response('{"unclosed": "dict"')

    def test_empty_string_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_json_response("")

    def test_whitespace_only_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _parse_json_response("   \n   ")

    def test_fenced_block_with_no_newline_raises(self):
        """A fence with no newline has no content — must raise."""
        with pytest.raises(ValueError, match="no content"):
            _parse_json_response("```")

    def test_non_json_content_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("This is just prose, not JSON at all.")
