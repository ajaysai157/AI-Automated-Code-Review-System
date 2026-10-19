
from app.tools.diff_parser import split_diff_by_file, extract_file_path
from app.tools.language_detector import detect_language


def create_review_plan(diff: str) -> dict:
    """
    Select specialist reviewers based on the changed files and code.
    """

    sections = split_diff_by_file(diff)

    if not sections:
        return {
            "languages": [],
            "changed_files": [],
            "agents": [],
            "reasons": ["No changes found to review."],
        }

    changed_files = []
    languages = set()
    added_lines = []
    reasons = set()

    for section in sections:
        file_path = extract_file_path(section)

        if not file_path:
            continue

        changed_files.append(file_path)
        language = detect_language(file_path)

        if language != "unknown":
            languages.add(language)

        for line in section.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append((file_path, line[1:].lower()))

    agents = set()

    # Security review is the default for source-code changes.
    source_extensions = {
        ".py", ".java", ".js", ".jsx", ".ts", ".tsx",
        ".cpp", ".cc", ".c", ".cs", ".go", ".rs",
        ".php", ".rb",
    }

    source_files = [
        path for path in changed_files
        if any(path.lower().endswith(ext) for ext in source_extensions)
    ]

    if source_files:
        agents.add("security")
        reasons.add("Source-code changes require security review.")

    security_patterns = (
        "eval(",
        "exec(",
        "password",
        "secret",
        "token",
        "executequery(",
        "runtime.getruntime",
        "processbuilder",
    )

    if any(
        pattern in line
        for _, line in added_lines
        for pattern in security_patterns
    ):
        agents.add("security")
        reasons.add("Potentially security-sensitive code was changed.")

    performance_patterns = (
        "for ",
        "while ",
        ".sort(",
        ".order_by(",
        "select ",
        "join ",
    )

    if any(
        pattern in line
        for _, line in added_lines
        for pattern in performance_patterns
    ):
        agents.add("performance")
        reasons.add("Changed code may warrant performance review.")

    test_files = [
        path for path in changed_files
        if (
            path.lower().startswith("tests/")
            or "/tests/" in path.lower()
            or path.lower().startswith("test_")
            or path.lower().endswith(("_test.py", ".test.js", ".spec.js",
                                      ".test.ts", ".spec.ts"))
        )
    ]

    if test_files:
        agents.add("test_coverage")
        reasons.add("Test files changed; review test quality and coverage.")

    if not agents:
        reasons.add("No supported source-code changes detected.")

    return {
        "languages": sorted(languages),
        "changed_files": changed_files,
        "agents": sorted(agents),
        "reasons": sorted(reasons),
    }
