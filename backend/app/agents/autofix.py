import ast
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from app.ai.autofix import generate_patch
from app.models import Autofix, Finding
from app.tools.language_detector import detect_language


# ---------------------------------------------------------------------------
# Finding eligibility and patch generation
# ---------------------------------------------------------------------------

def is_fixable(finding: dict) -> bool:
    return (
        finding.get("confidence", 0.0) >= 0.90
        and finding.get("severity", "").lower() in {"high", "critical"}
    )


def get_fixable_findings(findings: list[dict]) -> list[dict]:
    return [finding for finding in findings if is_fixable(finding)]


def requires_manual_review(finding: dict) -> bool:
    message = finding.get("message", "").lower()
    manual_review_keywords = ["api key", "secret", "credential", "password"]
    return any(keyword in message for keyword in manual_review_keywords)


def save_proposed_patch(
    finding: Finding,
    source_code: str,
) -> Autofix | None:
    finding_data = {
        "message": finding.message,
        "file_path": finding.file_path,
        "line": finding.line,
    }
    patch = generate_patch(finding_data, source_code)

    if not patch:
        return None

    return Autofix.objects.create(
        finding=finding,
        patch=patch,
        tests_passed=None,
        applied=False,
        status="proposed",
    )


# ---------------------------------------------------------------------------
# Syntax validation
# ---------------------------------------------------------------------------

def validate_patch_syntax(patch: str) -> bool:
    try:
        ast.parse(patch)
        return True
    except SyntaxError:
        return False


def validate_patch_compile(patch: str) -> bool:
    try:
        compile(patch, "<autofix>", "exec")
        return True
    except (SyntaxError, ValueError, TypeError):
        return False


def validate_patch_for_language(
    file_path: str,
    patch: str,
) -> bool | None:
    """Return True/False for supported languages, None for unsupported ones."""
    if detect_language(file_path) == "python":
        return validate_patch_compile(patch)
    return None


def validate_saved_patch(autofix: Autofix) -> bool | None:
    result = validate_patch_for_language(
        autofix.finding.file_path,
        autofix.patch,
    )

    if result is True:
        autofix.status = "syntax_valid"
    elif result is False:
        autofix.status = "rejected"
    else:
        autofix.status = "unsupported_language"

    # Syntax validation is not test execution.
    autofix.tests_passed = None
    autofix.save(update_fields=["status", "tests_passed"])
    return result


def validate_patch_in_workspace(
    autofix: Autofix,
    source_code: str,
) -> bool | None:
    """Check a proposed Python file in a disposable directory without running it."""
    if detect_language(autofix.finding.file_path) != "python":
        autofix.status = "unsupported_language"
        autofix.tests_passed = None
        autofix.save(update_fields=["status", "tests_passed"])
        return None

    try:
        with tempfile.TemporaryDirectory(prefix="autofix_") as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "original.py").write_text(
                source_code,
                encoding="utf-8",
            )
            proposed_file = workspace / "proposed.py"
            proposed_file.write_text(autofix.patch, encoding="utf-8")

            compile(
                proposed_file.read_text(encoding="utf-8"),
                str(proposed_file),
                "exec",
            )

    except (SyntaxError, ValueError, TypeError, OSError):
        autofix.status = "rejected"
        autofix.tests_passed = None
        autofix.save(update_fields=["status", "tests_passed"])
        return False

    autofix.status = "syntax_valid"
    autofix.tests_passed = None
    autofix.save(update_fields=["status", "tests_passed"])
    return True


# ---------------------------------------------------------------------------
# Test execution helpers
# ---------------------------------------------------------------------------

def run_project_tests(workspace_path: str) -> dict:
    """Run pytest locally for trusted code only.

    Do not use this function for untrusted pull-request code. Use
    run_project_tests_in_docker() for container-based execution instead.
    """
    workspace = Path(workspace_path).resolve()

    if not workspace.is_dir():
        return {
            "passed": None,
            "status": "workspace_missing",
            "output": "Project workspace does not exist.",
        }

    if not any(workspace.glob("test_*.py")) and not (workspace / "tests").exists():
        return {
            "passed": None,
            "status": "no_tests_found",
            "output": "No obvious Python test files or tests directory found.",
        }

    try:
        result = subprocess.run(
            [sys.executable,"-m","pytest","-q","-p","no:django","-p","no:cacheprovider",],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        output = (result.stdout + "\n" + result.stderr)[-5000:]

        if result.returncode == 0:
            status, passed = "tests_passed", True
        elif result.returncode == 1:
            status, passed = "tests_failed", False
        elif result.returncode == 5:
            status, passed = "no_tests_collected", None
        else:
            status, passed = "test_error", None

        return {"passed": passed, "status": status, "output": output}

    except subprocess.TimeoutExpired:
        return {
            "passed": None,
            "status": "test_timeout",
            "output": "Tests exceeded the 60-second timeout.",
        }
    except OSError as exc:
        return {"passed": None, "status": "test_error", "output": str(exc)}


def run_project_tests_in_docker(
    workspace_path: str,
    timeout_seconds: int = 90,
) -> dict:
    """Run pytest in a restricted Docker container against a disposable workspace."""
    workspace = Path(workspace_path).resolve()

    if not workspace.is_dir():
        return {
            "passed": None,
            "status": "workspace_missing",
            "output": "Workspace does not exist.",
        }

    container_name = f"codesentry-test-{uuid.uuid4().hex[:12]}"
    mount_source = str(workspace).replace("\\", "/")

    command = [
        "docker", "run", "--rm",
        "--pull=never",
        "--name", container_name,
        "--network", "none",
        "--memory", "512m",
        "--memory-swap", "512m",
        "--cpus", "1",
        "--pids-limit", "64",
        "--ulimit", "nofile=256:256",
        "--ulimit", "fsize=10485760:10485760",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=128m",
        "--mount", f"type=bind,source={mount_source},target=/workspace",
        "--user", "10001:10001",
        "--workdir", "/workspace",
        "codesentry-autofix:latest",
        "python", "-m", "pytest", "-q",
        "-p", "no:cacheprovider",
        "--disable-warnings",
        "--maxfail=1",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
        output = (result.stdout + "\n" + result.stderr)[-5000:]

        if result.returncode == 0:
            status, passed = "tests_passed", True
        elif result.returncode == 1:
            status, passed = "tests_failed", False
        elif result.returncode == 5:
            status, passed = "no_tests_collected", None
        else:
            # Docker/runtime errors and pytest internal errors are not proof
            # that the proposed code itself failed its tests.
            status, passed = "test_error", None

        return {"passed": passed, "status": status, "output": output}

    except subprocess.TimeoutExpired:
        return {
            "passed": None,
            "status": "test_timeout",
            "output": f"Tests exceeded {timeout_seconds} seconds.",
        }
    except OSError as exc:
        return {"passed": None, "status": "docker_error", "output": str(exc)}
    finally:
        # Remove a container that may still be running after a timeout.
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass


def record_test_result(autofix: Autofix, result: dict) -> Autofix:
    """Persist test outcomes without confusing validation with testing."""
    status = result["status"]

    if status == "tests_passed":
        autofix.tests_passed = True
    elif status == "tests_failed":
        autofix.tests_passed = False
    else:
        autofix.tests_passed = None

    autofix.status = status
    autofix.save(update_fields=["tests_passed", "status"])
    return autofix


# ---------------------------------------------------------------------------
# Temporary project workspace
# ---------------------------------------------------------------------------

def prepare_autofix_workspace(
    project_root: str,
    relative_file_path: str,
    patch: str,
) -> tuple[tempfile.TemporaryDirectory, Path]:
    """Copy a project to a temporary workspace and replace one file."""
    root = Path(project_root).resolve()
    relative_path = Path(relative_file_path)

    if (
        not root.is_dir()
        or relative_path.is_absolute()
        or ".." in relative_path.parts
        or not patch.strip()
    ):
        raise ValueError("Invalid project path, file path, or patch.")

    original_file = root / relative_path

    if (
        not original_file.is_file()
        or original_file.is_symlink()
        or not original_file.resolve().is_relative_to(root)
    ):
        raise ValueError("Target file is missing or outside the project.")

    temp_handle = tempfile.TemporaryDirectory(prefix="codesentry_autofix_")
    workspace = Path(temp_handle.name) / "project"

    try:
        shutil.copytree(
            root,
            workspace,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                "node_modules",
                ".env",
                ".env.*",
                "db.sqlite3",
                "*.pyc",
            ),
        )

        target = workspace / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(patch, encoding="utf-8")
        return temp_handle, workspace

    except Exception:
        temp_handle.cleanup()
        raise


# ---------------------------------------------------------------------------
# End-to-end proposal validation
# ---------------------------------------------------------------------------

def validate_autofix_with_tests(
    autofix: Autofix,
    project_root: str,
) -> dict:
    """Syntax-check a proposed patch, test a temporary copy in Docker,
    persist the actual result, and never modify the original repository.
    """
    file_path = autofix.finding.file_path
    syntax_valid = validate_patch_for_language(file_path, autofix.patch)

    if syntax_valid is None:
        result = {
            "passed": None,
            "status": "unsupported_language",
            "output": f"Validation is not implemented for: {file_path}",
        }
    elif not syntax_valid:
        result = {
            "passed": None,
            "status": "invalid_patch_syntax",
            "output": "The proposed Python file failed syntax compilation.",
        }
    else:
        temp_handle = None
        try:
            temp_handle, workspace = prepare_autofix_workspace(
                project_root=project_root,
                relative_file_path=file_path,
                patch=autofix.patch,
            )
            result = run_project_tests_in_docker(str(workspace))

        except (OSError, ValueError, shutil.Error) as exc:
            result = {
                "passed": None,
                "status": "workspace_error",
                "output": str(exc),
            }
        finally:
            if temp_handle is not None:
                temp_handle.cleanup()

    record_test_result(autofix, result)
    return result
