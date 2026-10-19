import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.tools.language_detector import detect_language
from app.agents.reviewer import run_baseline_checks


def test_language_detection():
    assert detect_language(r"src\Main.java") == "java"
    assert detect_language("src/app.js") == "javascript"
    assert detect_language("src/App.tsx") == "typescript"
    assert detect_language("src/service.py") == "python"
    assert detect_language("README") == "unknown"


def test_python_eval_rule():
    section = """diff --git a/app.py b/app.py
+++ b/app.py
@@ -1,0 +2,1 @@
+result = eval(user_input)
"""
    findings = run_baseline_checks(section, "app.py")
    assert any(f["severity"] == "critical" for f in findings)


def test_javascript_eval_rule():
    section = """diff --git a/app.js b/app.js
+++ b/app.js
@@ -1,0 +2,1 @@
+const result = eval(userInput);
"""
    findings = run_baseline_checks(section, "app.js")
    assert any(f["severity"] == "critical" for f in findings)


def test_java_sql_rule():
    section = """diff --git a/Repository.java b/Repository.java
+++ b/Repository.java
@@ -1,0 +2,1 @@
+statement.executeQuery("SELECT * FROM users WHERE id = " + userId);
"""
    findings = run_baseline_checks(section, "Repository.java")
    assert any("SQL injection" in f["message"] for f in findings)


def test_removed_eval_is_ignored():
    section = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +0,0 @@
-eval(user_input)
"""
    assert run_baseline_checks(section, "app.py") == []


from app.agents.reviewer import (
    run_baseline_checks,
    _is_test_or_fixture_path,
    _add_test_fixture_context,
)


def test_test_fixture_paths_are_recognized():
    assert _is_test_or_fixture_path(
        "backend/test_multiple_vulnerabilities.py"
    )
    assert _is_test_or_fixture_path("tests/test_security.py")
    assert not _is_test_or_fixture_path("backend/app/views.py")


def test_fixture_context_does_not_remove_findings():
    findings = [
        {
            "file_path": "backend/test_vulnerable.py",
            "severity": "critical",
            "message": "Dynamic code execution can execute untrusted input.",
        }
    ]

    result = _add_test_fixture_context(findings)

    assert len(result) == 1
    assert result[0]["severity"] == "critical"
    assert "Test/fixture context:" in result[0]["message"]


def test_normal_application_eval_remains_critical():
    section = """diff --git a/app.py b/app.py
+++ b/app.py
@@ -1,0 +2,1 @@
+result = eval(user_input)
"""
    findings = run_baseline_checks(section, "app.py")

    assert any(f["severity"] == "critical" for f in findings)