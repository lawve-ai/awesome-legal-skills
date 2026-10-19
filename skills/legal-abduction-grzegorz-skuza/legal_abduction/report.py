"""Reports: working profile and `exhibit`, with render gates (LA-020, R17).

Everything that goes into the report body is read through `ReadRepository` from the approved
set and frozen records (the SQLite authorizer denies `proposals`); the only queue-aware step is
the shared gate engine `review.evaluate_gates` (pending counts), which runs before rendering and
whose result is just gate findings. Templates are plain text with `{{name}}` placeholders and
no logic; blocks are built here from `strings.json` labels. Quotes are inserted literally.

Refusals happen before anything is written: a blocked report leaves no report, manifest or bundle.
The structure is PROVISIONAL (PRD R17): Report chapter 15 is unavailable (REPORT_SOURCE), so the
DoD item "structure equals the real Report" stays blocked. `exhibit` stays unpublishable until Q12.
"""
from __future__ import annotations

import datetime
import html
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from . import __version__, bundles, compare, facts, review, review_history, revisit, search, staleness, test_plan, uncovered
from .profile import load_profile, render_hash
from .repository import ReadRepository
from .runtime import EXIT_POLICY, EXIT_USAGE, LaError, atomic_write, canonical_json, sha256_hex, sha256_obj

SKILL_NAME = "legal-abduction"
POLICY_VERSION = "exhibit-use/1-working"
STRUCTURE_SOURCE = "provisional: PRD R17 (Report chapter 15 unavailable: REPORT_SOURCE)"
ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "assets" / "templates"
POLICY_DIR = ROOT / "docs" / "policy"
PROFILES = ("working", "exhibit")
LANGS = ("pl", "en")
_PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")
BLOCK_KEYS = {
    "working": {"title", "status_paragraph", "banner", "header", "method", "limits", "scope", "hypotheses",
                "observations", "matrix", "comparison", "uncovered", "tests", "searches", "review", "stale",
                "model_summary", "reproduction", "actions", "rejection_history"},
    "exhibit": {"title", "status_paragraph", "banner", "header", "method", "limits", "scope", "hypotheses",
                "observations", "matrix", "comparison", "uncovered", "tests", "searches", "review", "stale",
                "policy", "statement", "reproduction", "actions", "rejection_history"},
}


def _err(code: str, en: str, pl: str, exit_code: int = EXIT_USAGE, **ids: str) -> LaError:
    return LaError(code, en, pl, exit_code, ids or None)


# --- templates --------------------------------------------------------------------------------------

def template_placeholders(text: str) -> set[str]:
    rest = _PLACEHOLDER.sub("", text)
    if "{{" in rest or "}}" in rest or "{%" in rest or "%}" in rest:
        raise _err("E_TEMPLATE_LOGIC", "Templates may contain only {{name}} placeholders.",
                   "Szablony mogą zawierać wyłącznie symbole zastępcze {{nazwa}}.")
    return set(_PLACEHOLDER.findall(text))


def load_templates(lang: str) -> tuple[dict[str, str], dict[str, str]]:
    if lang not in LANGS:
        raise _err("E_LANG", "Report language must be pl or en.", "Język raportu: pl lub en.")
    strings = json.loads((TEMPLATES / lang / "strings.json").read_text(encoding="utf-8"))
    templates = {p: (TEMPLATES / lang / f"{p}.md").read_text(encoding="utf-8") for p in PROFILES}
    for p, t in templates.items():
        if template_placeholders(t) != BLOCK_KEYS[p]:
            raise _err("E_TEMPLATE_PLACEHOLDER", "The template placeholders differ from the block set.",
                       "Symbole zastępcze szablonu różnią się od zbioru bloków.", template=f"{lang}/{p}")
    return strings, templates


def fill(template: str, values: dict[str, str]) -> str:
    """Single pass: values are inserted verbatim and never re-scanned."""
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def policy_files() -> dict[str, str]:
    return {lang: sha256_hex((POLICY_DIR / f"exhibit-use.{lang}.md").read_bytes()) for lang in LANGS}


# --- facts (approved set only) ---------------------------------------------------------------------

def _quote_block(text: str) -> str:
    return "\n".join("> " + line for line in text.split("\n"))


def _loc(passage: dict[str, Any], docs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    doc = docs.get(passage["document_id"])
    if doc is None or not doc.get("sha256"):
        return None
    original = docs.get(doc["derived_from"]) if doc["kind"] == "derived" else doc
    if original is None:
        return None
    return {"document_id": original["id"], "origin": original["origin"], "sha256": original["sha256"],
            "passage_id": passage["id"], "locator": passage["locator"]}


def _loc_text(loc: dict[str, Any]) -> str:
    return (f"{loc['document_id']} ({loc['origin']}, sha256 {loc['sha256'][:12]}…) · {loc['passage_id']} · "
            + json.dumps(loc["locator"], sort_keys=True, ensure_ascii=False))


def collect(rd: ReadRepository, scope_id: str, *, coverage_threshold: float | None = None) -> dict[str, Any]:
    sets = {s["id"]: s for s in rd.approved_rows("observation_sets")}
    if scope_id not in sets:
        raise _err("E_SCOPE_UNKNOWN", "No approved ObservationSet with this id.",
                   "Brak zatwierdzonego ObservationSet o tym id.", scope_id=scope_id)
    docs = {d["id"]: d for d in rd.frozen_rows("documents")}
    psg = {p["id"]: p for p in rd.frozen_rows("passages")}
    clm = {c["id"]: c for c in rd.approved_rows("claims")}
    obs = {o["id"]: o for o in rd.approved_rows("observations")}
    hyps = sorted((h for h in rd.approved_rows("hypotheses") if h["scope_id"] == scope_id), key=lambda h: h["id"])
    assessments = {(a["observation_id"], a["hypothesis_id"]): a for a in rd.current_assessments()}
    observations, unresolved, bad_quotes = [], [], []
    for oid in facts.effective_observation_ids(rd, sets[scope_id]):  # withdrawn out, replacements in
        o = obs[oid]
        claims_out = []
        for cid in o["claim_ids"]:
            c = clm.get(cid)
            p = psg.get(c["passage_id"]) if c else None
            loc = _loc(p, docs) if p else None
            if loc is None:
                unresolved.append(f"{oid}/{cid}")
                continue
            if p["text"][c["start"]:c["end"]] != c["quote"]:
                bad_quotes.append(cid)
            claims_out.append({"claim": c, "locator": loc})
        if not claims_out:
            unresolved.append(oid)
        observations.append({"observation": o, "claims": claims_out})
    return {"set": sets[scope_id], "docs": docs, "psg": psg, "observations": observations, "hypotheses": hyps,
            "assessments": assessments, "unresolved": sorted(set(unresolved)), "bad_quotes": sorted(set(bad_quotes)),
            "comparison": compare.compare_scope(rd, scope_id, coverage_threshold=coverage_threshold)}


# --- blocks ------------------------------------------------------------------------------------------

def _cell(value: Any) -> str:
    """Keep untrusted text inside one Markdown table cell."""
    text = html.escape(str(value), quote=False)
    for char in ("\\", "`", "*", "_", "[", "]", "|", "~"):
        text = text.replace(char, "\\" + char)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _literal(text: str, language: str = "text") -> str:
    """A source cannot close the fence and inject report headings/HTML."""
    fence = "`" * max(3, max((len(s) + 1 for s in re.findall(r"`+", text)), default=0))
    return f"{fence}{language}\n{text}\n{fence}"


def _action_table(S: dict[str, str], plan: dict[str, Any], f: dict[str, Any]) -> str:
    lines = [S["actions_note"], "", S["actions_columns"], "| --- | --- | --- | --- | --- |"]
    for t in plan["tests"]:
        if t["action_status"] != "document_linked":
            note = S["actions_reassess"].format(issue=t["contract_issue"]) if t["contract_issue"] else S["actions_legacy"]
            cells = [t["id"], t["question"], note, "—", t["uninformative_outcome"]]
        else:
            u, d = t["uncertainty"], t["document"]
            locators = []
            for pid in d["basis_passage_ids"]:
                p = f["psg"].get(pid)
                loc = _loc(p, f["docs"]) if p else None
                locators.append(_loc_text(loc) if loc else f"{pid}: {S['actions_source_missing']}")
            document = "\n".join([d["description"], S["document_" + d["status"]], d["document_id"] or "—",
                                   d["basis"], *locators])
            action = "\n".join([t["next_step"], S["actions_period"].format(value=d["relevant_period"]),
                                 S["actions_custodian"].format(value=d["custodian"]),
                                 S["actions_access"].format(value=t["access_basis"])])
            outcomes = [o["label"] + ": " + ", ".join(f"{hid}={impact}" for hid, impact in sorted(o["impact"].items()))
                        for o in t["outcomes"]]
            outcomes.append(S["actions_inconclusive"].format(value=t["uninformative_outcome"]))
            cells = [t["id"], u["description"] + "\n" + ", ".join(u["observation_ids"] + u["hypothesis_ids"]),
                     document, action, "\n".join(outcomes)]
        lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    if not plan["tests"]:
        return S["actions_note"] + "\n\n" + S["actions_none"]
    return "\n".join(lines)


def _rejection_appendix(S: dict[str, str], history: dict[str, Any]) -> str:
    lines = [S["audit_note"]]
    if not history["rejections"]:
        return "\n\n".join([*lines, S["audit_none"]])
    for entry in history["rejections"]:
        lines += ["", "### " + entry["review_id"], "", S["audit_metadata"],
                  _literal(json.dumps({k: v for k, v in entry.items() if k != "snapshot"},
                                      ensure_ascii=False, indent=2), "json")]
        snapshot = entry["snapshot"]
        if not snapshot:
            lines += [S["audit_missing"]]
            continue
        lines += [S["audit_proposal"],
                  _literal(json.dumps({k: snapshot[k] for k in ("task_type", "item_hash", "binding", "proposed")},
                                      ensure_ascii=False, indent=2), "json")]
        for source in snapshot["sources"]:
            lines += [S["audit_source"],
                      _literal(json.dumps({k: v for k, v in source.items() if k not in ("text", "quote")},
                                          ensure_ascii=False, indent=2), "json")]
            if "text" in source:
                lines += [_literal(source["text"])]
            if "quote" in source:
                lines += [S["audit_quote"], _literal(source["quote"])]
        if not snapshot["sources"]:
            lines += [S["audit_no_source"]]
    return "\n\n".join(lines)

def _reason_text(S: dict[str, str], r: dict[str, Any]) -> str:
    code = r["code"]
    if code == "tie":
        return S["reason_tie"].format(ids=", ".join(r["hypothesis_ids"]))
    if code == "missing_assessments":
        return S["reason_missing_assessments"].format(count=r["count"])
    if code == "bridge_rule_without_basis":
        return S["reason_bridge_rule_without_basis"].format(ids=", ".join(r["assumption_ids"]))
    if code == "insufficient_coverage":
        return S["reason_insufficient_coverage"].format(ratio=r["ratio"], threshold=r["threshold"])
    if code == "stale_records":
        return S["reason_stale_records"].format(ids=", ".join(r["ids"]))
    return S["reason_no_approved_hypotheses"]


def status_paragraph(S: dict[str, str], cmp_: dict[str, Any], pending: int) -> str:
    st = cmp_["status"]
    if not cmp_["profiles"]:
        text = S["status_no_hypotheses"]
    elif st == "determined":
        text = S["status_determined"].format(leader=cmp_["leader"])
    elif st == "unstable":
        text = S["status_unstable"].format(leader=cmp_["leader"], families=", ".join(cmp_["unstable_families"]))
    else:
        text = S["status_underdetermined"].format(reasons="; ".join(_reason_text(S, r) for r in cmp_["underdetermined_reasons"]))
    if cmp_["partial"]:
        text += S["status_partial_suffix"].format(count=len(cmp_["missing_assessments"]))
    if pending:
        text += S["partial_pending"].format(count=pending)
    return text


def _stale_block(S: dict[str, str], stale: dict[str, list[str]], info: dict[str, Any] | None) -> str:
    """Changed facts with their void cells, then each judgment to revisit with impact, reason and path."""
    if info is None:
        return "\n".join(S["stale_line"].format(id=i) for i in stale) or S["stale_none"]
    lines: list[str] = []
    voids: dict[str, list[str]] = {}
    for v in info["void_assessments"]:
        voids.setdefault(v["observation_id"], []).append(v["id"])
    if info["changed_facts"]:
        lines.append(S["facts_header"])
        for c in info["changed_facts"]:
            key = "fact_changed" if c["change"] == "changed" else "fact_withdrawn"
            lines.append(S[key].format(id=c["fact_id"], replacement=c["replacement_id"] or "—", reason=c["reason"],
                                       event=c["event"], evidence=c["evidence_class"]))
            if voids.get(c["fact_id"]):
                lines.append(S["fact_void"].format(ids=", ".join(sorted(voids[c["fact_id"]]))))
    detail = {i["id"]: i for i in info["items"]}
    if stale:
        if lines:
            lines.append("")
        lines.append(S["revisit_header"])
    for rid in stale:
        item = detail.get(rid)
        if item is None or not item["triggers"]:
            lines.append(S["stale_line"].format(id=rid))
            continue
        paths = [" → ".join(t["path"]) for t in item["triggers"] if t.get("path")]
        lines.append(S["stale_why"].format(id=rid, impact=S["impact_" + item["impact"]],
                                           reasons="; ".join(t["reason"] for t in item["triggers"]),
                                           path=" | ".join(paths) if paths else "—"))
    return "\n".join(lines) or S["stale_none"]


def build_blocks(S: dict[str, str], profile: dict[str, Any], run: dict[str, Any], f: dict[str, Any], *, profile_name: str,
                 lang: str, date: str, scope_id: str, rd: ReadRepository, findings: list[dict[str, Any]],
                 excerpt: dict[str, Any] | None, summary: str | None, stale: dict[str, list[str]],
                 searches_state: list[dict[str, Any]], plan: dict[str, Any], reproduction: dict[str, Any] | None,
                 revisit_info: dict[str, Any] | None = None) -> dict[str, str]:
    omit_obs = set((excerpt or {}).get("omit_observation_ids", []))
    omit_hyp = set((excerpt or {}).get("omit_hypothesis_ids", []))
    cmp_ = f["comparison"]
    hyps = [h for h in f["hypotheses"] if h["id"] not in omit_hyp]
    observations = [o for o in f["observations"] if o["observation"]["id"] not in omit_obs]
    approved = [r for r in rd.review_rows() if r["decision"] in review.ADMITTING]
    total = len(approved)
    classes: dict[str, int] = {}
    for r in approved:
        classes[r["evidence_class"]] = classes.get(r["evidence_class"], 0) + 1
    bulk = sum(1 for r in approved if r.get("mode") == "bulk")
    pending = next((x.get("count", 0) for x in findings if x["gate"] == "pending_review"), 0)
    declarations = sorted({x["gate"] for x in findings if x["outcome"] in ("warn_and_declaration_required",
                                                                           "header_declaration_required")})
    agents = [r[0] for r in rd.conn.execute("SELECT DISTINCT agent FROM steps WHERE case_id = ? ORDER BY agent",
                                            (rd.case_id,))]
    models = sorted({a for a in agents if a.startswith("model:")} | ({run["model_id"]} - {"none"}))
    overrides = [b for b in rd.frozen_rows("value_records") if b.get("kind") == "budget_override"]
    ex_policy = profile_name == "exhibit"
    header = [f"- {S['lbl_skill']}: {SKILL_NAME}", f"- {S['lbl_code_version']}: {__version__}",
              f"- {S['lbl_model']}: {', '.join(models) if models else S['lbl_model_none']}",
              f"- {S['lbl_host_level']}: {profile.get('host_level', 'A')}",
              f"- {S['lbl_context']}: {profile['deployment_context']}", f"- {S['lbl_date']}: {date}",
              f"- {S['lbl_profile']}: {profile_name}", f"- {S['lbl_language']}: {lang}",
              f"- {S['lbl_corpus_hash']}: {run['corpus_hash']}", f"- {S['lbl_analysis_hash']}: {run['analysis_hash']}",
              f"- {S['lbl_render_hash']}: {render_hash({**profile, 'lang': lang, 'report_profile': profile_name})}",
              f"- {S['lbl_approved_set_hash']}: {rd.approved_set_hash()}", f"- {S['lbl_chain_head']}: {rd.chain_head()}",
              f"- {S['lbl_chain_check']}: {S['lbl_chain_ok']}", f"- {S['lbl_scope']}: {scope_id}"]
    if ex_policy:
        header.append(f"- {S['lbl_policy']}: {POLICY_VERSION}")
    header.append(f"- {S['lbl_evidence_shares']}: " + (", ".join(
        f"{k} {v} {S['lbl_of']} {total}" for k, v in sorted(classes.items())) or S["lbl_none"]))
    header.append(f"- {S['lbl_bulk_share']}: {bulk} {S['lbl_of']} {total}")
    header.append(f"- {S['lbl_budget_override']}: " + ("; ".join(f"{o['task_type']}: {o['reason']}" for o in overrides)
                                                     or S["lbl_none"]))
    if declarations:
        header.append("- " + S["lbl_declaration_required"].format(reasons=", ".join(declarations)))
    if ex_policy:
        header.append("- " + (S["lbl_excerpt"].format(
            observations=len(omit_obs), hypotheses=len(omit_hyp), reason=excerpt["reason"],
            hash=rd.approved_set_hash()) if excerpt else S["lbl_full_set"].format(hypotheses=len(f["hypotheses"]))))
    scope_lines = [f"- {S['lbl_question']}: {profile['question']}", f"- {S['lbl_scope']}: {scope_id} — {f['set']['rationale']}"]
    hypothesis_lines = []
    prof = {p["hypothesis_id"]: p for p in cmp_["profiles"]}
    asm = rd.approved_rows("assumptions")
    for h in hyps:
        own = [a["id"] for a in compare._assumptions_of(h["id"], asm) if compare._unconfirmed(a)]
        hypothesis_lines.append(S["hyp_line"].format(
            id=h["id"], kind=h["kind"], mechanism=h["mechanism"],
            burdens=S["hyp_burdens"].format(ids=", ".join(h["burdens"])) if h["burdens"] else "",
            unconfirmed=S["hyp_unconfirmed"].format(ids=", ".join(own)) if own else ""))
    obs_blocks = []
    for o in observations:
        lines = [S["obs_line"].format(id=o["observation"]["id"], description=o["observation"]["description"])]
        for c in o["claims"]:
            cl = c["claim"]
            lines.append(S["obs_claim"].format(id=cl["id"], speaker=cl["speaker"], role=cl["speaker_role"],
                                               locator=_loc_text(c["locator"])))
            lines.append(_quote_block(cl["quote"]))
        obs_blocks.append("\n".join(lines))
    head = "| " + S["col_observation"] + " | " + " | ".join(h["id"] for h in hyps) + " |"
    sep = "|" + "---|" * (len(hyps) + 1)
    rows = [head, sep]
    detail = []
    for o in observations:
        oid = o["observation"]["id"]
        cells = []
        for h in hyps:
            a = f["assessments"].get((oid, h["id"]))
            cells.append(a["relation"] if a else "not_assessed")
            if a:
                locs = [_loc_text(l) for l in (_loc(f["psg"][p], f["docs"]) for p in a["basis_passage_ids"] if p in f["psg"]) if l]
                detail.append(S["assessment_line"].format(
                    observation=oid, hypothesis=h["id"], relation=a["relation"], reason=a["reason"],
                    basis=S["assessment_basis"].format(locators="; ".join(locs)) if locs else ""))
        rows.append(f"| {oid} | " + " | ".join(cells) + " |")
    matrix_block = "\n".join([S["legend_matrix"], "", *rows, "", *detail])
    comp = [S["profile_line"].format(id=p["hypothesis_id"], conflicts=p["conflicting_families"],
                                     supports=p["supporting_families"], unconfirmed=p["unconfirmed_assumptions"])
            for p in cmp_["profiles"] if p["hypothesis_id"] not in omit_hyp]
    comp += [S["loo_line"].format(family=e["family_id"], leader=e["leader"] or S["loo_none"].format(
        tied=", ".join(e["tied_top"]))) for e in cmp_["loo"]]
    unc = uncovered.classify({"observation_ids": [o["observation"]["id"] for o in observations],
                              "hypotheses": len(f["hypotheses"]),
                              "rows": [{"observation_id": oid, "hypothesis_id": h["id"],
                                        "status": "assessed" if (oid, h["id"]) in f["assessments"] else "not_assessed",
                                        "assessment": f["assessments"].get((oid, h["id"]))}
                                       for oid in (o["observation"]["id"] for o in observations) for h in f["hypotheses"]]})
    unc_lines = [S["uncovered_line"].format(id=u["observation_id"], status=u["status"],
                                            categories=(" — " + ", ".join(u["categories"])) if u["categories"] else "")
                 for u in unc if u["status"] == "incomplete" or u["categories"]]
    test_lines = []
    for t in plan["tests"]:
        if t["contract_issue"]:
            test_lines.append(t["id"] + ": " + S["actions_reassess"].format(issue=t["contract_issue"]))
            continue
        test_lines.append(S["tests_line"].format(
            id=t["id"], question=t["question"], outcomes="; ".join(o["label"] for o in t["outcomes"]),
            uninformative=t["uninformative_outcome"], access=t["access_basis"]))
    for e in plan["required"]:
        pair = " × ".join(e["pair"])
        if e["state"] == "gap":
            test_lines.append(S["tests_gap"].format(pair=pair))
        for r in e["no_test_reasons"]:
            test_lines.append(S["tests_reason"].format(pair=pair, reason=r["reason"]))
    search_lines = [S["search_line"].format(query=s["query"], state=s["state"], id=s["id"], corpus=s["corpus_hash"])
                    for s in searches_state]
    review_lines = [S["review_line"].format(cls=k, count=v, of=S["lbl_of"], total=total) for k, v in sorted(classes.items())]
    review_lines += [S["review_warning"].format(gate=x["gate"], detail=x["outcome"]) for x in findings
                     if not x["outcome"].startswith("block")]
    blocks = {
        "title": S["title_exhibit" if ex_policy else "title_working"],
        "status_paragraph": status_paragraph(S, cmp_, pending),
        "banner": S["banner_exhibit"].format(policy=POLICY_VERSION) if ex_policy else S["banner_working"],
        "header": "\n".join(header), "method": S["method"], "limits": S["limits"], "scope": "\n".join(scope_lines),
        "hypotheses": "\n".join(hypothesis_lines), "observations": "\n\n".join(obs_blocks), "matrix": matrix_block,
        "comparison": "\n".join(comp), "uncovered": "\n".join(unc_lines) or S["uncovered_none"],
        "tests": "\n".join(test_lines) or S["tests_none"], "searches": "\n".join(search_lines) or S["search_none"],
        "review": "\n".join(review_lines),
        "actions": _action_table(S, plan, f),
        "rejection_history": _rejection_appendix(S, review_history.read(rd)),
        "stale": _stale_block(S, stale, revisit_info),
    }
    if ex_policy:
        blocks["policy"] = (POLICY_DIR / f"exhibit-use.{lang}.md").read_text(encoding="utf-8").strip()
        blocks["statement"] = S["statement_text"] + "\n\n" + S["statement_field"]
        blocks["reproduction"] = S["reproduction_text"] + "\n\n" + S["reproduction_ref"].format(
            bundle=reproduction["bundle"], code_version=__version__)
    else:
        blocks["model_summary"] = (S["summary_label"].format(lang=lang) + "\n\n" + summary) if summary else S["lbl_none"]
        blocks["reproduction"] = S["reproduction_note_working"]
    return blocks


# --- gates -----------------------------------------------------------------------------------------------

def _scope_name(scope_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", scope_id.split(":", 1)[-1])


def _validate_excerpt(excerpt: Any, f: dict[str, Any]) -> dict[str, Any] | None:
    if excerpt is None:
        return None
    ok = (isinstance(excerpt, dict) and str(excerpt.get("reason") or "").strip()
          and set(excerpt) <= {"omit_observation_ids", "omit_hypothesis_ids", "reason"})
    obs = {o["observation"]["id"] for o in f["observations"]}
    hyp = {h["id"] for h in f["hypotheses"]}
    if (not ok or not set(excerpt.get("omit_observation_ids", [])) <= obs
            or not set(excerpt.get("omit_hypothesis_ids", [])) <= hyp
            or not (excerpt.get("omit_observation_ids") or excerpt.get("omit_hypothesis_ids"))):
        raise _err("E_EXCERPT_INVALID", "An excerpt needs a reason and at least one known omitted observation or hypothesis.",
                   "Wyciąg wymaga powodu i co najmniej jednej znanej pominiętej obserwacji lub hipotezy.", EXIT_POLICY)
    return {"omit_observation_ids": sorted(excerpt.get("omit_observation_ids", [])),
            "omit_hypothesis_ids": sorted(excerpt.get("omit_hypothesis_ids", [])), "reason": str(excerpt["reason"]).strip()}


def _search_state(rd: ReadRepository, now: str) -> tuple[list[dict[str, Any]], list[str]]:
    by_key: dict[str, list[dict[str, Any]]] = {}
    for r in rd.frozen_rows("search_records"):
        by_key.setdefault(sha256_obj([r["query"], r["variants"], r["filters"]]), []).append(r)
    out, stale = [], []
    for key, recs in sorted(by_key.items()):
        current = [r for r in recs if r["corpus_hash"] == now]
        if current:
            for r in sorted(current, key=search.record_id):
                out.append({"query": r["query"], "state": search.state_of(r), "id": search.record_id(r),
                            "corpus_hash": r["corpus_hash"]})
        else:
            stale += [search.record_id(r) for r in recs if not r["hits"]]
            for r in recs:
                if r["hits"]:
                    out.append({"query": r["query"], "state": "found", "id": search.record_id(r),
                                "corpus_hash": r["corpus_hash"]})
    return out, sorted(stale)


def render(case_dir: Path | str, profile_name: str, scope_id: str, *, lang: str | None = None, date: str | None = None,
           summary: str | None = None, excerpt: dict[str, Any] | None = None, out_dir: str = "report",
           coverage_threshold: float | None = None) -> dict[str, Any]:
    root = Path(case_dir)
    if profile_name not in PROFILES:
        raise _err("E_UNKNOWN_PROFILE", "Report profile must be working or exhibit.", "Profil raportu: working lub exhibit.")
    profile = load_profile(root)
    lang = lang or profile["lang"]
    S, templates = load_templates(lang)
    date = date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise _err("E_DATE", "The date must be YYYY-MM-DD.", "Data musi mieć postać RRRR-MM-DD.")
    exhibit = profile_name == "exhibit"
    if exhibit and summary:
        raise _err("E_EXHIBIT_MODEL_SUMMARY", "The exhibit profile never contains a model summary.",
                   "Profil exhibit nigdy nie zawiera streszczenia modelu.", EXIT_POLICY)
    rd = ReadRepository(root / "case.db", profile["case_id"])
    try:
        verdict = rd.verify()
        if not verdict.ok:
            raise LaError("E_CHAIN_BROKEN", "Hash chain verification failed.", "Weryfikacja łańcucha haszy nie powiodła się.",
                          7, {"first_broken_id": verdict.first_broken_id or "", "reason": verdict.reason or ""})
        gates = review.evaluate_gates(root, profile_name)
        blocking = [x for x in gates["findings"] if x["outcome"].startswith("block")]
        if blocking:
            raise _err("E_REPORT_BLOCKED", "A render gate blocks this report; nothing was written.",
                       "Bramka renderu blokuje ten raport; nic nie zapisano.", EXIT_POLICY,
                       gates=",".join(sorted({x["gate"] for x in blocking})), count=str(len(blocking)))
        f = collect(rd, scope_id, coverage_threshold=coverage_threshold)
        if f["unresolved"]:
            raise _err("E_REPORT_LOCATOR", "An observation has no locator resolvable to a frozen Document (G3).",
                       "Obserwacja nie ma lokalizatora rozwiązywalnego do zamrożonego Document (G3).", EXIT_POLICY,
                       count=str(len(f["unresolved"])), first=f["unresolved"][0])
        if f["bad_quotes"]:
            raise _err("E_QUOTE_MISMATCH", "A claim quote is not a literal slice of its Passage.",
                       "Cytat twierdzenia nie jest dosłownym wycinkiem Passage.", EXIT_POLICY, first=f["bad_quotes"][0])
        docs_now = sha256_obj(sorted(rd.frozen_rows("documents"), key=lambda d: d["id"]))
        searches_state, stale_searches = _search_state(rd, docs_now)
        if stale_searches:
            raise _err("E_NOT_FOUND_BLOCKED", "`not_found` needs a current SearchRecord with no hits and no parser errors.",
                       "`not_found` wymaga aktualnego SearchRecord bez trafień i bez błędów parsera.", EXIT_POLICY,
                       first="E_SEARCH_STALE", count=str(len(stale_searches)))
        bad_nf = [s for s in searches_state if s["state"] == "not_found"]
        if bad_nf:
            search.require_not_found(root, [s["id"] for s in bad_nf])
        stale = staleness.stale_records(rd)
        if stale and exhibit:
            raise _err("E_STALE_RECORDS", "Records are marked for reassessment; they cannot be the basis of an exhibit.",
                       "Rekordy czekają na ponowną ocenę; nie mogą być podstawą exhibit.", EXIT_POLICY,
                       count=str(len(stale)), first=next(iter(stale)))
        cleaned = _validate_excerpt(excerpt, f)
        if exhibit:
            omitted_o = set((cleaned or {}).get("omit_observation_ids", []))
            omitted_h = set((cleaned or {}).get("omit_hypothesis_ids", []))
            missing = [m for m in f["comparison"]["missing_assessments"]
                       if m["observation_id"] not in omitted_o and m["hypothesis_id"] not in omitted_h]
            if missing or not f["hypotheses"]:
                raise _err("E_EXHIBIT_INCOMPLETE", "The exhibit needs the full set of hypotheses and a complete matrix, "
                           "or an explicit excerpt.", "Exhibit wymaga pełnego zestawu hipotez i kompletnej macierzy "
                           "albo jawnego wyciągu.", EXIT_POLICY, missing_pairs=str(len(missing)))
        plan = test_plan.plan(root, scope_id, coverage_threshold=coverage_threshold, write=False)
        run = rd.runs()[-1]
        reproduction = {"bundle": f"{_scope_name(scope_id)}-{lang}.lacase"} if exhibit else None
        blocks = build_blocks(S, profile, run, f, profile_name=profile_name, lang=lang, date=date, scope_id=scope_id,
                              rd=rd, findings=gates["findings"], excerpt=cleaned, summary=summary, stale=stale,
                              searches_state=searches_state, plan=plan, reproduction=reproduction,
                              revisit_info=revisit.build(rd))
        approved_set_hash, chain_head = rd.approved_set_hash(), rd.chain_head()
    finally:
        rd.close()
    text = fill(templates[profile_name], blocks)
    data = text.encode("utf-8")
    report_hash = sha256_hex(data)
    name = f"{out_dir}/report-{profile_name}-{_scope_name(scope_id)}-{lang}"
    manifest = {
        "format": "la-report-manifest", "format_version": 1, "report_sha256": report_hash, "profile": profile_name,
        "lang": lang, "scope_id": scope_id, "date": date, "code_version": __version__, "skill": SKILL_NAME,
        "structure_source": STRUCTURE_SOURCE, "policy_version": POLICY_VERSION if exhibit else None,
        "policy_sha256": policy_files() if exhibit else None,
        "template_sha256": {"strings": sha256_hex((TEMPLATES / lang / "strings.json").read_bytes()),
                            "template": sha256_hex((TEMPLATES / lang / f"{profile_name}.md").read_bytes())},
        "approved_set_hash": approved_set_hash, "chain_head": chain_head, "analysis_hash": run["analysis_hash"],
        "corpus_hash": run["corpus_hash"], "excerpt": cleaned, "coverage_threshold": coverage_threshold,
        "gate_findings": [{"gate": x["gate"], "outcome": x["outcome"]} for x in gates["findings"]],
        "locators": {"observations": len(f["observations"]), "resolved": len(f["observations"]) - len(f["unresolved"])},
    }
    written: list[Path] = []
    try:
        extra: dict[str, Any] = {}
        if exhibit:
            bundle_path = root / out_dir / reproduction["bundle"]
            (root / out_dir).mkdir(parents=True, exist_ok=True)
            if bundle_path.exists():
                bundle_path.unlink()
            bundles.export_case(root, bundle_path)
            written.append(bundle_path)
            repro = bundles.reproduction_manifest(bundle_path, report_sha256=report_hash, report_name=Path(name).name + ".md")
            repro.update({"profile": profile_name, "lang": lang, "scope_id": scope_id, "date": date})
            manifest["bundle_sha256"] = repro["bundle_sha256"]
            written.append(atomic_write(root, name + ".reproduction.json", canonical_json(repro) + b"\n"))
            extra = {"bundle": f"{out_dir}/{reproduction['bundle']}", "reproduction": name + ".reproduction.json"}
        written.append(atomic_write(root, name + ".md", data))
        written.append(atomic_write(root, name + ".manifest.json", canonical_json(manifest) + b"\n"))
    except BaseException:
        for p in written:
            p.unlink(missing_ok=True)
        raise
    return {"ok": True, "profile": profile_name, "lang": lang, "path": name + ".md", "manifest": name + ".manifest.json",
            "report_sha256": report_hash, "status": f["comparison"]["status"], "findings": gates["findings"], **extra}


# --- verification and replay --------------------------------------------------------------------------------

def verify_report(report_path: Path | str) -> dict[str, Any]:
    """Detect an edit after rendering: the file hash must equal the manifest hash."""
    p = Path(report_path)
    manifest_path = p.with_name(p.name[:-3] + ".manifest.json") if p.name.endswith(".md") else None
    if manifest_path is None or not manifest_path.is_file():
        raise _err("E_NO_MANIFEST", "No manifest next to the report.", "Brak manifestu obok raportu.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = sha256_hex(p.read_bytes())
    edited = actual != manifest["report_sha256"]
    return {"ok": not edited, "edited": edited, "report_sha256": actual, "manifest_sha256": manifest["report_sha256"],
            "exhibit_status_valid": manifest["profile"] == "exhibit" and not edited,
            "note": "a manual edit of the substantive content after rendering removes the exhibit status" if edited else ""}


def replay(bundle: Path | str, manifest_path: Path | str, report_path: Path | str) -> dict[str, Any]:
    """Rebuild the case from the reproduction bundle and re-render with the recorded parameters."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        target = Path(tmp) / "replayed"
        bundles.import_case(bundle, target)
        out = render(target, manifest["profile"], manifest["scope_id"], lang=manifest["lang"], date=manifest["date"],
                     excerpt=manifest.get("excerpt"), coverage_threshold=manifest.get("coverage_threshold"),
                     out_dir="replay")
        replayed = (target / out["path"]).read_bytes()
    original = Path(report_path).read_bytes()
    return {"ok": replayed == original, "identical": replayed == original, "report_sha256": sha256_hex(original),
            "replayed_sha256": sha256_hex(replayed), "approved_set_hash": manifest["approved_set_hash"],
            "chain_head": manifest["chain_head"]}
