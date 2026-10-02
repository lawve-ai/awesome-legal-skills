#!/usr/bin/env python3
"""ukcite — verify UK case-law citations against The National Archives.

Sources, and the only two hosts this tool ever contacts:
  - Find Case Law        https://caselaw.nationalarchives.gov.uk   (judgments)
  - legislation.gov.uk   https://www.legislation.gov.uk            (statutes)

Both are operated by The National Archives. Nothing else is queried; nothing
is sent anywhere except the citation being checked; results are written only
to the user's own machine under ~/.cache/uk-citation-verification/.

Verdicts are graded, and the grading is the point:
  VERIFIED             found on the official register; identity checks passed
  MISMATCH             the citation resolves, but to a different case
  NOT ON REGISTER      no record, though the court/year is within stated
                       coverage — presumptively unsafe, but NOT proof of
                       fabrication (coverage within range is incomplete)
  OUTSIDE COVERAGE     the register cannot answer (UKHL, pre-2001/2003, etc.)
                       — absence proves nothing
  UNCHECKABLE          not a neutral citation (law-report cite) — find the
                       neutral citation by name, or verify in the report

Python 3.9+, standard library only. Rate-limited to ~1 request/second
(Find Case Law permits 1,000 per rolling 5 minutes; we stay far below it).
"""

import difflib
import html
import io
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

FCL = "https://caselaw.nationalarchives.gov.uk"
LEG = "https://www.legislation.gov.uk"
UA = "ukcite/1.0 (UK citation verification; one-at-a-time checks under the Open Justice Licence)"
CACHE = Path.home() / ".cache" / "uk-citation-verification"

# ---------------------------------------------------------------------------
# Coverage, as stated by Find Case Law's "Types of courts and tribunals" page,
# read 27 August 2026. The range is TNA's earliest-to-latest holding; TNA's own
# caveat: "Coverage within that range may not be complete — not every judgment
# is sent to us for publication." Re-check the page when a verdict turns on it:
# https://caselaw.nationalarchives.gov.uk/courts-and-tribunals
# ---------------------------------------------------------------------------
COVERAGE = {
    "uksc": (2009, None, "United Kingdom Supreme Court"),
    "ukpc": (2009, None, "Privy Council"),
    "ewca/civ": (2001, None, "Court of Appeal (Civil Division)"),
    "ewca/crim": (2003, None, "Court of Appeal (Criminal Division)"),
    "ewhc/admin": (2003, None, "Administrative Court"),
    "ewhc/admlty": (2003, None, "Admiralty Court"),
    "ewhc/ch": (2003, None, "Chancery Division"),
    "ewhc/comm": (2003, None, "Commercial Court"),
    "ewhc/fam": (2003, None, "Family Division"),
    "ewhc/ipec": (2013, None, "Intellectual Property Enterprise Court"),
    "ewhc/kb": (2003, None, "King's Bench Division"),
    "ewhc/qb": (2003, None, "Queen's Bench Division"),
    "ewhc/mercantile": (2008, 2014, "Mercantile Court"),
    "ewhc/pat": (2003, None, "Patents Court"),
    "ewhc/scco": (2003, None, "Senior Courts Costs Office"),
    "ewhc/costs": (2003, None, "Senior Courts Costs Office"),
    "ewhc/tcc": (2003, None, "Technology and Construction Court"),
    "ewcop": (2009, None, "Court of Protection"),
    "ewfc": (2014, None, "Family Court"),
    "ewcr": (2020, None, "Crown Court (publication is exceptional)"),
    "ewcc": (2019, None, "County Court (publication is exceptional)"),
    "eat": (2021, None, "Employment Appeal Tribunal"),
    "ukut/aac": (2011, None, "Upper Tribunal (Administrative Appeals Chamber)"),
    "ukut/iac": (2007, None, "Upper Tribunal (Immigration and Asylum Chamber)"),
    "ukut/lc": (2014, None, "Upper Tribunal (Lands Chamber)"),
    "ukut/tcc": (2016, None, "Upper Tribunal (Tax and Chancery Chamber)"),
    "ukftt/grc": (2009, None, "First-tier Tribunal (General Regulatory Chamber)"),
    "ukftt/tc": (2009, None, "First-tier Tribunal (Tax Chamber)"),
    "uksiac": (2003, None, "Special Immigration Appeals Commission"),
    "ukiptrib": (2023, None, "Investigatory Powers Tribunal"),
}

NEVER_HELD = {
    "ukhl": "House of Lords judgments are not on Find Case Law at all "
            "(verified: the register holds UKSC from 2009 only). Its absence "
            "here proves nothing. The official archive of Lords judgments "
            "1996–2009 is on parliament.uk "
            "(publications.parliament.uk/pa/ld/ldjudgmt.htm) — it refuses "
            "scripted access, so open it in a browser — or verify in the "
            "printed reports or a subscription service.",
}

# Official archives to point the user at when the register cannot answer.
# Pointers only, checked by hand: these services are search engines, not
# citation-addressable registers, so an automated miss there would mean
# nothing — and automating them is deliberately out of scope (see SKILL.md).
ARCHIVE_POINTERS = {
    "eat": "Pre-2021 EAT decisions are in the official archive at "
           "gov.uk/employment-appeal-tribunal-decisions (check by hand).",
    "ukut/iac": "UT(IAC) decisions are also on the official service at "
                "tribunalsdecisions.service.gov.uk (check by hand).",
}

# Law-report series that cannot be resolved by neutral citation.
REPORT_RE = re.compile(
    r"\[(\d{4})\]\s+\d*\s*(AC|WLR|All\s*ER|QB|KB|Ch|Fam|Cr\s*App\s*R|EHRR|CMLR|Lloyd's\s*Rep)\b"
    r"|\(\d{4}\)\s+\d+\s+(EHRR|Cr\s*App\s*R)\b"
)

NCN_RE = re.compile(
    r"\[(?P<year>\d{4})\]\s+"
    r"(?P<court>UKSC|UKPC|UKHL|UKIPTrib|UKSIAC|UKUT|UKFTT|UKEAT|EAT|"
    r"EWCA\s+(?:Civ|Crim)|EWHC|EWCOP|EWFC|EWCC|EWCR)\s+"
    r"(?P<num>\d+)"
    r"(?:\s+\((?P<div>[A-Za-z]{1,12})\))?"
)


def slug_candidates(year, court, num, div):
    """Map a neutral citation to candidate Find Case Law URL slugs.

    The documented mapping: a ukncn identifier's slug is appended to the site
    root to form the human-facing URL, e.g. [2024] UKSC 123 -> uksc/2024/123.
    Where the slug shape is not certain (EWCOP/EWFC subdivisions), several
    candidates are tried and the one that resolved is reported.
    """
    court = re.sub(r"\s+", " ", court.strip())
    d = (div or "").lower()
    if court == "UKSC":
        return [f"uksc/{year}/{num}"]
    if court == "UKPC":
        return [f"ukpc/{year}/{num}"]
    if court == "UKHL":
        return []
    if court == "EWCA Civ":
        return [f"ewca/civ/{year}/{num}"]
    if court == "EWCA Crim":
        return [f"ewca/crim/{year}/{num}"]
    if court == "EWHC":
        if not d:
            return None  # an EWHC citation without a division is malformed
        return [f"ewhc/{d}/{year}/{num}"]
    if court == "EWCOP":
        return ([f"ewcop/{d}/{year}/{num}", f"ewcop/{year}/{num}"]
                if d in ("t1", "t2", "t3") else [f"ewcop/{year}/{num}"])
    if court == "EWFC":
        return ([f"ewfc/b/{year}/{num}", f"ewfc/{year}/{num}"]
                if d == "b" else [f"ewfc/{year}/{num}"])
    if court == "EWCC":
        return [f"ewcc/{year}/{num}"]
    if court == "EWCR":
        return [f"ewcr/{year}/{num}"]
    if court == "UKUT":
        return [f"ukut/{d}/{year}/{num}"] if d else None
    if court == "UKFTT":
        return [f"ukftt/{d}/{year}/{num}"] if d else None
    if court in ("EAT", "UKEAT"):
        return [f"eat/{year}/{num}"]
    if court == "UKIPTrib":
        return [f"ukiptrib/{year}/{num}"]
    if court == "UKSIAC":
        return [f"uksiac/{year}/{num}"]
    return None


def coverage_key(slug):
    parts = slug.split("/")
    for k in ("/".join(parts[:2]), parts[0]):
        if k in COVERAGE:
            return k
    return None


# ---------------------------------------------------------------------------
# HTTP, throttled per host. Find Case Law's published limit is 1,000 requests
# per rolling five minutes; we stay at ~1/second. legislation.gov.uk's
# robots.txt asks for a 5-second delay between automated requests, and this
# tool honours it even though a targeted lookup is not a crawl.
# ---------------------------------------------------------------------------
_last_request = {}
_HOST_DELAY = {"www.legislation.gov.uk": 5.0}


def _get(url, ok404=False):
    host = urllib.parse.urlsplit(url).netloc
    delay = _HOST_DELAY.get(host, 1.0)
    wait = delay - (time.monotonic() - _last_request.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_request[host] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404 and ok404:
            return 404, b""
        if e.code == 429:
            raise SystemExit("Rate-limited by the service (HTTP 429). Stop and wait; do not retry in a loop.")
        raise
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error reaching {urllib.parse.urlsplit(url).netloc}: {e.reason}. "
                         "The check did NOT run — the citation is unverified, not bad.")


# ---------------------------------------------------------------------------
# Judgment XML
# ---------------------------------------------------------------------------
def parse_judgment(xml_bytes):
    ns = {"akn": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0",
          "uk": "https://caselaw.nationalarchives.gov.uk/akn"}
    meta = {"name": None, "date": None, "court": None, "cite": None}
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return meta, ""
    el = root.find(".//akn:FRBRWork/akn:FRBRname", ns)
    if el is not None:
        meta["name"] = el.get("value")
    el = root.find(".//akn:FRBRWork/akn:FRBRdate", ns)
    if el is not None:
        meta["date"] = el.get("date")
    for tag in ("court", "cite"):
        el = root.find(f".//uk:{tag}", ns)
        if el is not None and el.text:
            meta[tag if tag != "court" else "court"] = el.text.strip()
            if tag == "cite":
                meta["cite"] = el.text.strip()
    body = root.find(".//akn:judgmentBody", ns)
    text = " ".join((body.itertext() if body is not None else root.itertext()))
    text = re.sub(r"\s+", " ", text).strip()
    return meta, text


def para_numbers(xml_bytes):
    ids = {int(m) for m in re.findall(rb'eId="para_(\d+)"', xml_bytes)}
    if not ids:
        ids = {int(m) for m in re.findall(rb"<num>\s*(\d+)\s*\.?\s*</num>", xml_bytes)}
    return ids


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
STOP = {"r", "v", "re", "the", "a", "an", "and", "of", "on", "in", "others",
        "ors", "anor", "application", "applications", "no"}


def _tokens(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP}


def name_match(claimed, official):
    c, o = _tokens(claimed), _tokens(official)
    if not c:
        return 1.0
    return len(c & o) / len(c)


def _norm_quote(s):
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("…", "...")
    return re.sub(r"\s+", " ", s).strip()


def quote_check(quote, text):
    q, t = _norm_quote(quote), _norm_quote(text)
    if q.lower() in t.lower():
        i = t.lower().find(q.lower())
        return "verbatim", t[max(0, i - 60):i + len(q) + 60]
    # Anchor on the quote's distinctive words: candidate windows are placed
    # wherever those words occur in the judgment, then scored character-wise.
    qw = q.lower().split()
    tw = t.split()
    twl = [w.lower().strip(".,;:()\"'") for w in tw]
    anchors = [(i, w.strip(".,;:()\"'")) for i, w in enumerate(qw) if len(w) > 4]
    starts = set()
    for qi, w in anchors:
        for ti, tword in enumerate(twl):
            if tword == w:
                starts.add(max(0, ti - qi))
    best, where = 0.0, ""
    for s in starts:
        window = " ".join(tw[s:s + len(qw) + 5])
        r = difflib.SequenceMatcher(None, q.lower(), window.lower()).ratio()
        if r > best:
            best, where = r, window
    if best >= 0.75:
        return "near", where
    return "absent", ""


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------
def check_citation(citation, name=None, para=None, quote=None):
    res = {"citation": citation.strip(), "verdict": None, "detail": [], "url": None}
    m = NCN_RE.search(citation)
    if not m:
        if REPORT_RE.search(citation):
            res["verdict"] = "UNCHECKABLE"
            res["detail"].append(
                "This is a law-report citation, not a neutral citation. Find Case Law "
                "resolves neutral citations only. Find the neutral citation with "
                "`ukcite find \"<case name>\"`, or verify the report citation in the "
                "printed series or a subscription service. This verdict says nothing "
                "about whether the case is real.")
        else:
            res["verdict"] = "UNPARSEABLE"
            res["detail"].append("Not recognised as a UK neutral citation or law-report citation.")
        return res

    year = int(m.group("year"))
    court = re.sub(r"\s+", " ", m.group("court"))
    num, div = m.group("num"), m.group("div")

    if court.lower() in NEVER_HELD:
        res["verdict"] = "OUTSIDE COVERAGE"
        res["detail"].append(NEVER_HELD[court.lower()])
        return res

    cands = slug_candidates(year, court, num, div)
    if cands is None:
        res["verdict"] = "UNPARSEABLE"
        res["detail"].append(f"{court} citations need a division/chamber in brackets "
                             "(e.g. (Admin), (IAC)) to resolve.")
        return res

    ck = coverage_key(cands[0]) if cands else None
    cov = COVERAGE.get(ck) if ck else None
    if cov:
        start, end, label = cov
        if year < start or (end and year > end):
            rng = f"{start}–{end or 'present'}"
            res["verdict"] = "OUTSIDE COVERAGE"
            res["detail"].append(
                f"{label}: Find Case Law's stated holdings run {rng}; this citation is "
                f"from {year}. The register cannot answer — absence proves nothing. "
                "Verify in the printed reports or a subscription service.")
            if ck in ARCHIVE_POINTERS:
                res["detail"].append(ARCHIVE_POINTERS[ck])
            return res

    hit = None
    for slug in cands:
        status, body = _get(f"{FCL}/{slug}/data.xml", ok404=True)
        if status == 200:
            hit = (slug, body)
            break
    if not hit:
        res["verdict"] = "NOT ON REGISTER"
        res["detail"].append(
            "No record at " + ", ".join(f"{FCL}/{s}" for s in cands) + ". The court and "
            "year are within Find Case Law's stated coverage, so a genuine judgment "
            "would usually be here — treat this citation as unsafe to rely on until "
            "the judgment itself is located somewhere. It is NOT proof of fabrication: "
            "TNA's own caveat is that coverage within a range is incomplete, since not "
            "every judgment is sent for publication. Cross-check by name "
            "(`ukcite find`), then on a subscription service, before any conclusion.")
        return res

    slug, body = hit
    res["url"] = f"{FCL}/{slug}"
    meta, text = parse_judgment(body)
    res["official_name"] = meta["name"]
    res["judgment_date"] = meta["date"]
    res["detail"].append(f"On the register: {meta['name'] or '(name not in XML)'}"
                         f" — {meta['court'] or ''} — {meta['date'] or ''}".strip())

    problems = []
    if meta.get("cite"):
        want = re.sub(r"\s+", " ", citation.strip())
        got = re.sub(r"\s+", " ", meta["cite"])
        if _tokens(want) != _tokens(got):
            problems.append(f"The document's own recorded citation is {got!r}.")
    if meta["date"]:
        try:
            jy = int(meta["date"][:4])
            if abs(jy - year) > 1:
                problems.append(f"Citation year {year} v judgment date {meta['date']}.")
        except ValueError:
            pass
    if name and meta["name"]:
        score = name_match(name, meta["name"])
        if score < 0.5:
            problems.append(
                f"Claimed name {name!r} does not match the register's "
                f"{meta['name']!r} (overlap {score:.0%}). The citation exists but may "
                "be attached to the wrong case — the classic miscitation.")
        else:
            res["detail"].append(f"Name matches ({score:.0%} of distinctive words).")

    if para is not None:
        nums = para_numbers(body)
        if not nums:
            res["detail"].append("Paragraph numbering not machine-readable in this "
                                 "document — check the pinpoint by eye.")
        elif para in nums:
            res["detail"].append(f"Paragraph [{para}] exists (judgment runs to [{max(nums)}]).")
        else:
            problems.append(f"No paragraph [{para}] — numbering runs to [{max(nums)}].")

    if quote:
        kind, ctx = quote_check(quote, text)
        if kind == "verbatim":
            res["detail"].append("Quoted passage found VERBATIM in the judgment text.")
        elif kind == "near":
            problems.append("Quoted passage is a NEAR MISS, not verbatim. The source "
                            f"reads: “{ctx}” — quote the source, not the memory of it.")
        else:
            problems.append("Quoted passage NOT FOUND in the judgment text. Do not use "
                            "it until located and checked against the source.")

    res["verdict"] = "MISMATCH" if problems else "VERIFIED"
    res["detail"].extend(problems)
    return res


# ---------------------------------------------------------------------------
# find by name (leads, not verdicts)
# ---------------------------------------------------------------------------
def find_by_name(name, court=None, limit=8):
    # Party-name search first (precise); full-text search as the fallback
    # (noisy — a much-cited case name matches every judgment citing it).
    for param in ("party", "query"):
        q = urllib.parse.urlencode(
            {k: v for k, v in ((param, name), ("court", court)) if v})
        status, body = _get(f"{FCL}/atom.xml?{q}")
        if re.search(rb"<entry>", body):
            break
    out = []
    for entry in re.findall(rb"<entry>.*?</entry>", body, re.S)[:limit]:
        t = re.search(rb"<title>(.*?)</title>", entry, re.S)
        ncn = re.search(rb'type="ukncn">(.*?)</tna:identifier>', entry)
        link = re.search(rb'<link href="([^"]+)" rel="alternate"/>', entry)
        out.append({
            "title": (html.unescape(t.group(1).decode("utf-8", "replace").strip()) if t else ""),
            "ncn": (ncn.group(1).decode() if ncn else ""),
            "url": (link.group(1).decode() if link else ""),
        })
    return out


# ---------------------------------------------------------------------------
# statutes
# ---------------------------------------------------------------------------
def check_statute(title, section=None, doctype="ukpga"):
    q = urllib.parse.urlencode({"title": title})
    status, body = _get(f"{LEG}/{doctype}/data.feed?{q}")
    ids = re.findall(rb"<id>http://www\.legislation\.gov\.uk/id/(%s/\d{4}/\d+)</id>"
                     % doctype.encode(), body)
    if not ids:
        return {"verdict": "NOT FOUND", "detail": [
            f"No {doctype} matching {title!r} on legislation.gov.uk. Check the short "
            "title and year; secondary legislation needs --type uksi."]}
    ref = ids[0].decode()
    out = {"act": ref, "detail": [], "verdict": "VERIFIED"}
    if section is None:
        out["url"] = f"{LEG}/{ref}"
        out["detail"].append(f"Act exists: {LEG}/{ref}")
        return out
    url = f"{LEG}/{ref}/section/{section}"
    status, body = _get(f"{url}/data.xml", ok404=True)
    if status == 404:
        out["verdict"] = "SECTION NOT FOUND"
        out["detail"].append(f"{url} returns no such provision in the current revised text.")
        return out
    out["url"] = url
    ver = re.search(rb'RestrictStartDate="([^"]+)"', body)
    unapplied = len(re.findall(rb"<ukm:UnappliedEffect\b", body))
    out["detail"].append(f"Section exists: {url}")
    if ver:
        out["detail"].append(
            f"Retrieved text is the revised version in force from {ver.group(1).decode()} "
            "(latest available). This is a point-in-time text — if the operative date of "
            "your matter is earlier, use the page's 'Changes over time' view.")
    if unapplied:
        out["detail"].append(
            f"⚠ {unapplied} outstanding amendment effect(s) not yet applied to this "
            "text — enacted changes may not be incorporated. Open the section's 'Changes "
            "over time' before relying on the wording.")
    return out


# ---------------------------------------------------------------------------
# document loading — lawyers' documents are .docx, so read them natively.
# A verification tool must never return a false clean bill because it could
# not read the file: anything unreadable is refused, never scanned as noise.
# ---------------------------------------------------------------------------
def load_document(path):
    raw = Path(path).read_bytes()
    if raw[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                names = z.namelist()
                if "word/document.xml" in names:
                    parts = []
                    for name in ("word/document.xml", "word/footnotes.xml",
                                 "word/endnotes.xml"):
                        if name in names:
                            xml = z.read(name).decode("utf-8", "replace")
                            xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
                            xml = re.sub(r"<w:(br|cr)[^>]*/>", "\n", xml)
                            xml = re.sub(r"</w:p>", "\n", xml)
                            parts.append(html.unescape(re.sub(r"<[^>]+>", "", xml)))
                    return "\n".join(parts)
        except zipfile.BadZipFile:
            pass
        raise SystemExit(f"{path} is a zip container but not a readable .docx. "
                         "Extract the text and scan that — do not treat this "
                         "refusal as 'no citations'.")
    if raw[:5] == b"%PDF-":
        raise SystemExit(f"{path} is a PDF. This tool does not extract PDF text; "
                         "convert it (e.g. `pdftotext`) and scan the result — do "
                         "not treat this refusal as 'no citations'.")
    if b"\x00" in raw[:2048]:
        raise SystemExit(f"{path} looks binary, not text. Extract the text and "
                         "scan that — do not treat this refusal as 'no citations'.")
    return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def write_report(kind, items):
    CACHE.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    lines = [f"# ukcite {kind} — {ts}Z", ""]
    for it in items:
        lines.append(f"## {it.get('citation') or it.get('act') or it.get('title', '?')}")
        lines.append(f"**{it['verdict']}**" + (f" — {it['url']}" if it.get("url") else ""))
        lines.extend(f"- {d}" for d in it.get("detail", []))
        lines.append("")
    path = CACHE / f"report-{ts}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    with (CACHE / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "kind": kind,
                            "results": [{k: v for k, v in it.items() if k != "detail"}
                                        for it in items]}) + "\n")
    return path


def print_result(r):
    mark = {"VERIFIED": "✔", "MISMATCH": "✖", "NOT ON REGISTER": "✖",
            "OUTSIDE COVERAGE": "◌", "UNCHECKABLE": "◌",
            "UNPARSEABLE": "?", "NOT FOUND": "✖",
            "SECTION NOT FOUND": "✖"}.get(r["verdict"], "?")
    head = r.get("citation") or r.get("act") or ""
    print(f"\n{mark} {head} — {r['verdict']}" + (f"\n  {r['url']}" if r.get("url") else ""))
    for d in r.get("detail", []):
        print(f"  · {d}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
USAGE = """usage:
  ukcite.py check "<neutral citation>" [--name "Case Name"] [--para N] [--quote "..."]
  ukcite.py scan <file>                 check every citation found in a document
  ukcite.py find "<case name>" [--court ewhc/admin]
  ukcite.py statute "<Short Title YYYY>" [--section N] [--type ukpga|uksi|asp|anaw]
"""


def _flag(args, name, cast=str):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return cast(v)
    return None


def main(argv):
    if len(argv) < 2:
        print(USAGE)
        return 2
    cmd, args = argv[1], argv[2:]
    if cmd == "check":
        name = _flag(args, "--name")
        para = _flag(args, "--para", int)
        quote = _flag(args, "--quote")
        if not args:
            print(USAGE)
            return 2
        r = check_citation(args[0], name=name, para=para, quote=quote)
        print_result(r)
        path = write_report("check", [r])
        print(f"\nreport: {path}")
        return 0 if r["verdict"] == "VERIFIED" else 1
    if cmd == "scan":
        text = load_document(args[0])
        seen, results = set(), []
        for m in list(NCN_RE.finditer(text)) + list(REPORT_RE.finditer(text)):
            c = re.sub(r"\s+", " ", m.group(0))
            if c not in seen:
                seen.add(c)
                r = check_citation(c)
                print_result(r)          # progressive: one result per check
                results.append(r)
        if results:
            path = write_report("scan", results)
            bad = [r for r in results if r["verdict"] in ("MISMATCH", "NOT ON REGISTER")]
            print(f"\n{len(results)} citation(s); {len(bad)} needing attention. report: {path}")
            return 1 if bad else 0
        print("No UK citations recognised in the document.")
        return 0
    if cmd == "find":
        court = _flag(args, "--court")
        hits = find_by_name(args[0], court=court)
        if not hits:
            print("No results. A nil search return is a lead exhausted, not a fact established.")
            return 1
        print("Leads (full-text search — confirm identity before relying on any):")
        for h in hits:
            print(f"  {h['ncn'] or '(no NCN)':>24}  {h['title']}\n{'':>28}{h['url']}")
        return 0
    if cmd == "statute":
        section = _flag(args, "--section")
        doctype = _flag(args, "--type") or "ukpga"
        r = check_statute(args[0], section=section, doctype=doctype)
        print_result(r)
        path = write_report("statute", [r])
        print(f"\nreport: {path}")
        return 0 if r["verdict"] == "VERIFIED" else 1
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
