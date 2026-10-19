
import json
from unittest.mock import patch

import pytest

from app.ai.reviewer import review_with_ai


SAMPLE_DIFF = """\
diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -1,2 +1,3 @@
 def calculate(value):
+    result = eval(value)
     return result
"""


def mock_gemini_response(text):
    """Create a mock Gemini response."""
    from unittest.mock import Mock

    response = Mock()
    response.text = text
    return response


def configure_gemini_response(mock_client, text):
    """Configure the mocked Gemini client to return response text."""
    mock_client.return_value.models.generate_content.return_value = (
        mock_gemini_response(text)
    )


@patch("app.ai.reviewer.genai.Client")
def test_gemini_api_rate_limit_returns_unavailable(mock_client):
    mock_client.return_value.models.generate_content.side_effect = Exception(
        "429 rate limit exceeded"
    )

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "unavailable"


@patch("app.ai.reviewer.genai.Client")
def test_gemini_service_unavailable_returns_unavailable(mock_client):
    mock_client.return_value.models.generate_content.side_effect = Exception(
        "503 service unavailable"
    )

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "unavailable"


@patch("app.ai.reviewer.genai.Client")
def test_unexpected_gemini_error_returns_failed(mock_client):
    mock_client.return_value.models.generate_content.side_effect = Exception(
        "Unexpected internal error"
    )

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "failed"


@patch("app.ai.reviewer.genai.Client")
def test_empty_gemini_response_returns_failed(mock_client):
    configure_gemini_response(mock_client, "")

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "failed"


@patch("app.ai.reviewer.genai.Client")
def test_invalid_json_returns_failed(mock_client):
    configure_gemini_response(mock_client, "This is not valid JSON")

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "failed"


@pytest.mark.parametrize(
    "response_text",
    [
        "[]",
        '{"findings": "not a list"}',
    ],
)
@patch("app.ai.reviewer.genai.Client")
def test_invalid_response_structure_returns_failed(
    mock_client,
    response_text,
):
    configure_gemini_response(mock_client, response_text)

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "failed"


@patch("app.ai.reviewer.genai.Client")
def test_valid_finding_returns_completed(mock_client):
    response_text = json.dumps(
        {
            "findings": [
                {
                    "filePath": "app.py",
                    "message": "Using eval() on input can execute arbitrary code.",
                    "pattern": "eval(",
                    "severity": "critical",
                    "confidence": 0.95,
                }
            ]
        }
    )
    configure_gemini_response(mock_client, response_text)

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert status == "completed"
    assert len(findings) == 1

    finding = findings[0]
    assert finding["agent"] == "ai"
    assert finding["file_path"] == "app.py"
    assert finding["severity"] == "critical"
    assert finding["confidence"] == 0.95
    assert finding["message"] == (
        "Using eval() on input can execute arbitrary code."
    )
    assert finding["line"] is not None


@patch("app.ai.reviewer.genai.Client")
def test_finding_for_file_outside_diff_is_rejected(mock_client):
    response_text = json.dumps(
        {
            "findings": [
                {
                    "filePath": "secret.py",
                    "message": "Potential security issue.",
                    "pattern": "eval(",
                    "severity": "high",
                    "confidence": 0.9,
                }
            ]
        }
    )
    configure_gemini_response(mock_client, response_text)

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "completed"


@patch("app.ai.reviewer.genai.Client")
def test_missing_api_key_returns_failed_without_calling_gemini(
    mock_client,
    monkeypatch,
):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    findings, status = review_with_ai(SAMPLE_DIFF)

    assert findings == []
    assert status == "failed"
    mock_client.assert_not_called()
