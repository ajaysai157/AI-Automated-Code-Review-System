import re


_DIFF_FILE_HEADER = re.compile(r"^diff --git ", re.MULTILINE)
_NEW_FILE_PATH = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", re.MULTILINE)


def extract_file_path(diff: str) -> str | None:
    """Return the new-side repository path for one unified diff section."""
    match = _NEW_FILE_PATH.search(diff)
    if not match:
        return None

    path = match.group(1).strip()
    # Git may quote paths containing unusual characters. Keep the parser
    # conservative instead of attempting to decode every Git quoting variant.
    if path == "/dev/null":
        return None
    return path


def extract_file_paths(diff: str) -> list[str]:
    """Return new-side paths found in a possibly multi-file diff."""
    paths = []
    for match in _NEW_FILE_PATH.finditer(diff):
        path = match.group(1).strip()
        if path != "/dev/null":
            paths.append(path)
    return paths


def split_diff_by_file(diff: str) -> list[str]:
    """Split a standard Git unified diff into per-file sections."""
    if not diff or not diff.strip():
        return []

    sections = _DIFF_FILE_HEADER.split(diff)
    # re.split consumes the matched header, so put it back for each section.
    # A diff without 'diff --git' is treated as one section for compatibility.
    if len(sections) == 1:
        return [diff.strip()] if diff.strip() else []

    result = []
    matches = list(_DIFF_FILE_HEADER.finditer(diff))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(diff)
        section = diff[match.start():end].strip()
        if section:
            result.append(section)
    return result


def find_changed_line(diff: str, keyword: str) -> int | None:
    """Find the new-side line number of the first added line containing keyword."""
    if not keyword:
        return None

    current_line = None
    for line in diff.splitlines():
        if line.startswith("@@"):
            match = _HUNK_HEADER.match(line)
            current_line = int(match.group(1)) if match else None
            continue

        if current_line is None:
            continue

        if line.startswith("+++"):
            # File metadata is not part of the hunk, defensively ignore it.
            continue
        if line.startswith("---"):
            continue
        if line.startswith("+"):
            if keyword in line[1:]:
                return current_line
            current_line += 1
        elif line.startswith("-"):
            # Removed lines do not advance the new-side line number.
            continue
        elif line.startswith("\\"):
            # For example: '\\ No newline at end of file'
            continue
        else:
            # Context lines exist on both sides.
            current_line += 1

    return None
