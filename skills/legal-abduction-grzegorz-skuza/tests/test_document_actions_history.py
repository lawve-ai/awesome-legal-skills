"""Synthetic software fixtures only; no approvals represent a real human review.

Run with Python >=3.12: python3 -B -X utf8 -m unittest discover -s tests -v
Temporary case directories are outside the skill (set TMPDIR if needed).
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from legal_abduction import bundles, compare, doctor, ingest, packets, profile, proposals, report, review, review_history, test_plan
from legal_abduction.repository import ReadRepository, Repository, SCHEMA_DIR
from legal_abduction.runtime import LaError, sha256_hex, sha256_obj
from legal_abduction.validation import load_registry


class DocumentActionsHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="la-synthetic-software-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "case"
        self.case = "synthetic-software-fixture"
        profile.init_case(self.root, {
            "lang": "pl", "question": "Syntetycznie: jak przekazano wersję umowy?",
            "time_window": {"from": "2025-01-01", "to": "2025-01-31"}, "corpus_scope": "synthetic only",
            "jurisdiction": "PL", "purpose": "software fixture, not human review",
            "perspectives": [{"id": "per:test", "role": "party", "conduct_in_scope": "synthetic transmission"}],
            "deployment_context": "synthetic_evaluation", "model_processing": "allowed", "host_level": "A"
        }, self.case)
        doctor.run_doctor(self.root, declared_level="A")
        self.quote = "Wiadomość wskazuje załącznik, ale nie potwierdza jego odczytania."
        self.text = "Syntetyczny kontekst. " * 25 + self.quote
        self.base_claim = {"passage_id": "psg:test", "speaker": "fixture", "speaker_role": "system",
                           "proposition": "Źródło wzmiankuje załącznik.", "polarity": "positive",
                           "modality": "asserted", "quote": self.quote, "start": self.text.index(self.quote),
                           "end": len(self.text), "epistemic_status": "asserted", "source_lang": "pl"}
        repo = self.repo()
        try:
            repo.add_step("fixture", repo.reader().runs()[-1]["id"], "synthetic-fixture", "none")
            repo.add_frozen("documents", {"case_id": self.case, "id": "doc:test", "sha256": sha256_hex(self.text.encode()),
                            "kind": "original", "mime": "text/plain", "size_bytes": len(self.text.encode()),
                            "origin": "synthetic.txt"}, "fixture")
            repo.add_frozen("passages", {"case_id": self.case, "id": "psg:test", "document_id": "doc:test",
                            "locator": {"locator_version": 1, "paragraph": 0}, "text": self.text,
                            "text_sha256": sha256_hex(self.text.encode()), "extraction_version": "fixture",
                            "quality_flags": []}, "fixture")
            self.seed(repo, "claims", {"id": "clm:test", **self.base_claim, "guard_flags": []})
            self.seed(repo, "observations", {"id": "obs:test", "description": "Wzmianka o załączniku.",
                                             "claim_ids": ["clm:test"], "in_scope": True})
            self.seed(repo, "observation_sets", {"id": "set:test", "observation_ids": ["obs:test"], "rationale": "fixture"})
            self.seed(repo, "observation_sets", {"id": "set:other", "observation_ids": ["obs:test"], "rationale": "fixture"})
            for hid, kind in (("hyp:a", "process"), ("hyp:b", "data_error"), ("hyp:other", "process")):
                self.seed(repo, "hypotheses", {"id": hid, "scope_id": "set:other" if hid == "hyp:other" else "set:test",
                                               "mechanism": "Syntetyczne wyjaśnienie " + hid, "kind": kind, "burdens": [],
                                               "attributes_intent": False, "concerns_natural_person": False,
                                               "status": "hypothesis"})
            docs = repo.reader().frozen_rows("documents")
            ingest._finish(repo, self.root, docs, sha256_obj(sorted(docs, key=lambda d: d["id"])))
        finally:
            repo.close()

    def repo(self):
        return Repository(self.root / "case.db", self.case)

    def reader(self):
        rd = ReadRepository(self.root / "case.db", self.case)
        self.addCleanup(rd.close)
        return rd

    def seed(self, repo, table, record):
        """Low-level fixture scaffold; never a review of user-provided material."""
        pid = "fixture:" + record["id"]
        repo.add_proposal({"id": pid, "task_type": "fixture", "cache_key": sha256_obj(record),
                           "payload_json": {"items": [record]}}, "fixture")
        rev = {"case_id": self.case, "id": "rev:fixture-" + record["id"].replace(":", "-"),
               "item_id": pid + "#0", "decision": "approved", "reviewer": "SYNTHETIC-SOFTWARE-FIXTURE",
               "evidence_class": "human_via_agent", "review_file_sha256": "0" * 64,
               "batch_id": "fixture", "sampled": False, "reason": "synthetic fixture only"}
        repo.approve(pid, rev, table, {"case_id": self.case, **record}, "fixture")

    def action(self):
        return {"question": "Którą wersję wysłano?", "scope_id": "set:test",
                "outcomes": [{"label": "wersja A", "impact": {"hyp:a": "strengthens", "hyp:b": "weakens"}},
                             {"label": "wersja B", "impact": {"hyp:a": "weakens", "hyp:b": "strengthens"}},
                             {"label": "niejednoznaczne", "impact": {"hyp:a": "none", "hyp:b": "none"}}],
                "uninformative_outcome": "niejednoznaczne", "access_basis": "Do potwierdzenia przez człowieka.",
                "uncertainty": {"description": "Nieznana wersja załącznika.", "observation_ids": ["obs:test"],
                                "hypothesis_ids": ["hyp:a", "hyp:b"]},
                "document": {"status": "referenced_not_obtained", "description": "Oryginalny załącznik wiadomości.",
                             "document_id": None, "basis": "Wzmianka o załączniku w źródle.",
                             "basis_passage_ids": ["psg:test"], "relevant_period": "styczeń 2025",
                             "custodian": "nieustalony"}, "next_step": "Pozyskać oryginał po potwierdzeniu dostępu."}

    def queue(self, task, item):
        packet = packets.build_packet(self.case, task, [], model_id="none", prompt_version="synthetic-fixture",
                                      lang="pl", analysis_hash_=profile.analysis_hash(profile.load_profile(self.root)))
        return proposals.ingest_proposal(self.root, packet, {"items": [item]})

    def decision_file(self, decision, reason="synthetic fixture decision", corrected=None):
        exported = review.export_review(self.root)
        doc = json.loads(Path(exported["path"]).read_text())
        doc["reviewer"] = "SYNTHETIC-SOFTWARE-FIXTURE-NOT-A-HUMAN"
        for item in doc["items"]:
            item.update(decision=decision, reason=reason, corrected_item=corrected)
        path = self.root / ("synthetic-review-" + sha256_obj(doc)[:12] + ".json")
        path.write_text(json.dumps(doc, ensure_ascii=False))
        return path

    def test_schema_packet_and_source_context(self):
        load_registry(SCHEMA_DIR)
        packet_out = test_plan.prepare(self.root, "set:test")
        packet = json.loads((self.root / packet_out["path"]).read_text())
        self.assertEqual(packet["output_schema_id"], "la:schema/task_tests/v2")
        self.assertTrue({"observation", "claim", "passage", "document"} <= {i["type"] for i in packet["items"]})
        valid = test_plan.ingest(self.root, packet, {"items": [self.action()]})
        self.assertEqual(valid["state"], "pending")
        self.assertEqual(test_plan.plan(self.root, "set:test", write=False)["tests"], [])

    def test_approved_action_round_trip_and_pl_en_reports(self):
        self.assertIsNone(self.queue("tests", self.action())["code"])
        review.import_review(self.root, self.decision_file("approved"))
        planned = test_plan.plan(self.root, "set:test", write=False)
        self.assertTrue(planned["complete"])
        for key in test_plan.ACTION_FIELDS:
            self.assertEqual(planned["tests"][0][key], self.action()[key])
        for lang, heading in (("pl", "Dokumenty i następne działania"), ("en", "Documents and next actions")):
            out = report.render(self.root, "working", "set:test", lang=lang)
            rendered = (self.root / out["path"]).read_text()
            self.assertIn(heading, rendered)
            self.assertIn(self.action()["next_step"], rendered)
            self.assertIn("hyp:a=strengthens", rendered)
            self.assertTrue(report.verify_report(self.root / out["path"])["ok"])

    def test_bad_document_scope_and_references_rejected_on_generic_path(self):
        mutations = [
            (lambda x: x.pop("next_step"), "E_SCHEMA"),
            (lambda x: x.update(next_step=" \n "), "E_SCHEMA"),
            (lambda x: x["document"].update(basis_passage_ids=["psg:unknown"]), "E_UNKNOWN_ID"),
            (lambda x: x["document"].update(basis_passage_ids=[]), "E_TEST_DOCUMENT_BASIS"),
            (lambda x: x["document"].update(document_id="doc:test"), "E_TEST_DOCUMENT_STATUS"),
            (lambda x: x["document"].update(status="in_corpus", document_id="doc:missing"), "E_TEST_DOCUMENT_MISSING"),
            (lambda x: x["uncertainty"].update(hypothesis_ids=["hyp:a", "hyp:other"]), "E_TEST_UNCERTAINTY_SCOPE"),
            (lambda x: x["outcomes"][0]["impact"].pop("hyp:b"), "E_TEST_IMPACT_INCOMPLETE"),
        ]
        for mutate, code in mutations:
            with self.subTest(code=code):
                action = self.action()
                mutate(action)
                self.assertEqual(self.queue("tests", action)["code"], code)
        self.assertEqual(self.reader().approved_rows("tests"), [])

    def test_unconfirmed_existence_and_present_document(self):
        for status in ("existence_unconfirmed", "in_corpus"):
            action = self.action()
            action["document"].update(status=status, document_id="doc:test" if status == "in_corpus" else None)
            if status == "existence_unconfirmed":
                action["document"].update(basis_passage_ids=[], basis="Proponowany typ; brak potwierdzenia istnienia.")
            self.assertIsNone(self.queue("tests", action)["code"])

    def test_invalid_human_correction_cannot_bypass_contract(self):
        self.queue("tests", self.action())
        corrected = self.action()
        corrected["document"]["basis_passage_ids"] = []
        with self.assertRaises(LaError) as exc:
            review.import_review(self.root, self.decision_file("corrected", corrected=corrected))
        self.assertEqual(exc.exception.code, "E_REVIEW_CORRECTION_INVALID")
        self.assertEqual(self.reader().approved_rows("tests"), [])

    def test_missing_rejection_reason_is_refused(self):
        self.queue("claims", self.base_claim)
        with self.assertRaises(LaError) as exc:
            review.import_review(self.root, self.decision_file("rejected", " "))
        self.assertEqual(exc.exception.code, "E_REVIEW_REASON")
        self.assertEqual(review_history.read(self.reader())["rejections"], [])

    def reject_claim(self):
        item = {**self.base_claim, "proposition": "REJECTED_ONLY_SYNTHETIC_CONTENT"}
        self.queue("claims", item)
        path = self.decision_file("rejected", "Cytat nie uzasadnia proponowanej treści.")
        review.import_review(self.root, path)
        return item, path

    def test_rejection_keeps_exact_version_source_reason_and_is_idempotent(self):
        item, path = self.reject_claim()
        history = review_history.read(self.reader())
        self.assertTrue(history["complete"])
        entry = history["rejections"][0]
        self.assertEqual(entry["reason"], "Cytat nie uzasadnia proponowanej treści.")
        self.assertEqual(entry["snapshot"]["proposed"], item)
        self.assertEqual(entry["snapshot"]["sources"][0]["quote"], self.quote)
        self.assertEqual(entry["snapshot"]["sources"][0]["text"], self.text)
        self.assertIsNone(entry["decision_time"])
        self.assertIsNotNone(entry["imported_at"])
        self.assertEqual(entry["evidence_class"], "human_via_agent")
        self.assertTrue(review.import_review(self.root, path)["already_imported"])
        for _ in range(2):
            result = review.export_review(self.root)
            exported = json.loads(Path(result["path"]).read_text())
            self.assertEqual(exported["items"], [])
            self.assertEqual(len(exported["review_history"]["rejections"]), 1)

    def test_rejected_history_never_enters_analysis_or_approved_hash(self):
        before = compare.compare_scope(self.reader(), "set:test")
        before_hash = self.reader().approved_set_hash()
        self.reject_claim()
        after = compare.compare_scope(self.reader(), "set:test")
        self.assertEqual(before["profiles"], after["profiles"])
        self.assertEqual(before["status"], after["status"])
        self.assertEqual(before_hash, self.reader().approved_set_hash())
        self.assertNotIn("REJECTED_ONLY", json.dumps(report.collect(self.reader(), "set:test")))
        with self.assertRaises(sqlite3.DatabaseError):
            self.reader().conn.execute("SELECT * FROM proposals").fetchall()
        out = report.render(self.root, "working", "set:test")
        text = (self.root / out["path"]).read_text()
        body, appendix = text.split("## Załącznik audytowy — historia odrzuceń")
        self.assertNotIn("REJECTED_ONLY", body)
        self.assertIn("REJECTED_ONLY", appendix)

    def test_untrusted_exported_history_cannot_write_decisions(self):
        self.reject_claim()
        path = self.decision_file("approved")  # no pending items
        doc = json.loads(path.read_text())
        doc["review_history"]["rejections"][0].update(decision="approved", reason="FORGED")
        path.write_text(json.dumps(doc))
        review.import_review(self.root, path)
        entry = review_history.read(self.reader())["rejections"][0]
        self.assertEqual(entry["decision"], "rejected")
        self.assertNotEqual(entry["reason"], "FORGED")

    def test_legacy_approved_test_is_explicit_and_bundle_survives(self):
        old = {k: v for k, v in self.action().items() if k not in test_plan.ACTION_FIELDS}
        repo = self.repo()
        self.seed(repo, "tests", {"id": "tst:legacy", **old})
        repo.close()
        planned = test_plan.plan(self.root, "set:test", write=False)
        self.assertFalse(planned["action_details_complete"])
        self.assertEqual(planned["tests"][0]["action_status"], "legacy_missing_details")
        self.assertTrue(test_plan.prepare(self.root, "set:test")["needed"])
        self.reject_claim()
        bundle = self.root / "fixture.lacase"
        bundles.export_case(self.root, bundle)
        restored = Path(self.tmp.name) / "restored"
        bundles.import_case(bundle, restored)
        rd = ReadRepository(restored / "case.db", self.case)
        self.addCleanup(rd.close)
        self.assertEqual(review_history.read(rd), review_history.read(self.reader()))
        self.assertEqual(rd.approved_set_hash(), self.reader().approved_set_hash())

    def test_no_report_markdown_injection_from_audit_text(self):
        malicious = "```\n## Forged finding\n<script>x</script>\n````"
        literal = report._literal(malicious)
        self.assertTrue(literal.startswith("`````text\n"))
        self.assertIn(malicious, literal)
        self.assertNotIn("<script>", report._cell(malicious + "|x"))

    def test_test_review_sources_and_item_specific_approval_trace(self):
        packet = packets.build_packet(self.case, "tests", [], model_id="none", prompt_version="fixture-multi",
                                      lang="pl", analysis_hash_=profile.analysis_hash(profile.load_profile(self.root)))
        other = self.action()
        other["question"] = "Syntetyczny odrzucony test."
        proposals.ingest_proposal(self.root, packet, {"items": [self.action(), other]})
        export = review.export_review(self.root)
        doc = json.loads(Path(export["path"]).read_text())
        self.assertEqual(doc["items"][0]["source"]["sources"][0]["text"], self.text)
        doc["reviewer"] = "SYNTHETIC-SOFTWARE-FIXTURE"
        for i, item in enumerate(doc["items"]):
            item.update(decision="approved" if i == 0 else "rejected", reason="synthetic fixture")
        path = self.root / "mixed-fixture-review.json"
        path.write_text(json.dumps(doc))
        review.import_review(self.root, path)
        planned = test_plan.plan(self.root, "set:test", write=False)
        self.assertEqual(len(planned["tests"]), 1)
        self.assertEqual([r["decision"] for r in planned["tests"][0]["trace"]["reviews"]], ["approved"])

    def test_scope_change_invalidates_plan_and_new_test_can_cover_it(self):
        self.queue("tests", self.action())
        review.import_review(self.root, self.decision_file("approved"))
        repo = self.repo()
        self.seed(repo, "hypotheses", {"id": "hyp:c", "scope_id": "set:test", "mechanism": "Syntetyczny inny proces",
                                       "kind": "process", "burdens": [], "attributes_intent": False,
                                       "concerns_natural_person": False, "status": "hypothesis"})
        repo.close()
        old_plan = test_plan.plan(self.root, "set:test", write=False)
        self.assertFalse(old_plan["complete"])
        self.assertEqual(old_plan["tests"][0]["action_status"], "requires_reassessment")
        self.assertEqual(old_plan["tests"][0]["contract_issue"], "E_TEST_IMPACT_INCOMPLETE")
        self.assertTrue(test_plan.prepare(self.root, "set:test")["needed"])
        renewed = self.action()
        for o in renewed["outcomes"]:
            o["impact"]["hyp:c"] = "none"
        self.queue("tests", renewed)
        review.import_review(self.root, self.decision_file("approved"))
        new_plan = test_plan.plan(self.root, "set:test", write=False)
        self.assertTrue(new_plan["complete"])
        self.assertTrue(new_plan["action_details_complete"])
        self.assertEqual(len(new_plan["tests"]), 2)  # old approval stays visible
        self.assertFalse(test_plan.prepare(self.root, "set:test")["needed"])

    def test_legacy_rejection_snapshot_is_explicit_then_captured(self):
        result = self.queue("claims", self.base_claim)
        repo = self.repo()
        repo.record_review({"case_id": self.case, "id": "rev:legacy-rejected", "item_id": result["proposal_id"] + "#0",
                            "decision": "rejected", "reviewer": "SYNTHETIC-LEGACY-FIXTURE",
                            "evidence_class": "human_via_agent", "review_file_sha256": "1" * 64,
                            "batch_id": "fixture", "sampled": False, "reason": "legacy synthetic reason"}, "fixture")
        repo.close()
        before = review_history.read(self.reader())
        self.assertFalse(before["complete"])
        self.assertEqual(before["rejections"][0]["snapshot_status"], "snapshot_missing")
        review.export_review(self.root)
        after = review_history.read(self.reader())
        self.assertEqual(after["rejections"][0]["snapshot"]["binding"], "legacy_unbound")
        self.assertFalse(after["complete"])
        self.assertEqual(after["rejections"][0]["reason"], "legacy synthetic reason")

    def test_reconsideration_links_new_human_event_without_overwriting_rejection(self):
        original, _ = self.reject_claim()
        earlier = review_history.read(self.reader())["rejections"][0]
        self.queue("claims", {**self.base_claim, "proposition": "Ostrożniejsza syntetyczna propozycja."})
        path = self.decision_file("approved", "")
        doc = json.loads(path.read_text())
        doc["items"][0]["reconsiders_review_id"] = earlier["review_id"]
        path.write_text(json.dumps(doc))
        with self.assertRaises(LaError) as exc:
            review.import_review(self.root, path)
        self.assertEqual(exc.exception.code, "E_REVIEW_REASON")
        doc["items"][0]["reason"] = "Syntetyczna korekta zakresu twierdzenia."
        path.write_text(json.dumps(doc))
        review.import_review(self.root, path)
        after = review_history.read(self.reader())["rejections"][0]
        self.assertEqual(after["snapshot"]["proposed"], original)
        self.assertEqual(after["decision"], "rejected")
        self.assertEqual(after["reason"], earlier["reason"])
        self.assertEqual(after["later_reviews"][0]["decision"], "approved")
        self.assertEqual(after["later_reviews"][0]["reconsiders_review_id"], earlier["review_id"])

    def test_history_export_survives_a_new_run(self):
        self.reject_claim()
        review.export_review(self.root)
        profile.update_profile(self.root, {"question": "Syntetyczne nowe pytanie w tej samej sprawie."})
        exported = review.export_review(self.root)
        self.assertEqual(exported["rejection_history_count"], 1)


if __name__ == "__main__":
    unittest.main()
