from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        cache_key = "acrs:health_check"
        cache.set(cache_key, "ok", timeout=10)
        cache_healthy = cache.get(cache_key) == "ok"
        cache.delete(cache_key)

        if not cache_healthy:
            raise RuntimeError("Cache health check failed")

        return JsonResponse(
            {
                "status": "healthy",
                "database": "ok",
                "cache": "ok",
            },
            status=200,
        )

    except Exception:
        return JsonResponse(
            {"status": "unhealthy"},
            status=503,
        )
