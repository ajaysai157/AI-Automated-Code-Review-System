import json
import os
import time

from dotenv import load_dotenv
from google import genai

from app.ai.prompt import build_review_prompt
from app.models import Finding
from app.tools.diff_parser import (
    extract_file_path,
    find_changed_line,
    split_diff_by_file,
)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def review_with_ai(diff: str) -> tuple[list[Finding], str]:
    prompt = build_review_prompt(diff)

    try:
        start_time = time.perf_counter()

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=prompt
        )

        elapsed = time.perf_counter() - start_time
        print(f"AI review time: {elapsed:.2f} seconds")

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        print(f"AI review failed after {elapsed:.2f} seconds: {e}")

        error_message = str(e)

        if "429" in error_message or "503" in error_message:
            return [], "unavailable"

        return [], "failed"

    raw_text = response.text.strip()

    # Remove Markdown JSON code fences if Gemini returns them
    if raw_text.startswith("```"):
        raw_text = raw_text.replace("```json", "", 1)
        raw_text = raw_text.replace("```", "", 1).strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"AI returned invalid JSON: {e}")
        return [], "failed"

    findings: list[Finding] = []

    sections = split_diff_by_file(diff)

    for item in data.get("findings", []):
        if not isinstance(item, dict):
            continue

        file_path = item.get("filePath")
        message = item.get("message")
        pattern = item.get("pattern")

        if not file_path or not message or not pattern:
            continue

        severity = item.get("severity", "medium").lower()

        if severity not in {"low", "medium", "high", "critical"}:
            severity = "medium"

        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        changed_line = None

        for section in sections:
            section_file_path = extract_file_path(section)

            if section_file_path == file_path:
                changed_line = find_changed_line(section, pattern)
                break

        findings.append(
            Finding(
                agent="ai",
                filePath=file_path,
                line=changed_line,
                severity=severity,
                confidence=confidence,
                message=message,
            )
        )

    return findings, "completed"
