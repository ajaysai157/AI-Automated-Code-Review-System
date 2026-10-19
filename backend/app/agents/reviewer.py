import re
from app.agents.orchestrator import create_review_plan

from app.tools.diff_parser import (
    extract_file_path,
    find_changed_line,
    split_diff_by_file,
)
from app.tools.language_detector import detect_language
from app.ai.reviewer import review_with_ai
from app.agents.aggregator import aggregate_findings




def _is_test_or_fixture_path(file_path: str) -> bool:
    """Identify files that are likely to contain tests or example fixtures."""
    path = file_path.replace("\\", "/").lower()
    parts = path.split("/")
    filename = parts[-1]

    test_directories = {"test", "tests", "fixture", "fixtures", "examples", "samples"}

    return (
        any(part in test_directories for part in parts[:-1])
        or filename.startswith("test_")
        or filename.endswith(("_test.py", ".test.js", ".test.ts",
                              ".spec.js", ".spec.ts"))
    )


def _add_test_fixture_context(findings: list[dict]) -> list[dict]:
    """Explain likely fixture context without suppressing security findings."""
    for finding in findings:
        file_path = finding.get("file_path", "")

        if (
            _is_test_or_fixture_path(file_path)
            and "Test/fixture context:" not in finding.get("message", "")
        ):
            finding["message"] = (
                "Test/fixture context: This file appears to contain test or "
                "example code. The unsafe pattern is real, but confirm whether "
                "the file is used in production before treating it as a "
                "production vulnerability. "
                + finding.get("message", "")
            )

    return findings




# Each rule is deliberately language-specific. These are high-signal starter
# checks, not a replacement for a full static-analysis engine.
def _is_sensitive_logging(line: str, language: str) -> bool:
    lower = line.lower()
    sensitive = re.search(
        r"\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)\b",
        lower,
    )
    if not sensitive:
        return False

    logging_patterns = {
        "python": r"\b(print|logging\.\w+|logger\.\w+)\s*\(",
        "java": r"\b(System\.out\.(print|println)|\w*log\.(debug|info|warn|error|trace))\s*\(",
        "javascript": r"\b(console\.(log|info|warn|error|debug)|logger\.(debug|info|warn|error))\s*\(",
        "typescript": r"\b(console\.(log|info|warn|error|debug)|logger\.(debug|info|warn|error))\s*\(",
    }
    pattern = logging_patterns.get(language)
    return bool(pattern and re.search(pattern, line, re.IGNORECASE))


def _rules_for_line(line: str, language: str) -> list[tuple[str, str, float, str]]:
    """Return (keyword, severity, confidence, message) for a changed line."""
    matches = []

    if language == "python":
        if re.search(r"\b(eval|exec)\s*\(", line):
            matches.append((
                "eval(" if re.search(r"\beval\s*\(", line) else "exec(",
                "critical", 0.98,
                "Dynamic code execution can execute untrusted input.",
            ))
        if re.search(r"\b(?:execute|executemany)\s*\(", line, re.IGNORECASE) and (
            "+" in line or re.search(r"\.format\s*\(|\bf[\"']", line)
        ):
            matches.append((
                "execute(", "high", 0.90,
                "Possible SQL injection through dynamically constructed SQL.",
            ))

    elif language in {"javascript", "typescript"}:
        if re.search(r"\beval\s*\(|\bnew\s+Function\s*\(|\bFunction\s*\(", line):
            keyword = "eval(" if "eval" in line else "Function"
            matches.append((
                keyword, "critical", 0.97,
                "Dynamic code execution can execute untrusted input.",
            ))
        if re.search(r"\b(query|execute|raw)\s*\(", line, re.IGNORECASE) and (
            "+" in line or "${" in line
        ):
            query_match = re.search(
                r"\b(query|execute|raw)\s*\(",
                line,
                re.IGNORECASE,
            )
            matches.append((
                query_match.group(1), "high", 0.88,
                "Possible SQL injection through dynamically constructed query text.",
            ))

    elif language == "java":
        if re.search(r"\bRuntime\.getRuntime\s*\(\s*\)\.exec\s*\(|\bnew\s+ProcessBuilder\s*\(", line):
            keyword = "ProcessBuilder" if "ProcessBuilder" in line else "exec("
            matches.append((
                keyword, "high", 0.90,
                "Process execution should be checked for untrusted command arguments.",
            ))
        if re.search(r"\b(executeQuery|executeUpdate|execute)\s*\(", line) and "+" in line:
            keyword_match = re.search(r"\b(executeQuery|executeUpdate|execute)\s*\(", line)
            matches.append((
                keyword_match.group(1), "high", 0.90,
                "Possible SQL injection through string-concatenated SQL.",
            ))

    if _is_sensitive_logging(line, language):
        matches.append((
            "password", "high", 0.94,
            "Possible exposure of a password, secret, or token through logging.",
        ))

    return matches


def run_baseline_checks(section: str, file_path: str) -> list[dict]:
    """Run starter rules against added lines only, avoiding removed-code alerts."""
    language = detect_language(file_path)
    findings = []

    for diff_line in section.splitlines():
        if not diff_line.startswith("+") or diff_line.startswith("+++"):
            continue

        source_line = diff_line[1:]
        for keyword, severity, confidence, message in _rules_for_line(source_line, language):
            changed_line = find_changed_line(section, keyword)
            finding = {
                "agent": "baseline",
                "file_path": file_path,
                "line": changed_line,
                "severity": severity,
                "confidence": confidence,
                "message": message,
            }
            if finding not in findings:
                findings.append(finding)

    return findings


def review_diff(diff: str) -> tuple[list[dict], str]:
    """Plan and run reviews for a pull request diff."""

    plan = create_review_plan(diff)

    # Avoid unnecessary work when there are no changed files.
    if not plan["changed_files"]:
        return [], "skipped_no_changes"

    # No specialist is needed for documentation-only changes.
    if not plan["agents"]:
        return [], "skipped_no_reviewers"

    findings = []
    sections = split_diff_by_file(diff)

    # Run baseline security rules only when security review is selected.
    if "security" in plan["agents"]:
        for section in sections:
            file_path = extract_file_path(section)
            if file_path:
                findings.extend(
                    run_baseline_checks(section, file_path)
                )

    # Run the existing AI reviewer for planned reviews.
    ai_findings, ai_review_status = review_with_ai(diff)
    findings.extend(ai_findings)

    findings = aggregate_findings(findings)
    findings = _add_test_fixture_context(findings)
    return findings, "completed"