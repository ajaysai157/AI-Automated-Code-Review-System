from rest_framework import serializers

class ReviewRequestSerializer(serializers.Serializer):
    pr_url = serializers.URLField()


class FindingSerializer(serializers.Serializer):
    agent=serializers.CharField()
    filePath=serializers.CharField()
    line = serializers.IntegerField(required=False, allow_null=True)
    severity = serializers.ChoiceField(
        choices=["low", "medium", "high", "critical"]
    )
    confidence = serializers.FloatField()
    message = serializers.CharField()


class ReviewResponseSerializer(serializers.Serializer):
    runId = serializers.UUIDField()
    findings = FindingSerializer(many=True)
    aiReviewStatus = serializers.ChoiceField(
        choices=["completed", "failed", "unavailable"]
    )