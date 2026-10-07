import json
from unittest.mock import MagicMock, patch
import pytest

from verbatim.errors import PipelineError
from verbatim.llm.ollama_client import OllamaClient, parse_structured_json
from verbatim.schemas import Proposal, ProposalList, RefinedTranscript, Segment


def test_parse_valid_qwen_json():
    """Test A: Valid Qwen JSON parses directly into ProposalList."""
    valid_json = json.dumps({
        "corrections": [
            {
                "segment_id": 3,
                "original": "cooper netties",
                "corrected": "Kubernetes",
                "reason": "Misheard Kubernetes",
            }
        ]
    })
    result = parse_structured_json(valid_json, ProposalList)
    assert isinstance(result, ProposalList)
    assert len(result.corrections) == 1
    assert result.corrections[0].segment_id == 3
    assert result.corrections[0].corrected == "Kubernetes"


def test_parse_markdown_fenced_json():
    """Test B: Qwen JSON wrapped in markdown code fences is handled cleanly."""
    fenced_json = """```json
{
  "corrections": [
    {
      "segment_id": 8,
      "original": "post gress Q L",
      "corrected": "PostgreSQL",
      "reason": "Misheard PostgreSQL"
    }
  ]
}
```"""
    result = parse_structured_json(fenced_json, ProposalList)
    assert isinstance(result, ProposalList)
    assert len(result.corrections) == 1
    assert result.corrections[0].corrected == "PostgreSQL"


def test_parse_truncated_json_eof_repair():
    """Test C: Truncated JSON ending at EOF repairs closed items without crashing."""
    # Truncated mid-item after two complete items
    truncated_json = (
        '{"corrections": ['
        '{"segment_id": 1, "original": "cooper netties", "corrected": "Kubernetes", "reason": "misheard"}, '
        '{"segment_id": 2, "original": "post gress", "corrected": "PostgreSQL", "reason": "misheard"}, '
        '{"segment_id": 3, "original": "interst'
    )
    result = parse_structured_json(truncated_json, ProposalList)
    assert isinstance(result, ProposalList)
    assert len(result.corrections) == 2
    assert result.corrections[0].corrected == "Kubernetes"
    assert result.corrections[1].corrected == "PostgreSQL"


def test_empty_corrections_is_valid():
    """Test F: Valid empty ProposalList is a legitimate successful result."""
    empty_json = '{"corrections": []}'
    result = parse_structured_json(empty_json, ProposalList)
    assert isinstance(result, ProposalList)
    assert len(result.corrections) == 0


def test_ollama_client_bounded_retries_on_malformed_json():
    """Test C & E: Bounded retry occurs when output is malformed, failing clearly on exhaustion."""
    mock_client = MagicMock()
    # Return malformed unfixable text every time
    mock_resp = MagicMock()
    mock_resp.message.content = "Not JSON at all! Just raw rambling text with no brackets"
    mock_client.chat.return_value = mock_resp

    ollama_c = OllamaClient()
    ollama_c.client = mock_client

    with pytest.raises(PipelineError) as exc_info:
        ollama_c.structured(
            model="qwen3:8b",
            system="system prompt",
            user="user prompt",
            schema=ProposalList,
            role="refiner",
        )

    # Must raise LLM_BAD_OUTPUT and attempt exactly 3 times (1 initial + 2 retries)
    assert exc_info.value.error.code == "LLM_BAD_OUTPUT"
    assert mock_client.chat.call_count == 3


def test_ollama_client_succeeds_on_retry():
    """Verify that if initial attempt is malformed, a valid retry output succeeds."""
    mock_client = MagicMock()
    resp1 = MagicMock()
    resp1.message.content = "Malformed: {"
    resp2 = MagicMock()
    resp2.message.content = '{"corrections": [{"segment_id": 1, "original": "foo", "corrected": "bar", "reason": "baz"}]}'
    mock_client.chat.side_effect = [resp1, resp2]

    ollama_c = OllamaClient()
    ollama_c.client = mock_client

    result = ollama_c.structured(
        model="qwen3:8b",
        system="system prompt",
        user="user prompt",
        schema=ProposalList,
        role="refiner",
    )
    assert isinstance(result, ProposalList)
    assert len(result.corrections) == 1
    assert mock_client.chat.call_count == 2
