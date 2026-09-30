from dataclasses import dataclass
from typing import Optional


@dataclass
class Finding:
    agent: str
    filePath: str
    line: Optional[int]
    severity: str
    confidence: float
    message: str