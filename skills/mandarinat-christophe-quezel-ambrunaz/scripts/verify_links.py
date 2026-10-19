#!/usr/bin/env python3
"""
verify_links.py — Vérification batch d'URLs juridiques (Légifrance, LibreJustice,
HUDOC, Curia).

Vérifications effectuées pour chaque URL :
    1. Correspondance à un pattern officiel reconnu (JURITEXT, CETATEXT,
       JORFTEXT, LEGIARTI, LEGITEXT, conseil-constitutionnel.fr, hudoc,
       curia, eur-lex).
    2. Accessibilité HTTP (HEAD).
    3. En mode --check-content (activé par défaut), récupération de la page
       (GET) et vérification que le numéro de pourvoi / numéro d'article /
       mot-clé attendu apparaît dans le contenu.

Les URLs LibreJustice (https://librejustice.fr/decision/… et
https://librejustice.fr/norm/{juridiction}/{code}/{article}, ainsi que
l'ancien format /texte/{code}/{article}) sont reconnues comme
patterns valides : elles constituent le lien vérifiable des décisions
non diffusées sur Légifrance (juridictions du fond, CNDA). Le mode
--extract-ids retourne pour chacune l'outil MCP LibreJustice à appeler
(get_decision / get_norm), qui n'est affecté ni par la liste des
domaines autorisés de l'espace de travail ni par le challenge anti-bot
Cloudflare de Légifrance.

Modes de fonctionnement :
    - --preflight : teste l'état de la sortie réseau et l'accès à
       Légifrance, sans vérifier d'URL. Distingue désormais quatre cas :
       réseau OK (0), bloqué par la liste des domaines autorisés (2), erreur réseau
       générique (3), bloqué par challenge anti-bot Cloudflare (4).
    - --extract-ids : lit une liste d'URLs (ou un texte brut via
       --extract-ids-from-text) et retourne les identifiants Légifrance
       reconnus (LEGIARTI, JURITEXT, CETATEXT, JORFTEXT, JORFARTI,
       LEGITEXT, CNILTEXT, KALITEXT) avec, pour chacun, le nom de
       l'outil OpenLegi à appeler pour vérifier son existence par API.
       Canal nominal : Légifrance est inaccessible aux requêtes
       automatisées (challenge Cloudflare) : la vérification est déléguée à OpenLegi par
       l'agent.
    - --strict : code de retour ≠ 0 si au moins une URL est invalide
                 (pattern non reconnu, inaccessible, contenu non concordant).
    - --check-content / --no-check-content : (dés)activer la vérification
       du contenu (par défaut : activée).

Format d'entrée :
    Une liste JSON dont chaque élément est :
    - soit une chaîne (URL seule, sans vérification de contenu) ;
    - soit un objet { "url": "...", "expected_number": "...",
                       "expected_keyword": "..." }
       Les champs expected_* sont facultatifs et déclenchent la
       vérification de contenu si --check-content est actif.

Usage :
    python3 scripts/verify_links.py --urls '[{"url": "https://...",
        "expected_number": "21-12.345"}]'
    python3 scripts/verify_links.py --from-file urls.json --strict
    python3 scripts/verify_links.py --from-file urls.json --no-check-content

Sortie : JSON avec, pour chaque URL :
    url, type_legifrance, pattern_valide, status, accessible,
    content_match (true / false / null si non vérifié),
    content_match_detail, error.

Code de retour : 0 si tout passe (ou si --strict est désactivé), sinon 1.
"""

# Fichier commun aux skills assistant-juridique-fr (7.5.0) et mandarinat
# (1.5.0) : toute modification doit être répercutée à l'identique dans
# l'autre skill.

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import concurrent.futures

TIMEOUT_HEAD = 10
TIMEOUT_GET = 20
MAX_WORKERS = 5
USER_AGENT = "Legal-Link-Checker/2.0"
MAX_CONTENT_BYTES = 1_500_000  # plafond de lecture pour --check-content

# URL Légifrance utilisée par le mode --preflight pour détecter
# l'accès réseau. Référence stable : article 1242 du Code civil
# (CID LEGIARTI000006437058, en vigueur).
PREFLIGHT_URL = (
    "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006437058"
)

# URL secondaire utilisée par --preflight pour qualifier la sortie réseau
# indépendamment de Légifrance. EUR-Lex est sélectionné car il est sur la
# liste des cinq domaines officiels recommandés et ne pratique pas, à la
# date de cette skill, de challenge anti-bot.
EGRESS_TEST_URL = "https://eur-lex.europa.eu/"

# Correspondance entre le type d'identifiant Légifrance et l'outil
# OpenLegi à appeler pour vérifier son existence par API. Utilisée par
# --extract-ids pour produire les instructions destinées à l'agent.
LEGIFRANCE_TYPE_TO_OPENLEGI_TOOL = {
    "JURITEXT": {
        "tool": "OpenLegi:get_decision_judiciaire",
        "argument": "identifiant",
        "verification": (
            "Appeler get_decision_judiciaire avec l'identifiant et "
            "vérifier que la juridiction, la date et le numéro d'affaire "
            "correspondent à ce qui est cité dans le livrable."
        ),
    },
    "CETATEXT": {
        "tool": "OpenLegi:get_decision_administrative",
        "argument": "identifiant",
        "verification": (
            "Appeler get_decision_administrative avec l'identifiant et "
            "vérifier que la juridiction, la date et le numéro de "
            "requête correspondent."
        ),
    },
    "CNILTEXT": {
        "tool": "OpenLegi:get_decision_cnil",
        "argument": "identifiant",
        "verification": (
            "Appeler get_decision_cnil avec l'identifiant et vérifier "
            "que la décision correspond."
        ),
    },
    "CONSTEXT": {
        "tool": "OpenLegi:get_decision_constitutionnelle",
        "argument": "identifiant",
        "verification": (
            "Appeler get_decision_constitutionnelle avec l'identifiant et "
            "vérifier le numéro (QPC, DC…), la date et l'objet de la décision."
        ),
    },
    "JUFITEXT": {
        "tool": "OpenLegi:get_decision_financiere",
        "argument": "identifiant",
        "verification": (
            "Appeler get_decision_financiere avec l'identifiant et vérifier "
            "la juridiction financière, la date et le numéro."
        ),
    },
    "LEGIARTI_CODE": {
        "tool": "OpenLegi:rechercher_code",
        "argument": "search=<numéro article>, code_name=<code>, champ='NUM_ARTICLE'",
        "verification": (
            "Appeler rechercher_code avec le numéro d'article et le nom "
            "exact du code. Vérifier que le CID retourné par OpenLegi "
            "correspond à l'identifiant LEGIARTI cité, et que l'état "
            "juridique est VIGUEUR à la date pertinente (champs "
            "date_debut_vigueur / date_fin_vigueur)."
        ),
    },
    "LEGIARTI_LODA": {
        "tool": "OpenLegi:rechercher_dans_texte_legal",
        "argument": "identifiant texte (LEGITEXT) + numéro article",
        "verification": (
            "Identifier d'abord le LEGITEXT parent du texte, puis "
            "appeler rechercher_dans_texte_legal pour vérifier que "
            "l'article LEGIARTI cité existe et est en vigueur."
        ),
    },
    "LEGITEXT_CODE": {
        "tool": "OpenLegi:lister_codes_juridiques",
        "argument": "(aucun)",
        "verification": (
            "Vérifier que le LEGITEXT cité figure dans la liste des "
            "codes retournée par lister_codes_juridiques."
        ),
    },
    "LEGITEXT_LODA": {
        "tool": "OpenLegi:rechercher_dans_texte_legal",
        "argument": "identifiant texte (LEGITEXT)",
        "verification": (
            "Appeler rechercher_dans_texte_legal sur le LEGITEXT cité "
            "et vérifier que la réponse n'est pas vide."
        ),
    },
    "JORFTEXT": {
        "tool": "OpenLegi:recherche_journal_officiel",
        "argument": "search=<référence loi/décret>",
        "verification": (
            "Appeler recherche_journal_officiel avec la référence du "
            "texte (numéro et date) et vérifier que l'identifiant "
            "JORFTEXT retourné correspond."
        ),
    },
    "JORFARTI": {
        "tool": "OpenLegi:recherche_journal_officiel",
        "argument": "search=<référence loi/décret + n° article>",
        "verification": (
            "Appeler recherche_journal_officiel avec la référence du "
            "texte et l'article cité, vérifier que l'identifiant "
            "JORFARTI retourné correspond."
        ),
    },
    "KALITEXT": {
        "tool": "OpenLegi:rechercher_conventions_collectives",
        "argument": "search=<intitulé convention>",
        "verification": (
            "Appeler rechercher_conventions_collectives avec "
            "l'intitulé de la convention et vérifier que l'identifiant "
            "KALITEXT retourné correspond."
        ),
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Patterns d'URL reconnus
# ─────────────────────────────────────────────────────────────────────────────

LIBREJUSTICE_TYPE_TO_TOOL = {
    "LIBREJUSTICE_DECISION": {
        "tool": "LibreJustice:get_decision",
        "argument": "url=<URL LibreJustice de la décision>",
        "verification": (
            "Appeler get_decision avec l'URL et vérifier que la "
            "juridiction, la date et le numéro d'affaire correspondent à "
            "ce qui est cité. Lire les motifs et le dispositif (jamais un "
            "aiSummary ni un snippet) pour le content-matching, et "
            "contrôler appellateFate : une décision infirmée ne peut "
            "être citée comme état du droit."
        ),
    },
    "LIBREJUSTICE_TEXTE": {
        "tool": "LibreJustice:get_norm",
        "argument": "url=<URL LibreJustice de l'article>, date=<date pertinente>",
        "verification": (
            "Appeler get_norm avec l'URL et la date pertinente "
            "(date des faits pour une analyse rétrospective). Vérifier "
            "que la rédaction citée est celle en vigueur à cette date et "
            "préciser la version citée."
        ),
    },
}

LEGIFRANCE_PATTERNS = [
    # Jurisprudence judiciaire (Cour de cassation, cours d'appel)
    ("JURITEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/juri/id/JURITEXT\d+/?$"
    , re.IGNORECASE)),
    # Jurisprudence administrative (Conseil d'État, CAA, TA)
    ("CETATEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/ceta/id/CETATEXT\d+/?$"
    , re.IGNORECASE)),
    # Articles de codes
    ("LEGIARTI_CODE", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/codes/article_lc/LEGIARTI\d+/?$"
    , re.IGNORECASE)),
    # Articles de textes consolidés (LODA)
    ("LEGIARTI_LODA", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/loda/article_lc/LEGIARTI\d+/?$"
    , re.IGNORECASE)),
    # Textes consolidés (LODA, niveau texte)
    ("LEGITEXT_LODA", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/loda/id/LEGITEXT\d+/?$"
    , re.IGNORECASE)),
    # Codes (niveau code)
    ("LEGITEXT_CODE", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/codes/texte_lc/LEGITEXT\d+/?$"
    , re.IGNORECASE)),
    # Textes JORF
    ("JORFTEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/jorf/id/JORFTEXT\d+/?$"
    , re.IGNORECASE)),
    # Articles JORF
    ("JORFARTI", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/jorf/article_jo/JORFARTI\d+/?$"
    , re.IGNORECASE)),
    # Décisions CNIL
    ("CNILTEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/cnil/id/CNILTEXT\d+/?$"
    , re.IGNORECASE)),
    # Conventions collectives (KALI)
    ("KALITEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/conv_coll/id/KALITEXT\d+/?$"
    , re.IGNORECASE)),
    # Conseil constitutionnel (fonds CONSTIT de Légifrance)
    ("CONSTEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/cons/id/CONSTEXT\d+/?$"
    , re.IGNORECASE)),
    # Juridictions financières (fonds JUFI)
    ("JUFITEXT", re.compile(
        r"^https?://www\.legifrance\.gouv\.fr/jufi/id/JUFITEXT\d+/?$"
    , re.IGNORECASE)),
]

EXTERNAL_OFFICIAL_PATTERNS = [
    # Conseil constitutionnel (site officiel)
    ("CONSEIL_CONSTITUTIONNEL", re.compile(
        r"^https?://(?:www\.)?conseil-constitutionnel\.fr/decision/\d{4}/"
        r"\d+(?:[A-Z]+)?\.htm$"
    )),
    # CEDH (HUDOC)
    ("HUDOC_CEDH", re.compile(
        r"^https?://hudoc\.echr\.coe\.int/(?:eng|fre)\??.*$"
    , re.IGNORECASE)),
    # CJUE (Curia)
    ("CURIA_CJUE", re.compile(
        r"^https?://curia\.europa\.eu/juris/.+$"
    , re.IGNORECASE)),
    # EUR-Lex (textes UE)
    ("EUR_LEX", re.compile(
        r"^https?://eur-lex\.europa\.eu/.+$"
    , re.IGNORECASE)),
]

LIBREJUSTICE_PATTERNS = [
    # Décision (identifiant opaque)
    ("LIBREJUSTICE_DECISION", re.compile(
        r"^https?://(?:www\.)?librejustice\.fr/decision/[A-Za-z0-9_\-]+/?$"
    , re.IGNORECASE)),
    # Article ou texte : /norm/{juridiction}/{code}[/{article}]
    ("LIBREJUSTICE_TEXTE", re.compile(
        r"^https?://(?:www\.)?librejustice\.fr/norm/[A-Za-z]{2,4}/"
        r"[A-Za-z0-9_\-]+(?:/[A-Za-z0-9_.\-]+)?/?$"
    , re.IGNORECASE)),
    # Ancien format (avant le renommage get_legal_text -> get_norm)
    ("LIBREJUSTICE_TEXTE", re.compile(
        r"^https?://(?:www\.)?librejustice\.fr/texte/[A-Za-z0-9_\-]+/"
        r"[A-Za-z0-9_.\-]+/?$"
    , re.IGNORECASE)),
]

ALL_PATTERNS = (
    LEGIFRANCE_PATTERNS + EXTERNAL_OFFICIAL_PATTERNS + LIBREJUSTICE_PATTERNS
)


def identify_pattern(url):
    """Retourne (type, valide) pour une URL donnée.

    Si l'URL ne matche aucun pattern, retourne (None, False).
    """
    if not isinstance(url, str):
        return (None, False)
    for type_name, pattern in ALL_PATTERNS:
        if pattern.match(url):
            return (type_name, True)
    return (None, False)


# ─────────────────────────────────────────────────────────────────────────────
# Vérification HTTP
# ─────────────────────────────────────────────────────────────────────────────

def head_check(url):
    """Effectue un HEAD. Retourne (status, accessible, error)."""
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_HEAD) as response:
            return (response.getcode(), True, None)
    except urllib.error.HTTPError as e:
        # 405 (Method Not Allowed) : certains serveurs n'acceptent pas HEAD,
        # on bascule sur GET court.
        if e.code == 405:
            return get_status_only(url)
        return (e.code, e.code < 400, f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return (None, False, f"URL Error: {e.reason}")
    except Exception as e:
        return (None, False, str(e))


def get_status_only(url):
    """GET court (sans lecture du corps) en repli si HEAD est refusé."""
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_HEAD) as response:
            return (response.getcode(), True, None)
    except urllib.error.HTTPError as e:
        return (e.code, e.code < 400, f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return (None, False, f"URL Error: {e.reason}")
    except Exception as e:
        return (None, False, str(e))


def fetch_content(url):
    """Récupère le contenu HTML (plafond MAX_CONTENT_BYTES)."""
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_GET) as response:
            raw = response.read(MAX_CONTENT_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
            try:
                return raw.decode(charset, errors="replace")
            except LookupError:
                return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Vérification de contenu
# ─────────────────────────────────────────────────────────────────────────────

def normalize_for_search(text):
    """Normalise le texte pour la recherche : minuscules, suppression des
    points et tirets dans les numéros, espaces normalisés."""
    if not text:
        return ""
    text = text.lower()
    # Pour les numéros de pourvoi : supprimer les points et tirets
    text = re.sub(r"[ \s]+", " ", text)
    return text


def number_variants(number):
    """Retourne plusieurs variantes d'un numéro de pourvoi / d'article.

    Exemple pour "21-12.345" : ["21-12.345", "2112345", "21 12 345",
    "21-12345", "2112.345"].
    """
    if not number:
        return []
    base = number.strip().lower()
    variants = {base}
    # Sans points
    variants.add(base.replace(".", ""))
    # Sans tirets
    variants.add(base.replace("-", ""))
    # Sans points ni tirets (numéro pur)
    variants.add(re.sub(r"[\.\-\s]", "", base))
    # Avec points uniquement (séparateur unique)
    variants.add(base.replace("-", "."))
    # Avec tirets uniquement
    variants.add(base.replace(".", "-"))
    # Forme "n° XX-XX.XXX"
    variants.add(f"n° {base}")
    variants.add(f"n°{base}")
    return [v for v in variants if v]


def check_content_match(html, expected_number=None, expected_keyword=None):
    """Vérifie que le numéro et/ou le mot-clé attendu apparaît dans le HTML.

    Retourne (match, detail) :
      - match = True si tous les critères fournis correspondent.
      - match = False sinon.
      - match = None si aucun critère n'a été fourni (rien à vérifier).
    """
    if expected_number is None and expected_keyword is None:
        return (None, "Aucun critère de contenu fourni.")
    if not html:
        return (False, "Contenu HTML indisponible.")

    haystack = normalize_for_search(html)
    details = []

    if expected_number is not None:
        variants = number_variants(expected_number)
        found = any(v in haystack for v in variants)
        if not found:
            return (
                False,
                f"Numéro '{expected_number}' (variantes : "
                f"{variants}) introuvable dans la page."
            )
        details.append(f"Numéro '{expected_number}' trouvé.")

    if expected_keyword is not None:
        kw = expected_keyword.lower()
        if kw not in haystack:
            return (
                False,
                f"Mot-clé '{expected_keyword}' introuvable dans la page."
            )
        details.append(f"Mot-clé '{expected_keyword}' trouvé.")

    return (True, " ".join(details))


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline complet
# ─────────────────────────────────────────────────────────────────────────────

def normalize_entry(entry):
    """Convertit une entrée d'entrée en dict normalisé."""
    if isinstance(entry, str):
        return {
            "url": entry,
            "expected_number": None,
            "expected_keyword": None,
        }
    if isinstance(entry, dict) and "url" in entry:
        return {
            "url": entry["url"],
            "expected_number": entry.get("expected_number"),
            "expected_keyword": entry.get("expected_keyword"),
        }
    return {
        "url": None,
        "expected_number": None,
        "expected_keyword": None,
        "_invalid_entry": entry,
    }


def check_one(entry, do_check_content):
    """Vérifie une URL. Retourne un dict structuré."""
    url = entry.get("url")
    if not url:
        return {
            "url": None,
            "type_legifrance": None,
            "pattern_valide": False,
            "status": None,
            "accessible": False,
            "content_match": None,
            "content_match_detail": None,
            "error": (
                f"Entrée invalide (pas d'URL) : {entry.get('_invalid_entry')}"
            ),
        }

    # Étape 1 : reconnaissance du pattern
    type_name, pattern_valide = identify_pattern(url)

    result = {
        "url": url,
        "type_legifrance": type_name,
        "pattern_valide": pattern_valide,
        "status": None,
        "accessible": False,
        "content_match": None,
        "content_match_detail": None,
        "error": None,
    }

    if not pattern_valide:
        result["error"] = (
            "URL ne correspondant à aucun pattern Légifrance / HUDOC / "
            "Curia / EUR-Lex reconnu. Possible signal d'hallucination ou "
            "de reconstruction de mémoire."
        )
        return result

    # Étape 2 : accessibilité HTTP
    status, accessible, http_error = head_check(url)
    result["status"] = status
    result["accessible"] = accessible
    if http_error:
        result["error"] = http_error

    if not accessible:
        return result

    # Étape 3 : vérification de contenu
    if do_check_content:
        html = fetch_content(url)
        match, detail = check_content_match(
            html,
            expected_number=entry.get("expected_number"),
            expected_keyword=entry.get("expected_keyword"),
        )
        result["content_match"] = match
        result["content_match_detail"] = detail
        if match is False:
            existing_error = result["error"]
            result["error"] = (
                (existing_error + " | " if existing_error else "")
                + "Contenu non concordant : " + str(detail)
            )

    return result


def verify_batch(entries, do_check_content):
    """Vérifie une liste d'entrées en parallèle."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        future_to_idx = {
            executor.submit(check_one, e, do_check_content): i
            for i, e in enumerate(entries)
        }
        ordered = [None] * len(entries)
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            ordered[idx] = future.result()
    return ordered


def is_failure(result):
    """Détermine si un résultat constitue un échec strict."""
    if not result.get("pattern_valide"):
        return True
    if not result.get("accessible"):
        return True
    if result.get("content_match") is False:
        return True
    return False



# ─────────────────────────────────────────────────────────────────────────────
# Mode preflight : détection de l'accès réseau Légifrance
# ─────────────────────────────────────────────────────────────────────────────

def _headers_to_lower_dict(headers):
    """Convertit un objet Headers (HTTPMessage) en dict {nom_lower: value}.

    Renvoie {} si headers est None ou n'est pas itérable.
    """
    if headers is None:
        return {}
    try:
        return {k.lower(): v for k, v in headers.items()}
    except Exception:
        return {}


def _classify_response_indicators(http_code, headers, raw_message=""):
    """Inspecte les en-têtes (et un message d'erreur brut) d'une réponse
    HTTP pour décider du statut du préflight.

    Statuts possibles :
      - "ok" (0)
      - "blocked_by_allowlist" (2) — proxy de l'espace de travail
      - "network_error" (3) — erreur générique
      - "blocked_by_anti_bot" (4) — challenge Cloudflare ou équivalent
    """
    h = _headers_to_lower_dict(headers)
    msg_lower = (raw_message or "").lower()

    indicators = {
        "x_proxy_error": h.get("x-proxy-error"),
        "cf_mitigated": h.get("cf-mitigated"),
        "server": h.get("server"),
        "cf_ray": h.get("cf-ray"),
        "http_status": http_code,
    }

    # 1. Blocage explicite par la liste des domaines autorisés (en-tête sentinelle).
    proxy_err = (indicators["x_proxy_error"] or "").lower()
    if (
        "blocked-by-allowlist" in proxy_err
        or "blocked-by-allowlist" in msg_lower
        or "cowork-egress-blocked" in msg_lower
        or "tunnel connection failed" in msg_lower
    ):
        return {
            "status": "blocked_by_allowlist",
            "exit_code": 2,
            "message": (
                "Accès réseau bloqué par la liste des domaines autorisés "
                "de l'espace de travail."
            ),
            "recommendation": (
                "Autoriser les cinq domaines (www.legifrance.gouv.fr, "
                "www.conseil-constitutionnel.fr, hudoc.echr.coe.int, "
                "curia.europa.eu, eur-lex.europa.eu) dans les paramètres "
                "d'accès réseau de Claude (Paramètres > Capacités), puis "
                "ouvrir une nouvelle conversation. Pour Légifrance, sans "
                "effet utile : le challenge anti-bot Cloudflare subsiste ; "
                "le canal nominal est OpenLegi / LibreJustice."
            ),
            "headers_indicators": indicators,
        }

    # 2. Challenge anti-bot Cloudflare (cas Légifrance, depuis 2026).
    cf_mitigated = (indicators["cf_mitigated"] or "").lower()
    server_lower = (indicators["server"] or "").lower()
    is_cf_challenge = (
        "challenge" in cf_mitigated
        or (server_lower.startswith("cloudflare")
            and http_code in (403, 503))
    )
    if is_cf_challenge:
        return {
            "status": "blocked_by_anti_bot",
            "exit_code": 4,
            "message": (
                "Accès bloqué par un challenge anti-bot Cloudflare "
                "(serveur distant). La couche réseau est opérationnelle, "
                "mais le serveur refuse les requêtes automatisées."
            ),
            "recommendation": (
                "Bascule recommandée : vérifier les identifiants "
                "Légifrance via OpenLegi (get_decision_judiciaire, "
                "get_decision_administrative, rechercher_code, "
                "recherche_journal_officiel, etc.) plutôt que par "
                "requête HTTP directe. Voir mode --extract-ids."
            ),
            "headers_indicators": indicators,
        }

    # 3. 200 OK : tout va bien.
    if http_code == 200:
        return {
            "status": "ok",
            "exit_code": 0,
            "message": (
                "Accès réseau à Légifrance opérationnel. La vérification "
                "automatique par requête HTTP est utilisable."
            ),
            "recommendation": None,
            "headers_indicators": indicators,
        }

    # 4. Autre erreur réseau (DNS, TLS, timeout, code HTTP inattendu...).
    return {
        "status": "network_error",
        "exit_code": 3,
        "message": (
            "Erreur réseau : code HTTP "
            + str(http_code)
            + " ; détail brut : "
            + (raw_message or "(non disponible)")
        ),
        "recommendation": (
            "Vérifier la connectivité réseau, l'état de Légifrance, ou "
            "réessayer ultérieurement."
        ),
        "headers_indicators": indicators,
    }


def _probe_url(url, method="HEAD"):
    """Effectue une requête HEAD (ou GET) sur `url` et retourne
    (http_code, headers, raw_message).

    En cas d'HTTPError, les en-têtes de l'erreur sont capturés (utile
    pour détecter cf-mitigated / X-Proxy-Error). En cas d'URLError ou
    autre exception, http_code = None et headers = None.
    """
    try:
        req = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_HEAD) as response:
            return (response.getcode(), response.headers, "")
    except urllib.error.HTTPError as e:
        return (e.code, getattr(e, "headers", None),
                str(e.code) + " " + str(e.reason))
    except urllib.error.URLError as e:
        return (None, None, str(e.reason))
    except Exception as e:
        return (None, None, type(e).__name__ + ": " + str(e))


def _test_egress():
    """Teste la sortie réseau via une URL UE (eur-lex). Retourne
    (egress_ok: bool, detail: dict)."""
    code, headers, raw = _probe_url(EGRESS_TEST_URL, method="HEAD")
    indicators = _classify_response_indicators(code, headers, raw)
    egress_ok = (
        code is not None
        and indicators["status"] != "blocked_by_allowlist"
    )
    return egress_ok, {
        "url": EGRESS_TEST_URL,
        "http_status": code,
        "status_classification": indicators["status"],
        "headers_indicators": indicators.get("headers_indicators"),
        "raw_message": raw,
    }


def preflight_check():
    """Teste l'état de la sortie réseau et l'accès à Légifrance.

    Retourne un dict consolidé contenant :
      - status / exit_code / message / recommendation
      - http_status, headers_indicators, error_detail (diagnostic)
      - network_egress ("ok" / "blocked"), network_egress_detail :
        état de la sortie réseau générique, distinct du statut
        spécifique Légifrance.
    """
    egress_ok, egress_detail = _test_egress()

    code, headers, raw = _probe_url(PREFLIGHT_URL, method="HEAD")
    if code == 405:
        code2, headers2, raw2 = _probe_url(PREFLIGHT_URL, method="GET")
        if code2 is not None:
            code, headers, raw = code2, headers2, raw2

    indicators = _classify_response_indicators(code, headers, raw)

    return {
        "status": indicators["status"],
        "exit_code": indicators["exit_code"],
        "message": indicators["message"],
        "http_status": code,
        "headers_indicators": indicators.get("headers_indicators"),
        "error_detail": raw if raw else None,
        "recommendation": indicators["recommendation"],
        "network_egress": "ok" if egress_ok else "blocked",
        "network_egress_detail": egress_detail,
    }


# Alias pour compatibilité ascendante avec le code 1.2.1 qui pouvait
# référencer _classify_network_error.
def _classify_network_error(exc):
    """Conserve la signature de la 1.2.1. Délègue à
    _classify_response_indicators à partir du message d'erreur brut."""
    return _classify_response_indicators(None, None, str(exc))


# ───────────────────────────────────────────────────────────────────────
# Mode --extract-ids : extraction d'identifiants Légifrance
# ───────────────────────────────────────────────────────────────────────

# Patterns d'identifiants Légifrance nus (sans préfixe URL). Ordre
# important : on teste d'abord les variantes spécifiques puis les
# génériques (LEGIARTI / LEGITEXT).
LEGIFRANCE_ID_PATTERNS = [
    ("JURITEXT", re.compile(r"\b(JURITEXT\d+)\b", re.IGNORECASE)),
    ("CETATEXT", re.compile(r"\b(CETATEXT\d+)\b", re.IGNORECASE)),
    ("CNILTEXT", re.compile(r"\b(CNILTEXT\d+)\b", re.IGNORECASE)),
    ("KALITEXT", re.compile(r"\b(KALITEXT\d+)\b", re.IGNORECASE)),
    ("CONSTEXT", re.compile(r"\b(CONSTEXT\d+)\b", re.IGNORECASE)),
    ("JUFITEXT", re.compile(r"\b(JUFITEXT\d+)\b", re.IGNORECASE)),
    ("JORFARTI", re.compile(r"\b(JORFARTI\d+)\b", re.IGNORECASE)),
    ("JORFTEXT", re.compile(r"\b(JORFTEXT\d+)\b", re.IGNORECASE)),
    ("LEGIARTI", re.compile(r"\b(LEGIARTI\d+)\b", re.IGNORECASE)),
    ("LEGITEXT", re.compile(r"\b(LEGITEXT\d+)\b", re.IGNORECASE)),
]


def _refine_legiarti_legitext_type(id_type, url_context):
    """Discriminer LEGIARTI / LEGITEXT en code vs LODA via l'URL parente.

    À défaut d'URL contextuelle, conserve le type générique.
    """
    if not url_context:
        return id_type
    u = url_context.lower()
    if id_type == "LEGIARTI":
        if "/codes/article_lc/" in u:
            return "LEGIARTI_CODE"
        if "/loda/article_lc/" in u:
            return "LEGIARTI_LODA"
    if id_type == "LEGITEXT":
        if "/codes/texte_lc/" in u:
            return "LEGITEXT_CODE"
        if "/loda/id/" in u:
            return "LEGITEXT_LODA"
    return id_type


def extract_ids_from_text(text):
    """Extrait les identifiants Légifrance d'un texte brut.

    Sans contexte d'URL, LEGIARTI et LEGITEXT retombent sur la variante
    code (LEGIARTI_CODE, LEGITEXT_CODE) par défaut. L'agent doit, le
    cas échéant, basculer sur la variante LODA.
    """
    if not isinstance(text, str):
        return []
    seen = set()
    results = []
    for id_type, pattern in LEGIFRANCE_ID_PATTERNS:
        for match in pattern.finditer(text):
            ident = match.group(1).upper()
            if ident in seen:
                continue
            seen.add(ident)
            tool_key = id_type
            if id_type == "LEGIARTI":
                tool_key = "LEGIARTI_CODE"
            if id_type == "LEGITEXT":
                tool_key = "LEGITEXT_CODE"
            mapping = LEGIFRANCE_TYPE_TO_OPENLEGI_TOOL.get(tool_key, {})
            results.append({
                "id": ident,
                "type": id_type,
                "type_resolved_assumption": tool_key,
                "openlegi_tool": mapping.get("tool"),
                "openlegi_argument": mapping.get("argument"),
                "openlegi_verification_instruction": mapping.get(
                    "verification"
                ),
                "source_context": "text",
            })
    return results


def extract_ids_from_urls(urls):
    """Extrait les identifiants Légifrance d'une liste d'URLs.

    L'URL parente permet de discriminer LEGIARTI_CODE vs LEGIARTI_LODA
    et LEGITEXT_CODE vs LEGITEXT_LODA.
    """
    results = []
    for url in urls:
        if not isinstance(url, str):
            continue
        for id_type, pattern in LEGIFRANCE_ID_PATTERNS:
            match = pattern.search(url)
            if not match:
                continue
            ident = match.group(1).upper()
            tool_key = _refine_legiarti_legitext_type(id_type, url)
            mapping = LEGIFRANCE_TYPE_TO_OPENLEGI_TOOL.get(tool_key, {})
            results.append({
                "id": ident,
                "type": id_type,
                "type_resolved": tool_key,
                "url": url,
                "openlegi_tool": mapping.get("tool"),
                "openlegi_argument": mapping.get("argument"),
                "openlegi_verification_instruction": mapping.get(
                    "verification"
                ),
            })
            break  # une seule extraction par URL
    return results


def extract_librejustice_from_urls(urls):
    """Extrait les URLs LibreJustice et l'outil MCP à appeler pour chacune.

    Pendant de extract_ids_from_urls pour le canal LibreJustice : le
    connecteur MCP n'est affecté ni par la liste des domaines autorisés ni par le
    challenge anti-bot Cloudflare de Légifrance, et reste donc
    utilisable lorsque la vérification HTTP directe est inopérante.
    """
    results = []
    seen = set()
    for url in urls:
        if not isinstance(url, str) or url in seen:
            continue
        for type_name, pattern in LIBREJUSTICE_PATTERNS:
            if not pattern.match(url):
                continue
            seen.add(url)
            mapping = LIBREJUSTICE_TYPE_TO_TOOL.get(type_name, {})
            results.append({
                "url": url,
                "type": type_name,
                "librejustice_tool": mapping.get("tool"),
                "librejustice_argument": mapping.get("argument"),
                "librejustice_verification_instruction": mapping.get(
                    "verification"
                ),
            })
            break
    return results


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Vérification batch d'URLs juridiques (Légifrance, HUDOC, "
            "Curia, EUR-Lex). Vérifie pattern, accessibilité, et "
            "concordance de contenu. Mode --preflight pour tester "
            "uniquement l'accès réseau à Légifrance."
        )
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--urls", help="JSON array d'URLs ou d'entrées.")
    group.add_argument(
        "--from-file",
        help="Fichier JSON contenant la liste d'URLs ou d'entrées."
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help=(
            "Tester l'état de la sortie réseau et l'accès à Légifrance. "
            "Codes de retour : 0 = réseau OK et Légifrance répond ; "
            "2 = bloqué par la liste des domaines autorisés ; 3 = erreur réseau "
            "générique ; 4 = bloqué par challenge anti-bot Cloudflare "
            "(la couche réseau est OK, mais Légifrance refuse les "
            "requêtes automatisées : utiliser --extract-ids et "
            "OpenLegi)."
        )
    )
    parser.add_argument(
        "--extract-ids",
        action="store_true",
        help=(
            "Extraire les identifiants Légifrance (LEGIARTI, JURITEXT, "
            "CETATEXT, JORFTEXT, JORFARTI, LEGITEXT, CNILTEXT, "
            "KALITEXT) d'une liste d'URLs (--urls / --from-file) ou "
            "d'un texte brut (--extract-ids-from-text). Pour chaque "
            "identifiant, retourne le nom de l'outil OpenLegi à "
            "appeler pour vérification par API. Mode utile dans les "
            "sandbox où Légifrance est inaccessible (Cloudflare ou "
            "allowlist) : la vérification est déléguée à OpenLegi par "
            "l'agent."
        )
    )
    parser.add_argument(
        "--extract-ids-from-text",
        help=(
            "Texte brut dans lequel rechercher les identifiants "
            "Légifrance (à utiliser avec --extract-ids). Sans "
            "contexte d'URL, LEGIARTI et LEGITEXT retombent sur la "
            "variante code par défaut."
        )
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Code de retour ≠ 0 si au moins une URL est invalide "
            "(pattern non reconnu, inaccessible, ou contenu non "
            "concordant)."
        )
    )
    parser.add_argument(
        "--check-content",
        dest="check_content",
        action="store_true",
        default=True,
        help=(
            "Activer la vérification du contenu (par défaut : activé). "
            "Récupère la page et vérifie la présence du numéro / mot-clé "
            "attendu."
        )
    )
    parser.add_argument(
        "--no-check-content",
        dest="check_content",
        action="store_false",
        help="Désactiver la vérification du contenu."
    )

    args = parser.parse_args()

    if args.preflight:
        result = preflight_check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(result["exit_code"])

    if args.extract_ids:
        if args.extract_ids_from_text:
            ids = extract_ids_from_text(args.extract_ids_from_text)
            librejustice = []
        elif args.urls or args.from_file:
            if args.urls:
                raw = json.loads(args.urls)
            else:
                with open(args.from_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            if not isinstance(raw, list):
                parser.error(
                    "--urls / --from-file doit fournir un array JSON."
                )
            urls_only = []
            for entry in raw:
                if isinstance(entry, str):
                    urls_only.append(entry)
                elif isinstance(entry, dict) and "url" in entry:
                    urls_only.append(entry["url"])
            ids = extract_ids_from_urls(urls_only)
            librejustice = extract_librejustice_from_urls(urls_only)
        else:
            parser.error(
                "--extract-ids requiert --urls, --from-file, ou "
                "--extract-ids-from-text."
            )
        output = {
            "total_ids": len(ids),
            "ids": ids,
            "total_librejustice": len(librejustice),
            "librejustice": librejustice,
            "instruction_agent": (
                "Pour chaque identifiant ci-dessous, appeler l'outil "
                "OpenLegi indiqué (champ openlegi_tool) avec l'argument "
                "décrit (champ openlegi_argument), puis exécuter la "
                "vérification décrite (champ "
                "openlegi_verification_instruction). Toute référence "
                "dont l'identifiant n'est pas confirmé par OpenLegi "
                "doit être supprimée du livrable ou convertie en "
                "formulation impersonnelle. Pour les entrées du bloc "
                "librejustice, appeler l'outil indiqué (champ "
                "librejustice_tool) : ce canal API reste opérationnel "
                "lorsque Légifrance est inaccessible, et fournit le "
                "texte intégral nécessaire au content-matching ainsi que "
                "le sort en voie de recours (appellateFate)."
            ),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(0 if ids else 2)

    if not args.urls and not args.from_file:
        parser.error(
            "--urls ou --from-file est requis (sauf en mode "
            "--preflight ou --extract-ids)."
        )

    if args.urls:
        raw = json.loads(args.urls)
    else:
        with open(args.from_file, "r", encoding="utf-8") as f:
            raw = json.load(f)

    if not isinstance(raw, list):
        print(json.dumps({
            "error": "L'entrée doit être un array JSON d'URLs ou d'entrées."
        }))
        sys.exit(2)

    entries = [normalize_entry(e) for e in raw]
    results = verify_batch(entries, do_check_content=args.check_content)

    # Synthèse
    total = len(results)
    pattern_ok = sum(1 for r in results if r.get("pattern_valide"))
    accessible = sum(1 for r in results if r.get("accessible"))
    content_ok = sum(1 for r in results if r.get("content_match") is True)
    content_ko = sum(1 for r in results if r.get("content_match") is False)
    failures = [r for r in results if is_failure(r)]

    summary = {
        "total": total,
        "pattern_valide": pattern_ok,
        "accessible": accessible,
        "content_match_ok": content_ok,
        "content_match_ko": content_ko,
        "echecs": len(failures),
        "check_content_active": args.check_content,
        "results": results,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.strict and failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
