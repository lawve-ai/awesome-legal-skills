#!/usr/bin/env python3
"""
reference_journal.py — Journal de références et génération du tableau de vérification.

Problème traité (faille « content-matching de mémoire »)
--------------------------------------------------------
La version antérieure de la checklist exige un tableau de vérification à quatre
colonnes, dont la colonne 3 (« extrait textuel pertinent retourné par l'outil »).
Rien n'empêche de remplir cette colonne *de mémoire*, longtemps après l'appel
d'outil — surtout en session longue où la réponse de l'outil est sortie du
contexte effectif. C'est la même vulnérabilité qui a motivé l'abandon de
l'« énumération mentale » au profit du tableau ; il faut la pousser jusqu'à la
SOURCE des données du tableau.

Principe
--------
Tenir un journal append-only au format NDJSON (un objet JSON par ligne), alimenté
AU MOMENT DE CHAQUE APPEL D'OUTIL de recherche — pendant que la réponse est sous
les yeux. Le tableau final de la checklist est ensuite GÉNÉRÉ depuis ce journal
par le présent script, et non reconstitué de mémoire.

Le journal suppose un espace de travail doté d'un système de fichiers (cas
normal). Il est écrit dans le dossier connecté de l'utilisateur lorsqu'il en
existe un (persistance et reprise), à défaut dans l'espace de travail, puis
remis avec le livrable. Sans système de fichiers (cas résiduel), le tableau est
produit manuellement (cf. checklist).

Format d'une entrée du journal (une ligne NDJSON)
-------------------------------------------------
  {
    "ref": "Cass. civ. 2e, 5 mars 2020, n° 19-12.345",   # référence telle qu'elle sera citée
    "tool": "OpenLegi:rechercher_jurisprudence_judiciaire", # outil ayant produit la réf.
    #         (ou "LibreJustice:get_decision", "LibreJustice:get_norm"…)
    "id": "JURITEXT000041...",                            # identifiant officiel / Légifrance / DOI / HAL
    "url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000041...",
    "excerpt": "La cour d'appel ... (motifs propres de la Cour) ...",  # EXTRAIT COPIÉ depuis la réponse
    "assertion": "fonde la majeure sur la garde de la chose",          # ce que la réf. est censée fonder
    "kind": "juris|texte|doctrine",
    "voice": "voix_cour|motifs_ca|moyens|null",           # cassation Themia : voix énonciative
    "supports": null,                                     # oui / non / reformulation (commande mark)
    "independent": null,                                  # verdict du vérificateur indépendant (commande mark)
    "note": null
  }

Commandes
---------
  add      Ajouter une entrée (au moment de l'appel d'outil)
  table    Générer le tableau Markdown de vérification depuis le journal
  list     Lister les entrées (debug)
  mark     Porter le verdict d'une ligne (rédacteur et/ou vérificateur indépendant)
  check    Contrôler la complétude (entrées sans excerpt / sans id → signalées)

Exemples
--------
  python3 scripts/reference_journal.py add \
      --journal verification/journal-references.ndjson \
      --ref "art. 1242 al. 1er C. civ." \
      --tool "OpenLegi:rechercher_code" --id "LEGIARTI000006437058" \
      --url "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006437058" \
      --excerpt "On est responsable ... des choses que l'on a sous sa garde." \
      --assertion "fonde le principe général de responsabilité du fait des choses" \
      --kind texte

  python3 scripts/reference_journal.py table \
      --journal verification/journal-references.ndjson \
      --livrable "Corrigé cas pratique RC L2" --out verification/2026-09-27-verification-cas-pratique.md

  python3 scripts/reference_journal.py mark \
      --journal verification/journal-references.ndjson \
      --index 3 --supports non --independent non --note "l'article vise l'âge minimal, non le débridage"

  python3 scripts/reference_journal.py check \
      --journal verification/journal-references.ndjson
"""

import argparse
import json
import os
import sys


def _read_journal(path):
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[avertissement] ligne {i} illisible, ignorée : {e}", file=sys.stderr)
    return entries


def cmd_add(args):
    os.makedirs(os.path.dirname(os.path.abspath(args.journal)) or ".", exist_ok=True)
    entry = {
        "ref": args.ref,
        "tool": args.tool,
        "id": args.id,
        "url": args.url,
        "excerpt": args.excerpt,
        "assertion": args.assertion,
        "kind": args.kind,
        "voice": args.voice,
        "supports": None,
        "independent": None,
        "note": None,
    }
    with open(args.journal, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"added": entry}, ensure_ascii=False))


def _md_escape(s):
    if s is None:
        return ""
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


_VERDICTS = {"oui": "✓", "non": "✗", "reformulation": "reformulation",
             "retiree": "retirée du livrable"}


def _verdict(v):
    if v is True:
        return "✓"
    if v is False:
        return "✗"
    if v is None:
        return None
    return _VERDICTS.get(str(v), str(v))


def cmd_table(args):
    entries = _read_journal(args.journal)
    lines = []
    lines.append("# Tableau de vérification pré-livraison")
    lines.append("")
    lines.append(f"**Livrable concerné** : {args.livrable or '[à compléter]'}")
    if args.mode:
        lines.append(f"**Canal de vérification** : {args.mode}")
    lines.append(f"**Source** : généré depuis `{os.path.basename(args.journal)}` "
                 f"({len(entries)} entrées journalisées)")
    lines.append("")
    lines.append("| # | Citation telle qu'écrite dans le document "
                 "| Outil + identifiant | Extrait textuel pertinent retourné par l'outil "
                 "| Voix (cassation) | Soutient l'assertion ? | Contrôle indépendant | Observations |")
    lines.append("|---|---|---|---|---|---|---|---|")
    n_missing = n_open = n_ko = n_reform = 0
    for i, e in enumerate(entries, 1):
        tool_id = f"`{_md_escape(e.get('tool'))}` — {_md_escape(e.get('id'))}"
        if e.get("url"):
            tool_id += f" — {_md_escape(e.get('url'))}"
        excerpt = _md_escape(e.get("excerpt"))
        sup = _verdict(e.get("supports"))
        ind = _verdict(e.get("independent"))
        if not e.get("excerpt") or not e.get("id"):
            n_missing += 1
            flag = "⚠ entrée incomplète"
        elif sup is None:
            n_open += 1
            flag = "à confronter"
        else:
            flag = sup
        if sup != "retirée du livrable" and (sup == "✗" or ind == "✗"):
            n_ko += 1
        if sup == "reformulation":
            n_reform += 1
        voice = _md_escape(e.get("voice")) or "—"
        lines.append(f"| {i} | {_md_escape(e.get('ref'))} | {tool_id} | "
                     f"« {excerpt} » | {voice} | {flag} | {ind or '—'} | "
                     f"{_md_escape(e.get('note'))} |")
    lines.append("")
    lines.append("**Synthèse** :")
    lines.append(f"- Lignes journalisées : {len(entries)}")
    lines.append(f"- Entrées incomplètes (sans extrait ou sans identifiant) : {n_missing}")
    lines.append(f"- Lignes non encore confrontées : {n_open}")
    lines.append(f"- Lignes en échec (rédacteur ou vérificateur indépendant) : {n_ko}")
    lines.append(f"- Reformulations : {n_reform}")
    lines.append("")
    if n_missing == 0 and n_open == 0 and n_ko == 0 and entries:
        lines.append("> Toutes les lignes sont confrontées et aucune n'est en échec : "
                     "la formule de clôture peut être prononcée.")
    else:
        lines.append("> ⚠ La formule de clôture ne peut pas être prononcée : compléter les "
                     "entrées incomplètes, confronter les lignes ouvertes et traiter les lignes "
                     "en échec (changer de référence, reformuler, formulation impersonnelle).")
    out = "\n".join(lines)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        print(json.dumps({"written": args.out, "lines": len(entries),
                          "ready_for_closure": n_missing == 0 and n_open == 0 and n_ko == 0 and bool(entries)},
                         ensure_ascii=False))
    else:
        print(out)


def cmd_mark(args):
    entries = _read_journal(args.journal)
    if not 1 <= args.index <= len(entries):
        print(json.dumps({"error": f"index hors limites (1..{len(entries)})"}, ensure_ascii=False))
        sys.exit(2)
    e = entries[args.index - 1]
    if args.supports:
        e["supports"] = args.supports
    if args.independent == "aucun":
        e["independent"] = None
    elif args.independent:
        e["independent"] = args.independent
    if args.note:
        e["note"] = (e.get("note") + " / " if e.get("note") else "") + args.note
    with open(args.journal, "w", encoding="utf-8") as fh:
        for x in entries:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(json.dumps({"marked": args.index, "entry": e}, ensure_ascii=False))


def cmd_list(args):
    entries = _read_journal(args.journal)
    print(json.dumps(entries, ensure_ascii=False, indent=2))


def cmd_check(args):
    entries = _read_journal(args.journal)
    problems = []
    for i, e in enumerate(entries, 1):
        miss = [k for k in ("ref", "tool", "id", "excerpt", "assertion") if not e.get(k)]
        if miss:
            problems.append({"line": i, "ref": e.get("ref"), "missing": miss})
    out = {
        "journal": args.journal,
        "total": len(entries),
        "incomplete": len(problems),
        "problems": problems,
        "unconfronted": [i for i, e in enumerate(entries, 1) if e.get("supports") in (None, "")],
        "failed": [i for i, e in enumerate(entries, 1)
                   if e.get("supports") != "retiree"
                   and (e.get("supports") in (False, "non") or e.get("independent") in (False, "non"))],
        "ready_for_closure": False,
    }
    out["ready_for_closure"] = (len(problems) == 0 and len(entries) > 0
                                and not out["unconfronted"] and not out["failed"])
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["ready_for_closure"] else 1)


def main():
    parser = argparse.ArgumentParser(description="Journal de références et tableau de vérification.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Ajouter une entrée au journal")
    p_add.add_argument("--journal", required=True)
    p_add.add_argument("--ref", required=True, help="Référence telle qu'elle sera citée")
    p_add.add_argument("--tool", required=True, help="Outil ayant produit la référence")
    p_add.add_argument("--id", required=True, help="Identifiant officiel (Légifrance/DOI/HAL/HUDOC...)")
    p_add.add_argument("--url", default=None, help="Lien officiel")
    p_add.add_argument("--excerpt", required=True, help="Extrait COPIÉ depuis la réponse de l'outil")
    p_add.add_argument("--assertion", required=True, help="Ce que la référence est censée fonder")
    p_add.add_argument("--kind", choices=["juris", "texte", "doctrine"], default="juris")
    p_add.add_argument("--voice", default=None,
                      help="Voix énonciative (cassation Themia) : voix_cour, motifs_ca, moyens...")
    p_add.set_defaults(func=cmd_add)

    p_tab = sub.add_parser("table", help="Générer le tableau Markdown de vérification")
    p_tab.add_argument("--journal", required=True)
    p_tab.add_argument("--livrable", default=None)
    p_tab.add_argument("--mode", default=None,
                       help="Canal de vérification (ex. « OpenLegi + LibreJustice ; HTTP pour HUDOC/Curia »)")
    p_tab.add_argument("--out", default=None, help="Écrire le tableau dans ce fichier (.md)")
    p_tab.set_defaults(func=cmd_table)

    p_mark = sub.add_parser("mark", help="Porter le verdict d'une ligne")
    p_mark.add_argument("--journal", required=True)
    p_mark.add_argument("--index", type=int, required=True, help="Numéro de ligne (1-based)")
    p_mark.add_argument("--supports", choices=["oui", "non", "reformulation", "retiree"], default=None,
                        help="retiree : référence supprimée ou remplacée dans le livrable")
    p_mark.add_argument("--independent", choices=["oui", "non", "aucun"], default=None,
                        help="Verdict d'un vérificateur indépendant qui a effectivement "
                             "contrôlé la ligne ; « aucun » efface un verdict porté par erreur. "
                             "Sans vérificateur indépendant, ne pas utiliser cette option.")
    p_mark.add_argument("--note", default=None)
    p_mark.set_defaults(func=cmd_mark)

    p_list = sub.add_parser("list", help="Lister les entrées (JSON)")
    p_list.add_argument("--journal", required=True)
    p_list.set_defaults(func=cmd_list)

    p_chk = sub.add_parser("check", help="Contrôler la complétude du journal")
    p_chk.add_argument("--journal", required=True)
    p_chk.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
