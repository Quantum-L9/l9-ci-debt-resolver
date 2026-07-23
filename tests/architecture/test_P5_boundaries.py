from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED = (
    "raw_log",
    "patch_body",
    "diff_body",
    "developer_email",
    "github_actor",
    "automatic_merge",
    "merge_pull_request",
    "l9_debt_intelligence.internal",
    "l9_debt_intelligence.private",
)


def test_feedback_runtime_has_no_prohibited_payload_fields() -> None:
    feedback = SOURCE / "feedback"
    exemptions = {
        "privacy.py",
    }
    for path in feedback.rglob("*.py"):
        if path.name in exemptions:
            continue
        content = path.read_text(encoding="utf-8").lower()
        for term in PROHIBITED:
            assert term not in content, (
                f"{path} contains prohibited feedback term {term}"
            )


def test_no_private_intelligence_imports() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(encoding="utf-8").lower()
        assert "l9_debt_intelligence.internal" not in content
        assert "l9_debt_intelligence.private" not in content
