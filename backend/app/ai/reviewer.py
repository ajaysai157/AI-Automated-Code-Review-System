import json
import os
import time

from dotenv import load_dotenv
from google import genai

from app.ai.prompt import build_review_prompt
from app.tools.diff_parser import extract_file_path, find_changed_line, split_diff_by_file
from app.tools.language_detector import detect_language

load_dotenv()



def get_gemini_client():
    """Create the Gemini client only when an AI review is requested."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    return genai.Client(api_key=api_key)


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./").strip()


def review_with_ai(diff: str,specialist: str = "general",) -> tuple[list[dict], str]:
    sections = split_diff_by_file(diff)
    file_languages = {}
    for section in sections:
        path = extract_file_path(section)
        if path:
            file_languages[_normalize_path(path)] = detect_language(path)

    language_summary = "\n".join(
        f"- {path}: {language}"
        for path, language in sorted(file_languages.items())
    ) or "- No file paths could be identified."

    prompt = build_review_prompt(diff, specialist)
    prompt += f"""

MULTI-LANGUAGE REVIEW REQUIREMENTS
Detected file languages:
{language_summary}

Review each file according to its actual language and idioms. Do not apply
Python-only assumptions to Java, JavaScript, TypeScript, or other languages.
Look for concrete defects in correctness, security, error handling, resource
management, and performance. Report only actionable issues introduced by the
changed lines; avoid speculative findings and style-only comments. Use exact
repository-relative file paths from the diff. Return the same JSON structure
required by the base review prompt, with a top-level "findings" array.
For each finding include filePath, message, pattern, severity, and confidence.
"""

    start_time = time.perf_counter()
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=prompt,
        )
        elapsed = time.perf_counter() - start_time
        print(f"AI review time: {elapsed:.2f} seconds")
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        print(f"AI review failed after {elapsed:.2f} seconds: {exc}")
        error_message = str(exc)
        if "429" in error_message or "503" in error_message:
            return [], "unavailable"
        return [], "failed"

    raw_text = (response.text or "").strip()
    if not raw_text:
        return [], "failed"

    if raw_text.startswith("```"):
        raw_text = raw_text.removeprefix("```json").removeprefix("```").strip()
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"AI returned invalid JSON: {exc}")
        return [], "failed"

    if not isinstance(data, dict) or not isinstance(data.get("findings", []), list):
        return [], "failed"

    sections_by_path = {}
    for section in sections:
        path = extract_file_path(section)
        if path:
            sections_by_path[_normalize_path(path)] = section

    findings = []
    for item in data.get("findings", []):
        if not isinstance(item, dict):
            continue

        file_path = item.get("filePath")
        message = item.get("message")
        pattern = item.get("pattern")
        if not isinstance(file_path, str) or not isinstance(message, str) or not isinstance(pattern, str):
            continue

        normalized_path = _normalize_path(file_path)
        section = sections_by_path.get(normalized_path)
        # Reject findings for files that were not part of this PR diff.
        if section is None:
            continue

        severity = str(item.get("severity", "medium")).lower()
        if severity not in {"low", "medium", "high", "critical"}:
            severity = "medium"

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        findings.append({
            "agent": "ai",
            "file_path": file_path.replace("\\", "/"),
            "line": find_changed_line(section, pattern),
            "severity": severity,
            "confidence": confidence,
            "message": message,
        })

    return findings, "completed"
