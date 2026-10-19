
import os
import django
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from app.agents.reviewer import review_diff


def test_review_pipeline_combines_baseline_and_ai_findings():
    diff = """diff --git a/app.js b/app.js
--- a/app.js
+++ b/app.js
@@ -1 +1 @@
-old
+const result = eval(userInput);
"""

    ai_findings = [
        {
            "agent": "ai",
            "file_path": "app.js",
            "line": 1,
            "severity": "critical",
            "confidence": 0.99,
            "message": "Untrusted input is executed using eval().",
        }
    ]

    with patch(
        "app.agents.reviewer.review_with_ai",
        return_value=(ai_findings, "completed"),
    ):
        findings, status = review_diff(diff)

    assert status == "completed"
    assert findings
    assert all(f["file_path"] == "app.js" for f in findings)
    assert all(f["line"] == 1 for f in findings)
    assert any(f["confidence"] == 0.99 for f in findings)
    assert len(findings) == 1



def test_review_pipeline_handles_empty_diff():
    findings, status = review_diff("")

    assert findings == []
    assert status == "skipped_no_changes"
