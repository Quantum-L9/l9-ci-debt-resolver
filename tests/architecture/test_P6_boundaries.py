from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/l9_debt_resolver"
PROHIBITED = (
    "pr_repair.push",
    "pr_repair.merge",
    "pr_repair.commit",
    "pr_repair.execute",
    "automatic_merge",
    "merge_pull_request",
    "create_subprocess_shell",
    "shell=true",
)
PROHIBITED_PRIVATE_IMPORTS = (
    "pr_repair.internal",
    "pr_repair.private",
)


def test_PR_Repair_has_no_remote_authority() -> None:
    delegation = SOURCE / "delegation"
    for path in delegation.rglob("*.py"):
        content = path.read_text(encoding="utf-8").lower()
        for term in PROHIBITED:
            assert term not in content, (
                f"{path} contains prohibited delegation authority {term}"
            )


def test_no_private_PR_Repair_imports() -> None:
    for path in SOURCE.rglob("*.py"):
        content = path.read_text(encoding="utf-8").lower()
        for term in PROHIBITED_PRIVATE_IMPORTS:
            assert term not in content, (
                f"{path} imports private PR_Repair module {term}"
            )


def test_delegation_transport_has_no_shell() -> None:
    for path in (SOURCE / "delegation").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        assert "subprocess" not in content
        assert "os.system" not in content
