
from rest_framework.throttling import UserRateThrottle


class CodeReviewRateThrottle(UserRateThrottle):
    scope = "code_review"
