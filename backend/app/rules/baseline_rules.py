from app.models import Finding
from app.tools.diff_parser import extract_file_path, find_changed_line


def check_eval(section: str) -> Finding | None:
    if "eval(" not in section:
        return None

    file_path = extract_file_path(section)
    line = find_changed_line(section, "eval(")

    return Finding(
        agent="baseline",
        filePath=file_path or "unknown",
        line=line,
        severity="critical",
        confidence=0.99,
        message="Use of eval() can execute arbitrary code."
    )

def check_password_logging(section: str) -> Finding | None:
    if "password" not in section.lower() or "print(" not in section:
        return None

    file_path = extract_file_path(section)
    line = find_changed_line(section, "password")

    return Finding(
        agent="baseline",
        filePath=file_path or "unknown",
        line=line,
        severity="high",
        confidence=0.95,
        message="Possible password exposure through logging."
    )


def check_sql_injection(section: str) -> Finding | None:
    if "execute(" not in section.lower() or "+" not in section:
        return None

    file_path = extract_file_path(section)
    line = find_changed_line(section, "execute(")

    return Finding(
        agent="baseline",
        filePath=file_path or "unknown",
        line=line,
        severity="high",
        confidence=0.90,
        message="Possible SQL injection through dynamically constructed SQL."
    )


def check_command_injection(section: str) -> Finding | None:
    if "os.system(" not in section and "subprocess.run(" not in section:
        return None

    file_path = extract_file_path(section)
    line = find_changed_line(section, "os.system(")

    return Finding(
        agent="baseline",
        filePath=file_path or "unknown",
        line=line,
        severity="critical",
        confidence=0.90,
        message="Possible command injection through execution of system commands."
    )


def check_hardcoded_secret(section: str) -> Finding | None:
    if "api_key" not in section.lower() and "password =" not in section.lower():
        return None

    file_path = extract_file_path(section)
    line = find_changed_line(section, "api_key")

    return Finding(
        agent="baseline",
        filePath=file_path or "unknown",
        line=line,
        severity="high",
        confidence=0.85,
        message="Possible hardcoded secret detected."
    )


BASELINE_RULES = [
    check_eval,
    check_password_logging,
    check_sql_injection,
    check_command_injection,
    check_hardcoded_secret,
]