"""
Tests for annotation extraction service.

Uses a mock LLM provider — tests the prompt construction and
response parsing, not the LLM quality. LLM quality testing
happens with real fixtures in integration tests.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest

from services.storage.models import Annotation, Trace
from services.annotation import AnnotationExtractionService, EXTRACTION_PROMPT


# ------------------------------------------------------------------
# Mock provider
# ------------------------------------------------------------------


class MockProvider:
    """Returns a predetermined response for any complete() call."""

    def __init__(self, response: str = "[]"):
        self.response = response
        self.last_prompt = None
        self.last_system = None

    async def complete(self, prompt, *, system_prompt=None, model=None, max_tokens=None):
        self.last_prompt = prompt
        self.last_system = system_prompt
        return self.response

    async def vision(self, image_base64, prompt):
        return ""


def make_trace(
    content: str = "test trace",
    source: str = "user",
    conversation_id: str = "conv-001",
) -> Trace:
    return Trace(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        content=content,
        conversation_id=conversation_id,
        source=source,
    )


# ------------------------------------------------------------------
# Response parsing
# ------------------------------------------------------------------


class TestParseResponse:
    def test_valid_json_array(self):
        """Standard LLM response with valid JSON."""
        response = json.dumps([
            {"type": "decision", "key": "rowing", "value": "dropped", "confidence": 0.9},
            {"type": "emotion", "key": "frustration", "value": "ankle pain", "confidence": 0.7},
        ])
        provider = MockProvider(response)
        service = AnnotationExtractionService(provider)

        annotations = service._parse_response(response, "trace-001")
        assert len(annotations) == 2
        assert annotations[0].type == "decision"
        assert annotations[0].key == "rowing"
        assert annotations[0].trace_id == "trace-001"

    def test_empty_array(self):
        """No annotations extracted."""
        service = AnnotationExtractionService(MockProvider())
        annotations = service._parse_response("[]", "trace-001")
        assert annotations == []

    def test_markdown_fenced_json(self):
        """LLM wraps response in ```json fences."""
        inner = json.dumps([{"type": "topic", "key": "AI"}])
        response = f"```json\n{inner}\n```"
        service = AnnotationExtractionService(MockProvider())

        annotations = service._parse_response(response, "trace-001")
        assert len(annotations) == 1
        assert annotations[0].type == "topic"

    def test_invalid_json_returns_empty(self):
        """Garbage response returns empty, doesn't crash."""
        service = AnnotationExtractionService(MockProvider())
        annotations = service._parse_response("not json at all", "trace-001")
        assert annotations == []

    def test_non_array_json_returns_empty(self):
        """JSON object without nested list returns empty."""
        service = AnnotationExtractionService(MockProvider())
        annotations = service._parse_response('{"type": "topic"}', "trace-001")
        assert annotations == []

    def test_dict_wrapped_array_unwrapped(self):
        """Groq json_object mode wraps arrays in a dict — unwrap it."""
        inner = [{"type": "decision", "key": "rowing", "value": "dropped", "confidence": 0.9}]
        response = json.dumps({"annotations": inner})
        service = AnnotationExtractionService(MockProvider())

        annotations = service._parse_response(response, "trace-001")
        assert len(annotations) == 1
        assert annotations[0].type == "decision"
        assert annotations[0].key == "rowing"

    def test_caps_at_five_annotations(self):
        """Never returns more than 5 annotations."""
        items = [{"type": f"topic{i}", "key": f"k{i}"} for i in range(10)]
        response = json.dumps(items)
        service = AnnotationExtractionService(MockProvider())

        annotations = service._parse_response(response, "trace-001")
        assert len(annotations) == 5

    def test_skips_items_without_type(self):
        """Items missing 'type' field are dropped."""
        response = json.dumps([
            {"type": "topic", "key": "valid"},
            {"key": "no_type", "value": "missing"},
            {"type": "decision", "key": "also_valid"},
        ])
        service = AnnotationExtractionService(MockProvider())

        annotations = service._parse_response(response, "trace-001")
        assert len(annotations) == 2

    def test_default_confidence(self):
        """Missing confidence defaults to 0.5."""
        response = json.dumps([{"type": "topic", "key": "no_confidence"}])
        service = AnnotationExtractionService(MockProvider())

        annotations = service._parse_response(response, "trace-001")
        assert annotations[0].confidence == 0.5

    def test_annotation_has_uuid_id(self):
        """Each annotation gets a unique UUID."""
        response = json.dumps([{"type": "topic"}, {"type": "decision"}])
        service = AnnotationExtractionService(MockProvider())

        annotations = service._parse_response(response, "trace-001")
        assert annotations[0].id != annotations[1].id
        # Verify it's a valid UUID
        uuid.UUID(annotations[0].id)


# ------------------------------------------------------------------
# Extraction call
# ------------------------------------------------------------------


class TestExtract:
    @pytest.mark.asyncio
    async def test_extract_calls_provider(self):
        """Extract sends prompt to provider and parses response."""
        response = json.dumps([
            {"type": "decision", "key": "career", "value": "chose AI engineering", "confidence": 0.9}
        ])
        provider = MockProvider(response)
        service = AnnotationExtractionService(provider)

        trace = make_trace(content="I've decided to pursue AI engineering")
        annotations = await service.extract(trace)

        assert len(annotations) == 1
        assert annotations[0].type == "decision"
        assert provider.last_system == EXTRACTION_PROMPT
        assert "AI engineering" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_extract_with_conversation_context(self):
        """Conversation context appears in the prompt."""
        provider = MockProvider("[]")
        service = AnnotationExtractionService(provider)

        context = [
            make_trace(content="What should I focus on?", source="user"),
            make_trace(content="Consider your strengths.", source="assistant"),
        ]
        trace = make_trace(content="I'll focus on AI engineering")
        await service.extract(trace, conversation_context=context)

        assert "What should I focus on?" in provider.last_prompt
        assert "Consider your strengths." in provider.last_prompt
        assert "I'll focus on AI engineering" in provider.last_prompt

    @pytest.mark.asyncio
    async def test_extract_provider_failure_returns_empty(self):
        """LLM failure returns empty list, doesn't crash."""
        provider = MockProvider()

        async def failing_complete(*args, **kwargs):
            raise Exception("LLM down")

        provider.complete = failing_complete
        service = AnnotationExtractionService(provider)

        trace = make_trace(content="Should extract but LLM fails")
        annotations = await service.extract(trace)
        assert annotations == []

    @pytest.mark.asyncio
    async def test_extract_sets_extractor_field(self):
        """Extractor field records the provider class name."""
        response = json.dumps([{"type": "topic", "key": "test"}])
        provider = MockProvider(response)
        service = AnnotationExtractionService(provider)

        trace = make_trace(content="Test trace")
        annotations = await service.extract(trace)

        assert annotations[0].extractor == "MockProvider"


# ------------------------------------------------------------------
# Prompt construction
# ------------------------------------------------------------------


class TestPromptConstruction:
    def test_user_trace_labeled_correctly(self):
        service = AnnotationExtractionService(MockProvider())
        trace = make_trace(content="My content", source="user")
        prompt = service._build_user_prompt(trace, None)
        assert "User" in prompt
        assert "My content" in prompt

    def test_assistant_trace_labeled_correctly(self):
        service = AnnotationExtractionService(MockProvider())
        trace = make_trace(content="AI response", source="assistant")
        prompt = service._build_user_prompt(trace, None)
        assert "Assistant" in prompt

    def test_context_limited_to_last_four(self):
        """Only last 4 context traces included (token budget)."""
        service = AnnotationExtractionService(MockProvider())
        context = [make_trace(content=f"msg {i}") for i in range(6)]
        trace = make_trace(content="Current message")
        prompt = service._build_user_prompt(trace, context)

        # Last 4 should be present, first 2 should not
        assert "msg 2" in prompt
        assert "msg 5" in prompt
        assert "msg 0" not in prompt
        assert "msg 1" not in prompt
