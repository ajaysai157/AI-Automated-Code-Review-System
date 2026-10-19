from urllib.parse import urlsplit

from rest_framework import serializers
from .models import Review
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class ReviewRequestSerializer(serializers.Serializer):
    pr_url = serializers.URLField()


class FindingSerializer(serializers.Serializer):
    agent = serializers.CharField()
    filePath = serializers.CharField(source="file_path")
    line = serializers.IntegerField(required=False, allow_null=True)
    severity = serializers.ChoiceField(
        choices=["low", "medium", "high", "critical"]
    )
    confidence = serializers.FloatField()
    message = serializers.CharField()


class ReviewResponseSerializer(serializers.Serializer):
    runId = serializers.UUIDField(allow_null=True)
    findings = FindingSerializer(many=True)
    aiReviewStatus = serializers.ChoiceField(
        choices=[
            "completed",
            "failed",
            "unavailable",
            "skipped_no_changes",
            "skipped_no_reviewers",
        ]
    )


class ReviewHistorySerializer(serializers.ModelSerializer):
    runId = serializers.UUIDField(source="run_id")
    prUrl = serializers.URLField(source="pr_url")
    aiReviewStatus = serializers.CharField(source="ai_review_status")
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Review
        fields = [
            "runId",
            "prUrl",
            "aiReviewStatus",
            "createdAt",
        ]

class ReviewDetailSerializer(serializers.ModelSerializer):
    runId = serializers.UUIDField(source="run_id")
    prUrl = serializers.URLField(source="pr_url")
    aiReviewStatus = serializers.CharField(source="ai_review_status")
    createdAt = serializers.DateTimeField(source="created_at")
    findings = FindingSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = [
            "runId",
            "prUrl",
            "aiReviewStatus",
            "createdAt",
            "findings",
        ]


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

class LoginSerializer(TokenObtainPairSerializer):
    pass

class ReviewRequestSerializer(serializers.Serializer):
    pr_url = serializers.URLField(max_length=2048)

    def validate_pr_url(self, value):
        parsed = urlsplit(value)

        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.query
            or parsed.fragment
        ):
            raise serializers.ValidationError(
                "Provide a valid HTTPS GitHub pull request URL."
            )

        import re

        if not re.fullmatch(
            r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9]\d*/?",
            parsed.path,
        ):
            raise serializers.ValidationError(
                "URL must point to a GitHub pull request."
            )

        return value