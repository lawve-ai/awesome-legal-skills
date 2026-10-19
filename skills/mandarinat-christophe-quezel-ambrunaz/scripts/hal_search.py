#!/usr/bin/env python3
"""
hal_search.py — Requêtes structurées à l'API HAL pour la doctrine juridique.

Usage :
    python3 scripts/hal_search.py --query "responsabilité civile" [options]
    python3 scripts/hal_search.py --pourvoi "21-19.900"
    python3 scripts/hal_search.py --author "Brun"

Sortie : JSON structuré sur stdout.
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
import urllib.error

BASE_URL = "https://api.archives-ouvertes.fr/search/"
DOMAIN_FILTER = "domain_s:1.shs.droit"
DOC_TYPES = "(ART OR OUV OR COUV OR COMM OR DOUV OR THESE OR HDR)"
FIELDS = "halId_s,title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,docType_s,citationFull_s,abstract_s,keyword_s,fileMain_s,submitType_s"
TIMEOUT = 15


def build_query(args):
    """Construit les paramètres de la requête HAL."""
    params = {
        "wt": "json",
        "fl": FIELDS,
        "rows": str(args.rows),
        "sort": "producedDate_tdate desc",
    }

    fq_filters = [f"domain_s:{DOMAIN_FILTER.split(':')[1]}"]

    # Type de requête
    if args.pourvoi:
        # Recherche de notes d'arrêt par numéro de pourvoi
        params["q"] = f'title_t:"{args.pourvoi}"'
    elif args.author:
        params["q"] = f"authLastName_t:{args.author}"
    elif args.exact:
        # Expression exacte dans le titre
        params["q"] = f'title_t:"{args.query}"'
    else:
        # Recherche thématique multi-champs (usage principal)
        terms = args.query
        params["q"] = f"(title_t:({terms}) OR abstract_t:({terms}) OR keyword_t:({terms}))"

    # Filtre types de documents
    if not args.all_types:
        fq_filters.append(f"docType_s:{DOC_TYPES}")

    # Filtre temporel
    if args.year_from or args.year_to:
        year_from = args.year_from or 1900
        year_to = args.year_to or 2030
        fq_filters.append(f"producedDateY_i:[{year_from} TO {year_to}]")

    # Filtre accès ouvert uniquement
    if args.open_access:
        fq_filters.append("submitType_s:file")

    # Filtre revue
    if args.journal:
        fq_filters.append(f'journalTitle_t:"{args.journal}"')

    params["fq"] = fq_filters
    return params


def execute_query(params):
    """Exécute la requête HAL et retourne le JSON brut."""
    # Construire l'URL manuellement pour gérer les multiples fq
    query_parts = []
    for key, value in params.items():
        if key == "fq":
            for fq_val in value:
                query_parts.append(f"fq={urllib.parse.quote(fq_val, safe=':()[]')}")
        else:
            safe_chars = ':()[]"'
            query_parts.append(f"{key}={urllib.parse.quote(str(value), safe=safe_chars)}")

    url = BASE_URL + "?" + "&".join(query_parts)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HAL-Search-Script/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": f"Erreur réseau : {e}", "url": url}
    except Exception as e:
        return {"error": f"Erreur inattendue : {e}", "url": url}


def format_results(raw_response):
    """Formate la réponse HAL en structure exploitable."""
    if "error" in raw_response:
        return raw_response

    response = raw_response.get("response", {})
    num_found = response.get("numFound", 0)
    docs = response.get("docs", [])

    results = []
    for doc in docs:
        result = {
            "halId": doc.get("halId_s", ""),
            "title": doc.get("title_s", [""])[0] if isinstance(doc.get("title_s"), list) else doc.get("title_s", ""),
            "authors": doc.get("authFullName_s", []),
            "year": doc.get("producedDateY_i"),
            "journal": doc.get("journalTitle_s", ""),
            "uri": doc.get("uri_s", ""),
            "docType": doc.get("docType_s", ""),
            "citation": doc.get("citationFull_s", ""),
            "abstract": (doc.get("abstract_s", [""])[0] if isinstance(doc.get("abstract_s"), list) else doc.get("abstract_s", ""))[:500],
            "keywords": doc.get("keyword_s", []),
            "openAccess": doc.get("submitType_s") == "file",
            "fileUrl": doc.get("fileMain_s", ""),
        }
        results.append(result)

    return {
        "numFound": num_found,
        "numReturned": len(results),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Recherche doctrinale sur HAL (API)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", "-q", help="Termes de recherche thématique")
    group.add_argument("--pourvoi", "-p", help="Numéro de pourvoi (recherche notes d'arrêt)")
    group.add_argument("--author", "-a", help="Nom de famille de l'auteur")

    parser.add_argument("--rows", "-n", type=int, default=10, help="Nombre de résultats (défaut: 10)")
    parser.add_argument("--year-from", type=int, help="Année de début (filtre temporel)")
    parser.add_argument("--year-to", type=int, help="Année de fin (filtre temporel)")
    parser.add_argument("--exact", action="store_true", help="Recherche d'expression exacte dans le titre")
    parser.add_argument("--open-access", action="store_true", help="Texte intégral en accès ouvert uniquement")
    parser.add_argument("--all-types", action="store_true", help="Inclure tous les types de documents")
    parser.add_argument("--journal", help="Filtrer par titre de revue")
    parser.add_argument("--raw", action="store_true", help="Sortie brute (réponse HAL non formatée)")

    args = parser.parse_args()
    params = build_query(args)
    raw = execute_query(params)

    if args.raw:
        print(json.dumps(raw, ensure_ascii=False, indent=2))
    else:
        formatted = format_results(raw)
        print(json.dumps(formatted, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
