"""Build a resolver knowledge document from a public SDK finding bundle.

DECISION-005: `l9.sdk-knowledge-document/v1` is resolver-owned. The SDK does not
emit it and is not asked to. The document is resolver-shaped and
resolver-consumed -- `DocumentSDKKnowledgeProvider` turns it into snapshots,
repository entities, related tests, contract references and finding
correlations, which are resolver concepts. Asking `l9-ci-sdk` to emit it would
widen the SDK from a producer of canonical facts into a producer of a
resolver-specific semantic index.

So the projection belongs here, and this module is it:

    l9.finding-bundle/v1  (public SDK artifact)
    + repository identity (the bundle does not name it)
    + optional resolver-side repository context
    -> l9.sdk-knowledge-document/v1
    -> DocumentSDKKnowledgeProvider

Boundary
--------
Public artifacts only. This reads a finding bundle as a JSON document, the same
way any other consumer would; it imports nothing from `l9_ci`, vendors no SDK
schema, and rejects a document whose contract token it does not recognise rather
than guessing at the shape.

Honesty about what a finding bundle does not contain
----------------------------------------------------
A finding bundle records where a scanner matched, not how the repository is
structured. It has no symbol table, no test graph and no contract inventory. So
entities come out at file granularity, tests come out empty, and both facts are
recorded as limitations on the snapshot rather than filled in with guesses. A
resolver-side scan can enrich them later; a fabricated symbol would be worse
than an absent one, because the correlation step would then attribute a failure
to a function that was never proven to exist.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import SDKContractError

#: The one producer contract this projection understands. A bundle declaring
#: anything else is refused: the resolver's own registry sets
#: `unknown_sdk_contract_behavior: reject`, and inferring a shape from an
#: unrecognised token is how a consumer silently starts reading a contract it
#: was never written for.
SUPPORTED_PRODUCER_CONTRACT = "l9.finding-bundle/v1"
SCHEMA_VERSION = "l9.sdk-knowledge-document/v1"
SDK_INTEGRATION_CONTRACT = "l9.integration-contract/v1"

_FILE_ENTITY_KIND = "file"
_SDK_CONTRACT_KIND = "sdk_integration_contract"

#: Extension to language, used only to report a capability profile for files the
#: bundle actually names. Nothing is inferred for an unrecognised extension.
_LANGUAGE_BY_SUFFIX: Mapping[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
}


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return list(value)
    return []


def _entity_id(path: str) -> str:
    return f"entity:file:{path}"


def _language_for(path: str) -> str | None:
    return _LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower())


def _locations(item: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        location
        for location in _sequence(item.get("locations"))
        if isinstance(location, Mapping)
    ]


def _paths(item: Mapping[str, Any]) -> list[str]:
    seen: list[str] = []
    for location in _locations(item):
        path = _text(location.get("normalized_path"))
        if path is not None and path not in seen:
            seen.append(path)
    return seen


class FindingBundleKnowledgeAdapter:
    """Project one public SDK finding bundle onto the resolver's document."""

    def build(
        self,
        bundle: Mapping[str, Any],
        *,
        repository: str,
        repository_root: Path | None = None,
    ) -> dict[str, Any]:
        """Return the knowledge document for ``bundle``.

        ``repository`` is required from the caller because a finding bundle does
        not name the repository it scanned -- `snapshot.repository_root` is a
        local filesystem path, not an identity -- and the resolver's own
        correlation is keyed on `owner/name`.
        """
        contract = _text(bundle.get("schema"))
        if contract != SUPPORTED_PRODUCER_CONTRACT:
            raise SDKContractError(
                f"unsupported SDK producer contract: {contract!r}; "
                f"this projection reads {SUPPORTED_PRODUCER_CONTRACT} only"
            )

        snapshot = bundle.get("snapshot")
        if not isinstance(snapshot, Mapping):
            raise SDKContractError("SDK finding bundle has no snapshot object")
        revision = _text(snapshot.get("revision"))
        if revision is None:
            raise SDKContractError("SDK finding bundle snapshot has no revision")
        snapshot_id = _text(snapshot.get("snapshot_id")) or revision

        findings = [
            item
            for item in _sequence(bundle.get("findings"))
            if isinstance(item, Mapping)
        ]
        evidence = [
            item
            for item in _sequence(bundle.get("evidence"))
            if isinstance(item, Mapping)
        ]

        entities, entity_limitations = self._entities(findings, evidence)
        projected, finding_limitations = self._findings(findings)
        tests, test_limitations = self._tests(repository_root)

        limitations = sorted(
            {
                *(str(item) for item in _sequence(bundle.get("limitations"))),
                *entity_limitations,
                *finding_limitations,
                *test_limitations,
            }
        )

        return {
            "schema_version": SCHEMA_VERSION,
            "repository": repository,
            "revision": revision,
            "snapshot": {
                "snapshot_id": snapshot_id,
                "repository": repository,
                "revision": revision,
                "capability_profile": self._capability_profile(entities),
                "limitations": limitations,
            },
            "entities": entities,
            "tests": tests,
            "contracts": self._contracts(bundle, entities),
            "findings": projected,
        }

    def build_from_path(
        self,
        path: Path,
        *,
        repository: str,
        repository_root: Path | None = None,
    ) -> dict[str, Any]:
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise SDKContractError("SDK finding bundle must be an object")
        return self.build(
            document,
            repository=repository,
            repository_root=repository_root,
        )

    def _entities(
        self,
        findings: list[Mapping[str, Any]],
        evidence: list[Mapping[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """One file-level entity per path the bundle names.

        Line bounds are deliberately absent. `resolve_repository_entities`
        skips the range check when they are, so a stack frame anywhere in a
        named file attributes to it -- which is what a bundle actually
        supports. Emitting a finding's own line span as the entity bound would
        be narrower and wrong: a failure rarely occurs on the same line as the
        static finding, so the frame would match nothing.
        """
        paths: list[str] = []
        for item in [*findings, *evidence]:
            for path in _paths(item):
                if path not in paths:
                    paths.append(path)

        entities = [
            {
                "entity_id": _entity_id(path),
                "kind": _FILE_ENTITY_KIND,
                "path": path,
                "start_line": None,
                "end_line": None,
                "symbol": None,
                "language": _language_for(path),
                "metadata": {"source": "sdk_finding_bundle_locations"},
            }
            for path in sorted(paths)
        ]
        limitations = [
            "SDK knowledge entities are file-level: a finding bundle carries no "
            "symbol structure, so no function or class boundaries were inferred"
        ]
        if not entities:
            limitations.append(
                "SDK finding bundle named no source locations; no entities were derived"
            )
        return entities, limitations

    def _tests(
        self,
        repository_root: Path | None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Empty, and said so.

        A finding bundle has no test graph. `find_related_tests` therefore
        returns nothing and the resolver's correlation records
        `related_test_count: 0`, which is true. Resolver-side test discovery can
        populate this later; inventing a related test would make the
        classification cite evidence that does not exist.
        """
        if repository_root is None:
            return [], [
                "no repository context supplied; related tests are unknown and "
                "the tests list is empty"
            ]
        return [], [
            "resolver-side test discovery is not implemented; related tests are "
            "unknown and the tests list is empty"
        ]

    def _contracts(
        self,
        bundle: Mapping[str, Any],
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """The one contract a finding bundle actually evidences.

        The SDK integration contract governs the whole snapshot, so every
        derived entity is a subject of it. No repository-level contract
        inventory is claimed, because a finding bundle contains none.
        """
        metadata: dict[str, Any] = {
            "producer_contract": SUPPORTED_PRODUCER_CONTRACT,
            "source": "sdk_finding_bundle",
        }
        sdk_version = _text(bundle.get("SDK_version"))
        if sdk_version is not None:
            metadata["sdk_version"] = sdk_version
        providers = [
            _text(item.get("provider_id"))
            for item in _sequence(bundle.get("providers"))
            if isinstance(item, Mapping)
        ]
        known = sorted({value for value in providers if value is not None})
        if known:
            metadata["provider_ids"] = known
        return [
            {
                "contract_id": SDK_INTEGRATION_CONTRACT,
                "kind": _SDK_CONTRACT_KIND,
                "subject_entity_ids": [entity["entity_id"] for entity in entities],
                "metadata": metadata,
            }
        ]

    def _findings(
        self,
        findings: list[Mapping[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        projected: list[dict[str, Any]] = []
        provider_rule_fallbacks = 0
        skipped = 0

        for item in findings:
            finding_id = _text(item.get("finding_id"))
            severity = _text(item.get("severity"))
            canonical = _text(item.get("canonical_rule_id"))
            provider_rule = _text(item.get("provider_rule_id"))
            rule_id = canonical or provider_rule
            if finding_id is None or severity is None or rule_id is None:
                # Refuse to invent an identity for a finding that has none.
                skipped += 1
                continue
            if canonical is None:
                provider_rule_fallbacks += 1

            metadata: dict[str, Any] = {
                "rule_id_source": (
                    "canonical_rule_id" if canonical is not None else "provider_rule_id"
                ),
            }
            for key in ("category", "confidence", "fingerprint", "provider_id"):
                value = _text(item.get(key))
                if value is not None:
                    metadata[key] = value
            if canonical is not None:
                metadata["canonical_rule_id"] = canonical
            if provider_rule is not None:
                metadata["provider_rule_id"] = provider_rule

            projected.append(
                {
                    "finding_id": finding_id,
                    "rule_id": rule_id,
                    "severity": severity,
                    "entity_ids": [_entity_id(path) for path in _paths(item)],
                    "evidence_ids": sorted(
                        {
                            value
                            for value in (
                                _text(entry)
                                for entry in _sequence(item.get("evidence_ids"))
                            )
                            if value is not None
                        }
                    ),
                    "metadata": metadata,
                }
            )

        limitations: list[str] = []
        if provider_rule_fallbacks:
            limitations.append(
                f"{provider_rule_fallbacks} finding(s) had no canonical rule id; "
                "the provider rule id was used as the resolver rule identity"
            )
        if skipped:
            limitations.append(
                f"{skipped} finding(s) lacked an identity, severity or rule and "
                "were not projected"
            )
        return sorted(
            projected, key=lambda value: str(value["finding_id"])
        ), limitations

    def _capability_profile(
        self,
        entities: list[dict[str, Any]],
    ) -> list[str]:
        return sorted(
            {
                str(entity["language"])
                for entity in entities
                if entity.get("language") is not None
            }
        )
