"""Offline adapter checks: provenance, failure handling, and pinned config shape."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pandas as pd

from aurevion_knowledge_lab import graphrag_runner as runner


def index_tables():
    return {
        "documents": pd.DataFrame([
            {"id": "paper-a", "title": "Paper A", "raw_data": {"pmcid": "PMC123", "license": "CC-BY"}},
            {"id": "paper-b", "title": "Paper B", "raw_data": '{"pmcid":"PMC456"}'},
        ]),
        "text_units": pd.DataFrame([
            {"id": "unit-uuid-a", "human_readable_id": 17, "document_id": "paper-a"},
            {"id": "unit-uuid-b", "human_readable_id": 42, "document_id": "paper-b"},
        ]),
        "entities": pd.DataFrame([
            {"id": "entity-uuid", "human_readable_id": 3, "text_unit_ids": ["unit-uuid-a", "unit-uuid-b"]},
        ]),
        "relationships": pd.DataFrame([
            {"id": "relationship-uuid", "human_readable_id": 23, "text_unit_ids": ["unit-uuid-b"]},
            {"id": "relationship-partial", "human_readable_id": 24, "text_unit_ids": ["unit-uuid-b", "missing-unit"]},
        ]),
        "communities": pd.DataFrame([
            {"id": "community-uuid", "community": 2, "text_unit_ids": ["unit-uuid-a", "unit-uuid-b"]},
        ]),
        "community_reports": pd.DataFrame([
            {"id": "report-uuid", "human_readable_id": 901, "community": 2, "title": "Generated report"},
        ]),
    }


class ProvenanceTests(unittest.TestCase):
    def test_sources_join_short_ids_to_singular_document_id(self):
        context = {"sources": pd.DataFrame([
            {"id": "42", "text": "retrieved B", "in_context": True},
            {"id": "17", "text": "candidate A", "in_context": False},
            {"id": "999", "text": "unresolved", "in_context": True},
        ])}
        resolved = runner.resolve_source_context(context, index_tables())
        self.assertEqual(len(resolved), 2)
        self.assertEqual(resolved[0]["text_unit_id"], "unit-uuid-b")
        self.assertEqual(resolved[0]["document_id"], "paper-b")
        self.assertEqual(resolved[0]["source_metadata"]["pmcid"], "PMC456")
        self.assertTrue(resolved[0]["resolved"])
        self.assertFalse(resolved[1]["resolved"])
        self.assertIsNone(resolved[1]["document_id"])

    def test_generated_markers_are_independent_from_context(self):
        answer = "Claim [Data: Sources (17, 42); Entities (3)] and [Data: Reports (2, +more)]."
        markers = runner.parse_citation_markers(answer)
        self.assertEqual([marker["dataset"] for marker in markers], ["Sources", "Entities", "Reports"])
        self.assertEqual(markers[0]["ids"], ["17", "42"])
        self.assertTrue(markers[2]["truncated"])
        self.assertEqual(runner.parse_citation_markers("An unsupported uncited claim."), [])

    def test_relationship_marker_traces_to_original_paper(self):
        markers = runner.parse_citation_markers("Claim [Data: Relationships (23)].")
        resolved = runner.resolve_citation_markers(markers, index_tables())
        self.assertEqual(len(resolved), 1)
        citation = resolved[0]
        self.assertEqual((citation["dataset"], citation["id"], citation["status"]), ("Relationships", "23", "resolved"))
        self.assertEqual(citation["source_document_ids"], ["paper-b"])
        self.assertEqual(citation["source_paths"][0]["text_unit_id"], "unit-uuid-b")
        self.assertEqual(citation["source_paths"][0]["source_metadata"]["pmcid"], "PMC456")
        self.assertFalse(citation["claim_correctness_verified"])
        json.dumps(citation, allow_nan=False)

    def test_source_and_entity_markers_use_the_correct_id_spaces(self):
        markers = runner.parse_citation_markers("Claim [Data: Sources (17); Entities (3)].")
        resolved = runner.resolve_citation_markers(markers, index_tables())
        self.assertEqual(resolved[0]["source_document_ids"], ["paper-a"])
        self.assertEqual(resolved[1]["source_document_ids"], ["paper-a", "paper-b"])

    def test_unknown_dataset_and_missing_id_remain_unresolved(self):
        markers = runner.parse_citation_markers("Claim [Data: Relationships (999); Invented (3)].")
        resolved = runner.resolve_citation_markers(markers, index_tables())
        self.assertEqual([citation["status"] for citation in resolved], ["unresolved", "unresolved"])
        self.assertTrue(all(citation["source_document_ids"] == [] for citation in resolved))
        self.assertIn("missing_record", resolved[0]["resolution_issues"])
        self.assertIn("unsupported_dataset", resolved[1]["resolution_issues"])

    def test_missing_text_unit_prevents_fully_resolved_status(self):
        markers = runner.parse_citation_markers("Claim [Data: Relationships (24)].")
        resolved = runner.resolve_citation_markers(markers, index_tables())[0]
        self.assertEqual(resolved["status"], "partially_resolved")
        self.assertEqual(resolved["source_document_ids"], ["paper-b"])
        self.assertIn("missing_text_unit:missing-unit", resolved["resolution_issues"])

    def test_report_marker_uses_community_id_and_is_labeled_derived(self):
        markers = runner.parse_citation_markers("Claim [Data: Reports (2)].")
        resolved = runner.resolve_citation_markers(markers, index_tables())[0]
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(resolved["source_document_ids"], ["paper-a", "paper-b"])
        self.assertTrue(resolved["derived_community_summary"])
        self.assertFalse(resolved["claim_correctness_verified"])
        self.assertIn("derived", resolved["provenance_note"])
        wrong_id = runner.resolve_citation_markers([{"dataset": "Reports", "ids": ["901"]}], index_tables())[0]
        self.assertEqual(wrong_id["status"], "unresolved")

    def test_context_can_be_serialized_with_null_values(self):
        frame = pd.DataFrame({"number": [float("nan")], "extra": [pd.NA]})
        value = runner._json_safe({"sources": frame})
        self.assertEqual(value["sources"][0], {"number": None, "extra": None})
        json.dumps(value, allow_nan=False)

    def test_document_dataframe_preserves_provenance_and_drops_extra_columns(self):
        frame = runner._documents_dataframe([
            {"id": "paper-a", "title": "A", "text": "abstract", "pmcid": "PMC123", "generated": False}
        ])
        self.assertEqual(list(frame.columns), list(runner.DOCUMENT_COLUMNS))
        self.assertEqual(frame.iloc[0]["raw_data"]["pmcid"], "PMC123")
        self.assertNotIn("generated", frame.columns)
        with self.assertRaisesRegex(ValueError, "unique"):
            runner._documents_dataframe([
                {"id": "same", "title": "A", "text": "text"},
                {"id": "same", "title": "B", "text": "text"},
            ])

    def test_missing_index_tables_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            config = SimpleNamespace(output_storage=SimpleNamespace(type="file", base_dir=directory))
            with self.assertRaisesRegex(FileNotFoundError, "documents, text_units"):
                runner.load_index(config)


class AsyncAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_error_cannot_load_partial_or_stale_results(self):
        api = SimpleNamespace(build_index=AsyncMock(return_value=[
            SimpleNamespace(workflow="extract_graph", error=RuntimeError("private-api-key-in-error"))
        ]))
        with patch.object(runner, "_graphrag_api", return_value=api), patch.object(runner, "load_index") as loader:
            with self.assertRaisesRegex(RuntimeError, "extract_graph") as caught:
                await runner.build_graph(None, [{"id": "x", "title": "x", "text": "text"}])
            loader.assert_not_called()
            self.assertNotIn("private-api-key", str(caught.exception))

    async def test_successful_pipeline_loads_required_tables(self):
        api = SimpleNamespace(build_index=AsyncMock(return_value=[SimpleNamespace(workflow="final", error=None)]))
        tables = index_tables()
        with patch.object(runner, "_graphrag_api", return_value=api), patch.object(runner, "load_index", return_value=tables):
            result = await runner.build_graph("config", [{"id": "x", "title": "x", "text": "text"}])
        self.assertIs(result, tables)
        self.assertEqual(api.build_index.await_args.kwargs["method"], "standard")
        self.assertEqual(list(api.build_index.await_args.kwargs["input_documents"].columns), list(runner.DOCUMENT_COLUMNS))

    async def test_basic_search_context_is_not_claimed_as_generated_citation(self):
        api = SimpleNamespace(basic_search=AsyncMock(return_value=(
            "Answer has no citation marker.", {"sources": pd.DataFrame([{"id": "17", "text": "passage"}])}
        )))
        with patch.object(runner, "_graphrag_api", return_value=api):
            result = await runner.ask("config", index_tables(), "question", method="basic")
        self.assertEqual(len(result["retrieved_source_context"]), 1)
        self.assertEqual(result["citation_markers"], [])
        self.assertIn("not automatically citations", result["citation_note"])
        json.dumps(result, allow_nan=False)

    async def test_local_search_passes_current_communities_contract(self):
        api = SimpleNamespace(local_search=AsyncMock(return_value=("Answer [Data: Sources (42)].", {})))
        tables = index_tables()
        with patch.object(runner, "_graphrag_api", return_value=api):
            result = await runner.ask("config", tables, "question")
        arguments = api.local_search.await_args.kwargs
        self.assertIs(arguments["communities"], tables["communities"])
        self.assertIsNone(arguments["covariates"])
        self.assertEqual(arguments["community_level"], 0)
        self.assertEqual(result["citation_markers"][0]["ids"], ["42"])
        self.assertEqual(result["resolved_citation_markers"][0]["source_document_ids"], ["paper-b"])
        self.assertEqual(result["retrieved_source_context"], [])

    async def test_provider_failure_does_not_expose_exception_body(self):
        api = SimpleNamespace(basic_search=AsyncMock(side_effect=RuntimeError("secret-key-123")))
        with patch.object(runner, "_graphrag_api", return_value=api):
            with self.assertRaises(RuntimeError) as caught:
                await runner.ask("config", index_tables(), "question", method="basic")
        self.assertNotIn("secret-key", str(caught.exception))

    async def test_smoke_failure_reports_safe_stage_and_type(self):
        completion = SimpleNamespace(completion_async=AsyncMock(side_effect=ValueError("secret-key-123")))
        config = SimpleNamespace(
            completion_models={runner.COMPLETION_ID: SimpleNamespace(model="gemini-test")},
            embedding_models={runner.EMBEDDING_ID: SimpleNamespace(model="embedding-test")},
            cache=None,
        )
        with patch.object(runner, "_model_factories", return_value=(lambda *a, **k: completion, None)):
            result = await runner.smoke_test(config)
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "completion")
        self.assertEqual(result["error_type"], "ValueError")
        self.assertNotIn("secret-key", json.dumps(result))

    async def test_smoke_detects_embedding_dimension_mismatch(self):
        completion = SimpleNamespace(completion_async=AsyncMock(return_value=SimpleNamespace(
            formatted_response=SimpleNamespace(entity="resistance training", evidence_quote="Resistance training was studied in adults.")
        )))
        embedding = SimpleNamespace(embedding_async=AsyncMock(return_value=SimpleNamespace(first_embedding=[0.1, 0.2])))
        config = SimpleNamespace(
            completion_models={runner.COMPLETION_ID: SimpleNamespace(model="gemini-test")},
            embedding_models={runner.EMBEDDING_ID: SimpleNamespace(model="embedding-test")},
            cache=None, vector_store=SimpleNamespace(vector_size=3072),
        )
        with patch.object(runner, "_model_factories", return_value=(lambda *a, **k: completion, lambda *a, **k: embedding)):
            result = await runner.smoke_test(config)
        self.assertFalse(result["ok"])
        self.assertTrue(result["schema_valid"])
        self.assertEqual(result["embedding_dimensions"], 2)
        self.assertEqual(result["error_type"], "EmbeddingDimensionMismatch")

    async def test_smoke_rejects_quote_not_present_in_synthetic_source(self):
        completion = SimpleNamespace(completion_async=AsyncMock(return_value=SimpleNamespace(
            formatted_response=SimpleNamespace(entity="resistance training", evidence_quote="It cured disease.")
        )))
        make_embedding = unittest.mock.Mock()
        config = SimpleNamespace(
            completion_models={runner.COMPLETION_ID: SimpleNamespace(model="gemini-test")},
            embedding_models={runner.EMBEDDING_ID: SimpleNamespace(model="embedding-test")}, cache=None,
        )
        with patch.object(runner, "_model_factories", return_value=(lambda *a, **k: completion, make_embedding)):
            result = await runner.smoke_test(config)
        self.assertFalse(result["ok"])
        self.assertFalse(result["evidence_quote_verified"])
        self.assertEqual(result["stage"], "completion")
        make_embedding.assert_not_called()

    async def test_smoke_rejects_nonfinite_embedding(self):
        completion = SimpleNamespace(completion_async=AsyncMock(return_value=SimpleNamespace(
            formatted_response=SimpleNamespace(entity="resistance training", evidence_quote="Resistance training was studied in adults.")
        )))
        embedding = SimpleNamespace(embedding_async=AsyncMock(return_value=SimpleNamespace(first_embedding=[float("nan")] * 3072)))
        config = SimpleNamespace(
            completion_models={runner.COMPLETION_ID: SimpleNamespace(model="gemini-test")},
            embedding_models={runner.EMBEDDING_ID: SimpleNamespace(model="embedding-test")},
            cache=None, vector_store=SimpleNamespace(vector_size=3072),
        )
        with patch.object(runner, "_model_factories", return_value=(lambda *a, **k: completion, lambda *a, **k: embedding)):
            result = await runner.smoke_test(config)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "InvalidEmbeddingValues")

    async def test_smoke_success_reports_only_bounded_compatibility(self):
        completion = SimpleNamespace(completion_async=AsyncMock(return_value=SimpleNamespace(
            formatted_response=SimpleNamespace(entity="resistance training", evidence_quote="Resistance training was studied in adults.")
        )))
        embedding = SimpleNamespace(embedding_async=AsyncMock(return_value=SimpleNamespace(first_embedding=[0.1] * 3072)))
        config = SimpleNamespace(
            completion_models={runner.COMPLETION_ID: SimpleNamespace(model="gemini-test")},
            embedding_models={runner.EMBEDDING_ID: SimpleNamespace(model="embedding-test")},
            cache=None, vector_store=SimpleNamespace(vector_size=3072),
        )
        with patch.object(runner, "_model_factories", return_value=(lambda *a, **k: completion, lambda *a, **k: embedding)):
            result = await runner.smoke_test(config)
        self.assertTrue(result["ok"])
        self.assertTrue(result["evidence_quote_verified"])
        self.assertEqual(result["compatibility"], "smoke_test_passed_only")
        self.assertEqual(completion.completion_async.await_count, 1)
        self.assertEqual(embedding.embedding_async.await_count, 1)
        self.assertNotIn("first_embedding", result)
        json.dumps(result, allow_nan=False)

    async def test_smoke_does_not_access_or_pass_persistent_response_cache(self):
        completion = SimpleNamespace(completion_async=AsyncMock(return_value=SimpleNamespace(
            formatted_response=SimpleNamespace(entity="resistance training", evidence_quote="Resistance training was studied in adults.")
        )))
        embedding = SimpleNamespace(embedding_async=AsyncMock(return_value=SimpleNamespace(first_embedding=[0.1] * 3072)))

        class SmokeConfig:
            completion_models = {runner.COMPLETION_ID: SimpleNamespace(model="gemini-test")}
            embedding_models = {runner.EMBEDDING_ID: SimpleNamespace(model="embedding-test")}
            vector_store = SimpleNamespace(vector_size=3072)

            @property
            def cache(self):
                raise AssertionError("Smoke probes must not access persistent cache configuration")

        make_completion = unittest.mock.Mock(return_value=completion)
        make_embedding = unittest.mock.Mock(return_value=embedding)
        config = SmokeConfig()
        with patch.object(runner, "_model_factories", return_value=(make_completion, make_embedding)):
            result = await runner.smoke_test(config)
        self.assertTrue(result["ok"])
        make_completion.assert_called_once_with(config.completion_models[runner.COMPLETION_ID])
        make_embedding.assert_called_once_with(config.embedding_models[runner.EMBEDDING_ID])


@unittest.skipUnless(importlib.util.find_spec("graphrag"), "Pinned GraphRAG dependency is not installed")
class ActualConfigurationTests(unittest.TestCase):
    def test_actual_model_factories_default_to_no_cache(self):
        import inspect
        completion, embedding = runner._model_factories()
        self.assertIsNone(inspect.signature(completion).parameters["cache"].default)
        self.assertIsNone(inspect.signature(embedding).parameters["cache"].default)

    def test_config_validates_against_real_graphrag_models_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            config = runner.make_config(directory, "placeholder-for-config-validation-only")
            self.assertEqual(config.vector_store.vector_size, 3072)
            self.assertEqual(config.chunking.size, 600)
            self.assertEqual(config.chunking.overlap, 80)
            self.assertEqual(config.concurrent_requests, 1)
            self.assertEqual(config.extract_graph.max_gleanings, 0)
            self.assertFalse(config.extract_claims.enabled)
            self.assertEqual(config.cache.type, "json")
            self.assertEqual(config.embed_text.names, ["entity_description", "text_unit_text"])
            self.assertTrue(Path(config.output_storage.base_dir).is_absolute())
            self.assertEqual(config.completion_models[runner.COMPLETION_ID].model_provider, "gemini")


if __name__ == "__main__":
    unittest.main()
