"""DECISION-005: the resolver builds its own knowledge document.

`l9.sdk-knowledge-document/v1` is resolver-owned. `l9-ci-sdk` does not emit it,
its README says so, and it is not asked to -- the document projects public SDK
artifacts onto resolver concepts, so asking the SDK for it would widen the SDK
from a producer of canonical facts into a producer of a resolver-specific
semantic index.

`tests/fixtures/sdk/native-finding-bundle.json` is not hand-written. It is the
bundle the Core-provisioned SDK produced from a real Semgrep 1.176.1 scan of
Quantum-L9/PR_Repair@edeef6dc, trimmed to its first two findings and the
evidence they reference and otherwise carried over unmodified.

The load-bearing assertion is `test_the_document_is_accepted_by_the_consumer`:
a projection that validates against the schema but that
`DocumentSDKKnowledgeProvider` refuses would be no wire at all.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from l9_debt_resolver.contracts.schema import SchemaValidator, schema_root
from l9_debt_resolver.correlation.models import StackFrame
from l9_debt_resolver.sdk.document_adapter import DocumentSDKKnowledgeProvider
from l9_debt_resolver.sdk.errors import SDKContractError
from l9_debt_resolver.sdk.finding_bundle_adapter import (
    FindingBundleKnowledgeAdapter,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "tests/fixtures/sdk/native-finding-bundle.json"
REPOSITORY = "Quantum-L9/PR_Repair"
REVISION = "edeef6dcc316ec79b2f672ec2c827083f4035656"


def _bundle() -> dict[str, Any]:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def _document(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"repository": REPOSITORY}
    kwargs.update(overrides)
    return FindingBundleKnowledgeAdapter().build(_bundle(), **kwargs)


class TestPremise:
    def test_the_fixture_is_a_real_sdk_bundle(self) -> None:
        """If this stops holding, the adapter is projecting something else."""
        bundle = _bundle()
        assert bundle["schema"] == "l9.finding-bundle/v1"
        assert bundle["snapshot"]["revision"] == REVISION
        assert bundle["findings"], "fixture must carry findings"
        assert bundle["providers"][0]["provider_version"] == "1.176.1"

    def test_the_sdk_does_not_emit_this_token(self) -> None:
        """The premise of DECISION-005, asserted against the bundle itself.

        A finding bundle declares `l9.finding-bundle/v1`. If the SDK ever did
        emit the knowledge document, this projection would be redundant and
        should be removed rather than left to compete with the producer.
        """
        assert _bundle()["schema"] != "l9.sdk-knowledge-document/v1"


class TestProjection:
    def test_the_document_declares_the_resolver_contract(self) -> None:
        document = _document()
        assert document["schema_version"] == "l9.sdk-knowledge-document/v1"
        assert document["repository"] == REPOSITORY
        assert document["revision"] == REVISION

    def test_the_document_validates_against_the_resolver_schema(self) -> None:
        """This could not be asserted before.

        The schema referenced l9://sdk/repository-snapshot/v1,
        l9://sdk/repository-entity/v1, l9://sdk/contract-reference/v1 and
        l9://sdk/finding/v1 -- URIs no schema anywhere declares -- so
        validation raised Unresolvable and `l9-debt-resolver validate
        sdk-knowledge-document` had never been able to run.
        """
        SchemaValidator(schema_root() / "sdk-knowledge-document.schema.json").validate(
            _document()
        )

    def test_entities_come_from_the_locations_the_bundle_names(self) -> None:
        bundle = _bundle()
        paths = {
            location["normalized_path"]
            for collection in ("findings", "evidence")
            for item in bundle[collection]
            for location in item["locations"]
        }
        document = _document()
        assert {entity["path"] for entity in document["entities"]} == paths
        assert all(entity["kind"] == "file" for entity in document["entities"])

    def test_entities_have_no_line_bounds_and_that_is_deliberate(self) -> None:
        """A frame anywhere in a named file must attribute to it.

        `resolve_repository_entities` skips the range check when bounds are
        absent. Using a finding's own line span as the bound would be narrower
        and wrong: a runtime failure rarely lands on the same line as a static
        finding, so the frame would match nothing at all.
        """
        for entity in _document()["entities"]:
            assert entity["start_line"] is None
            assert entity["end_line"] is None
            assert entity["symbol"] is None

    def test_the_rule_identity_prefers_the_canonical_rule_id(self) -> None:
        for finding in _document()["findings"]:
            assert finding["metadata"]["rule_id_source"] == "canonical_rule_id"
            assert finding["rule_id"] == finding["metadata"]["canonical_rule_id"]

    def test_the_provider_rule_id_is_the_documented_fallback(self) -> None:
        bundle = _bundle()
        for finding in bundle["findings"]:
            del finding["canonical_rule_id"]
        document = FindingBundleKnowledgeAdapter().build(bundle, repository=REPOSITORY)
        for finding in document["findings"]:
            assert finding["metadata"]["rule_id_source"] == "provider_rule_id"
            assert finding["rule_id"] == finding["metadata"]["provider_rule_id"]
        assert any(
            "no canonical rule id" in item
            for item in document["snapshot"]["limitations"]
        ), document["snapshot"]["limitations"]

    def test_findings_are_correlated_to_their_entities(self) -> None:
        document = _document()
        entity_ids = {entity["entity_id"] for entity in document["entities"]}
        for finding in document["findings"]:
            assert finding["entity_ids"]
            assert set(finding["entity_ids"]) <= entity_ids

    def test_the_capability_profile_is_observed_not_assumed(self) -> None:
        assert _document()["snapshot"]["capability_profile"] == ["python"]

    def test_the_projection_is_deterministic(self) -> None:
        assert _document() == _document()


class TestHonestyAboutWhatIsMissing:
    def test_tests_are_empty_and_the_reason_is_recorded(self) -> None:
        """A finding bundle has no test graph.

        Inventing a related test would make the classification cite evidence
        that does not exist.
        """
        document = _document()
        assert document["tests"] == []
        assert any(
            "related tests are unknown" in item
            for item in document["snapshot"]["limitations"]
        ), document["snapshot"]["limitations"]

    def test_file_level_entity_granularity_is_recorded(self) -> None:
        assert any(
            "file-level" in item for item in _document()["snapshot"]["limitations"]
        )

    def test_only_the_contract_the_bundle_evidences_is_claimed(self) -> None:
        """No repository contract inventory: a bundle contains none."""
        contracts = _document()["contracts"]
        assert len(contracts) == 1
        assert contracts[0]["contract_id"] == "l9.integration-contract/v1"
        assert contracts[0]["metadata"]["provider_ids"] == ["semgrep"]

    def test_a_finding_without_an_identity_is_dropped_not_invented(self) -> None:
        bundle = _bundle()
        del bundle["findings"][0]["severity"]
        document = FindingBundleKnowledgeAdapter().build(bundle, repository=REPOSITORY)
        assert len(document["findings"]) == len(bundle["findings"]) - 1
        assert any(
            "were not projected" in item for item in document["snapshot"]["limitations"]
        )

    def test_producer_limitations_are_carried_not_dropped(self) -> None:
        bundle = _bundle()
        bundle["limitations"] = ["provider coverage was partial"]
        document = FindingBundleKnowledgeAdapter().build(bundle, repository=REPOSITORY)
        assert "provider coverage was partial" in document["snapshot"]["limitations"]


class TestBoundary:
    def test_an_unknown_producer_contract_is_refused(self) -> None:
        """`unknown_sdk_contract_behavior: reject`, per the resolver's registry."""
        bundle = _bundle()
        bundle["schema"] = "l9.finding-bundle/v2"
        with pytest.raises(SDKContractError, match="unsupported SDK producer contract"):
            FindingBundleKnowledgeAdapter().build(bundle, repository=REPOSITORY)

    def test_a_bundle_without_a_revision_is_refused(self) -> None:
        """A document with no exact revision cannot be bound to a snapshot."""
        bundle = _bundle()
        del bundle["snapshot"]["revision"]
        with pytest.raises(SDKContractError, match="no revision"):
            FindingBundleKnowledgeAdapter().build(bundle, repository=REPOSITORY)

    def test_the_adapter_imports_nothing_from_the_sdk(self) -> None:
        """Public artifacts only: no private SDK imports, no vendored schema."""
        source = (
            ROOT / "src/l9_debt_resolver/sdk/finding_bundle_adapter.py"
        ).read_text(encoding="utf-8")
        for prohibited in ("import l9_ci", "from l9_ci"):
            assert prohibited not in source

    def test_no_sdk_schema_is_vendored_into_the_resolver(self) -> None:
        """The sub-shapes are the resolver's own, not copies.

        There is no SDK schema of any of the four names the document used to
        reference; the SDK publishes under https://schemas.quantum-l9.dev/.
        """
        for path in (schema_root()).glob("*.json"):
            document = json.loads(path.read_text(encoding="utf-8"))
            assert not str(document.get("$id", "")).startswith(
                "https://schemas.quantum-l9.dev/"
            ), path


class TestConsumerAcceptance:
    def test_the_document_is_accepted_by_the_consumer(self) -> None:
        """The assertion that makes this a wire and not a shape.

        A projection the real consumer refuses would prove nothing, however
        well it validated.
        """
        provider = DocumentSDKKnowledgeProvider(_document())
        snapshot = asyncio.run(
            provider.open_repository_snapshot(
                repository=REPOSITORY,
                revision=REVISION,
            )
        )
        assert snapshot.repository == REPOSITORY
        assert snapshot.revision == REVISION
        assert snapshot.capability_profile == ("python",)

    def test_a_real_stack_frame_resolves_to_a_real_entity(self) -> None:
        document = _document()
        provider = DocumentSDKKnowledgeProvider(document)
        snapshot_id = document["snapshot"]["snapshot_id"]
        path = document["entities"][0]["path"]
        # Line 4211 is deliberately nowhere near any finding's span: a runtime
        # frame rarely lands on the line a static finding matched, and it must
        # still attribute to the file.
        entities = asyncio.run(
            provider.resolve_repository_entities(
                snapshot_id=snapshot_id,
                locations=(
                    StackFrame(
                        frame_id="frame-1",
                        path=path,
                        line=4211,
                        column=None,
                        symbol_hint=None,
                        language_family="python",
                        log_line_number=1,
                        confidence=1.0,
                        limitations=(),
                    ),
                ),
            )
        )
        assert [entity.path for entity in entities] == [path]

    def test_findings_correlate_through_the_consumer(self) -> None:
        document = _document()
        provider = DocumentSDKKnowledgeProvider(document)
        snapshot_id = document["snapshot"]["snapshot_id"]
        entity_id = document["findings"][0]["entity_ids"][0]
        findings = asyncio.run(
            provider.correlate_findings(
                snapshot_id=snapshot_id,
                entity_ids=(entity_id,),
                evidence_ids=(),
            )
        )
        assert findings
        assert {finding.rule_id for finding in findings} <= {
            "AST-LOGGING-001",
            "L9-PYTHON-BROAD-EXCEPT",
        }

    def test_the_sdk_contract_is_applicable_to_a_derived_entity(self) -> None:
        document = _document()
        provider = DocumentSDKKnowledgeProvider(document)
        contracts = asyncio.run(
            provider.find_applicable_contracts(
                snapshot_id=document["snapshot"]["snapshot_id"],
                entity_ids=(document["entities"][0]["entity_id"],),
            )
        )
        assert [contract.contract_id for contract in contracts] == [
            "l9.integration-contract/v1"
        ]

    def test_related_tests_are_empty_rather_than_failing(self) -> None:
        document = _document()
        provider = DocumentSDKKnowledgeProvider(document)
        tests = asyncio.run(
            provider.find_related_tests(
                snapshot_id=document["snapshot"]["snapshot_id"],
                entity_ids=(document["entities"][0]["entity_id"],),
            )
        )
        assert tests == ()
