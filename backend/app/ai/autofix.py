
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def generate_patch(
    finding: dict,
    source_code: str,
) -> str | None:
    prompt = f"""
You are a security-focused code repair assistant.

Fix only the specific issue described below.
Preserve unrelated code and existing behavior.
Do not add explanations or Markdown fences.

Finding:
{finding["message"]}

File:
{finding["file_path"]}

Affected line:
{finding.get("line")}

Source code:
{source_code}

Return the complete corrected file content only.
"""

    try:
        response = client.models.generate_content(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-3.5-flash-lite",
            ),
            contents=prompt,
        )

        if not response.text:
            return None

        return response.text.strip()

    except Exception as e:
        print(f"Patch generation failed: {e}")
        return None
