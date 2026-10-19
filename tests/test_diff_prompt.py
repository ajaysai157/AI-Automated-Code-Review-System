import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.ai.prompt import build_review_prompt
from app.tools.diff_parser import (
    extract_file_path,
    extract_file_paths,
    find_changed_line,
    split_diff_by_file,
)


def test_prompt_is_multi_language_and_not_security_only():
    prompt = build_review_prompt("diff --git a/Main.java b/Main.java")
    assert "Do not assume all files are Python" in prompt
    assert "Correctness and logic errors" in prompt
    assert "Security vulnerabilities" in prompt


def test_multi_file_diff_is_split_and_paths_extracted():
    diff = """diff --git a/src/Main.java b/src/Main.java
--- a/src/Main.java
+++ b/src/Main.java
@@ -1 +1 @@
-old
+new
diff --git a/src/app.js b/src/app.js
--- a/src/app.js
+++ b/src/app.js
@@ -1 +1 @@
-old
+new
"""
    sections = split_diff_by_file(diff)
    assert len(sections) == 2
    assert extract_file_paths(diff) == ["src/Main.java", "src/app.js"]
    assert extract_file_path(sections[0]) == "src/Main.java"
    assert extract_file_path(sections[1]) == "src/app.js"


def test_changed_line_tracks_context_and_removed_lines():
    diff = """diff --git a/app.js b/app.js
--- a/app.js
+++ b/app.js
@@ -10,3 +10,3 @@
 const first = 1;
-oldLine();
+const result = eval(input);
 const last = 2;
"""
    assert find_changed_line(diff, "eval(") == 11
    assert find_changed_line(diff, "oldLine") is None


def test_empty_diff():
    assert split_diff_by_file("") == []
    assert extract_file_path("") is None
    assert find_changed_line("", "x") is None
