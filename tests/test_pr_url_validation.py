import pytest
from rest_framework.exceptions import ValidationError

from app.serializers import ReviewRequestSerializer


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/owner/repo/pull/1",
        "https://github.com/owner/repo/pull/123/",
    ],
)
def test_accepts_valid_pull_request_urls(url):
    serializer = ReviewRequestSerializer(data={"pr_url": url})

    assert serializer.is_valid(), serializer.errors


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo/pull/1",
        "https://github.com.evil.example/owner/repo/pull/1",
        "https://evil.example/owner/repo/pull/1",
        "https://github.com/owner/repo/issues/1",
        "https://github.com/owner/repo/pull/0",
        "https://user:pass@github.com/owner/repo/pull/1",
        "https://github.com/owner/repo/pull/1?redirect=evil.example",
    ],
)
def test_rejects_invalid_pull_request_urls(url):
    serializer = ReviewRequestSerializer(data={"pr_url": url})

    assert not serializer.is_valid()
    assert "pr_url" in serializer.errors