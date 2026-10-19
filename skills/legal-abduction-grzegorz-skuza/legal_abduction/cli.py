"""argparse CLI core. Domain commands are registered by later tasks."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import __version__
from . import (altcause, bundles, claims, compare, doctor, extract, facts, families, hypotheses, ingest, matrix, observations,
               packets, proposals, report, review, review_budget, revisit, search, staleness, status, test_plan, uncovered,
               update)
from . import profile as prof
from .runtime import (EXIT_INTERRUPTED, EXIT_NOT_IMPLEMENTED, EXIT_OK, EXIT_USAGE, EXIT_INTERNAL, LaError)

MIN_PYTHON = (3, 12)

Handler = Callable[[argparse.Namespace], dict[str, Any]]


@dataclass(frozen=True)
class Command:
    help: str
    handler: Handler
    configure: Callable[[argparse.ArgumentParser], None] | None = None
    gate: bool = True  # run the profile/processing gate before the handler
    touches_corpus: bool = True


REGISTRY: dict[str, Command] = {}


def command(name: str, help_text: str, *, configure: Callable[[argparse.ArgumentParser], None] | None = None,
            gate: bool = True, touches_corpus: bool = True) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        REGISTRY[name] = Command(help_text, fn, configure, gate, touches_corpus)
        return fn
    return deco


@command("version", "Print the version.", gate=False, touches_corpus=False)
def _version(_args: argparse.Namespace) -> dict[str, Any]:
    return {"ok": True, "version": __version__}


def _init_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--profile-file", required=True, help="JSON file with the human-supplied profile answers")


@command("init", "Create case.json, the case database and the first Run.", configure=_init_args,
         gate=False, touches_corpus=False)
def _init(args: argparse.Namespace) -> dict[str, Any]:
    if not args.case_dir:
        raise LaError("USAGE", "--case-dir is required.", "Wymagane jest --case-dir.", EXIT_USAGE)
    try:
        answers = json.loads(Path(args.profile_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LaError("E_PROFILE_FILE", "Profile file is unreadable or not JSON.",
                      "Plik profilu jest nieczytelny lub nie jest JSON.", EXIT_USAGE) from e
    if not isinstance(answers, dict):
        raise LaError("E_PROFILE_FILE", "Profile file must contain a JSON object.",
                      "Plik profilu musi zawierać obiekt JSON.", EXIT_USAGE)
    if args.lang:
        answers["lang"] = args.lang
    case_id = answers.pop("case_id", None) or f"case-{uuid.uuid4().hex[:12]}"
    return prof.init_case(args.case_dir, answers, case_id)


def _ingest_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("files", nargs="+", help="explicit input files (no directories or links)")
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--max-files", type=int, default=None)
    p.add_argument("--max-file-bytes", type=int, default=None)


@command("ingest", "Freeze the corpus: hash, copy and publish the manifest atomically.", configure=_ingest_args)
def _ingest(args: argparse.Namespace) -> dict[str, Any]:
    profile = prof.load_profile(args.case_dir)
    return ingest.freeze(args.case_dir, profile["case_id"], args.files, batch_size=args.batch_size,
                         resume=args.resume, budget_s=args.step_budget_s, max_files=args.max_files,
                         max_file_bytes=args.max_file_bytes)


@command("families", "Group identical bytes and EML threads into source families.")
def _families(args: argparse.Namespace) -> dict[str, Any]:
    profile = prof.load_profile(args.case_dir)
    return families.compute_families(args.case_dir, profile["case_id"])


def _prepare_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("task_type", choices=packets.TASK_TYPES)
    p.add_argument("--objects-file", required=True, help="JSON list of {type, id, content}")
    p.add_argument("--model-id", default="none")
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--max-chars", type=int, default=None)
    p.add_argument("--declared-hypotheses", type=int, default=None, help="forecast input for the review budget")
    p.add_argument("--observations", type=int, default=None, help="forecast input for the review budget")
    p.add_argument("--budget-override-reason", default=None)


@command("prepare", "Emit a task packet for a host model or manual (none) filling.", configure=_prepare_args)
def _prepare(args: argparse.Namespace) -> dict[str, Any]:
    objs = _read_json(args.objects_file, "objects file")
    if not isinstance(objs, list):
        raise LaError("E_PROFILE_FILE", "Objects file must contain a JSON list.", "Plik obiektów musi zawierać listę JSON.",
                      EXIT_USAGE)
    hook = review_budget.make_budget_hook(args.case_dir, declared_hypotheses=args.declared_hypotheses,
                                          observations=args.observations, override_reason=args.budget_override_reason)
    return packets.prepare(args.case_dir, args.task_type, objs, model_id=args.model_id,
                           prompt_version=args.prompt_version, max_chars=args.max_chars, budget_hook=hook)


def _ingest_proposal_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--packet", required=True)
    p.add_argument("--proposal", required=True)


@command("ingest-proposal", "Validate a proposal and queue it (never approves).", configure=_ingest_proposal_args)
def _ingest_proposal(args: argparse.Namespace) -> dict[str, Any]:
    return proposals.ingest_proposal(args.case_dir, _read_json(args.packet, "packet"),
                                     _read_json(args.proposal, "proposal"))


def _read_json(path: str, what: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LaError("E_INPUT_FILE", f"The {what} is unreadable or not JSON.", f"Plik ({what}) jest nieczytelny lub nie "
                      "jest JSON.", EXIT_USAGE) from e


def _claims_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("prepare", "ingest"))
    p.add_argument("--packet", default=None)
    p.add_argument("--proposal", default=None)
    p.add_argument("--model-id", default="none")
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--max-chars", type=int, default=None)


@command("claims", "Prepare claim packets (prepare) or ingest a claims proposal (ingest).", configure=_claims_args)
def _claims(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "prepare":
        return claims.prepare_claims(args.case_dir, model_id=args.model_id, prompt_version=args.prompt_version,
                                     max_chars=args.max_chars)
    if not args.packet or not args.proposal:
        raise LaError("USAGE", "--packet and --proposal are required for ingest.",
                      "Dla ingest wymagane są --packet i --proposal.", EXIT_USAGE)
    return claims.ingest_claims(args.case_dir, _read_json(args.packet, "packet"), _read_json(args.proposal, "proposal"))


def _hypotheses_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("prepare", "ingest", "check", "exceptions"))
    p.add_argument("--scope", default=None, help="ObservationSet id for prepare")
    p.add_argument("--packet", default=None)
    p.add_argument("--proposal", default=None)
    p.add_argument("--file", default=None, help="exceptions file")
    p.add_argument("--model-id", default="none")
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--max-chars", type=int, default=None)
    p.add_argument("--declared-hypotheses", type=int, default=None)
    p.add_argument("--budget-override-reason", default=None)


@command("hypotheses", "Prepare/ingest hypothesis proposals, check set completeness (R11), record exceptions.",
         configure=_hypotheses_args)
def _hypotheses(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "check":
        return hypotheses.require_complete(args.case_dir)
    if args.action == "exceptions":
        if not args.file:
            raise LaError("USAGE", "--file is required.", "Wymagane --file.", EXIT_USAGE)
        return hypotheses.grant_exceptions(args.case_dir, args.file)
    if args.action == "prepare":
        if not args.scope:
            raise LaError("USAGE", "--scope is required for prepare.", "Dla prepare wymagane jest --scope.", EXIT_USAGE)
        hook = review_budget.make_budget_hook(args.case_dir, declared_hypotheses=args.declared_hypotheses,
                                              override_reason=args.budget_override_reason)
        return hypotheses.prepare_hypotheses(args.case_dir, args.scope, model_id=args.model_id,
                                             prompt_version=args.prompt_version, max_chars=args.max_chars,
                                             budget_hook=hook)
    if not args.packet or not args.proposal:
        raise LaError("USAGE", "--packet and --proposal are required for ingest.",
                      "Dla ingest wymagane są --packet i --proposal.", EXIT_USAGE)
    return hypotheses.ingest_hypotheses(args.case_dir, _read_json(args.packet, "packet"), _read_json(args.proposal, "proposal"))


def _altcause_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("check", "prepare", "ingest"))
    p.add_argument("--packet", default=None)
    p.add_argument("--proposal", default=None)
    p.add_argument("--model-id", default="none")


@command("altcause", "Check/prepare/ingest non-intent alternatives for intent hypotheses.", configure=_altcause_args)
def _altcause(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "check":
        return altcause.check(args.case_dir)
    if args.action == "prepare":
        return altcause.prepare(args.case_dir, model_id=args.model_id)
    if not args.packet or not args.proposal:
        raise LaError("USAGE", "--packet and --proposal are required for ingest.",
                      "Dla ingest wymagane są --packet i --proposal.", EXIT_USAGE)
    return altcause.ingest(args.case_dir, _read_json(args.packet, "packet"), _read_json(args.proposal, "proposal"))


def _audit_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("export",))
    p.add_argument("--out", default=None)


@command("audit", "Export the run log (step, agent, time, evidence class) without case content.", configure=_audit_args)
def _audit(args: argparse.Namespace) -> dict[str, Any]:
    return hypotheses.export_audit_log(args.case_dir, args.out)


def _matrix_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("prepare", "ingest", "check"))
    p.add_argument("--scope", default=None)
    p.add_argument("--packet", default=None)
    p.add_argument("--proposal", default=None)
    p.add_argument("--model-id", default="none")
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--max-chars", type=int, default=None)
    p.add_argument("--observations", type=int, default=None)
    p.add_argument("--declared-hypotheses", type=int, default=None)
    p.add_argument("--budget-override-reason", default=None)


@command("matrix", "Prepare, ingest or check the approved observation-hypothesis matrix.", configure=_matrix_args)
def _matrix(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "ingest":
        if not args.packet or not args.proposal:
            raise LaError("USAGE", "--packet and --proposal are required for ingest.",
                          "Dla ingest wymagane są --packet i --proposal.", EXIT_USAGE)
        return matrix.ingest(args.case_dir, _read_json(args.packet, "packet"), _read_json(args.proposal, "proposal"))
    if not args.scope:
        raise LaError("USAGE", "--scope is required.", "Wymagane jest --scope.", EXIT_USAGE)
    if args.action == "check":
        return matrix.check(args.case_dir, args.scope)
    hook = review_budget.make_budget_hook(args.case_dir, declared_hypotheses=args.declared_hypotheses,
                                          observations=args.observations, override_reason=args.budget_override_reason)
    return matrix.prepare(args.case_dir, args.scope, model_id=args.model_id, prompt_version=args.prompt_version,
                          max_chars=args.max_chars, budget_hook=hook)


def _uncovered_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("run",))
    p.add_argument("--scope", required=True)


@command("uncovered", "Classify approved observations by their approved assessment profile.", configure=_uncovered_args)
def _uncovered(args: argparse.Namespace) -> dict[str, Any]:
    return uncovered.report(args.case_dir, args.scope)


def _review_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("export", "import", "gates"))
    p.add_argument("--out", default=None)
    p.add_argument("--file", default=None)
    p.add_argument("--profile", choices=("working", "exhibit"), default="working")


def _tests_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("prepare", "ingest", "plan", "reasons"))
    p.add_argument("--scope", default=None)
    p.add_argument("--packet", default=None)
    p.add_argument("--proposal", default=None)
    p.add_argument("--file", default=None, help="no-test reasons file for `reasons`")
    p.add_argument("--model-id", default="none")
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--max-chars", type=int, default=None)


@command("tests", "Plan discriminating tests (prepare/ingest proposals, plan coverage of tied or unstable pairs, "
         "record reviewed reasons for a missing test).", configure=_tests_args)
def _tests(args: argparse.Namespace) -> dict[str, Any]:
    def need(value: Any, flag: str) -> Any:
        if not value:
            raise LaError("USAGE", f"{flag} is required for {args.action}.", f"Dla {args.action} wymagane jest {flag}.",
                          EXIT_USAGE)
        return value
    if args.action == "ingest":
        return test_plan.ingest(args.case_dir, _read_json(need(args.packet, "--packet"), "packet"),
                                _read_json(need(args.proposal, "--proposal"), "proposal"))
    if args.action == "reasons":
        return test_plan.grant_no_test_reasons(args.case_dir, need(args.file, "--file"))
    if args.action == "plan":
        return test_plan.plan(args.case_dir, need(args.scope, "--scope"))
    return test_plan.prepare(args.case_dir, need(args.scope, "--scope"), model_id=args.model_id,
                             prompt_version=args.prompt_version, max_chars=args.max_chars)


def _update_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("run", "invalidate", "reassess", "stale", "semantic",
                                      "withdraw", "change", "reinstate", "revisit"))
    p.add_argument("--files", nargs="*", default=None, help="new input files for run (already frozen paths are skipped)")
    p.add_argument("--id", action="append", default=None,
                   help="record id to invalidate (repeatable); the clm:/obs: fact for withdraw/change/reinstate")
    p.add_argument("--replacement", default=None, help="approved clm:/obs: that replaces the fact (change)")
    p.add_argument("--dry-run", action="store_true",
                   help="withdraw/change/reinstate: report what would be flagged and voided; writes nothing")
    p.add_argument("--reason", default=None, help="required for invalidate/withdraw/change/reinstate")
    p.add_argument("--file", default=None, help="reviewer decision file for reassess")
    p.add_argument("--scope", default=None, help="scope for semantic; optional filter for revisit")
    p.add_argument("--template", nargs="?", const="", default=None,
                   help="revisit: also write an empty reassessment file for the human (optional path)")
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--coverage-threshold", type=float, default=None)


@command("update", "Delta update after new material; withdraw/change/reinstate a fact; list judgments to revisit; reassess.",
         configure=_update_args)
def _update(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "run":
        return update.run(args.case_dir, args.files, batch_size=args.batch_size, resume=args.resume,
                          coverage_threshold=args.coverage_threshold)
    if args.action == "invalidate":
        if not args.id or not args.reason:
            raise LaError("USAGE", "--id and --reason are required.", "Wymagane --id i --reason.", EXIT_USAGE)
        return staleness.invalidate(args.case_dir, args.id, args.reason, flag_roots=True)
    if args.action in ("withdraw", "change", "reinstate"):
        if not args.id or len(args.id) != 1 or not args.reason:
            raise LaError("USAGE", "Exactly one --id and a --reason are required.",
                          "Wymagane dokładnie jedno --id i --reason.", EXIT_USAGE)
        change = {"withdraw": "withdrawn", "change": "changed", "reinstate": "reinstated"}[args.action]
        return facts.record(args.case_dir, args.id[0], change, args.reason, args.replacement, dry_run=args.dry_run)
    if args.action == "revisit":
        return revisit.run(args.case_dir, args.scope, args.template)
    if args.action == "reassess":
        if not args.file:
            raise LaError("USAGE", "--file is required.", "Wymagane --file.", EXIT_USAGE)
        return staleness.reassess(args.case_dir, args.file)
    if args.action == "semantic":
        if not args.scope:
            raise LaError("USAGE", "--scope is required.", "Wymagane --scope.", EXIT_USAGE)
        return {"ok": True, **update.semantic_view(args.case_dir, args.scope)}
    rd = repository_reader(args.case_dir)
    try:
        return {"ok": True, "stale": staleness.stale_records(rd)}
    finally:
        rd.close()


def repository_reader(case_dir: str) -> Any:
    from .repository import ReadRepository
    return ReadRepository(Path(case_dir) / "case.db", prof.load_profile(case_dir)["case_id"])


def _case_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("export", "import", "inspect", "originals", "pending"))
    p.add_argument("--out", default=None, help="bundle file to write (*.lacase)")
    p.add_argument("--bundle", default=None, help="bundle file to read")
    p.add_argument("--with-originals", action="store_true", help="include the frozen files (off by default)")
    p.add_argument("--files", nargs="*", default=None, help="frozen files to re-supply (matched by SHA-256)")


@command("case", "Export/import a .lacase bundle, inspect it, and re-supply or list missing frozen files.",
         configure=_case_args, gate=False, touches_corpus=False)
def _case(args: argparse.Namespace) -> dict[str, Any]:
    def need(value: Any, flag: str) -> Any:
        if not value:
            raise LaError("USAGE", f"{flag} is required for {args.action}.", f"Dla {args.action} wymagane jest {flag}.",
                          EXIT_USAGE)
        return value
    if args.action == "inspect":
        return bundles.inspect_bundle(need(args.bundle, "--bundle"))
    case_dir = need(args.case_dir, "--case-dir")
    if args.action == "import":
        return bundles.import_case(need(args.bundle, "--bundle"), case_dir)
    if args.action == "export":
        return bundles.export_case(case_dir, need(args.out, "--out"), with_originals=args.with_originals)
    if args.action == "originals":
        return bundles.attach_originals(case_dir, need(args.files, "--files"))
    return {"ok": True, "originals_pending": bundles.pending_originals(case_dir)}


def _report_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", nargs="?", choices=("render", "verify", "replay"), default="render")
    p.add_argument("--profile", choices=("working", "exhibit"), default="working")
    p.add_argument("--scope", default=None)
    p.add_argument("--date", default=None, help="YYYY-MM-DD printed in the header (default: today, UTC)")
    p.add_argument("--summary-file", default=None, help="optional model summary text (working profile only)")
    p.add_argument("--excerpt-file", default=None, help="JSON {omit_observation_ids, omit_hypothesis_ids, reason}")
    p.add_argument("--coverage-threshold", type=float, default=None)
    p.add_argument("--file", default=None, help="report file for verify/replay")
    p.add_argument("--bundle", default=None, help="reproduction bundle for replay")


@command("report", "Render the working or exhibit report (gates first, nothing written on refusal); verify or replay it.",
         configure=_report_args)
def _report(args: argparse.Namespace) -> dict[str, Any]:
    def need(value: Any, flag: str) -> Any:
        if not value:
            raise LaError("USAGE", f"{flag} is required for {args.action}.", f"Dla {args.action} wymagane jest {flag}.",
                          EXIT_USAGE)
        return value
    if args.action == "verify":
        return report.verify_report(need(args.file, "--file"))
    if args.action == "replay":
        f = Path(need(args.file, "--file"))
        return report.replay(need(args.bundle, "--bundle"), f.with_name(f.name[:-3] + ".manifest.json"), f)
    summary = Path(args.summary_file).read_text(encoding="utf-8") if args.summary_file else None
    excerpt = _read_json(args.excerpt_file, "excerpt file") if args.excerpt_file else None
    return report.render(args.case_dir, args.profile, need(args.scope, "--scope"), lang=args.lang, date=args.date,
                         summary=summary, excerpt=excerpt, coverage_threshold=args.coverage_threshold)


def _compare_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--scope", required=True)
    p.add_argument("--coverage-threshold", type=float, default=None,
                   help="explicit coverage ratio 0-1; without it the T-COVERAGE predicate stays undefined")


@command("compare", "Compare explanations by family profile (no score) and test leave-one-family-out stability.",
         configure=_compare_args)
def _compare(args: argparse.Namespace) -> dict[str, Any]:
    return compare.compare(args.case_dir, args.scope, coverage_threshold=args.coverage_threshold)


@command("review", "Export a review file, import decisions, or evaluate render gates.", configure=_review_args)
def _review(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "export":
        return review.export_review(args.case_dir, args.out)
    if args.action == "gates":
        return review.evaluate_gates(args.case_dir, args.profile)
    if not args.file:
        raise LaError("USAGE", "--file is required for import.", "Dla import wymagane jest --file.", EXIT_USAGE)
    return review.import_review(args.case_dir, args.file)


@command("metrics", "Review load, bulk share, sample corrections and pace.")
def _metrics(args: argparse.Namespace) -> dict[str, Any]:
    return review.review_metrics(args.case_dir)


def _observations_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("select", "coverage", "time"))
    p.add_argument("--file", default=None, help="selection file for select")
    p.add_argument("--observation", default=None)
    p.add_argument("--text", default=None, help="date expression for time")
    p.add_argument("--date-order", choices=("DMY", "MDY"), default=None)


@command("observations", "Select observations from approved claims, record event time, report coverage.",
         configure=_observations_args)
def _observations(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "select":
        if not args.file:
            raise LaError("USAGE", "--file is required for select.", "Dla select wymagane jest --file.", EXIT_USAGE)
        return observations.select_observations(args.case_dir, args.file)
    if args.action == "time":
        if not args.observation or args.text is None:
            raise LaError("USAGE", "--observation and --text are required.", "Wymagane --observation i --text.", EXIT_USAGE)
        return observations.record_event_time(args.case_dir, args.observation, text=args.text, date_order=args.date_order)
    return observations.coverage_report(args.case_dir)


def _search_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=("run", "rerun", "verify"))
    p.add_argument("--query", default=None)
    p.add_argument("--variant", action="append", default=None)
    p.add_argument("--scope", nargs="+", default=None, help="'all' or document ids (required for run)")
    p.add_argument("--ignore-case", action="store_true")
    p.add_argument("--record", action="append", default=None, help="SearchRecord ids for verify")


@command("search", "Literal search with a logged SearchRecord; rerun stale empty searches; verify not_found.",
         configure=_search_args)
def _search(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "rerun":
        return {"ok": True, "reruns": search.rerun_stale(args.case_dir)}
    if args.action == "verify":
        return search.verify_not_found(args.case_dir, args.record or [])
    if not args.query or not args.scope:
        raise LaError("USAGE", "--query and an explicit --scope are required.", "Wymagane --query i jawny --scope.", EXIT_USAGE)
    scope: Any = "all" if args.scope == ["all"] else args.scope
    return search.run_search(args.case_dir, args.query, scope=scope, variants=args.variant,
                             case_sensitive=not args.ignore_case)


def _extract_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--max-pages", type=int, default=None)
    p.add_argument("--max-uncompressed-bytes", type=int, default=None)


@command("extract", "Extract text and locators from frozen documents.", configure=_extract_args)
def _extract(args: argparse.Namespace) -> dict[str, Any]:
    profile = prof.load_profile(args.case_dir)
    limits = {k: v for k, v in (("max_pages", args.max_pages), ("max_uncompressed_bytes", args.max_uncompressed_bytes))
              if v is not None}
    return extract.extract_all(args.case_dir, profile["case_id"], batch_size=args.batch_size, resume=args.resume,
                               budget_s=args.step_budget_s, limits=limits)


def _doctor_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--declared-level", choices=("A", "B", "C"), default=None)
    p.add_argument("--review-dir", default=None)
    p.add_argument("--min-free-bytes", type=int, default=None)


@command("doctor", "Detect host capabilities (installs nothing, reads no case files).",
         configure=_doctor_args, gate=False, touches_corpus=False)
def _doctor(args: argparse.Namespace) -> dict[str, Any]:
    level = args.declared_level
    if level is None and args.case_dir:
        try:
            level = prof.load_profile(args.case_dir).get("host_level")
        except (LaError, OSError, ValueError):
            level = None
    caps = doctor.run_doctor(args.case_dir, declared_level=level, review_dir=args.review_dir,
                             step_budget_s=int(args.step_budget_s), min_free_bytes=args.min_free_bytes)
    return {"ok": True, **caps}


def _status_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--session-end", action="store_true", help="include the end-of-session export reminder")


@command("status", "Show steps, queue, gaps and the export reminder.", configure=_status_args,
         gate=False, touches_corpus=False)
def _status(args: argparse.Namespace) -> dict[str, Any]:
    if not args.case_dir:
        raise LaError("USAGE", "--case-dir is required.", "Wymagane jest --case-dir.", EXIT_USAGE)
    return status.build_status(args.case_dir, session_end=args.session_end)


def not_implemented(name: str) -> Handler:
    def handler(_args: argparse.Namespace) -> dict[str, Any]:
        raise LaError("NOT_IMPLEMENTED", f"Command '{name}' is not implemented.",
                      f"Polecenie '{name}' nie jest zaimplementowane.",
                      EXIT_NOT_IMPLEMENTED, {"command": name})
    return handler


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise LaError("USAGE", message, message, EXIT_USAGE)


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="la", description="legal-abduction CLI")
    p.add_argument("--version", action="version", version=f"la {__version__}")
    p.add_argument("--json", action="store_true", help="machine-readable JSON on stdout")
    p.add_argument("--lang", choices=("en", "pl"), default=None)
    p.add_argument("--case-dir", default=None)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--step-budget-s", type=float, default=90.0)
    sub = p.add_subparsers(dest="command", metavar="COMMAND", parser_class=_Parser)
    for name, cmd in sorted(REGISTRY.items()):
        sp = sub.add_parser(name, help=cmd.help)
        if cmd.configure:
            cmd.configure(sp)
    return p


def _emit(result: dict[str, Any], args: argparse.Namespace | None, lang: str, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(json.dumps(result, sort_keys=True, ensure_ascii=False) + "\n")
    elif result.get("ok"):
        sys.stdout.write("ok\n")
    else:
        err = result["error"]
        sys.stderr.write(f"error {err['code']}: {err['message']}\n")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv
    lang = "pl" if "pl" in argv else "en"
    if sys.version_info < MIN_PYTHON and "doctor" not in argv:
        sys.stderr.write("error PYTHON_TOO_OLD: Python >= 3.12 required\n")
        return EXIT_USAGE
    try:
        args = build_parser().parse_args(argv)
        as_json, lang = args.json, args.lang or lang
        if args.command is None:
            raise LaError("USAGE", "A command is required.", "Wymagane jest polecenie.", EXIT_USAGE)
        cmd = REGISTRY.get(args.command)
        if cmd is None:
            raise LaError("UNKNOWN_COMMAND", f"Unknown command '{args.command}'.",
                          f"Nieznane polecenie '{args.command}'.", EXIT_USAGE)
        if cmd.gate:
            if not args.case_dir:
                raise LaError("USAGE", "--case-dir is required.", "Wymagane jest --case-dir.", EXIT_USAGE)
            try:
                gate = prof.require_ready(args.case_dir, args.command, touches_corpus=cmd.touches_corpus)
            except LaError:
                lang = args.lang or prof.declared_lang(args.case_dir) or lang
                raise
            lang = args.lang or gate["lang"]
        result = cmd.handler(args)
        _emit(result, args, lang, as_json)
        return EXIT_OK
    except SystemExit as e:  # --help / --version
        return int(e.code or 0)
    except KeyboardInterrupt:
        err = LaError("CANCELLED", "Cancelled; no final artifact published.",
                      "Anulowano; nie opublikowano wyniku końcowego.", EXIT_INTERRUPTED)
        _emit(err.envelope(lang), None, lang, as_json)
        return EXIT_INTERRUPTED
    except LaError as e:
        _emit(e.envelope(lang), None, lang, as_json)
        return e.exit_code
    except Exception as e:  # unexpected: never report success
        err = LaError("INTERNAL", "Internal error.", "Błąd wewnętrzny.", EXIT_INTERNAL,
                      {"type": type(e).__name__})
        _emit(err.envelope(lang), None, lang, as_json)
        return EXIT_INTERNAL
