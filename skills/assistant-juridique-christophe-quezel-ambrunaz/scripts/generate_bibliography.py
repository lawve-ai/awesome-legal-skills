#!/usr/bin/env python3
"""
generate_bibliography.py — Compilation d'une bibliographie structurée.

Usage :
    python3 scripts/generate_bibliography.py --from-json references.json [--sort type|alpha|chrono]

Entrée : fichier JSON contenant une liste de références avec métadonnées.
Sortie : Bibliographie formatée (texte) et JSON structuré sur stdout.

Format d'entrée attendu (chaque référence) :
{
    "type": "juris_cass|juris_ce|code_article|loi|doctrine_article|...",
    "citation": "Citation formatée complète",
    "url": "URL vers la source",
    "authors": ["Nom1", "Nom2"],
    "year": 2023,
    "source_tool": "OpenLegi|LibreJustice|HAL|web_search"
}
"""

import argparse
import json
import sys
from collections import defaultdict

TYPE_ORDER = {
    "code_article": 0,
    "loi": 1,
    "decret": 1,
    "ordonnance": 1,
    "juris_const": 2,
    "juris_cass": 3,
    "juris_ce": 3,
    "juris_ca": 4,
    "juris_tj": 4,
    "juris_ta_caa": 4,
    "doctrine_article": 5,
    "doctrine_ouvrage": 5,
    "doctrine_these": 5,
    "doctrine_note": 5,
    "rapport": 6,
    "source_web": 7,
    "autre": 8,
}

TYPE_LABELS = {
    0: "Textes",
    1: "Législation et réglementation",
    2: "Conseil constitutionnel",
    3: "Jurisprudence des cours suprêmes",
    4: "Jurisprudence du fond",
    5: "Doctrine",
    6: "Rapports et documents institutionnels",
    7: "Sources web",
    8: "Autres sources",
}


def deduplicate(refs):
    """Dédoublonne par citation (comparaison insensible à la casse)."""
    seen = set()
    unique = []
    for ref in refs:
        key = ref.get("citation", "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


def sort_within_group(refs, sort_mode):
    """Trie les références au sein d'un groupe."""
    if sort_mode == "alpha":
        # Tri alphabétique par premier auteur ou par citation
        return sorted(refs, key=lambda r: (r.get("authors", [""])[0] if r.get("authors") else r.get("citation", "")).lower())
    elif sort_mode == "chrono":
        # Tri chronologique (plus ancien d'abord)
        return sorted(refs, key=lambda r: r.get("year") or 9999)
    else:
        # Par défaut : textes et jurisprudence par date (plus récent d'abord), doctrine alphabétique
        ref_type = refs[0].get("type", "") if refs else ""
        type_group = TYPE_ORDER.get(ref_type, 8)
        if type_group <= 4:  # Textes et jurisprudence
            return sorted(refs, key=lambda r: -(r.get("year") or 0))
        else:  # Doctrine et autres
            return sorted(refs, key=lambda r: (r.get("authors", [""])[0] if r.get("authors") else r.get("citation", "")).lower())


def generate(refs, sort_mode="type"):
    """Génère la bibliographie structurée."""
    refs = deduplicate(refs)

    # Grouper par type
    groups = defaultdict(list)
    for ref in refs:
        type_key = TYPE_ORDER.get(ref.get("type", "autre"), 8)
        groups[type_key].append(ref)

    sections = []
    for group_key in sorted(groups.keys()):
        group_refs = sort_within_group(groups[group_key], sort_mode)
        label = TYPE_LABELS.get(group_key, "Autres")

        entries = []
        for ref in group_refs:
            entry = ref.get("citation", "[Citation manquante]")
            if ref.get("url"):
                entry += f"\n  → {ref['url']}"
            entries.append(entry)

        sections.append({
            "label": label,
            "count": len(entries),
            "entries": entries,
        })

    return {
        "total": len(refs),
        "duplicates_removed": 0,  # Calculé en amont par deduplicate
        "sections": sections,
    }


def format_text(bibliography):
    """Formate la bibliographie en texte lisible."""
    lines = []
    lines.append(f"BIBLIOGRAPHIE ({bibliography['total']} références)")
    lines.append("=" * 60)

    for section in bibliography["sections"]:
        lines.append("")
        lines.append(f"## {section['label']} ({section['count']})")
        lines.append("-" * 40)
        for i, entry in enumerate(section["entries"], 1):
            lines.append(f"  {i}. {entry}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compilation bibliographique structurée")
    parser.add_argument("--from-json", "-f", required=True, help="Fichier JSON de références")
    parser.add_argument("--sort", choices=["type", "alpha", "chrono"], default="type",
                       help="Mode de tri (défaut: type)")
    parser.add_argument("--format", choices=["json", "text", "both"], default="both",
                       help="Format de sortie (défaut: both)")

    args = parser.parse_args()

    with open(args.from_json, "r", encoding="utf-8") as f:
        refs = json.load(f)

    bibliography = generate(refs, args.sort)

    if args.format == "json":
        print(json.dumps(bibliography, ensure_ascii=False, indent=2))
    elif args.format == "text":
        print(format_text(bibliography))
    else:
        print(format_text(bibliography))
        print("\n\n--- JSON ---\n")
        print(json.dumps(bibliography, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
