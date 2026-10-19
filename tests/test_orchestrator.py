
from app.agents.orchestrator import create_review_plan


def test_python_source_selects_security_reviewer():
    diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-old
+result = eval(user_input)
"""

    plan = create_review_plan(diff)

    assert "python" in plan["languages"]
    assert "security" in plan["agents"]
    assert "app.py" in plan["changed_files"]


def test_documentation_only_change_selects_no_specialists():
    diff = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-old text
+new documentation
"""

    plan = create_review_plan(diff)

    assert plan["agents"] == []


def test_test_file_selects_test_coverage_reviewer():
    diff = """diff --git a/tests/test_app.py b/tests/test_app.py
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -1 +1 @@
-assert True
+assert result == expected
"""

    plan = create_review_plan(diff)

    assert "test_coverage" in plan["agents"]


def test_empty_diff_returns_empty_plan():
    plan = create_review_plan("")

    assert plan["agents"] == []
    assert plan["changed_files"] == []
