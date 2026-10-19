
import pytest
import requests
from unittest.mock import MagicMock, patch

from app.github.pull_request import (
    GitHubAccessDenied,
    GitHubPullRequestError,
    GitHubRateLimitError,
    GitHubRequestTimeout,
    PullRequestDiffTooLarge,
    PullRequestNotFound,
    get_pr_diff,
)


PR_URL = "https://github.com/example/repo/pull/1"


def make_response(
    status_code=200,
    headers=None,
    chunks=None,
):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers or {}
    response.iter_content.return_value = (
        chunks if chunks is not None else [b"sample diff"]
    )
    return response


@patch("app.github.pull_request.requests.get")
def test_streams_and_returns_diff(mock_get):
    response = make_response(chunks=[b"sample ", b"diff"])
    mock_get.return_value = response

    assert get_pr_diff(PR_URL) == "sample diff"
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["stream"] is True
    response.close.assert_called_once()


@patch("app.github.pull_request.requests.get")
def test_rejects_oversized_content_length(mock_get):
    response = make_response(
        headers={"Content-Length": "100"},
    )
    mock_get.return_value = response

    with pytest.raises(PullRequestDiffTooLarge):
        get_pr_diff(PR_URL, max_bytes=10)

    response.iter_content.assert_not_called()
    response.close.assert_called_once()


@patch("app.github.pull_request.requests.get")
def test_stops_when_stream_exceeds_limit(mock_get):
    response = make_response(
        chunks=[b"123456", b"789012"],
    )
    mock_get.return_value = response

    with pytest.raises(PullRequestDiffTooLarge):
        get_pr_diff(PR_URL, max_bytes=10)

    response.close.assert_called_once()


@patch("app.github.pull_request.requests.get")
def test_maps_request_timeout(mock_get):
    mock_get.side_effect = requests.Timeout()

    with pytest.raises(GitHubRequestTimeout):
        get_pr_diff(PR_URL)


@patch("app.github.pull_request.requests.get")
def test_maps_not_found(mock_get):
    response = make_response(status_code=404)
    mock_get.return_value = response

    with pytest.raises(PullRequestNotFound):
        get_pr_diff(PR_URL)

    response.close.assert_called_once()


@patch("app.github.pull_request.requests.get")
def test_distinguishes_rate_limit_from_forbidden(mock_get):
    rate_limited = make_response(
        status_code=403,
        headers={"X-RateLimit-Remaining": "0"},
    )
    mock_get.return_value = rate_limited

    with pytest.raises(GitHubRateLimitError):
        get_pr_diff(PR_URL)

    forbidden = make_response(status_code=403)
    mock_get.return_value = forbidden

    with pytest.raises(GitHubAccessDenied):
        get_pr_diff(PR_URL)


@patch("app.github.pull_request.requests.get")
def test_maps_server_errors(mock_get):
    response = make_response(status_code=502)
    mock_get.return_value = response

    with pytest.raises(GitHubPullRequestError):
        get_pr_diff(PR_URL)

    response.close.assert_called_once()
