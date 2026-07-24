from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK_PACKAGE = ROOT / "src" / "l9_debt_resolver" / "sdk"


def test_resolver_does_not_generate_SDK_IDs() -> None:
    prohibited_prefixes = (
        'namespaced_identity("snapshot_',
        'namespaced_identity("finding_',
        'namespaced_identity("entity_',
        'namespaced_identity("source_location_',
        'namespaced_identity("validation_plan_',
        'namespaced_identity("validation_result_',
    )
    for path in SDK_PACKAGE.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for prefix in prohibited_prefixes:
            assert prefix not in content, (
                f"{path} generates SDK-owned identity {prefix}"
            )
