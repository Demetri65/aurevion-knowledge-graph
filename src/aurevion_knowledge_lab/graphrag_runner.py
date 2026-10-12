"""Pinned GraphRAG 3.3 adapter; live calls are made only by explicit callers."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd
    from graphrag.config.models.graph_rag_config import GraphRagConfig

GRAPHRAG_VERSION = "3.3.0"
COMPLETION_ID = "default_completion_model"
EMBEDDING_ID = "default_embedding_model"
TABLE_NAMES = ("documents", "text_units", "entities", "relationships", "communities", "community_reports")
DOCUMENT_COLUMNS = ("id", "human_readable_id", "title", "text", "creation_date", "raw_data")


def _graphrag_api():
    from graphrag import api
    return api


def _model_factories():
    from graphrag_llm.completion import create_completion
    from graphrag_llm.embedding import create_embedding
    return create_completion, create_embedding


def make_config(
    run_dir: str | Path,
    api_key: str,
    completion_model: str = "gemini-3.1-flash-lite",
    embedding_model: str = "gemini-embedding-001",
) -> GraphRagConfig:
    """Validate an isolated run configuration without calling a model.

    A successful config validation does not verify provider/model compatibility.
    Never display or serialize the returned config: it contains the API key.
    """
    from graphrag.config.models.graph_rag_config import GraphRagConfig

    root = Path(run_dir).expanduser().resolve()
    retry = {"type": "exponential_backoff", "max_retries": 2, "base_delay": 2.0, "max_delay": 10.0}
    model_base = {"model_provider": "gemini", "api_key": api_key, "retry": retry}
    return GraphRagConfig(
        completion_models={COMPLETION_ID: {
            **model_base, "model": completion_model,
            "call_args": {"temperature": 0, "max_tokens": 2048, "timeout": 60},
        }},
        embedding_models={EMBEDDING_ID: {
            **model_base, "model": embedding_model,
            "call_args": {"dimensions": 3072, "timeout": 60},
        }},
        concurrent_requests=1,
        async_mode="asyncio",
        chunking={"type": "tokens", "size": 600, "overlap": 80, "encoding_model": "o200k_base"},
        input_storage={"type": "file", "base_dir": str(root / "input")},
        output_storage={"type": "file", "base_dir": str(root / "output")},
        update_output_storage={"type": "file", "base_dir": str(root / "update_output")},
        reporting={"type": "file", "base_dir": str(root / "logs")},
        cache={"type": "json", "storage": {"type": "file", "base_dir": str(root / "cache")}},
        vector_store={"type": "lancedb", "db_uri": str(root / "lancedb"), "vector_size": 3072},
        embed_text={"names": ["entity_description", "text_unit_text"], "batch_size": 8},
        extract_graph={
            "entity_types": ["intervention", "outcome", "population", "nutrient", "exercise", "study"],
            "max_gleanings": 0,
        },
        extract_claims={"enabled": False},
        community_reports={"max_length": 600, "max_input_length": 4000},
        local_search={"max_context_tokens": 4000, "top_k_entities": 5, "top_k_relationships": 5},
        basic_search={"max_context_tokens": 4000, "k": 5},
    )


async def smoke_test(config: GraphRagConfig) -> dict[str, Any]:
    """Uncached opt-in credential/model probe; return only safe diagnostics."""
    from pydantic import BaseModel

    class Probe(BaseModel):
        entity: str
        evidence_quote: str

    result: dict[str, Any] = {
        "ok": False,
        "completion_model": config.completion_models[COMPLETION_ID].model,
        "embedding_model": config.embedding_models[EMBEDDING_ID].model,
        "schema_valid": False,
        "evidence_quote_verified": False,
        "embedding_dimensions": None,
        "compatibility": "unverified",
    }
    stage = "completion"
    try:
        create_completion, create_embedding = _model_factories()
        completion = create_completion(config.completion_models[COMPLETION_ID])
        passage = "Resistance training was studied in adults."
        response = await completion.completion_async(
            messages=[{"role": "user", "content": (
                "Extract the exercise entity and an exact evidence quote from this passage. "
                "Return entity as 'resistance training' and evidence_quote as a verbatim passage excerpt. "
                f"Passage: {passage}"
            )}],
            response_format=Probe,
            max_tokens=128,
            timeout=60,
        )
        probe = response.formatted_response
        if probe is None:
            probe = Probe.model_validate(json.loads(response.content))
        if probe.entity.strip().lower() != "resistance training":
            raise ValueError("Unexpected entity in schema probe")
        if not probe.evidence_quote.strip() or probe.evidence_quote not in passage:
            raise ValueError("Evidence quote is not present in the synthetic source")
        result["schema_valid"] = True
        result["evidence_quote_verified"] = True
        stage = "embedding"
        embedding = create_embedding(config.embedding_models[EMBEDDING_ID])
        embedded = await embedding.embedding_async(input=["resistance training and protein"], timeout=60)
        vector = embedded.first_embedding
        dimensions = len(vector)
        result["embedding_dimensions"] = dimensions
        if dimensions != config.vector_store.vector_size:
            result["stage"] = stage
            result["error_type"] = "EmbeddingDimensionMismatch"
            return result
        if not all(math.isfinite(float(value)) for value in vector):
            result["stage"] = stage
            result["error_type"] = "InvalidEmbeddingValues"
            return result
        result.update(ok=True, compatibility="smoke_test_passed_only")
    except Exception as exc:
        # Provider exceptions can include credentials, URLs, or request bodies.
        result.update(stage=stage, error_type=type(exc).__name__)
    return result


def _documents_dataframe(documents: list[dict[str, Any]]) -> pd.DataFrame:
    import pandas as pd

    if not documents:
        raise ValueError("At least one source document is required")
    rows = []
    seen = set()
    for position, document in enumerate(documents):
        if not all(str(document.get(field) or "").strip() for field in ("id", "title", "text")):
            raise ValueError("Each source document requires nonempty id, title, and text")
        identifier = str(document["id"])
        if identifier in seen:
            raise ValueError("Source document IDs must be unique")
        seen.add(identifier)
        rows.append({
            "id": identifier,
            "human_readable_id": position,
            "title": str(document["title"]),
            "text": str(document["text"]),
            "creation_date": str(document.get("creation_date") or ""),
            "raw_data": document.get("raw_data") or {
                key: value for key, value in document.items() if key not in DOCUMENT_COLUMNS
            } or None,
        })
    return pd.DataFrame(rows, columns=DOCUMENT_COLUMNS)


async def build_graph(config: GraphRagConfig, documents: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    """Run Standard indexing; partial/error runs cannot be loaded as success."""
    frame = _documents_dataframe(documents)
    try:
        outputs = await _graphrag_api().build_index(config=config, method="standard", input_documents=frame)
    except Exception as exc:
        raise RuntimeError(f"GraphRAG indexing failed ({type(exc).__name__}); inspect the private run logs") from None
    failures = [output for output in outputs if output.error is not None]
    if failures:
        workflows = ", ".join(str(output.workflow) for output in failures)
        raise RuntimeError(f"GraphRAG pipeline failed in {workflows}; inspect the private run logs")
    if not outputs:
        raise RuntimeError("GraphRAG returned no pipeline results")
    return load_index(config)


def load_index(config: GraphRagConfig) -> dict[str, pd.DataFrame]:
    """Load six required local Parquet tables; existing files do not prove a valid run."""
    import pandas as pd

    if config.output_storage.type != "file":
        raise ValueError("This lab supports local file output storage only")
    root = Path(config.output_storage.base_dir)
    missing = [name for name in TABLE_NAMES if not (root / f"{name}.parquet").is_file()]
    if missing:
        raise FileNotFoundError("Missing GraphRAG index tables: " + ", ".join(missing))
    return {name: pd.read_parquet(root / f"{name}.parquet") for name in TABLE_NAMES}


def _json_safe(value: Any) -> Any:
    """Convert context frames and nullable/NumPy values without lossy repr output."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict") and hasattr(value, "columns"):
        return _json_safe(value.to_dict(orient="records"))
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    if hasattr(value, "item"):
        return _json_safe(value.item())
    if hasattr(value, "isoformat"):
        return value.isoformat()
    # pandas.NA and pandas.NaT cannot be coerced to bool safely.
    if type(value).__name__ in {"NAType", "NaTType"}:
        return None
    raise TypeError(f"Unsupported context value type: {type(value).__name__}")


def parse_citation_markers(answer: str) -> list[dict[str, Any]]:
    """Parse generated Data markers separately from retrieved source context."""
    citations = []
    for marker in re.finditer(r"\[Data:\s*([^\]]+)\]", answer, re.IGNORECASE):
        for group in re.finditer(r"([A-Za-z][A-Za-z _-]*?)\s*\(([^)]*)\)", marker.group(1)):
            identifiers = re.findall(r"\b\d+\b", group.group(2))
            citations.append({
                "dataset": group.group(1).strip(),
                "ids": identifiers,
                "truncated": "+more" in group.group(2).lower(),
                "marker": marker.group(0),
            })
    return citations


def _source_metadata(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return _json_safe(json.loads(value))
        except json.JSONDecodeError:
            return value
    return _json_safe(value)


def resolve_source_context(context: dict[str, Any], tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """Resolve Sources short IDs through text units' singular document_id field."""
    sources = context.get("sources")
    if sources is None:
        return []
    rows = _json_safe(sources)
    units = {str(row["human_readable_id"]): row for row in tables["text_units"].to_dict(orient="records")}
    documents = {str(row["id"]): row for row in tables["documents"].to_dict(orient="records")}
    resolved = []
    for row in rows:
        if row.get("in_context") is False:
            continue
        short_id = str(row.get("id", ""))
        unit = units.get(short_id)
        document = documents.get(str(unit.get("document_id"))) if unit else None
        resolved.append({
            "context_id": short_id,
            "text": row.get("text", ""),
            "resolved": document is not None,
            "text_unit_id": str(unit["id"]) if unit else None,
            "document_id": str(unit["document_id"]) if unit else None,
            "document_title": document.get("title") if document else None,
            "source_metadata": _source_metadata(document.get("raw_data")) if document else None,
        })
    return resolved


def _identifier(value: Any) -> str:
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return str(int(value))
    return str(value)


def resolve_citation_markers(
    markers: list[dict[str, Any]], tables: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    """Trace generated record IDs to papers; this does not verify cited claims.

    GraphRAG 3.3 uses Sources/Entities/Relationships human_readable_id values,
    but Reports IDs refer to community IDs, not report human_readable_id values.
    """
    def lookup(name: str, field: str) -> dict[str, dict[str, Any]]:
        frame = tables.get(name)
        rows = _json_safe(frame) if frame is not None else []
        return {_identifier(row[field]): row for row in rows if row.get(field) is not None}

    units_by_id = lookup("text_units", "id")
    units_by_short_id = lookup("text_units", "human_readable_id")
    documents = lookup("documents", "id")
    entities = lookup("entities", "human_readable_id")
    relationships = lookup("relationships", "human_readable_id")
    communities = lookup("communities", "community")
    reports = lookup("community_reports", "community")

    def trace_units(unit_ids: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        paths = []
        issues = []
        for unit_id in dict.fromkeys(unit_ids):
            unit = units_by_id.get(unit_id)
            if unit is None:
                issues.append(f"missing_text_unit:{unit_id}")
                continue
            document_id = _identifier(unit.get("document_id"))
            document = documents.get(document_id)
            if document is None:
                issues.append(f"missing_document:{document_id}")
                continue
            paths.append({
                "text_unit_id": unit_id,
                "document_id": document_id,
                "document_title": document.get("title"),
                "source_metadata": _source_metadata(document.get("raw_data")),
            })
        return paths, issues

    resolved = []
    for marker in markers:
        dataset = str(marker.get("dataset", ""))
        dataset_key = dataset.strip().lower()
        for value in marker.get("ids", []) or [None]:
            identifier = _identifier(value) if value is not None else None
            unit_ids = []
            issues = []
            record = None
            derived_report = dataset_key == "reports"
            if identifier is None:
                issues.append("missing_citation_id")
            elif dataset_key == "sources":
                record = units_by_short_id.get(identifier)
                if record is not None:
                    unit_ids = [_identifier(record["id"])]
            elif dataset_key in {"entities", "relationships"}:
                record = (entities if dataset_key == "entities" else relationships).get(identifier)
                if record is not None:
                    unit_ids = [_identifier(item) for item in record.get("text_unit_ids") or []]
            elif derived_report:
                report = reports.get(identifier)
                community = communities.get(identifier)
                if report is None:
                    issues.append("missing_report")
                if community is None:
                    issues.append("missing_community")
                if report is not None and community is not None:
                    record = report
                    unit_ids = [_identifier(item) for item in community.get("text_unit_ids") or []]
            else:
                issues.append("unsupported_dataset")
            if record is None and not issues:
                issues.append("missing_record")
            if record is not None and not unit_ids:
                issues.append("missing_text_unit_references")
            paths, path_issues = trace_units(unit_ids)
            issues.extend(path_issues)
            status = "resolved" if paths and not issues else "partially_resolved" if paths else "unresolved"
            resolved.append({
                "dataset": dataset,
                "id": identifier,
                "status": status,
                "source_document_ids": list(dict.fromkeys(path["document_id"] for path in paths)),
                "source_paths": paths,
                "resolution_issues": issues,
                "derived_community_summary": derived_report,
                "claim_correctness_verified": False,
                "marker": marker.get("marker"),
                "truncated": bool(marker.get("truncated", False)),
                "provenance_note": (
                    "This is a derived community summary. The links identify originating papers and do not establish claim correctness."
                    if derived_report else
                    "The links identify originating papers; resolving record IDs does not establish claim correctness."
                ),
            })
    return resolved


async def ask(
    config: GraphRagConfig,
    tables: dict[str, pd.DataFrame],
    question: str,
    method: str = "local",
) -> dict[str, Any]:
    """Query the same index using graph/local or ordinary vector/basic retrieval."""
    if method not in {"basic", "local"}:
        raise ValueError("method must be 'basic' or 'local'")
    if not question.strip():
        raise ValueError("A nonempty question is required")
    api = _graphrag_api()
    arguments = {"config": config, "text_units": tables["text_units"], "response_type": "multiple paragraphs", "query": question}
    try:
        if method == "basic":
            answer, context = await api.basic_search(**arguments)
        else:
            answer, context = await api.local_search(
                **arguments,
                entities=tables["entities"],
                communities=tables["communities"],
                community_reports=tables["community_reports"],
                relationships=tables["relationships"],
                covariates=None,
                community_level=0,
            )
    except Exception as exc:
        raise RuntimeError(f"GraphRAG {method} query failed ({type(exc).__name__}); inspect the private run logs") from None
    context_dict = context if isinstance(context, dict) else {}
    markers = parse_citation_markers(answer) if isinstance(answer, str) else []
    return {
        "method": method,
        "answer": _json_safe(answer),
        "retrieved_source_context": resolve_source_context(context_dict, tables),
        "context_tables": _json_safe(context),
        "citation_markers": markers,
        "resolved_citation_markers": resolve_citation_markers(markers, tables),
        "citation_note": "Retrieved rows are context, not automatically citations used by the answer. Generated markers require claim-level review.",
    }
