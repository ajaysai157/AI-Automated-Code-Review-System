from uuid import uuid4

from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ReviewRequestSerializer,
    ReviewResponseSerializer,
)

from .agents.reviewer import review_diff
from .github.pull_request import get_pr_diff


class ReviewAPIView(APIView):

    def post(self, request):

        serializer = ReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pr_url = serializer.validated_data["pr_url"]

        try:
            diff = get_pr_diff(pr_url)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=400
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch PR: {str(e)}"},
                status=400
            )

        findings, ai_review_status = review_diff(diff)

        response_data = {
            "runId": uuid4(),
            "findings": findings,
            "aiReviewStatus": ai_review_status,
        }

        response_serializer = ReviewResponseSerializer(response_data)

        return Response(
            response_serializer.data,
            status=200
        )