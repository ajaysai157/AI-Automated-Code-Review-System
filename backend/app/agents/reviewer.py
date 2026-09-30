from app.models import Finding

from app.tools.diff_parser import (
    extract_file_path,
    find_changed_line,
    split_diff_by_file
)
from app.ai.reviewer import review_with_ai
from app.agents.aggregator import aggregate_findings


def review_diff(diff: str) -> tuple[list[Finding], str]:
    findings = []

    sections = split_diff_by_file(diff)

    # --------------------------------------------------
    # 1. Deterministic baseline review
    # --------------------------------------------------

    for section in sections:
        file_path = extract_file_path(section)

        # eval()
        if "eval(" in section:
            changed_line = find_changed_line(section, "eval(")

            findings.append(
                Finding(
                    agent="baseline",
                    filePath=file_path or "unknown",
                    line=changed_line,
                    severity="critical",
                    confidence=0.99,
                    message="Use of eval() can execute arbitrary code."
                )
            )

        # Password logging
        if "password" in section.lower() and "print(" in section:
            changed_line = find_changed_line(section, "password")

            findings.append(
                Finding(
                    agent="baseline",
                    filePath=file_path or "unknown",
                    line=changed_line,
                    severity="high",
                    confidence=0.95,
                    message="Possible password exposure through logging."
                )
            )

        # SQL injection
        if "execute(" in section.lower() and "+" in section:
            changed_line = find_changed_line(section, "execute(")

            # Fallback: find the first added line containing execute()
            if changed_line is None:
                for line in section.splitlines():
                    if line.startswith("+") and "execute(" in line.lower():
                        changed_line = find_changed_line(section, line[1:].strip())
                        break

            findings.append(
                Finding(
                    agent="baseline",
                    filePath=file_path or "unknown",
                    line=changed_line,
                    severity="high",
                    confidence=0.90,
                    message="Possible SQL injection through dynamically constructed SQL."
                )
            )

    # --------------------------------------------------
    # 2. ONE AI review for the complete PR
    # --------------------------------------------------

    ai_findings, ai_review_status = review_with_ai(diff)

    findings.extend(ai_findings)

    # --------------------------------------------------
    # 3. Aggregate + deduplicate
    # --------------------------------------------------

    findings = aggregate_findings(findings)

    return findings, ai_review_status