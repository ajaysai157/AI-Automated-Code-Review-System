from uuid import uuid4

from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ReviewRequestSerializer,
    ReviewResponseSerializer,
)

from .agents.reviewer import review_diff


class ReviewAPIView(APIView):
    def post(self, request):

        serializer=ReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        diff=serializer.validated_data["diff"]
        findings, ai_review_status=review_diff(diff)

        response_data = {
            "runId": uuid4(),
            "findings": findings,
            "aiReviewStatus": ai_review_status,
        }
        response_serializer=ReviewResponseSerializer(response_data)
        return Response(response_serializer.data)