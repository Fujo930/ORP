"""Tests for ORP evidence"""

from orp.evidence import (
    compute_hash, redact_text, redact_sensitive_fields,
    infer_trust_level, make_evidence_ref,
)
from orp.schema import TrustLevel


def test_compute_hash():
    h = compute_hash("hello")
    assert h.startswith("sha256:")


def test_redact_api_key():
    text = "api_key=sk-1234567890abcdef"
    result = redact_text(text)
    assert "sk-1234567890abcdef" not in result
    assert "REDACTED" in result


def test_redact_jwt():
    text = "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    result = redact_text(text)
    assert "eyJ" not in result
    assert "REDACTED" in result


def test_redact_sensitive_dict():
    data = {"name": "test", "api_key": "sk-12345", "nested": {"token": "abc"}}
    result = redact_sensitive_fields(data)
    assert result["api_key"] == "***REDACTED***"
    assert result["nested"]["token"] == "***REDACTED***"
    assert result["name"] == "test"


def test_infer_trust_level():
    assert infer_trust_level([], "agent") == TrustLevel.ASSERTED
    assert infer_trust_level(["ref:1"], "tool") == TrustLevel.OBSERVED
    assert infer_trust_level(["ref:1"], "human") == TrustLevel.HUMAN_CONFIRMED


def test_make_evidence_ref():
    ref = make_evidence_ref("file://test.txt", "content")
    assert ref.uri == "file://test.txt"
    assert ref.digest is not None
    assert ref.digest.startswith("sha256:")
