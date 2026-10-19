import re

import requests


DEFAULT_MAX_DIFF_BYTES = 1024 * 1024
CHUNK_SIZE = 64 * 1024


class GitHubPullRequestError(Exception):
    status_code = 502


class InvalidPullRequestURL(GitHubPullRequestError):
    status_code = 400


class PullRequestNotFound(GitHubPullRequestError):
    status_code = 404


class GitHubRateLimitError(GitHubPullRequestError):
    status_code = 503


class GitHubRequestTimeout(GitHubPullRequestError):
    status_code = 504


class GitHubAccessDenied(GitHubPullRequestError):
    status_code = 502


class PullRequestDiffTooLarge(GitHubPullRequestError):
    status_code = 413


def get_pr_diff(
    pr_url: str,
    max_bytes: int = DEFAULT_MAX_DIFF_BYTES,
) -> str:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive.")

    pattern = (
        r"https://github\.com/"
        r"([A-Za-z0-9_.-]+)/"
        r"([A-Za-z0-9_.-]+)/pull/(\d+)/?"
    )

    match = re.fullmatch(pattern, pr_url.strip())

    if not match:
        raise InvalidPullRequestURL(
            "Provide a valid GitHub pull request URL."
        )

    owner, repo, number = match.groups()

    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{number}"
    )

    response = None

    try:
        response = requests.get(
            api_url,
            headers={"Accept": "application/vnd.github.v3.diff"},
            timeout=(3.05, 15),
            stream=True,
            allow_redirects=False,
        )

        if response.status_code == 404:
            raise PullRequestNotFound(
                "Pull request not found or repository is private."
            )

        if response.status_code == 429:
            raise GitHubRateLimitError(
                "GitHub rate limit reached. Try again later."
            )

        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            if (
                remaining == "0"
                or response.headers.get("Retry-After")
                or "rate limit" in response.text.lower()
            ):
                raise GitHubRateLimitError(
                    "GitHub rate limit reached. Try again later."
                )

            raise GitHubAccessDenied(
                "GitHub denied access to the pull request."
            )

        if 300 <= response.status_code < 400:
            raise GitHubPullRequestError(
                "GitHub returned an unexpected redirect."
            )

        if response.status_code >= 500:
            raise GitHubPullRequestError(
                "GitHub is temporarily unavailable."
            )

        if not response.ok:
            raise GitHubPullRequestError(
                "GitHub could not provide the pull request diff."
            )

        content_length = response.headers.get("Content-Length")

        if content_length:
            try:
                if int(content_length) > max_bytes:
                    raise PullRequestDiffTooLarge(
                        "Pull request diff exceeds the configured size limit."
                    )
            except ValueError:
                # Ignore malformed Content-Length; enforce the limit
                # while streaming instead.
                pass

        chunks = []
        total_bytes = 0

        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if not chunk:
                continue

            total_bytes += len(chunk)

            if total_bytes > max_bytes:
                raise PullRequestDiffTooLarge(
                    "Pull request diff exceeds the configured size limit."
                )

            chunks.append(chunk)

        return b"".join(chunks).decode(
            "utf-8",
            errors="replace",
        )

    except requests.Timeout as exc:
        raise GitHubRequestTimeout(
            "GitHub took too long to respond."
        ) from exc

    except requests.RequestException as exc:
        raise GitHubPullRequestError(
            "Could not connect to GitHub."
        ) from exc

    finally:
        if response is not None:
            response.close()
