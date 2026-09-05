"""Project a classification the resolver produced onto a resolution outcome.

`build_feedback_event` needs a `ResolutionOutcome`, and the only thing that
builds one is `remote_resolution_service`, on the remote-rerun path. So a
failure the resolver acquired, classified, and did *not* attempt to repair had
no route to a feedback event at all -- and observing a failure without repairing
it is the resolver's most common state, not an edge case.

That gap is why the Resolver -> Intelligence seam could not be established even
with acquisition and classification both working: the projection existed
(`feedback/builder.py`), and nothing could supply it an outcome.

This module supplies the honest one. A classified-but-unattempted failure is
terminal state `new_failure`: the fingerprint was observed once, no rerun was
requested, no remote operation occurred, and nothing was changed. Every field
that would describe a repair is empty rather than defaulted to something that
reads like a successful no-op, and the outcome carries a limitation saying so,
which travels into the event's own limitations.

What this is not
----------------
It does not synthesise a repair, a rerun, or a validation result. A caller that
has a real `ResolutionOutcome` from the remote path should pass that instead;
this exists so that "observed and classified" is expressible, not so that
"unattempted" can be dressed up as "resolved".
"""

from __future__ import annotations

from l9_debt_resolver.classification.models import ClassificationTrace
from l9_debt_resolver.contracts.canonical import namespaced_identity
from l9_debt_resolver.resolution.models import ResolutionOutcome

#: No rerun was requested, so no rerun conclusion exists to compare against.
#: `determine_terminal_state` would read a missing observed fingerprint as
#: `remote_operation_failed`, which would be a false claim: no remote operation
#: was attempted, so none failed.
OBSERVED_ONLY_TERMINAL_STATE = "new_failure"

OBSERVED_ONLY_LIMITATION = (
    "no resolution was attempted: this event reports an observed and classified "
    "failure only, so remediation, rerun and validation fields carry no outcome"
)


def observed_failure_outcome(
    *,
    classification: ClassificationTrace,
    repository: str,
    run_id: str,
    branch: str,
) -> ResolutionOutcome:
    """The outcome of having observed a failure and gone no further.

    `observed_failure_fingerprint` is the classification's own fingerprint
    rather than `None`. The fingerprint *was* observed -- in the acquired log
    this classification came from -- and `None` in that field means "a rerun
    happened and produced nothing to compare", which is not what occurred.
    Keeping it equal to the original also makes
    `failure.observed_fingerprint_changed` come out `False`, which is true.
    """
    identity = {
        "repository": repository,
        "run_id": run_id,
        "classification_id": classification.classification_id,
        "failure_fingerprint": classification.failure_fingerprint,
    }
    return ResolutionOutcome(
        outcome_id=namespaced_identity("outcome_", identity),
        attempt_id=namespaced_identity("attempt_", identity),
        terminal_state=OBSERVED_ONLY_TERMINAL_STATE,
        original_failure_fingerprint=classification.failure_fingerprint,
        observed_failure_fingerprint=classification.failure_fingerprint,
        repository=repository,
        branch=branch,
        commit_sha=None,
        original_run_id=run_id,
        rerun_id=None,
        evidence_ids=tuple(classification.evidence_ids),
        limitations=(OBSERVED_ONLY_LIMITATION,),
    )
