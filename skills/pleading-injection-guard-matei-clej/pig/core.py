"""Core model, normalisation, patterns and content analysis for pleading-injection-guard."""
from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

SCANNER_VERSION = "2.1.0"
SCHEMA_VERSION = "2.0"

SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
VERDICT_EXIT = {"CLEAN": 0, "REVIEW": 1, "HOSTILE": 2, "ERROR": 3, "UNSCANNED": 3}

# --------------------------------------------------------------------------
# Channels
# --------------------------------------------------------------------------
VISIBLE = "visible"            # what a reader sees on the page
VISIBLE_OCR = "visible-ocr"    # what a reader sees, recovered by our OCR (scanned pages, images)
LINK = "link"                  # hyperlink targets: an affordance the reader can see
OCR_LAYER = "ocr-layer"        # a sender's invisible OCR layer over a scanned image
OCR_DIFF = "ocr-diff"          # text-layer words the rendered page does not support

# Concealed body text: natural language here is the attack itself.
BODY_HIDDEN = {
    "hidden-format", "hidden-covered", "hidden-clipped", "hidden-offpage",
    "hidden-extraction-only", "hidden-ocg", "hidden-fallback", "hidden-orphan-part",
    "hidden-css", "hidden-alternative", "hidden-aggregate",
}
# Hidden, but a known document feature (comments, tracked changes, metadata…).
SECONDARY_HIDDEN = {
    "hidden-comment", "hidden-tracked-deletion", "hidden-alt-text", "hidden-annotation",
    "hidden-form-field", "hidden-field-code", "hidden-metadata", "hidden-customxml",
    "hidden-docvar", "hidden-glossary", "hidden-webextension", "hidden-header",
    "hidden-html-comment", "hidden-outline", "hidden-embedded-name", "hidden-speaker-notes",
    "hidden-mime", "hidden-actions", "hidden-binary-strings", "hidden-form-value",
}
VISIBLE_LIKE = {VISIBLE, VISIBLE_OCR, OCR_LAYER}


def is_hidden(channel: str) -> bool:
    return channel not in VISIBLE_LIKE and channel != LINK


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------
@dataclass
class Segment:
    text: str
    channel: str
    where: str
    note: str = ""
    page: int | None = None


@dataclass
class Finding:
    severity: str
    kind: str
    channel: str
    where: str
    excerpt: str = ""
    detail: str = ""
    page: int | None = None


@dataclass
class Report:
    file: str
    display_name: str
    sha256: str = ""
    size: int = 0
    sniffed_type: str = "unknown"
    status: str = "scanned"        # scanned | partial | unscanned | error
    verdict: str = "CLEAN"
    parent: str | None = None
    pages: int | None = None
    pages_ocr: int = 0
    pages_unverified: list = field(default_factory=list)
    duration_ms: int = 0
    findings: list = field(default_factory=list)
    channel_chars: dict = field(default_factory=dict)
    invisible_chars: int = 0
    visible_citations: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    children: list = field(default_factory=list)
    embedded: bool = False     # embedded object: an unscannable one does not block the parent
    visible_text: list = field(default_factory=list)   # not serialised

    def add(self, *a, **k):
        self.findings.append(Finding(*a, **k))


class Unscannable(Exception):
    """The file cannot be scanned (encrypted, unsupported, empty). Verdict UNSCANNED."""


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------
TAG_RANGE = (0xE0000, 0xE007F)
VS_RANGES = ((0xFE00, 0xFE0F), (0xE0100, 0xE01EF))
ZW = {0x200B, 0x200C, 0x200D, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0x180E, 0xFEFF}
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
MARKS = {0x200E, 0x200F, 0x061C}
FILLERS = {0x034F, 0x2800, 0x3164, 0x115F, 0x1160, 0xFFA0, 0x17B4, 0x17B5}
SOFT = {0x00AD}


def _in(cp, rng):
    return rng[0] <= cp <= rng[1]


def is_carrier(cp: int) -> bool:
    return (cp in ZW or cp in BIDI or cp in MARKS or cp in FILLERS or cp in SOFT
            or _in(cp, TAG_RANGE) or any(_in(cp, r) for r in VS_RANGES))


def strip_invisible(s: str) -> str:
    return "".join(ch for ch in s if not is_carrier(ord(ch)))


CONFUSABLES = str.maketrans({
    # Cyrillic
    "а": "a", "в": "b", "е": "e", "ё": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c",
    "т": "t", "у": "y", "х": "x", "ѕ": "s", "і": "i", "ї": "i", "ј": "j", "ԁ": "d", "һ": "h", "ԛ": "q",
    "ԝ": "w", "ɡ": "g", "ӏ": "l", "ո": "n", "ս": "u",
    "А": "a", "В": "b", "Е": "e", "К": "k", "М": "m", "Н": "h", "О": "o", "Р": "p", "С": "c", "Т": "t",
    "У": "y", "Х": "x", "Ѕ": "s", "І": "i", "Ј": "j",
    # Greek
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u",
    "χ": "x", "Α": "a", "Β": "b", "Ε": "e", "Ζ": "z", "Η": "h", "Ι": "i", "Κ": "k", "Μ": "m", "Ν": "n",
    "Ο": "o", "Ρ": "p", "Τ": "t", "Υ": "y", "Χ": "x",
    # Latin look-alikes and punctuation
    "ı": "i", "ȷ": "j", "ℓ": "l", "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "’": "'", "‘": "'",
})


def norm_for_match(s: str) -> str:
    """Text as a pattern sees it: NFKC, carriers and combining marks removed,
    confusables folded to Latin, hyphenated line breaks joined, whitespace collapsed."""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(ch for ch in s if not is_carrier(ord(ch))
                and unicodedata.category(ch) not in ("Cf", "Me"))
    # remove combining marks only where they decorate Latin/ASCII (keeps ă, ș, ł composed forms)
    s = unicodedata.normalize("NFD", s)
    out = []
    for ch in s:
        if unicodedata.category(ch) == "Mn" and out and ord(out[-1]) < 0x80:
            continue
        out.append(ch)
    s = unicodedata.normalize("NFC", "".join(out))
    s = s.translate(CONFUSABLES)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    s = re.sub(r"\s+", " ", s)
    return s


def fold(s: str) -> str:
    """Aggressive fold for word comparison: norm_for_match, lowercase, diacritics stripped."""
    s = norm_for_match(s).casefold()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


WORD_RE = re.compile(r"[^\W_]+")


def words(s: str, minlen: int = 1) -> list[str]:
    return [w for w in WORD_RE.findall(fold(s)) if len(w) >= minlen]


def letters(s: str) -> int:
    return sum(1 for ch in s if ch.isalpha())


def show(s: str, n: int = 280) -> str:
    """Render invisible/format characters so a reader can see them."""
    out = []
    for ch in s:
        cp = ord(ch)
        if is_carrier(cp):
            out.append(f"<U+{cp:04X}>")
        elif ch in "\r\n\t":
            out.append(" ")
        elif unicodedata.category(ch) == "Cc":
            out.append(f"<0x{cp:02X}>")
        else:
            out.append(ch)
    r = re.sub(r"\s+", " ", "".join(out)).strip()
    return r if len(r) <= n else r[: n - 1] + "…"


# --------------------------------------------------------------------------
# Patterns (applied to norm_for_match text, case-insensitive)
# --------------------------------------------------------------------------
_AI = (r"(?:ai|a\.i\.|ia|ki|llm|large language model|language[- ]model(?:[- ]based)?|assistant|chatbot|gpt|chatgpt|claude|"
       r"copilot|gemini|harvey|co-?counsel|model|bot|digital assistant|summari[sz]er|machine reader|"
       r"automated (?:system|tool|reviewer|reader|review|analysis|assistant|process)|reviewing system|"
       r"ai (?:system|tool|reviewer|model)|text[- ]analysis (?:system|tool)|computer (?:system|program))")
_AI_RO = r"(?:asistent\w*|model\w* de limbaj|inteligen\w* artificial\w*|sistem\w* automat\w*)"
_AI_PL = r"(?:asystent\w*|model\w* językow\w*|sztuczn\w* inteligencj\w*|system\w* automatyczn\w*)"
_AI_ANY = rf"(?:{_AI}|{_AI_RO}|{_AI_PL}|asistente|assistente|assistent|asszisztens|асистент\w*|ассистент\w*|pomocník)"

_IGNORE = (r"(?:ignore|disregard|forget|override|bypass|set aside|discard|ignor[aăeiu]\w*|zignoruj\w*|ignoruj\w*|"
           r"nepaisyk\w*|ignorē\w*|figyelmen kívül|игнорира\w*|игнорируй\w*|ignorieren?|ignorez|ignorar)")
_INSTR = (r"(?:instruction|prompt|direction|rule|guideline|guidance|what (?:you|it) (?:was|were|have been|has been) told|"
          r"instruc[tț]iun\w*|instrukcj\w*|instrukcij\w*|nurodym\w*|utasítás\w*|инструкци\w*|pokyn\w*|"
          r"istruzion\w*|instrucc\w*|instruç\w*|anweisung\w*|consignes?)")

GENERIC = [
    ("override", rf"\b{_IGNORE}\b.{{0,40}}\b(?:previous|prior|above|earlier|all|any|your|other|system|whatever|anything|"
                 rf"anterioare|precedente|poprzedni\w*|wcześniejsz\w*|toate|wszystki\w*)\b.{{0,30}}\b{_INSTR}"),
    ("override", rf"\b{_IGNORE}\b.{{0,15}}\b(?:whatever|what|anything)\b.{{0,10}}\byou\b.{{0,10}}\b(?:were|have been|are)\b.{{0,5}}\btold\b"),
    ("system-prompt", r"\b(?:system|developer|hidden)\s*(?:prompt|message|instruction)s?\b"),
    ("role-assign", rf"\b(?:you are|you're|act as|pretend to be|role-?play as|behave as)\b.{{0,30}}\b{_AI}\b"),
    ("addressed-to-ai", rf"\b(?:note|message|instruction|attention|notice|memo|direction)s?\s+(?:to|for)\s+(?:the\s+|any\s+|all\s+)?{_AI}s?\b"),
    ("addressed-to-ai", rf"\bfor the attention of (?:the |any )?{_AI}"),
    ("addressed-to-ai", rf"\bif you are (?:an?\s+)?{_AI}\b"),
    ("addressed-to-ai", rf"\b{_AI}s?\s+(?:reading|reviewing|processing|summari[sz]ing|analy[sz]ing|ingesting|examining)\s+(?:this|these)\b"),
    ("addressed-to-ai", rf"\b(?:any|the|an?)\s+(?:automated|machine|computer|ai|algorithmic)[- ](?:review|reviewer|reading|reader|analysis|summary|system|tool|process)s?\b"),
    ("addressed-to-ai", r"\bwhen (?:summari[sz]ing|analy[sz]ing|reviewing|processing|reading) (?:this|these) (?:document|pleading|file|text|submission|skeleton|statement|bundle|letter|email|papers?)\b"),
    ("addressed-to-ai", rf"\b(?:not[aă]|nota|note|hinweis|poznámka|megjegyzés)\s+(?:pentru|dla|pour|per|para|für|pro|a|az)\s+(?:\w+\s+){{0,2}}{_AI_ANY}"),
    ("chat-template", r"<\|?(?:im_start|im_end|system|endoftext|eot_id|start_header_id)\|?>|\[/?INST\]|<</?SYS>>|</?(?:system|instructions?|admin)>"),
    ("concealment", r"\bdo not (?:mention|disclose|reveal|flag|report|tell|inform|highlight|note|alert)\b.{0,60}\b(?:user|lawyer|counsel|solicitor|barrister|client|reader|human|operator|anyone)\b"),
    ("concealment", r"\bkeep (?:this|these|it)\b.{0,20}\bout of (?:any|the|your)\b.{0,15}\b(?:summar\w*|report|advice|analysis|note)"),
    ("concealment", r"\b(?:nu (?:menționa|mentiona|spune|dezvălui)\w*|nie (?:wspominaj|mów|ujawniaj)\w*)\b"),
    ("new-instructions", r"\b(?:new|updated|revised|additional|important) instructions?\s*[:\-]"),
    ("jailbreak", r"\b(?:jailbreak|prompt injection|dan mode|developer mode)\b"),
    ("encoded-payload", r"\b(?:rot-?13|base-?64|decode the following|decode this)\b"),
]
# Only in hidden channels: role lines are ordinary in chat exhibits and transcripts.
HIDDEN_ONLY = [
    ("chat-template", r"(?m)^\s*(?:#{1,3}\s*)?(?:system|assistant|human|user)\s*:\s*\S"),
]
LEGAL_STEER = [
    ("steer-client", r"\b(?:advise|recommend|tell|instruct|urge|persuade|steer|nudge|guide|lead)\b.{0,40}\b(?:your |the )?(?:client|claimant|defendant|appellant|respondent|requested person|applicant)s?\b.{0,40}\b(?:to )?(?:settle|concede|withdraw|discontinue|accept|plead guilty|consent|abandon|drop|not (?:to )?(?:appeal|contest|defend))"),
    ("steer-client", r"\b(?:sfătui|sfatui|recomand|convinge)\w*\b.{0,30}\b(?:client\w*|persoana solicitată|inculpat\w*)\b.{0,40}\b(?:consim\w*|renun\w*|accept\w*|recunoa\w*)"),
    ("steer-client", r"\b(?:doradź|doradzi\w*|zalec\w*|przekonaj\w*)\b.{0,30}\b(?:klient\w*|oskarżon\w*|osob\w* ścigan\w*)\b.{0,40}\b(?:zgod\w*|wycof\w*|przyzna\w*|zrezygn\w*)"),
    ("steer-outcome", r"\b(?:recommend|advise|suggest|propose)\b.{0,30}\b(?:settlement|concession|a guilty plea|withdrawal|discontinuance|consent(?:ing)? to (?:extradition|the order|judgment)|not appealing|accepting the offer)\b"),
    ("steer-outcome", r"\b(?:should|must|will) conclude that\b.{0,60}\b(?:hopeless|without merit|meritless|bound to fail|unarguable|no (?:real )?prospect)"),
    ("deadline", r"\b(?:deadline|time limit|limitation period|time for (?:service|filing|appeal)|return date)\b.{0,40}\b(?:has been|have been|is|are|was)\s+(?:extended|waived|vacated|suspended|dispensed with)\b"),
    ("no-action", r"\bno (?:response|reply|acknowledg(?:e)?ment|action|step|objection)s? (?:is|are) (?:required|necessary|needed|expected)\b"),
    ("suppress-verification", r"\b(?:do not|don't|no need to|unnecessary to|need not)\s+(?:check|verify|confirm|look up|cross-?check|validate|research)\b"),
    ("assert-verified", r"\b(?:this|these|all|the) (?:authorit(?:y|ies)|citations?|cases?|quotations?|references?) (?:has|have) (?:already )?been (?:verified|checked|confirmed|validated)\b"),
    ("treat-as", r"\b(?:treat|regard|accept)\b.{0,30}\bas (?:binding|authoritative|verified|conclusive|settled|correct|agreed)\b"),
    ("omit", r"\b(?:omit|skip|ignore|disregard|exclude|leave out)\b.{0,20}\b(?:paragraph|para|section|exhibit|ground|annex|appendix|page|footnote|schedule)s?\b"),
    ("frame-summary", r"\b(?:summari[sz]e|describe|characteri[sz]e|present|report|conclude)\b.{0,40}\b(?:as|to be|that it is)\s+(?:weak|strong|meritless|unarguable|without merit|hopeless|compelling|favourable|favorable|unanswerable|conceded)\b"),
    ("rate-prospects", r"\b(?:rate|score|assess|put)\b.{0,30}\b(?:prospects?|merits?|chances?)\b.{0,20}\b(?:at|as)\s+(?:\d{1,3}\s?%|nil|low|minimal)"),
]
EXFIL = [
    ("exfil-request", r"\b(?:include|append|insert|output|print|repeat|reveal|send|email|forward|post|upload|share|list|quote|attach)\b.{0,40}\b(?:system prompt|your instructions|privileged|client'?s? (?:instructions|confidential|advice|statement|proof)|confidential (?:instructions|advice|material)|conversation|chat history|previous (?:messages|documents|conversation)|your memory|your notes|your (?:context|files)|other (?:matters|clients))\b"),
    ("exfil-image", r"!\[[^\]]*\]\(\s*https?://[^)\s]+\)"),
    ("exfil-url-template", r"https?://\S+\?\S*=(?:\{|%7B|\[|<|\$)"),
    ("tool-call", r"\b(?:visit|open|fetch|browse to|navigate to|call|curl|download from|click)\b.{0,20}https?://"),
]

URL_RE = re.compile(r"https?://[^\s)>\]\"']+", re.I)
CITE_RE = re.compile(
    r"\[(?:19|20)\d{2}\]\s+(?:UKSC|UKHL|UKPC|EWCA\s+(?:Civ|Crim)|EWHC|UKUT|UKFTT|UKEAT|CSIH|CSOH|NICA|NIQB|EWFC|EWCOP)\s+\d+"
    r"|\[(?:19|20)\d{2}\]\s+\d?\s*(?:AC|QB|KB|Ch|Fam|WLR|All ER|Cr App R|Imm AR|INLR|EHRR|ECR)\s+\d+"
    r"|\((?:19|20)\d{2}\)\s+\d+\s+(?:EHRR|Cr App R|BHRC)\s+\d+"
    r"|\b(?:C|T)-\d{1,4}/\d{2}\b"
    r"|\bApplication no\.?\s*\d{3,6}/\d{2}\b",
    re.I,
)

_F = re.I | re.S
GENERIC_C = [(n, re.compile(p, _F)) for n, p in GENERIC]
HIDDEN_ONLY_C = [(n, re.compile(p, _F)) for n, p in HIDDEN_ONLY]
STEER_C = [(n, re.compile(p, _F)) for n, p in LEGAL_STEER]
EXFIL_C = [(n, re.compile(p, _F)) for n, p in EXFIL]

# Machine markers left by bundling / e-disclosure software. Hidden but harmless.
_MARK = re.compile(r":casedo_id=\d+:|\{\{[^{}]{0,40}\}\}|\b[0-9a-f]{32,128}(?:-\d+)?\b|\b[A-Z]{1,4}\d{1,5}\b"
                   r"|\bPicture\.|\b\w+_SigImage\b")


def benign_marker(t: str) -> bool:
    """Linear-time test: nothing alphabetic survives once machine markers are removed."""
    return not re.search(r"[^\W\d_]", _MARK.sub("", t))


# Function words: an instruction is a sentence; a form label or an ID is not.
STOPWORDS = set("""
the a an to of and or in on at for from by with as is are was were be been being this that these those it its
you your yours we our they their he she his her not no do does did should must will would can could may might
shall any all if then than when which who whom what there here into onto upon about only also so such very
si să sa la în in pe cu de din pentru nu este sunt fi va ca care ce acest această aceste acestei dumneavoastră
nie się to i w na z do że jest są być jak dla przez ten ta te tego tej czy lub oraz
der die das und zu den ist nicht ein eine le la les et de des un une est pas pour que qui
el los las y del es por para con no que il lo gli e di che per non è
""".split())


LEGAL_AI_VOCAB = re.compile(
    r"\b(?:ai|a\.i\.|llm|assistant|aide|model|bot|machine|automated|summar\w*|client\w*|appeal\w*|court|judge\w*|"
    r"counsel|lawyer|solicitor|barrister|advise\w*|advice|extradit\w*|concede\w*|concession|consent\w*|plead\w*|"
    r"guilty|settle\w*|withdraw\w*|hopeless|doomed|merit\w*|prospects?|deadline|instruction\w*|ignore\w*|"
    r"disregard\w*|omit\w*|verify|verified|authorit\w*|agreement|surrender\w*|avocat\w*|clientul\w*|apel\w*|"
    r"instan\w*|extr[aă]d\w*|klient\w*|apelacj\w*|sąd\w*|ekstradycj\w*)\b", re.I)


def legal_ai_terms(t: str) -> int:
    return len({m.group(0).lower() for m in LEGAL_AI_VOCAB.finditer(norm_for_match(t))})


def is_prose(t: str) -> bool:
    ws = [w for w in re.findall(r"[^\W\d_]+", norm_for_match(t).casefold())]
    if len(ws) < 5:
        return False
    sw = sum(1 for w in ws if w in STOPWORDS)
    return sw >= 3 and sw / len(ws) >= 0.15


def cite_key(c: str) -> str:
    return re.sub(r"\s+", " ", c).strip().upper()


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------
def _decoded_variants(t: str):
    """Yield (label, text) for encoded carriers worth rescanning."""
    for m in re.finditer(r"[A-Za-z0-9+/]{24,}={0,2}", t):
        tok = m.group(0)
        try:
            raw = base64.b64decode(tok + "=" * (-len(tok) % 4), validate=True)
            dec = raw.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        if letters(dec) >= 12 and sum(c.isprintable() for c in dec) / max(1, len(dec)) > 0.95:
            yield "base64", dec
    for m in re.finditer(r"(?:[0-9A-Fa-f]{2}){16,}", t):
        try:
            dec = bytes.fromhex(m.group(0)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        if letters(dec) >= 12 and sum(c.isprintable() for c in dec) / max(1, len(dec)) > 0.95:
            yield "hex", dec
    if len(re.findall(r"%[0-9A-Fa-f]{2}", t)) >= 5:
        from urllib.parse import unquote
        dec = unquote(t)
        if dec != t and letters(dec) >= 12:
            yield "percent", dec


def pattern_hits(text: str, hidden: bool):
    """Yield (group, name, match_text, excerpt)."""
    t = norm_for_match(text)
    groups = [("injection", GENERIC_C), ("legal-steer", STEER_C), ("exfiltration", EXFIL_C)]
    if hidden:
        groups.append(("injection", HIDDEN_ONLY_C))
    for group, pats in groups:
        for name, rx in pats:
            for m in rx.finditer(t):
                a, b = max(0, m.start() - 80), min(len(t), m.end() + 80)
                yield group, name, m.group(0), t[a:b]


def analyse_segment(seg: Segment, rep: Report, visible_cites: set, stats: dict):
    ch = seg.channel
    if ch == "css-unverified":
        rep.add("medium", "css-unverified", "hidden-css", seg.where, "", f"visibility depends on CSS this scanner "
                f"does not evaluate: {seg.note}")
        return
    hidden = is_hidden(ch)
    raw = seg.text
    t = strip_invisible(raw)
    rep.channel_chars[ch] = rep.channel_chars.get(ch, 0) + len(raw)

    # Unicode carriers: counted per document, reported once in finalise().
    for c in raw:
        cp = ord(c)
        if not is_carrier(cp):
            continue
        rep.invisible_chars += 1
        if _in(cp, TAG_RANGE):
            stats["tag"].append(c)
            stats.setdefault("tag_where", seg.where)
        elif any(_in(cp, r) for r in VS_RANGES):
            stats["vs"].append(c)
            stats.setdefault("vs_where", seg.where)
        elif cp in BIDI:
            stats["bidi"] += 1
            stats.setdefault("bidi_where", (seg.where, show(raw)))
        elif cp in ZW and not (cp == 0xFEFF and raw.startswith(c)):
            stats["zw"] += 1
            stats.setdefault("zw_where", (seg.where, show(raw)))
        elif cp in FILLERS:
            stats["fill"] += 1
            stats.setdefault("fill_where", (seg.where, show(raw)))
    # VS whose base is not an emoji-ish symbol or CJK ideograph = smuggling
    for i, c in enumerate(raw):
        if any(_in(ord(c), r) for r in VS_RANGES):
            base = raw[i - 1] if i else ""
            if not base or not (unicodedata.category(base) == "So" or 0x2E80 <= ord(base) <= 0x9FFF
                                or 0x1F000 <= ord(base) <= 0x1FAFF or any(_in(ord(base), r) for r in VS_RANGES)
                                or base in "0123456789#*"):
                stats["vs_bad"] += 1
    # Mixed-script words (homoglyph substitution)
    for w in re.findall(r"[^\W\d_]{3,}", raw):
        scripts = set()
        for c in w:
            name = unicodedata.name(c, "")
            for s in ("LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "CHEROKEE"):
                if name.startswith(s):
                    scripts.add(s)
        if len(scripts) > 1:
            stats["mixed"].add(w)
            stats.setdefault("mixed_where", seg.where)

    if ch == LINK:
        for group, name, mt, ex in pattern_hits(t, False):
            if group == "exfiltration":
                rep.add("high", f"{group}:{name}", ch, seg.where, show(ex), f"matched: {show(mt, 120)!r}", seg.page)
        return

    # Pattern analysis, including decoded carriers and rot13 in hidden text
    variants = [("", t)]
    joined = re.sub(r"(?<=[^\W\d_])[-\u00ad](?=[^\W\d_])", "", t)
    if joined != t:
        variants.append((" (hyphen-joined)", joined))
    variants += [(f" ({lbl}-decoded)", d) for lbl, d in _decoded_variants(t)]
    if hidden:
        variants.append((" (rot13-decoded)", codecs.decode(t, "rot13")))
    hit = False
    seen_kinds = set()
    first_idx = len(rep.findings)
    for suffix, text in variants:
        for group, name, mt, ex in pattern_hits(text, hidden):
            if suffix == " (rot13-decoded)" and group == "legal-steer":
                continue
            hit = True
            if suffix == " (hyphen-joined)" and any(f.kind.startswith(f"{group}:{name}") for f in rep.findings[first_idx:]):
                continue
            if group in ("injection", "exfiltration"):
                seen_kinds.add(name)
            if hidden or suffix:
                sev = "critical" if hidden else "high"
            elif group == "legal-steer":
                sev = "low"
            else:
                sev = "high"
            rep.add(sev, f"{group}:{name}{suffix.replace(' ', '')}", ch, seg.where, show(ex),
                    f"matched: {show(mt, 120)!r}", seg.page)
    stats["pattern_segments"].add(id(seg)) if hit else None
    # Several distinct injection markers, or one plus legal steering, in the same visible passage
    # = a payload, not a quotation.
    steer_hit = any(f.kind.startswith("legal-steer:") for f in rep.findings[first_idx:])
    if not hidden and (len(seen_kinds) >= 2 or (seen_kinds and steer_hit)):
        for f in rep.findings[first_idx:]:
            if f.severity == "high" and f.kind.split(":")[0] in ("injection", "exfiltration"):
                f.severity = "critical"
                f.detail += f" [escalated: {len(seen_kinds)} distinct injection markers in one visible passage]"

    if hidden:
        for m in URL_RE.finditer(t):
            rep.add("low" if ch in ("hidden-metadata", "hidden-header") else "high",
                    "url-in-hidden-channel", ch, seg.where, m.group(0), "", seg.page)
        for m in CITE_RE.finditer(t):
            if cite_key(m.group(0)) in visible_cites:
                continue
            sev = "critical" if ch in BODY_HIDDEN else "high"
            rep.add(sev, "authority-in-hidden-channel", ch, seg.where,
                    show(t[max(0, m.start() - 80): m.end() + 80]),
                    f"citation {m.group(0)!r} does not appear in the visible text: treat as planted until verified",
                    seg.page)
        _hidden_bulk(seg, t, rep, hit)


def _hidden_bulk(seg: Segment, t: str, rep: Report, pattern_hit: bool):
    ch = seg.channel
    if ch in ("hidden-metadata", "hidden-customxml", "hidden-mime", "hidden-actions", "hidden-binary-strings"):
        b = strip_invisible(t).strip()
        signal = (is_prose(b) and legal_ai_terms(b) >= 2) if ch == "hidden-metadata" else \
            (is_prose(b) or legal_ai_terms(b) >= 2)
        if letters(b) >= 40 and signal \
                and not re.search(r"multi-?part message in MIME format", b, re.I):
            rep.add("medium", "hidden-prose", ch, seg.where, show(b), "natural-language text in a channel no reader sees",
                    seg.page)
        return
    if ch == "hidden-header":
        return
    body = t.strip()
    n = letters(_MARK.sub(" ", body))
    if n < 4:
        return
    if benign_marker(body):
        rep.add("info", "hidden-machine-markers", ch, seg.where, show(body, 120), seg.note, seg.page)
        return
    if ch in BODY_HIDDEN:
        clean = _MARK.sub(" ", body)
        if n >= 25 and (is_prose(clean) or legal_ai_terms(clean) >= 2):
            sev, kind = "critical", "concealed-text"
        elif n >= 8:
            sev, kind = "high", "hidden-text"
        else:
            sev, kind = "medium", "hidden-text"
    elif ch == OCR_DIFF:
        return   # scored in the PDF module with page context
    else:  # secondary: comments, tracked deletions, alt text, fields, notes…
        if n < 12:
            return
        stealthy = ch in ("hidden-docvar", "hidden-glossary", "hidden-webextension", "hidden-field-code")
        sev, kind = ("medium" if stealthy and n >= 60 else "low"), "hidden-text"
    rep.add(sev, kind, ch, seg.where, show(body), seg.note, seg.page)


REDACT_GROUPS = [GENERIC_C, EXFIL_C, [c for c in STEER_C if c[0] in ("steer-client",)]]


def redact(text: str) -> tuple[str, int]:
    """Replace sentences carrying injection markers with a placeholder (for --emit-visible)."""
    out, n = [], 0
    for sent in re.split(r"(?<=[.!?;:])\s+|\n+", text):
        t = norm_for_match(sent)
        t2 = re.sub(r"(?<=[^\W\d_])[-\u00ad](?=[^\W\d_])", "", t)
        if any(rx.search(x) for grp in REDACT_GROUPS for _, rx in grp for x in (t, t2)):
            out.append("[REMOVED BY INJECTION GUARD]")
            n += 1
        else:
            out.append(sent)
    return " ".join(out) if "\n" not in text else "\n".join(out), n


def new_stats():
    return {"tag": [], "vs": [], "vs_bad": 0, "bidi": 0, "zw": 0, "fill": 0, "mixed": set(),
            "pattern_segments": set()}


def finalise_unicode(rep: Report, stats: dict):
    if stats["tag"]:
        decoded = "".join(chr(ord(c) - 0xE0000) for c in stats["tag"] if 0x20 <= ord(c) - 0xE0000 < 0x7F)
        rep.add("critical", "unicode-tag-smuggling", "unicode", stats["tag_where"], show(decoded),
                f"{len(stats['tag'])} Unicode TAG characters; decoded payload: {decoded!r}")
    if stats["vs_bad"]:
        bs = bytes((ord(c) - 0xFE00) if ord(c) <= 0xFE0F else (ord(c) - 0xE0100 + 16) for c in stats["vs"])
        dec = bs.decode("utf-8", "replace")
        sev = "critical" if stats["vs_bad"] >= 8 else "high"
        rep.add(sev, "variation-selector-smuggling", "unicode", stats["vs_where"], "",
                f"{stats['vs_bad']} variation selectors on non-emoji bases; byte-decoded: {dec[:200]!r}")
    if stats["bidi"]:
        w, ex = stats["bidi_where"]
        rep.add("high", "bidi-override", "unicode", w, ex,
                f"{stats['bidi']} bidirectional control characters: displayed order differs from stored order")
    if stats["zw"] >= 3:
        w, ex = stats["zw_where"]
        rep.add("medium", "zero-width-characters", "unicode", w, ex,
                f"{stats['zw']} zero-width characters in the document (can split trigger words or carry a payload)")
    if stats["fill"] >= 3:
        w, ex = stats["fill_where"]
        rep.add("medium", "invisible-filler-characters", "unicode", w, ex,
                f"{stats['fill']} blank/filler code points (U+034F, U+2800, U+3164, …)")
    if stats["mixed"]:
        rep.add("medium", "homoglyph-mixed-script", "unicode", stats["mixed_where"],
                ", ".join(sorted(stats["mixed"])[:10]),
                f"{len(stats['mixed'])} word(s) mixing Latin with Cyrillic/Greek letters")


def group_findings(findings: list) -> list:
    """Merge identical findings across pages; keep first location, count and page list."""
    out, idx = [], {}
    for f in findings:
        key = (f.severity, f.kind, f.channel, f.excerpt, f.detail if not f.page else f.detail)
        if key in idx:
            g = idx[key]
            g["count"] += 1
            if f.page and f.page not in g["pages"]:
                g["pages"].append(f.page)
            continue
        g = {"id": hashlib.sha1("|".join(map(str, (f.kind, f.channel, f.excerpt))).encode()).hexdigest()[:12],
             "severity": f.severity, "kind": f.kind, "channel": f.channel, "where": f.where,
             "pages": [f.page] if f.page else [], "count": 1, "excerpt": f.excerpt, "detail": f.detail}
        idx[key] = g
        out.append(g)
    return out


def repeated_template_downgrade(rep: Report):
    """Identical hidden body text on >= 3 pages with no pattern hit = template furniture
    (form headers, bundling stamps). Downgrade to low; pattern hits stay critical."""
    by_text = {}
    for f in rep.findings:
        if f.kind == "hidden-text" and f.channel in BODY_HIDDEN and f.page:
            by_text.setdefault((f.channel, f.excerpt), set()).add(f.page)
    rep_texts = {k for k, pages in by_text.items() if len(pages) >= 3 and len(k[1]) <= 300}
    if not rep_texts:
        return
    hit_excerpts = {(f.channel, f.excerpt) for f in rep.findings if ":" in f.kind}
    for f in rep.findings:
        if (f.channel, f.excerpt) in rep_texts and f.kind == "hidden-text" \
                and (f.channel, f.excerpt) not in hit_excerpts:
            f.severity, f.kind = "low", "repeated-hidden-template"
            f.detail = (f.detail + "; " if f.detail else "") + "identical non-prose hidden text on 3+ pages (template furniture?)"


def decide(rep: Report):
    if rep.status == "error":
        rep.verdict = "ERROR"
        return
    if rep.status == "unscanned":
        rep.verdict = "UNSCANNED"
        return
    if rep.status == "partial":   # part of the file deliberately or unavoidably not analysed
        crit = any(SEV_ORDER[f.severity] >= 4 for f in rep.findings)
        rep.verdict = "HOSTILE" if crit else "UNSCANNED"
        return
    worst = max((SEV_ORDER[f.severity] for f in rep.findings), default=0)
    rep.verdict = "HOSTILE" if worst >= 4 else "REVIEW" if worst >= 2 else "CLEAN"


ORDER = ["CLEAN", "REVIEW", "UNSCANNED", "ERROR", "HOSTILE"]


def overall(rep: Report) -> str:
    """Worst verdict of a report and its children. HOSTILE ranks highest for display;
    exit code is computed separately by exit_code()."""
    v = rep.verdict
    for c in rep.children:
        cv = overall(c)
        if c.embedded and cv in ("UNSCANNED", "ERROR"):
            continue
        if ORDER.index(cv) > ORDER.index(v):
            v = cv
    return v


def exit_code(rep: Report) -> int:
    code = VERDICT_EXIT[rep.verdict]
    for c in rep.children:
        cc = exit_code(c)
        if c.embedded and cc == 3:
            continue
        code = max(code, cc)
    return code
