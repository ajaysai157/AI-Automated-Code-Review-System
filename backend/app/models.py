import uuid

from django.db import models
from django.contrib.auth.models import User


class Review(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    run_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    pr_url = models.URLField()
    ai_review_status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.run_id)


class Finding(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="findings"
    )

    agent = models.CharField(max_length=20)

    file_path = models.CharField(max_length=500)

    line = models.IntegerField(
        null=True,
        blank=True
    )

    severity = models.CharField(max_length=20)

    confidence = models.FloatField()

    message = models.TextField()

    def __str__(self):
        return f"{self.severity}: {self.file_path}:{self.line}"


class Autofix(models.Model):
    finding = models.ForeignKey(
        Finding,
        on_delete=models.CASCADE,
        related_name="autofixes"
    )
    patch = models.TextField()
    tests_passed = models.BooleanField(
        null=True,
        blank=True
    )
    applied = models.BooleanField(default=False)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Autofix for finding {self.finding_id}"
