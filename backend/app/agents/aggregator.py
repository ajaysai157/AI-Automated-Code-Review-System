from app.models import Finding

def _normalize_message(message: str) -> set[str]:
    """
    Convert a finding message into a small set of meaningful words.

    This helps recognize that baseline and AI messages describing
    the same vulnerability may use different wording.
    """

    stop_words = {
        "the",
        "a",
        "an",
        "of",
        "to",
        "is",
        "can",
        "allows",
        "allow",
        "using",
        "use",
        "with",
        "on",
        "in",
        "for",
        "and",
        "which",
        "may",
        "be",
        "lead",
        "leads",
        "leading",
    }

    words = set()

    for word in message.lower().replace("(", " ").replace(")", " ").split():
        word = word.strip(".,:;\"'`")

        if word and word not in stop_words:
            words.add(word)

    return words


def _same_vulnerability(first: Finding, second: Finding) -> bool:
    """
    Determine whether two findings represent the same vulnerability.
    """

    # Different files cannot represent the same vulnerability.
    if first.filePath != second.filePath:
        return False

    first_words = _normalize_message(first.message)
    second_words = _normalize_message(second.message)

    if not first_words or not second_words:
        return False

    overlap = first_words & second_words

    # Strong message similarity.
    #
    # This is important because different agents may identify
    # the same vulnerability at slightly different line numbers.
    if len(overlap) >= 2:
        return True

    # If both agents point to exactly the same line,
    # allow a weaker message overlap.
    if (
        first.line is not None
        and second.line is not None
        and first.line == second.line
        and len(overlap) >= 1
    ):
        return True

    return False


def aggregate_findings(findings: list[Finding]) -> list[Finding]:
    """
    Merge duplicate findings produced by different review agents.

    Baseline and AI may report the same vulnerability with different
    wording. Keep the highest-confidence finding while preserving
    genuinely different vulnerabilities.
    """

    unique_findings: list[Finding] = []

    for finding in findings:
        duplicate_index = None

        for index, existing in enumerate(unique_findings):
            if _same_vulnerability(existing, finding):
                duplicate_index = index
                break

        if duplicate_index is None:
            unique_findings.append(finding)
            continue

        existing = unique_findings[duplicate_index]

        # Prefer the higher-confidence finding.
        if finding.confidence > existing.confidence:
            unique_findings[duplicate_index] = finding

    return unique_findings