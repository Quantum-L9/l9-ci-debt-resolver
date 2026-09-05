"""Project an acquired failed-job log onto `l9.evidence-bundle/v1`.

The gap this closes
-------------------
`acquire-github-run` emitted `l9.acquisition-report/v1` and `correlate-classify`
consumed `l9.evidence-bundle/v1`, and nothing converted one into the other. The
two shapes are not variants of each other:

- the report carries a *list* of evidence, one entry per failed job; the bundle
  describes exactly *one*;
- the report carries `log_sha256` and `log_size_bytes` and deliberately no log
  body; the bundle *requires* `redacted_log`, because correlation reads stack
  frames out of it;
- the report carries `failed_job_count`; the bundle requires the `failed_job`
  object itself;
- the report names no revision; the bundle requires one.

So there was no path from the resolver's own acquisition output to its own
classification input, which is why the Resolver -> Intelligence seam could not be
established even with acquisition working: `correlate-classify` needs a
ClassificationTrace input that acquisition could not produce.

Everything the bundle needs is already in hand at acquisition time --
`FailedRun.head_sha` is the revision, `AcquiredLog.redacted_text` is the body,
and the `FailedJob` that produced each log is the loop variable. The report
projection simply dropped all three. This module builds the bundle from those
values at the one point in the process where the log body exists without
re-fetching it.

Completeness gate
-----------------
Only evidence assessed `complete` becomes a bundle. Classifying against a
truncated log yields a category derived from bytes the provider never sent,
and the resolver's terminal state already refuses to call such acquisition
`evidence_ready`. Skipped jobs are reported as limitations rather than silently
omitted.

Locality
--------
A bundle carries the redacted log body and real repository-relative paths,
because correlation matches stack frames against them. It is resolver-internal
classification input, never delivery output -- the artifact the resolver
publishes is `l9.intelligence-feedback-event/v1`, which carries pseudonyms,
fingerprints and bucketed magnitudes and is validated by `feedback.privacy`
before it leaves. Nothing here may be routed to a consumer of that event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts.models import CIRunEvidence
from .models import AcquiredLog, FailedJob

SCHEMA_VERSION = "l9.evidence-bundle/v1"

#: The one completeness verdict that may be classified against.
#: `assess_log_completeness` returns `possibly_truncated` when it cannot prove
#: the tail arrived, and a classification drawn from a partial log is a guess
#: wearing a receipt.
_CLASSIFIABLE_COMPLETENESS = "complete"


@dataclass(frozen=True)
class BundleProjection:
    """Bundles built for one acquisition, plus what was left out and why."""

    bundles: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]

    def as_index(self) -> dict[str, Any]:
        """A manifest of what was projected.

        `l9.acquisition-report/v1` is `additionalProperties: false`, so the
        emitted paths cannot be added to the report. They are recorded beside
        the bundles instead.
        """
        return {
            "schema_version": "l9.evidence-bundle-index/v1",
            "bundle_count": len(self.bundles),
            "evidence_ids": [
                str(bundle["evidence"]["evidence_id"]) for bundle in self.bundles
            ],
            "limitations": list(self.limitations),
        }


def build_evidence_bundle(
    *,
    repository: str,
    revision: str,
    evidence: CIRunEvidence,
    redacted_log: str,
    failed_job: FailedJob,
) -> dict[str, Any]:
    """One `l9.evidence-bundle/v1` document.

    `evidence` and `failed_job` are serialised through their own `as_dict`,
    which is the same projection the acquisition report uses -- the bundle does
    not re-describe either shape, so a change to `l9.ci-run-evidence/v1` or
    `l9.failed-job/v1` cannot leave this module behind.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "revision": revision,
        "evidence": evidence.as_dict(),
        "redacted_log": redacted_log,
        "failed_job": failed_job.as_dict(),
    }


def project_bundles(
    *,
    repository: str,
    revision: str,
    pairs: tuple[tuple[FailedJob, AcquiredLog], ...],
) -> BundleProjection:
    """Build one bundle per complete acquired log, in evidence-id order."""
    bundles: list[dict[str, Any]] = []
    skipped: list[str] = []
    empty: list[str] = []

    for job, acquired in sorted(
        pairs,
        key=lambda pair: (
            pair[1].evidence.run_id,
            pair[1].evidence.job_id,
            pair[1].evidence.evidence_id,
        ),
    ):
        item = acquired.evidence
        if item.log_completeness != _CLASSIFIABLE_COMPLETENESS:
            skipped.append(item.job_name)
            continue
        if not acquired.redacted_text:
            # The schema sets `redacted_log` minLength 1. A complete assessment
            # over zero bytes is a contradiction, so it is reported rather than
            # written as an invalid bundle.
            empty.append(item.job_name)
            continue
        bundles.append(
            build_evidence_bundle(
                repository=repository,
                revision=revision,
                evidence=item,
                redacted_log=acquired.redacted_text,
                failed_job=job,
            )
        )

    limitations: list[str] = []
    if skipped:
        limitations.append(
            f"{len(skipped)} failed job(s) were not projected to an evidence "
            "bundle because their logs are not assessed complete: "
            + ", ".join(sorted(skipped))
        )
    if empty:
        limitations.append(
            f"{len(empty)} failed job(s) assessed complete but carry an empty "
            "redacted log and were not projected: " + ", ".join(sorted(empty))
        )
    if not bundles:
        limitations.append(
            "no evidence bundle could be projected; correlate-classify has no "
            "input from this acquisition"
        )
    return BundleProjection(
        bundles=tuple(bundles),
        limitations=tuple(limitations),
    )
