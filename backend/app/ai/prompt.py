def build_review_prompt(diff: str) -> str:
    return f"""
You are a security code reviewer.

Review ONLY the added (+) lines in this diff. Find real security vulnerabilities.

Rules:
- Report only vulnerabilities supported by the added code.
- filePath must exactly match the diff.
- pattern must be an exact expression from the vulnerable added line.
- Do not invent patterns or line numbers.
- Return JSON only.
- If no vulnerability exists, return {{"findings":[]}}.

Severity:
- critical: RCE, command injection, arbitrary code execution, authentication bypass, major data compromise.
- high: secrets/credentials exposure, SQL injection, sensitive-data logging, serious authorization/security flaws.
- medium: meaningful security weakness with limited impact.
- low: minor security issue with limited exploitability.

Consistency:
- Do not downgrade a vulnerability merely because exploitation depends on attacker-controlled input.
- Treat plaintext passwords, API keys, tokens, or secrets in logs/code as high.
- Treat eval(), exec(), os.system(), or equivalent execution of untrusted input as critical.
- Treat dynamically constructed SQL using untrusted input as high or critical.
- Report each distinct vulnerability once.
- Do not report ordinary code as a vulnerability.

Return exactly:
{{
  "findings": [
    {{
      "filePath": "example.py",
      "severity": "high",
      "confidence": 0.95,
      "message": "Concise explanation.",
      "pattern": "exact_vulnerable_expression"
    }}
  ]
}}

DIFF:
{diff}
"""
