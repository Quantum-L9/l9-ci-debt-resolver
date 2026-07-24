from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
ALLOWED_RAW_LOG_MODULES = {
    (SOURCE / "acquisition" / "redaction.py").resolve(),
    (SOURCE / "providers" / "github" / "provider.py").resolve(),
}
PROHIBITED_PERSISTENCE_TERMS = (
    "raw.log",
    "unredacted.log",
    "raw_log_path",
    "persist_raw_log",
)


def test_raw_log_persistence_is_absent() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(encoding="utf-8").lower()
        for term in PROHIBITED_PERSISTENCE_TERMS:
            assert term not in content, (
                f"{path} contains prohibited raw-log persistence term {term}"
            )


def test_store_only_persists_redacted_log() -> None:
    path = SOURCE / "acquisition" / "store.py"
    content = path.read_text(encoding="utf-8")
    assert '"redacted.log"' in content
    assert '"raw.log"' not in content
