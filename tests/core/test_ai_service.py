import pytest
from core.ai_service import get_ai_service, ClaudeProvider, OpenAIProvider, GeminiProvider

def test_get_ai_service():
    assert isinstance(get_ai_service("Claude"), ClaudeProvider)
    assert isinstance(get_ai_service("OpenAI"), OpenAIProvider)
    assert isinstance(get_ai_service("Gemini"), GeminiProvider)
    assert get_ai_service("Unknown") is None

def test_claude_parse_json():
    provider = ClaudeProvider()
    res = provider._parse_json('Here is the json: {"test": "C1"} ')
    assert res == {"test": "C1"}

def test_gemini_parse_json():
    provider = GeminiProvider()
    res = provider._parse_json('```json\n{"test": "C1"}\n```')
    assert res == {"test": "C1"}
