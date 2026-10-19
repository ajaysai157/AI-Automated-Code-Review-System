
from app.ai.prompt import build_review_prompt


def test_security_prompt_has_security_focus():
    prompt = build_review_prompt("diff", "security").lower()
    assert "injection" in prompt
    assert "authorization" in prompt


def test_performance_prompt_has_performance_focus():
    prompt = build_review_prompt("diff", "performance").lower()
    assert "inefficient algorithms" in prompt
    assert "database queries" in prompt


def test_test_coverage_prompt_has_testing_focus():
    prompt = build_review_prompt("diff", "test_coverage").lower()
    assert "edge cases" in prompt
    assert "assertions" in prompt


def test_general_prompt_is_default():
    assert build_review_prompt("diff") == build_review_prompt(
        "diff", "general"
    )
