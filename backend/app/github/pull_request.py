import re
import requests


def get_pr_diff(pr_url: str) -> str:
    match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)",
        pr_url
    )

    if not match:
        raise ValueError("Invalid GitHub PR URL")

    owner, repo, number = match.groups()

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"

    response = requests.get(
        url,
        headers={
            "Accept": "application/vnd.github.v3.diff"
        },
        timeout=10
    )

    response.raise_for_status()

    return response.text