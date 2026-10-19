import logging

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.db import transaction

from rest_framework.exceptions import APIException, ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .agents.reviewer import review_diff
from .github.pull_request import (
    GitHubPullRequestError,
    get_pr_diff,
)
from .models import Finding, Review
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    ReviewDetailSerializer,
    ReviewHistorySerializer,
    ReviewRequestSerializer,
    ReviewResponseSerializer,
)
from .throttles import CodeReviewRateThrottle


logger = logging.getLogger(__name__)


class RequestEntityTooLarge(APIException):
    status_code = 413
    default_detail = "Request body is too large."
    default_code = "request_entity_too_large"


class ReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CodeReviewRateThrottle]

    def initial(self, request, *args, **kwargs):
        # Run authentication, permissions, and throttling first.
        super().initial(request, *args, **kwargs)

        content_length = request.META.get("CONTENT_LENGTH")

        if content_length is None:
            return

        try:
            content_length = int(content_length)
        except (TypeError, ValueError):
            raise ParseError("Invalid Content-Length header.")

        if content_length < 0:
            raise ParseError("Invalid Content-Length header.")

        if content_length > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
            raise RequestEntityTooLarge()

    def handle_exception(self, exc):
        # Convert Django's request-body limit exception to HTTP 413.
        if isinstance(exc, RequestDataTooBig):
            return Response(
                {"detail": "Request body is too large."},
                status=413,
            )

        return super().handle_exception(exc)

    def post(self, request):
        serializer = ReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pr_url = serializer.validated_data["pr_url"]
        max_diff_bytes = settings.CODE_REVIEW_MAX_DIFF_BYTES

        try:
            diff = get_pr_diff(
                pr_url,
                max_bytes=max_diff_bytes,
            )
        except GitHubPullRequestError as exc:
            logger.warning(
                "GitHub diff retrieval failed",
                extra={
                    "user_id": request.user.pk,
                    "error_type": type(exc).__name__,
                    "http_status": exc.status_code,
                },
            )
            return Response(
                {"error": str(exc)},
                status=exc.status_code,
            )

        pipeline_failed = False

        try:
            findings, ai_review_status = review_diff(diff)
        except Exception:
            logger.exception(
                "Unexpected code review pipeline failure",
                extra={"user_id": request.user.pk},
            )
            findings = []
            ai_review_status = "failed"
            pipeline_failed = True

        with transaction.atomic():
            review = Review.objects.create(
                user=request.user,
                pr_url=pr_url,
                ai_review_status=ai_review_status,
            )

            Finding.objects.bulk_create(
                [
                    Finding(
                        review=review,
                        agent=finding["agent"],
                        file_path=finding["file_path"],
                        line=finding.get("line"),
                        severity=finding["severity"],
                        confidence=finding["confidence"],
                        message=finding["message"],
                    )
                    for finding in findings
                ]
            )

        if pipeline_failed:
            return Response(
                {
                    "error": (
                        "The code review could not be completed. "
                        "Please try again later."
                    ),
                    "runId": str(review.run_id),
                },
                status=500,
            )

        response_data = {
            "runId": review.run_id,
            "findings": findings,
            "aiReviewStatus": ai_review_status,
        }

        response_serializer = ReviewResponseSerializer(response_data)
        return Response(response_serializer.data)


class ReviewHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reviews = Review.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = ReviewHistorySerializer(reviews, many=True)
        return Response(serializer.data)


class ReviewDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id):
        try:
            review = Review.objects.get(
                run_id=run_id,
                user=request.user,
            )
        except Review.DoesNotExist:
            return Response(
                {"error": "Review not found"},
                status=404,
            )

        serializer = ReviewDetailSerializer(review)
        return Response(serializer.data)


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "User registered successfully"},
            status=201,
        )


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)
