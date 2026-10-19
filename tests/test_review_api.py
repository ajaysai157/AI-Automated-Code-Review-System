
import pytest

from django.contrib.auth.models import User
from rest_framework.test import APIClient

from unittest.mock import patch
from django.conf import settings

from app.models import Review, Finding

from app.github.pull_request import (
    GitHubAccessDenied,
    GitHubRateLimitError,
    GitHubRequestTimeout,
    InvalidPullRequestURL,
    PullRequestDiffTooLarge,
    PullRequestNotFound,
)

from unittest.mock import patch


@pytest.mark.django_db
def test_review_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/review/",
        {"pr_url": "https://github.com/example/repo/pull/1"},
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_review_saves_findings():
    user = User.objects.create_user(
        username="reviewer",
        password="test-password-123",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    findings = [{
        "agent": "ai",
        "file_path": "app.py",
        "line": 5,
        "severity": "high",
        "confidence": 0.95,
        "message": "Potential security vulnerability.",
    }]

    with (
        patch("app.views.get_pr_diff", return_value="sample diff"),
        patch(
            "app.views.review_diff",
            return_value=(findings, "completed"),
        ),
    ):
        response = client.post(
            "/api/review/",
            {"pr_url": "https://github.com/example/repo/pull/1"},
            format="json",
        )

    assert response.status_code == 200
    assert response.data["aiReviewStatus"] == "completed"
    assert Review.objects.filter(user=user).count() == 1
    assert Finding.objects.count() == 1
    assert response.data["findings"][0]["filePath"] == "app.py"


@pytest.mark.django_db
def test_invalid_pull_request_returns_controlled_error():
    user = User.objects.create_user(
        username="reviewer2",
        password="test-password-123",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "app.views.get_pr_diff",
        side_effect=InvalidPullRequestURL(
            "Provide a valid GitHub pull request URL."
        ),
    ):
        response = client.post(
            "/api/review/",
            {"pr_url": "https://github.com/example/repo/pull/1"},
            format="json",
        )

    assert response.status_code == 400
    assert Review.objects.count() == 0


@pytest.mark.django_db
def test_review_pipeline_failure_is_recorded():
    user = User.objects.create_user(
        username="reviewer3",
        password="test-password-123",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    with (
        patch("app.views.get_pr_diff", return_value="sample diff"),
        patch(
            "app.views.review_diff",
            side_effect=RuntimeError("Internal test error"),
        ),
    ):
        response = client.post(
            "/api/review/",
            {"pr_url": "https://github.com/example/repo/pull/1"},
            format="json",
        )

    assert response.status_code == 500
    assert response.data["error"] == (
        "The code review could not be completed. Please try again later."
    )
    assert Review.objects.filter(
        user=user,
        ai_review_status="failed",
    ).exists()



from django.test import override_settings



@pytest.mark.django_db
@override_settings(CODE_REVIEW_MAX_DIFF_BYTES=10)
def test_oversized_diff_is_rejected_before_ai_review():
    user = User.objects.create_user(
        username="large_diff_user",
        password="test-password-123",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    with (
        patch(
            "app.views.get_pr_diff",
            side_effect=PullRequestDiffTooLarge(
                "Pull request diff exceeds the configured size limit."
            ),
        ),
        patch("app.views.review_diff") as mock_review,
    ):
        response = client.post(
            "/api/review/",
            {"pr_url": "https://github.com/example/repo/pull/1"},
            format="json",
        )

    assert response.status_code == 413
    mock_review.assert_not_called()
    assert not Review.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_oversized_request_body_returns_413():
    user = User.objects.create_user(
        username="oversized_request_test",
        password="test-password-123",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    oversized_body = b"x" * (
        settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1
    )

    with patch("app.views.review_diff") as mock_review:
        response = client.generic(
            "POST",
            "/api/review/",
            data=oversized_body,
            content_type="application/json",
        )

    assert response.status_code == 413
    mock_review.assert_not_called()



@pytest.mark.django_db
def test_review_detail_is_not_accessible_to_another_user():
    owner = User.objects.create_user(
        username="review_owner",
        password="test-password-123",
    )
    other_user = User.objects.create_user(
        username="other_reviewer",
        password="test-password-123",
    )

    review = Review.objects.create(
        user=owner,
        pr_url="https://github.com/example/repo/pull/1",
        ai_review_status="completed",
    )

    client = APIClient()
    client.force_authenticate(user=other_user)

    response = client.get(f"/api/reviews/{review.run_id}/")

    assert response.status_code == 404
    assert response.data["error"] == "Review not found"


@pytest.mark.django_db
def test_review_history_only_returns_current_users_reviews():
    owner = User.objects.create_user(
        username="history_owner",
        password="test-password-123",
    )
    other_user = User.objects.create_user(
        username="history_other",
        password="test-password-123",
    )

    owner_review = Review.objects.create(
        user=owner,
        pr_url="https://github.com/example/repo/pull/1",
        ai_review_status="completed",
    )
    Review.objects.create(
        user=other_user,
        pr_url="https://github.com/example/repo/pull/2",
        ai_review_status="completed",
    )

    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.get("/api/reviews/")

    assert response.status_code == 200
    returned_ids = {
        str(item["runId"]) for item in response.data
    }
    assert returned_ids == {str(owner_review.run_id)}



@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error_class", "expected_status"),
    [
        (PullRequestNotFound, 404),
        (GitHubRateLimitError, 503),
        (GitHubRequestTimeout, 504),
        (GitHubAccessDenied, 502),
    ],
)
def test_github_failures_return_controlled_api_errors(
    error_class,
    expected_status,
):
    user = User.objects.create_user(
        username=f"github_error_{expected_status}",
        password="test-password-123",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "app.views.get_pr_diff",
        side_effect=error_class("Simulated GitHub failure"),
    ):
        response = client.post(
            "/api/review/",
            {"pr_url": "https://github.com/example/repo/pull/1"},
            format="json",
        )

    assert response.status_code == expected_status
    assert response.data["error"] == "Simulated GitHub failure"
    assert not Review.objects.filter(user=user).exists()
