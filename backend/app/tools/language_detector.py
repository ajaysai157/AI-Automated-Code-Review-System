from pathlib import PurePosixPath


EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
}


def detect_language(file_path: str) -> str:
    """Detect a language from a repository-relative path or filename."""
    if not isinstance(file_path, str) or not file_path.strip():
        return "unknown"

    # GitHub paths use '/', but callers may supply Windows-style paths.
    normalized_path = file_path.strip().replace("\\", "/")
    extension = PurePosixPath(normalized_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(extension, "unknown")
