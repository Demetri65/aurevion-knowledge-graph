"""Integrity and scope tests for the source ingestion boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aurevion_knowledge_lab.corpus import (
    CorpusValidationError,
    fetch_corpus,
    load_manifest,
    prepare_documents,
)


def record(pmcid="PMC5477153", pmid="28642676", doi="10.1186/s12970-017-0177-8"):
    return {
        "id": pmcid, "pmcid": pmcid, "pmid": pmid, "doi": doi,
        "title": "Test article", "year": 2017,
        "source_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/",
        "license": "CC-BY-4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "download_url": f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
    }


def xml(item, *, pmcid=None, license_kind="by", abstract="Abstract finding."):
    return f'''<article><front><article-meta>
      <article-id pub-id-type="pmcid">{pmcid or item["pmcid"]}</article-id>
      <article-id pub-id-type="pmid">{item["pmid"]}</article-id>
      <article-id pub-id-type="doi">{item["doi"]}</article-id>
      <title-group><article-title>Test article</article-title></title-group>
      <contrib-group><contrib contrib-type="author"><name>
        <surname>Researcher</surname><given-names>Alice</given-names>
      </name></contrib></contrib-group>
      <permissions><license><license-p>Licensed at
        https://creativecommons.org/licenses/{license_kind}/4.0/
      </license-p></license></permissions>
      <abstract><p>{abstract}</p></abstract>
    </article-meta></front><body><sec><title>Results</title><p>Body finding.</p>
      <ref-list><ref><mixed-citation>EMBEDDED BIBLIOGRAPHY</mixed-citation></ref></ref-list>
    </sec></body><back><ref-list><ref><mixed-citation>
      BACK BIBLIOGRAPHY
    </mixed-citation></ref></ref-list></back></article>'''.encode()


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "corpus" / "papers").mkdir(parents=True)
        self.item = record()
        self.install([self.item], [xml(self.item)])

    def install(self, items, payloads):
        for item, payload in zip(items, payloads):
            item["sha256"] = hashlib.sha256(payload).hexdigest()
            (self.root / "corpus" / "papers" / f"{item['pmcid']}.xml").write_bytes(payload)
        self.write_manifest(items)

    def write_manifest(self, items):
        (self.root / "corpus" / "manifest.jsonl").write_text(
            "".join(json.dumps(item) + "\n" for item in items), encoding="utf-8"
        )

    def test_default_abstract_is_deterministic_and_contains_provenance(self):
        documents = prepare_documents(self.root)
        self.assertEqual(documents, prepare_documents(self.root))
        document = documents[0]
        self.assertIn("Abstract finding.", document["text"])
        self.assertNotIn("Body finding.", document["text"])
        self.assertEqual(document["creation_date"], "2017")
        self.assertEqual(document["id"], self.item["pmcid"])
        self.assertEqual(document["human_readable_id"], 1)
        self.assertEqual(document["char_count"], len(document["text"]))
        metadata = json.loads(document["raw_data"])
        self.assertEqual(metadata["authors"], ["Alice Researcher"])
        self.assertEqual(metadata["sha256"], self.item["sha256"])
        self.assertTrue(metadata["historical_test_corpus"])

    def test_full_text_excludes_embedded_and_back_bibliographies(self):
        text = prepare_documents(self.root, content_mode="full_text")[0]["text"]
        self.assertIn("Abstract finding.", text)
        self.assertIn("Results", text)
        self.assertIn("Body finding.", text)
        self.assertNotIn("BIBLIOGRAPHY", text)

    def test_author_type_can_be_inherited_from_contribution_group(self):
        payload = xml(self.item).replace(
            b'<contrib-group><contrib contrib-type="author">',
            b'<contrib-group content-type="author"><contrib>'
        )
        self.install([self.item], [payload])
        document = prepare_documents(self.root)[0]
        self.assertEqual(json.loads(document["raw_data"])["authors"], ["Alice Researcher"])

    def test_scope_caps_text_and_selects_first_records_in_manifest_order(self):
        other = record("PMC3879660", "24299050", "10.1186/1550-2783-10-53")
        third = record("PMC5470183", "28630601", "10.1186/s12970-017-0174-y")
        self.install([self.item, other, third], [xml(self.item), xml(other), xml(third)])
        documents = prepare_documents(self.root, max_chars_per_document=12)
        self.assertEqual([doc["id"] for doc in documents], [self.item["id"], other["id"]])
        self.assertTrue(all(doc["char_count"] <= 12 and doc["truncated"] for doc in documents))

    def test_xml_identity_mismatch_is_rejected_even_with_matching_hash(self):
        self.install([self.item], [xml(self.item, pmcid="PMC3879660")])
        with self.assertRaisesRegex(CorpusValidationError, "pmcid mismatch"):
            prepare_documents(self.root)

    def test_noncommercial_xml_license_is_rejected_even_with_matching_hash(self):
        self.install([self.item], [xml(self.item, license_kind="by-nc")])
        with self.assertRaisesRegex(CorpusValidationError, "license mismatch"):
            prepare_documents(self.root)

    def test_changed_cache_hash_is_rejected(self):
        path = self.root / "corpus" / "papers" / f"{self.item['pmcid']}.xml"
        path.write_bytes(xml(self.item, abstract="Changed finding."))
        with self.assertRaisesRegex(CorpusValidationError, "SHA-256 mismatch"):
            prepare_documents(self.root)

    def test_manifest_rejects_non_allowlisted_network_route(self):
        self.item["download_url"] = "https://example.org/article.xml"
        self.write_manifest([self.item])
        with self.assertRaisesRegex(CorpusValidationError, "Unapproved download route"):
            load_manifest(self.root)

    def test_existing_cache_never_downloads(self):
        with patch("aurevion_knowledge_lab.corpus._download_xml") as download:
            result = fetch_corpus(self.root)
        download.assert_not_called()
        self.assertEqual(result[0]["sha256"], self.item["sha256"])

    def test_refresh_validates_all_downloads_before_replacing_any_file(self):
        other = record("PMC3879660", "24299050", "10.1186/1550-2783-10-53")
        self.install([self.item, other], [xml(self.item), xml(other)])
        original_manifest = (self.root / "corpus" / "manifest.jsonl").read_bytes()
        original_xml = (self.root / "corpus" / "papers" / f"{self.item['pmcid']}.xml").read_bytes()
        with patch("aurevion_knowledge_lab.corpus._download_xml", side_effect=[
            xml(self.item, abstract="Updated finding."), xml(other, license_kind="by-nc")
        ]):
            with self.assertRaisesRegex(CorpusValidationError, "license mismatch"):
                fetch_corpus(self.root, refresh=True)
        self.assertEqual((self.root / "corpus" / "manifest.jsonl").read_bytes(), original_manifest)
        self.assertEqual((self.root / "corpus" / "papers" / f"{self.item['pmcid']}.xml").read_bytes(), original_xml)

    def test_refresh_updates_manifest_hash_and_prepares_new_cache(self):
        replacement = xml(self.item, abstract="Updated finding.")
        with patch("aurevion_knowledge_lab.corpus._download_xml", return_value=replacement) as download:
            metadata = fetch_corpus(self.root, refresh=True)
        download.assert_called_once_with(self.item["download_url"])
        self.assertEqual(metadata[0]["sha256"], hashlib.sha256(replacement).hexdigest())
        self.assertIn("Updated finding.", prepare_documents(self.root)[0]["text"])
        self.assertEqual(load_manifest(self.root)[0]["sha256"], metadata[0]["sha256"])

    def test_refresh_retains_previous_source_and_manifest_without_unchanged_duplicates(self):
        original_xml = xml(self.item)
        original_manifest = (self.root / "corpus" / "manifest.jsonl").read_bytes()
        replacement = xml(self.item, abstract="Updated finding.")
        with patch("aurevion_knowledge_lab.corpus._download_xml", return_value=replacement):
            fetch_corpus(self.root, refresh=True)
        history = self.root / "runs" / "source-history"
        xml_snapshot = history / self.item["pmcid"] / f"{self.item['sha256']}.xml"
        manifest_snapshot = history / "manifests" / f"{hashlib.sha256(original_manifest).hexdigest()}.jsonl"
        self.assertEqual(xml_snapshot.read_bytes(), original_xml)
        self.assertEqual(manifest_snapshot.read_bytes(), original_manifest)
        self.assertIn("Updated finding.", prepare_documents(self.root)[0]["text"])
        snapshots_before = sorted(path.relative_to(history) for path in history.rglob("*") if path.is_file())
        with patch("aurevion_knowledge_lab.corpus._download_xml", return_value=replacement):
            fetch_corpus(self.root, refresh=True)
        snapshots_after = sorted(path.relative_to(history) for path in history.rglob("*") if path.is_file())
        self.assertEqual(snapshots_before, snapshots_after)
        self.assertEqual(len(snapshots_after), 2)

    def test_failed_history_backup_leaves_current_source_and_manifest_intact(self):
        original_manifest = (self.root / "corpus" / "manifest.jsonl").read_bytes()
        path = self.root / "corpus" / "papers" / f"{self.item['pmcid']}.xml"
        original_xml = path.read_bytes()
        with patch("aurevion_knowledge_lab.corpus._download_xml", return_value=xml(self.item, abstract="Updated.")):
            with patch("aurevion_knowledge_lab.corpus._atomic_write", side_effect=OSError("No backup space")):
                with self.assertRaisesRegex(OSError, "No backup space"):
                    fetch_corpus(self.root, refresh=True)
        self.assertEqual(path.read_bytes(), original_xml)
        self.assertEqual((self.root / "corpus" / "manifest.jsonl").read_bytes(), original_manifest)

    def test_invalid_mode_or_unbounded_limits_are_rejected(self):
        for kwargs in ({"content_mode": "pdf"}, {"max_documents": 0}, {"max_chars_per_document": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                prepare_documents(self.root, **kwargs)


if __name__ == "__main__":
    unittest.main()
