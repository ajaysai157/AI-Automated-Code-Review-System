import pytest

from unittest.mock import patch
from django.test import Client


@pytest.mark.django_db
def test_health_endpoint_returns_200_when_services_are_healthy():
    response = Client().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "ok",
        "cache": "ok",
    }


@pytest.mark.django_db
def test_health_endpoint_returns_503_when_database_fails():
    with patch(
        "app.health.connection.cursor",
        side_effect=Exception("Database unavailable"),
    ):
        response = Client().get("/api/health/")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy"}


@pytest.mark.django_db
def test_health_endpoint_returns_503_when_cache_fails():
    with patch(
        "app.health.cache.set",
        side_effect=Exception("Cache unavailable"),
    ):
        response = Client().get("/api/health/")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy"}