"""Graph inspection and portable, explicitly labelled research artifacts."""

from __future__ import annotations

import html
import json
import textwrap
from pathlib import Path
from typing import Any


COLORS = {"paper": "#7eb8cf", "topic": "#8e99a8", "claim": "#f5b45a", "entity": "#7eb8cf", "decision": "#f08350", "population": "#ad9ac8"}


def example_graph(manifest: list[dict], annotations: dict) -> dict:
    """Validate source references and return a human-authored example graph."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, kind: str, label: str, **properties: Any) -> None:
        nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, **properties})

    for paper in manifest:
        add_node(paper["id"], "paper", paper["title"], year=paper["year"], url=paper["source_url"], status="source_metadata")
        for topic in paper.get("topics", []):
            topic_id = f"topic:{topic}"
            add_node(topic_id, "topic", topic.replace("_", " "), status="manifest_tag")
            edges.append({"source": paper["id"], "target": topic_id, "relation": "TAGGED_WITH", "provenance": "manifest_metadata"})

    for claim in annotations["claims"]:
        add_node(claim["id"], "claim", claim["title"], status=claim["status"], note=claim["note"])
        population_id = f"population:{claim['id']}"
        add_node(population_id, "population", claim["population"], status="draft_example")
        edges.append({"source": claim["id"], "target": population_id, "relation": "CONTEXT_TO_REVIEW", "provenance": "human_authored_example"})
        for source_id in claim["source_ids"]:
            if source_id not in nodes or nodes[source_id]["kind"] != "paper":
                raise ValueError(f"Unknown paper reference in {claim['id']}: {source_id}")
            edges.append({"source": source_id, "target": claim["id"], "relation": "SOURCE_TO_REVIEW", "provenance": "human_authored_example"})

    for decision in annotations["decisions"]:
        add_node(decision["id"], "decision", decision["title"], status=decision["status"], note=decision["rationale"])
        for claim_id in decision["claim_ids"]:
            if claim_id not in nodes or nodes[claim_id]["kind"] != "claim":
                raise ValueError(f"Unknown claim reference in {decision['id']}: {claim_id}")
            edges.append({"source": claim_id, "target": decision["id"], "relation": "INFORMS_PROPOSAL", "provenance": "human_authored_example"})

    return {"status": "human_authored_draft_examples", "nodes": list(nodes.values()), "edges": edges}


def graph_from_index(tables: dict, max_nodes: int = 80) -> dict:
    """Produce a bounded view of actual extracted entities and relationships."""
    entities = tables["entities"].head(max_nodes)
    nodes = []
    title_to_id = {}
    for row in entities.to_dict("records"):
        node_id = str(row["id"])
        title = str(row["title"])
        title_to_id[title] = node_id
        nodes.append({"id": node_id, "kind": "entity", "label": title, "status": "model_extracted_unreviewed", "note": str(row.get("description", ""))})
    edges = []
    for row in tables["relationships"].to_dict("records"):
        source, target = title_to_id.get(str(row["source"])), title_to_id.get(str(row["target"]))
        if source and target:
            edges.append({"source": source, "target": target, "relation": "EXTRACTED_RELATIONSHIP", "description": str(row.get("description", "")), "provenance": "model_extracted_unreviewed"})
    return {"status": "model_extracted_unreviewed", "nodes": nodes, "edges": edges, "view_max_nodes": max_nodes}


def write_interactive_graph(graph: dict, path: Path) -> Path:
    from pyvis.network import Network

    network = Network(height="650px", width="100%", bgcolor="#111b24", font_color="#eef0ec", directed=True, cdn_resources="in_line")
    for node in graph["nodes"]:
        tooltip = html.escape(f"{node['label']}\n{node['kind']} · {node.get('status', '')}\n{node.get('note', '')}\n{node.get('url', '')}")
        short_label = textwrap.fill(textwrap.shorten(node["label"], width=58, placeholder="…"), width=28)
        if node["kind"] == "paper":
            short_label = f"{node['id']}\n{short_label}"
        network.add_node(node["id"], label=short_label, title=tooltip, color=COLORS.get(node["kind"], "#7eb8cf"), shape="dot", size=23 if node["kind"] == "decision" else 13)
    for edge in graph["edges"]:
        network.add_edge(edge["source"], edge["target"], title=html.escape(edge.get("description", edge["relation"])), color="#536878", arrows="to")
    network.set_options('{"layout":{"randomSeed":7},"physics":{"solver":"repulsion","repulsion":{"nodeDistance":180,"centralGravity":0.03,"springLength":190,"springConstant":0.02,"damping":0.09},"stabilization":{"iterations":250}},"interaction":{"hover":true,"navigationButtons":true},"nodes":{"font":{"size":12,"face":"sans-serif"}},"edges":{"smooth":{"type":"continuous"}}}')
    path.parent.mkdir(parents=True, exist_ok=True)
    network.write_html(str(path), open_browser=False, notebook=False)
    return path


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    return path


def impacted_decisions(graph: dict, source_id: str) -> list[dict]:
    """Trace explicit draft links; this does not detect a correction upstream."""
    import networkx as nx

    network = nx.DiGraph()
    nodes = {node["id"]: node for node in graph["nodes"]}
    if source_id not in nodes or nodes[source_id]["kind"] != "paper":
        raise ValueError("Choose a paper ID present in the graph.")
    for edge in graph["edges"]:
        if edge["relation"] in {"SOURCE_TO_REVIEW", "INFORMS_PROPOSAL"}:
            network.add_edge(edge["source"], edge["target"])
    if source_id not in network:
        return []
    return [{"decision_id": identifier, "title": nodes[identifier]["label"],
             "status": nodes[identifier]["status"],
             "source_path": nx.shortest_path(network, source_id, identifier)}
            for identifier in sorted(nx.descendants(network, source_id))
            if nodes[identifier]["kind"] == "decision"]


def evaluation_rows(questions: list[dict], source_ids: set[str], content_mode: str = "abstract") -> list[dict]:
    """Unscored rows distinguish missing source coverage from retrieval quality."""
    return [{**question, "corpus_covered": set(question.get("required_source_ids", [])) <= source_ids,
             "mode_covered": question.get("minimum_document_mode", "abstract") != "full_text" or content_mode == "full_text",
             "basic_answer": None, "local_answer": None, "citation_accuracy": None,
             "population_fit": None, "unsupported_claims": None, "review_notes": None}
            for question in questions]
