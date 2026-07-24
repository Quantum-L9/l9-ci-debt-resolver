from __future__ import annotations

import hashlib
from pathlib import Path

from l9_debt_resolver.classification.models import (
    ClassificationTrace,
)
from l9_debt_resolver.contracts.canonical import (
    namespaced_identity,
)
from l9_debt_resolver.remediation.models import (
    RemediationPlan,
    ReplaceTextOperation,
)
from l9_debt_resolver.remediation.policy import (
    validate_mutable_path,
)

from .errors import DelegationProposalError
from .identity import stable_hash
from .models import (
    PRRepairProposal,
    PRRepairRequest,
)


def convert_proposal_to_remediation_plan(
    *,
    workspace_root: Path,
    request: PRRepairRequest,
    proposal: PRRepairProposal,
    path_token_map: dict[str, str],
    classification_trace: ClassificationTrace,
    repository_snapshot_id: str,
    repository_revision: str,
    validation_plan_id: str,
) -> RemediationPlan:
    if proposal.status != "proposed":
        raise DelegationProposalError("unsupported response cannot be converted")
    classification = classification_trace.classification
    evidence_hash_to_id = {
        stable_hash(evidence_id): evidence_id
        for evidence_id in (classification.evidence_ids)
    }
    operations = []
    for item in proposal.operations:
        path = path_token_map.get(item.path_token)
        if path is None:
            raise DelegationProposalError("path token cannot be resolved")
        validate_mutable_path(path)
        target = (workspace_root.resolve() / path).resolve()
        try:
            target.relative_to(workspace_root.resolve())
        except ValueError as error:
            raise DelegationProposalError("resolved path escapes workspace") from error
        if not target.is_file():
            raise DelegationProposalError(f"proposal target does not exist: {path}")
        file_bytes = target.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        if file_hash != item.expected_file_sha256:
            raise DelegationProposalError(f"proposal file hash mismatch: {path}")
        text = file_bytes.decode("utf-8")
        matching_fragments = [
            candidate
            for candidate in _candidate_fragments(text)
            if hashlib.sha256(candidate.encode("utf-8")).hexdigest()
            == item.expected_text_sha256
        ]
        if len(matching_fragments) != 1:
            raise DelegationProposalError(
                "expected-text hash must identify exactly "
                f"one bounded fragment in {path}"
            )
        evidence_ids = tuple(
            sorted(
                evidence_hash_to_id[value]
                for value in (item.evidence_id_hashes)
                if value in evidence_hash_to_id
            )
        )
        if not evidence_ids:
            raise DelegationProposalError(
                "proposal operation lacks known evidence identity"
            )
        expected_text = matching_fragments[0]
        operation = ReplaceTextOperation(
            operation_id=namespaced_identity(
                "operation_",
                {
                    "proposal_operation_id": (item.operation_id),
                    "path": path,
                    "expected_file_sha256": (item.expected_file_sha256),
                    "expected_text_sha256": (item.expected_text_sha256),
                    "replacement_sha256": (item.replacement_sha256),
                },
            ),
            path=path,
            expected_file_sha256=(item.expected_file_sha256),
            expected_text=expected_text,
            replacement_text=(item.replacement_text),
            replacement_sha256=(item.replacement_sha256),
            evidence_ids=evidence_ids,
            justification=item.justification,
        )
        operations.append(operation)
    expected_paths = tuple(sorted({operation.path for operation in operations}))
    maximum_files = int(request.constraints["maximum_changed_files"])
    if len(expected_paths) > maximum_files:
        raise DelegationProposalError("proposal exceeds changed-file limit")
    plan_material = {
        "proposal_id": proposal.proposal_id,
        "classification_id": (classification.classification_id),
        "failure_fingerprint": (classification.failure_fingerprint),
        "repository_snapshot_id": (repository_snapshot_id),
        "operations": [operation.operation_id for operation in operations],
    }
    return RemediationPlan(
        plan_id=namespaced_identity(
            "remediation_plan_",
            plan_material,
        ),
        classification_id=(classification.classification_id),
        failure_fingerprint=(classification.failure_fingerprint),
        repository_snapshot_id=(repository_snapshot_id),
        repository_revision=(repository_revision),
        remediation_class=(proposal.remediation_class or "bounded_source"),
        evidence_ids=tuple(sorted(classification.evidence_ids)),
        justification=proposal.rationale,
        operations=tuple(operations),
        expected_changed_paths=expected_paths,
        expected_package_boundaries=(),
        expected_contract_ids=tuple(
            sorted(classification_trace.applicable_contract_ids)
        ),
        expected_dependency_edges=(),
        validation_plan_id=validation_plan_id,
        approval=None,
    )


def _candidate_fragments(
    text: str,
) -> tuple[str, ...]:
    lines = text.splitlines(keepends=True)
    candidates = set(lines)
    maximum_window = min(
        20,
        len(lines),
    )
    for window in range(
        2,
        maximum_window + 1,
    ):
        for start in range(
            0,
            len(lines) - window + 1,
        ):
            candidates.add("".join(lines[start : start + window]))
    return tuple(candidates)
