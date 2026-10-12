"""Fetch and prepare the small, explicitly licensed historical research corpus."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET


_ALLOWED_PMCIDS = {
    "PMC5477153", "PMC3879660", "PMC5470183", "PMC6081873", "PMC4362642"
}
_LICENSES = {
    "CC-BY-2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
}
_TIMEOUT_SECONDS = 30
_MAX_XML_BYTES = 4 * 1024 * 1024
_LICENSE_URL_RE = re.compile(
    r"https?://creativecommons\.org/licenses/([a-z-]+)/([0-9.]+)/?", re.I
)
_BLOCK_TAGS = {"title", "p", "list-item", "table", "tr", "caption", "sec"}
_EXCLUDED_TAGS = {"ref-list", "ref", "element-citation", "mixed-citation"}


class CorpusValidationError(ValueError):
    """A source, cached file, or manifest failed an integrity check."""


def _project_root(project_root: str | Path) -> Path:
    return Path(project_root).expanduser().resolve()


def _cache_path(project_root: Path, record: dict) -> Path:
    return project_root / "corpus" / "papers" / f"{record['pmcid']}.xml"


def _download_url(pmcid: str) -> str:
    return f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"


def load_manifest(project_root: str | Path) -> list[dict]:
    """Load the fixed five-source allowlist without accessing the network."""
    manifest_path = _project_root(project_root) / "corpus" / "manifest.jsonl"
    records: list[dict] = []
    seen: set[str] = set()
    required = (
        "id", "pmcid", "pmid", "doi", "title", "year", "source_url",
        "license", "license_url", "download_url",
    )
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusValidationError(f"Invalid JSON on manifest line {line_number}") from exc
        if not isinstance(record, dict) or any(key not in record for key in required):
            raise CorpusValidationError(f"Missing required fields on manifest line {line_number}")
        pmcid = record["pmcid"]
        if not isinstance(pmcid, str) or pmcid not in _ALLOWED_PMCIDS or record["id"] != pmcid:
            raise CorpusValidationError(f"Source ID is outside the fixed corpus on line {line_number}")
        if pmcid in seen:
            raise CorpusValidationError(f"Duplicate source ID: {pmcid}")
        if record["download_url"] != _download_url(pmcid):
            raise CorpusValidationError(f"Unapproved download route for {pmcid}")
        if record["source_url"] != f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/":
            raise CorpusValidationError(f"Unexpected citation URL for {pmcid}")
        if record["license"] not in _LICENSES or record["license_url"] != _LICENSES[record["license"]]:
            raise CorpusValidationError(f"Unapproved license for {pmcid}")
        if not re.fullmatch(r"\d{4}", str(record["year"])):
            raise CorpusValidationError(f"Invalid publication year for {pmcid}")
        if not all(isinstance(record[key], str) and record[key].strip() for key in ("pmid", "doi", "title")):
            raise CorpusValidationError(f"Invalid citation metadata for {pmcid}")
        if record.get("sha256") and not re.fullmatch(r"[a-f0-9]{64}", record["sha256"]):
            raise CorpusValidationError(f"Invalid SHA-256 for {pmcid}")
        seen.add(pmcid)
        records.append(record)
    if not records:
        raise CorpusValidationError("The corpus manifest is empty")
    return records


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _validate_article(data: bytes, record: dict) -> tuple[ET.Element, dict]:
    if not data or len(data) > _MAX_XML_BYTES:
        raise CorpusValidationError(f"XML size is outside the allowed range for {record['pmcid']}")
    try:
        article = ET.fromstring(data)
    except ET.ParseError as exc:
        raise CorpusValidationError(f"Invalid article XML for {record['pmcid']}") from exc
    meta = article.find("./front/article-meta")
    if _local_name(article.tag) != "article" or meta is None:
        raise CorpusValidationError(f"Missing article metadata for {record['pmcid']}")
    ids = {node.get("pub-id-type"): _text(node) for node in meta.findall("article-id")}
    actual_pmcid = ids.get("pmcid") or ids.get("pmc")
    if actual_pmcid and actual_pmcid.isdigit():
        actual_pmcid = f"PMC{actual_pmcid}"
    for field, actual in (("pmcid", actual_pmcid), ("pmid", ids.get("pmid")), ("doi", ids.get("doi"))):
        if actual != record[field]:
            raise CorpusValidationError(f"Article {field} mismatch for {record['pmcid']}: {actual!r}")
    permissions = meta.find("permissions")
    if permissions is None:
        raise CorpusValidationError(f"Missing license statement for {record['pmcid']}")
    license_nodes = permissions.findall("license")
    license_text = " ".join(
        " ".join([_text(node), *node.attrib.values()]) for node in license_nodes
    )
    actual_licenses = {
        f"CC-{kind.upper()}-{version}" for kind, version in _LICENSE_URL_RE.findall(license_text)
    }
    if actual_licenses != {record["license"]}:
        raise CorpusValidationError(
            f"Article license mismatch for {record['pmcid']}: {sorted(actual_licenses)!r}"
        )
    authors = []
    for group in meta.findall("contrib-group"):
        for author in group.findall("contrib"):
            inherited_type = "author" if group.get("content-type") == "author" else ""
            if author.get("contrib-type", inherited_type) != "author":
                continue
            name = author.find("name")
            if name is not None:
                authors.append(" ".join(filter(None, (
                    _text(name.find("given-names")), _text(name.find("surname"))
                ))))
            elif author.find("collab") is not None:
                authors.append(_text(author.find("collab")))
    return article, {
        "authors": authors,
        "license_statement": " ".join(_text(node) for node in license_nodes),
        "xml_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _read_verified_cache(project_root: Path, record: dict) -> tuple[ET.Element, dict]:
    path = _cache_path(project_root, record)
    if not path.is_file():
        raise FileNotFoundError(f"Missing cached XML: {path}. Run fetch_corpus(project_root).")
    if path.stat().st_size > _MAX_XML_BYTES:
        raise CorpusValidationError(f"Cached XML exceeds the byte cap for {record['pmcid']}")
    data = path.read_bytes()
    article, parsed = _validate_article(data, record)
    if not record.get("sha256"):
        raise CorpusValidationError(f"Missing manifest SHA-256 for {record['pmcid']}")
    if parsed["sha256"] != record["sha256"]:
        raise CorpusValidationError(f"Cached XML SHA-256 mismatch for {record['pmcid']}")
    return article, parsed


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download_xml(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "AurevionKnowledgeLab/0.1 (research corpus)"})
    opener = build_opener(_NoRedirects())
    with opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise CorpusValidationError(f"Unexpected download status: {response.status}")
        size = response.headers.get("Content-Length")
        if size is not None and int(size) > _MAX_XML_BYTES:
            raise CorpusValidationError("Article download exceeds the byte cap")
        data = response.read(_MAX_XML_BYTES + 1)
    if len(data) > _MAX_XML_BYTES:
        raise CorpusValidationError("Article download exceeds the byte cap")
    return data


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _preserve_source_history(root: Path, pending: list[tuple[Path, bytes]]) -> None:
    snapshots: list[tuple[Path, bytes]] = []
    history = root / "runs" / "source-history"
    for path, replacement in pending:
        if not path.exists():
            continue
        if path.stat().st_size > _MAX_XML_BYTES:
            raise CorpusValidationError(f"Cached XML exceeds the byte cap for {path.stem}")
        previous = path.read_bytes()
        previous_hash = hashlib.sha256(previous).hexdigest()
        if previous_hash != hashlib.sha256(replacement).hexdigest():
            snapshots.append((history / path.stem / f"{previous_hash}.xml", previous))
    if not snapshots:
        return
    previous_manifest = (root / "corpus" / "manifest.jsonl").read_bytes()
    manifest_hash = hashlib.sha256(previous_manifest).hexdigest()
    snapshots.append((history / "manifests" / f"{manifest_hash}.jsonl", previous_manifest))
    for snapshot_path, data in snapshots:
        if snapshot_path.exists():
            if snapshot_path.read_bytes() != data:
                raise CorpusValidationError(f"Existing source-history snapshot is corrupt: {snapshot_path}")
            continue
        _atomic_write(snapshot_path, data)


def fetch_corpus(project_root: str | Path, refresh: bool = False) -> list[dict]:
    """Fetch only approved XML routes; otherwise verify and reuse the local cache.

    All downloads are validated before any writes. Each cache file and the final
    manifest are replaced atomically. Before a changed source is replaced,
    its previous bytes and manifest are retained in ignored, hash-addressed
    runs/source-history snapshots. Unchanged XML creates no history copy.
    An interrupted multi-file replacement is detected by SHA-256 checks.
    """
    root = _project_root(project_root)
    records = load_manifest(root)
    pending: list[tuple[Path, bytes]] = []
    updated: list[dict] = []
    for record in records:
        path = _cache_path(root, record)
        if path.exists() and not refresh:
            _, parsed = _read_verified_cache(root, record)
            updated.append({**record, **parsed})
            continue
        data = _download_xml(record["download_url"])
        _, parsed = _validate_article(data, record)
        if not refresh and record.get("sha256") and parsed["sha256"] != record["sha256"]:
            raise CorpusValidationError(f"Downloaded XML SHA-256 mismatch for {record['pmcid']}; use refresh=True to update")
        updated.append({
            **record, **parsed,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cache_path": str(path.relative_to(root)),
        })
        pending.append((path, data))
    if refresh:
        _preserve_source_history(root, pending)
    for path, data in pending:
        _atomic_write(path, data)
    if pending or updated != records:
        serialized = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in updated)
        _atomic_write(root / "corpus" / "manifest.jsonl", serialized.encode("utf-8"))
    return updated


def _content_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    parts: list[str] = []

    def visit(element: ET.Element) -> None:
        tag = _local_name(element.tag)
        if tag in _EXCLUDED_TAGS:
            return
        if tag in _BLOCK_TAGS:
            parts.append("\n")
        if element.text:
            parts.append(element.text)
        for child in element:
            visit(child)
            if child.tail:
                parts.append(child.tail)
        if tag in _BLOCK_TAGS:
            parts.append("\n")

    visit(node)
    return "\n".join(
        line for line in (" ".join(line.split()) for line in "".join(parts).splitlines()) if line
    )


def prepare_documents(
    project_root: str | Path,
    content_mode: str = "abstract",
    max_documents: int = 2,
    max_chars_per_document: int = 12000,
) -> list[dict]:
    """Prepare deterministic, bounded GraphRAG input from verified cached XML.

    This function never downloads or calls a model. The default is the first two
    abstracts in manifest order. References are excluded in both modes.
    """
    if content_mode not in {"abstract", "full_text"}:
        raise ValueError("content_mode must be 'abstract' or 'full_text'")
    for name, value in (("max_documents", max_documents), ("max_chars_per_document", max_chars_per_document)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    root = _project_root(project_root)
    documents = []
    for number, record in enumerate(load_manifest(root)[:max_documents], 1):
        article, parsed = _read_verified_cache(root, record)
        abstracts = article.findall("./front/article-meta/abstract")
        abstract = "\n\n".join(filter(None, (_content_text(node) for node in abstracts)))
        if not abstract:
            raise CorpusValidationError(f"Missing abstract for {record['pmcid']}")
        sections = ["Abstract\n" + abstract]
        if content_mode == "full_text":
            body = _content_text(article.find("body"))
            if not body:
                raise CorpusValidationError(f"Missing article body for {record['pmcid']}")
            sections.append("Body\n" + body)
        full_text = "\n\n".join(sections)
        text = full_text[:max_chars_per_document].rstrip()
        provenance = {
            "source_url": record["source_url"], "doi": record["doi"],
            "license": record["license"], "license_url": record["license_url"],
            "sha256": parsed["sha256"], "content_mode": content_mode,
            "char_count": len(text), "truncated": len(full_text) > max_chars_per_document,
        }
        raw_data = {
            **provenance, "pmid": record["pmid"], "pmcid": record["pmcid"],
            "year": record["year"], "authors": parsed["authors"],
            "document_type": record.get("document_type"), "topics": record.get("topics", []),
            "historical_test_corpus": True,
        }
        documents.append({
            "id": record["pmcid"], "human_readable_id": number,
            "title": record["title"], "text": text, "creation_date": str(record["year"]),
            "raw_data": json.dumps(raw_data, ensure_ascii=False, sort_keys=True),
            **provenance,
        })
    return documents
