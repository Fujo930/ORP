"""证据管理 — 哈希、引用、可信等级、脱敏"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional

from orp.schema import TrustLevel, EvidenceRef


DEFAULT_REDACTION_PATTERNS: list[tuple[str, str]] = [
    (r'(api[_-]?key|apikey|token|secret|password|passwd|credential)\s*[:=]\s*["\']?[^"\'&\s]+', r'***REDACTED***'),
    (r'(?:(?:sk|pk|ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{10,})', '***REDACTED***'),
    (r'(?:(?:AKIA|ASIA)[0-9A-Z]{16})', '***REDACTED***'),
    (r'(?:\d{4}[-]?\d{4}[-]?\d{4}[-]?\d{4})', '***REDACTED***'),
    (r'(?:eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,})', '***JWT-REDACTED***'),
]


def compute_hash(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def compute_file_hash(path: str) -> Optional[str]:
    try:
        content = Path(path).read_text()
        return compute_hash(content)
    except (FileNotFoundError, IOError):
        return None


def redact_text(text: str, patterns: Optional[list[tuple[str, str]]] = None) -> str:
    """对文本应用脱敏模式"""
    if patterns is None:
        patterns = DEFAULT_REDACTION_PATTERNS
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def redact_sensitive_fields(data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """递归脱敏字典中的敏感字段"""
    SENSITIVE_KEYS = {"api_key", "apiKey", "apikey", "token", "secret", "password", "credential", "private_key"}
    if depth > 10:
        return data
    result = {}
    for k, v in data.items():
        if any(sk in k.lower() for sk in SENSITIVE_KEYS):
            result[k] = "***REDACTED***"
        elif isinstance(v, dict):
            result[k] = redact_sensitive_fields(v, depth + 1)
        elif isinstance(v, str):
            result[k] = redact_text(v)
        else:
            result[k] = v
    return result


def make_evidence_ref(uri: str, content: Optional[str] = None) -> EvidenceRef:
    """创建证据引用，可选带内容哈希"""
    ref = EvidenceRef(
        evidence_id=f"ref_{hashlib.md5(uri.encode()).hexdigest()[:12]}",
        kind="tool_output",
        uri=uri,
    )
    if content:
        ref.digest = compute_hash(content)
    return ref


def infer_trust_level(evidence_refs: list[str], source: str) -> TrustLevel:
    """根据证据引用和来源推断可信等级"""
    if not evidence_refs:
        return TrustLevel.ASSERTED
    if source == "human":
        return TrustLevel.HUMAN_CONFIRMED
    if source == "tool" or source == "system":
        return TrustLevel.OBSERVED
    return TrustLevel.ASSERTED


def canonicalize_evidence_id(raw: str) -> str:
    """规范化证据 ID 格式"""
    raw = raw.strip()
    if raw.startswith("artifact:") or raw.startswith("file:") or raw.startswith("eval:"):
        return raw
    if raw.startswith("sha256:") or raw.startswith("ref_"):
        return raw
    # default to artifact prefix
    return f"artifact:{raw}"
