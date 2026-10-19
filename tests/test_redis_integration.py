
import pytest

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import caches
from django.test import override_settings
from rest_framework.test import APIClient


REDIS_CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": settings.REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "acrs",
        "TIMEOUT": 300,
    }
}

pytestmark = pytest.mark.skipif(
    not settings.REDIS_URL,
    reason="REDIS_URL is not configured",
)


@pytest.mark.django_db
@override_settings(CACHES=REDIS_CACHES)
def test_redis_cache_connection():
    cache = caches["default"]
    key = "acrs_test:redis_integration_connection"

    try:
        assert type(cache).__name__ == "RedisCache"

        cache.set(key, "connected", timeout=30)
        assert cache.get(key) == "connected"
    finally:
        cache.delete(key)


@pytest.mark.django_db
@override_settings(CACHES=REDIS_CACHES)
def test_review_endpoint_throttles_after_five_requests():
    cache = caches["default"]

    user = User.objects.create_user(
        username="redis_throttle_test",
        password="test-password-123",
    )

    # Clear only this user's throttle entry, not the entire Redis cache.
    throttle_key = f"throttle_code_review_{user.pk}"
    cache.delete(throttle_key)

    try:
        client = APIClient()
        client.force_authenticate(user=user)
        url = "/api/review/"

        # Invalid input avoids running the GitHub and AI review pipeline.
        for _ in range(5):
            response = client.post(
                url,
                {"pr_url": "not-a-valid-url"},
                format="json",
            )
            assert response.status_code == 400

        response = client.post(
            url,
            {"pr_url": "not-a-valid-url"},
            format="json",
        )

        assert response.status_code == 429

    finally:
        cache.delete(throttle_key)
