#!/usr/bin/env python3
"""
tirer_ordre.py : tire au sort l'ordre des documents d'un dossier de note de
synthèse, sous contraintes, puis les renumérote.

Usage :
    python3 tirer_ordre.py dossier.json [--graine N] [--sortie autre.json]
                                        [--autoriser-saga] [--essais 50000]

Sans --sortie, dossier.json est réécrit sur place. La graine retenue est
consignée dans le champ "tirage" du JSON : relancer avec --graine N redonne
exactement le même ordre.

Champs lus pour chaque document (les autres champs sont conservés tels quels) :
    id            identifiant stable, obligatoire (ex. "cass_civ1_1962_lunus")
    registre      texte | jurisprudence | doctrine | institutionnel | non_juridique
    saga          facultatif : étiquette commune aux pièces d'une même affaire
                  ou d'un même débat (ex. "abattage_rituel")
    couple_avec   facultatif : id de la décision que ce document commente
                  (note, résumé, communiqué) ; il est placé juste après elle
    cle_de_voute  facultatif : true pour la pièce centrale, qui ne peut pas
                  être le document 1
    date          facultatif : "AAAA" ou "AAAA-MM-JJ", sert à refuser un
                  ordre trop proche de l'ordre chronologique

Contraintes appliquées :
    1. le document 1 n'est jamais une clé de voûte ;
    2. jamais deux textes normatifs consécutifs ;
    3. jamais trois documents consécutifs du même registre ;
    4. jamais deux pièces d'une même saga consécutives, sauf à l'intérieur
       d'un couple décision plus commentaire (levée par --autoriser-saga) ;
    5. si au moins cinq documents sont datés, corrélation de rang entre
       position et date inférieure à 0,4 en valeur absolue.

Le tirage doit intervenir AVANT la rédaction de la grille, qui renvoie aux
numéros définitifs. Si une grille existe déjà, les numéros des résumés et des
listes de documents des sous-thèmes sont remappés ; le texte libre
(problématique, plan, corps des résumés) ne l'est pas, et le script le signale.
"""

import argparse
import json
import random
import re
import sys
from collections import Counter

REGISTRES = {"texte", "jurisprudence", "doctrine", "institutionnel", "non_juridique"}
SEUIL_CHRONO = 0.4


def erreur(msg):
    print("Erreur : " + msg, file=sys.stderr)
    sys.exit(1)


def construire_blocs(docs):
    par_id = {d["id"]: d for d in docs}
    commentaires = {}
    for d in docs:
        cible = d.get("couple_avec")
        if cible:
            if cible not in par_id:
                erreur(f"'{d['id']}' est couplé à '{cible}', absent du dossier")
            if par_id[cible].get("couple_avec"):
                erreur(f"'{cible}' est lui-même un commentaire : un couple ne s'enchaîne pas")
            commentaires.setdefault(cible, []).append(d)
    blocs = []
    for d in docs:
        if not d.get("couple_avec"):
            blocs.append([d] + commentaires.get(d["id"], []))
    return blocs


def annee(d):
    v = str(d.get("date") or "")
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", v)
    if not m:
        return None
    return int(m.group(1)) + int(m.group(2) or 1) / 13 + int(m.group(3) or 1) / 400


def rangs(valeurs):
    ordre = sorted(range(len(valeurs)), key=lambda i: valeurs[i])
    r = [0] * len(valeurs)
    for rang, i in enumerate(ordre):
        r[i] = rang
    return r


def spearman(xs, ys):
    n = len(xs)
    rx, ry = rangs(xs), rangs(ys)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1))


def violations(seq, meme_bloc, autoriser_saga):
    v = []
    if seq[0].get("cle_de_voute"):
        v.append("clé de voûte en position 1")
    for i in range(1, len(seq)):
        a, b = seq[i - 1], seq[i]
        if a.get("registre") == "texte" and b.get("registre") == "texte":
            v.append("deux textes consécutifs")
        if (not autoriser_saga and a.get("saga") and a.get("saga") == b.get("saga")
                and not meme_bloc(a, b)):
            v.append("deux pièces d'une même saga consécutives")
        if i >= 2 and seq[i - 2].get("registre") == a.get("registre") == b.get("registre"):
            v.append("trois documents consécutifs du même registre")
    dates = [(i, annee(d)) for i, d in enumerate(seq) if annee(d) is not None]
    if len(dates) >= 5:
        rho = spearman([i for i, _ in dates], [y for _, y in dates])
        if abs(rho) >= SEUIL_CHRONO:
            v.append("ordre trop proche de la chronologie")
    return v


def remapper_grille(d, correspondance):
    g = d.get("grille")
    if not g:
        return False
    for r in g.get("resumes", []):
        if r.get("n") in correspondance:
            r["n"] = correspondance[r["n"]]
    g["resumes"] = sorted(g.get("resumes", []), key=lambda r: r.get("n", 0))
    for t in g.get("themes", []):
        for st in t.get("sous_themes", []):
            if isinstance(st.get("documents"), str):
                st["documents"] = re.sub(
                    r"\d+", lambda m: str(correspondance.get(int(m.group()), m.group())),
                    st["documents"])
    return True


def main():
    ap = argparse.ArgumentParser(description="Tirage de l'ordre des documents sous contraintes")
    ap.add_argument("dossier")
    ap.add_argument("--graine", type=int)
    ap.add_argument("--sortie")
    ap.add_argument("--autoriser-saga", action="store_true")
    ap.add_argument("--essais", type=int, default=50000)
    args = ap.parse_args()

    with open(args.dossier, encoding="utf-8") as f:
        d = json.load(f)
    docs = d.get("documents") or []
    if len(docs) < 2:
        erreur("moins de deux documents dans le dossier")

    ids = [x.get("id") for x in docs]
    if any(not i for i in ids):
        erreur("chaque document doit porter un champ 'id'")
    doublons = [i for i, c in Counter(ids).items() if c > 1]
    if doublons:
        erreur("identifiants en double : " + ", ".join(doublons))
    sans_registre = [x["id"] for x in docs if x.get("registre") not in REGISTRES]
    if sans_registre:
        erreur("registre absent ou inconnu pour : " + ", ".join(sans_registre)
               + " (valeurs admises : " + ", ".join(sorted(REGISTRES)) + ")")
    if not any(x.get("cle_de_voute") for x in docs):
        print("Avertissement : aucune pièce marquée 'cle_de_voute'.", file=sys.stderr)

    blocs = construire_blocs(docs)
    bloc_de = {x["id"]: k for k, bloc in enumerate(blocs) for x in bloc}

    def meme_bloc(a, b):
        return bloc_de[a["id"]] == bloc_de[b["id"]]

    graine = args.graine if args.graine is not None else random.SystemRandom().randrange(10**9)
    rng = random.Random(graine)
    echecs = Counter()
    retenu = None
    for essai in range(1, args.essais + 1):
        ordre = blocs[:]
        rng.shuffle(ordre)
        seq = [x for bloc in ordre for x in bloc]
        v = violations(seq, meme_bloc, args.autoriser_saga)
        if not v:
            retenu = seq
            break
        echecs.update(set(v))

    if retenu is None:
        print(f"Aucun ordre valide en {args.essais} essais (graine {graine}).", file=sys.stderr)
        print("Contraintes le plus souvent violées :", file=sys.stderr)
        for motif, nb in echecs.most_common():
            print(f"  - {motif} ({nb} fois)", file=sys.stderr)
        print("Revoir la composition du dossier (trop de textes, saga trop fournie) "
              "ou, pour une saga, envisager --autoriser-saga.", file=sys.stderr)
        sys.exit(2)

    correspondance = {}
    for nouveau, x in enumerate(retenu, start=1):
        if isinstance(x.get("n"), int):
            correspondance[x["n"]] = nouveau
        x["n"] = nouveau
    d["documents"] = retenu
    grille_remappee = remapper_grille(d, correspondance) if correspondance else False

    d["tirage"] = {
        "graine": graine,
        "essais": essai,
        "autoriser_saga": args.autoriser_saga,
        "ordre": [x["id"] for x in retenu],
    }

    sortie = args.sortie or args.dossier
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    print(f"Ordre tiré (graine {graine}, {essai} essai{'s' if essai > 1 else ''}) :")
    for x in retenu:
        extra = []
        if x.get("saga"):
            extra.append("saga " + x["saga"])
        if x.get("couple_avec"):
            extra.append("commente " + x["couple_avec"])
        if x.get("cle_de_voute"):
            extra.append("clé de voûte")
        suffixe = f"  [{', '.join(extra)}]" if extra else ""
        print(f"  {x['n']:>2}. {x['id']}  ({x['registre']}){suffixe}")
    print("Écrit : " + sortie)
    if grille_remappee:
        print("Avertissement : la grille existait déjà. Numéros des résumés et des sous-thèmes "
              "remappés ; relire la problématique, le plan et le corps des résumés, qui peuvent "
              "encore citer les anciens numéros.", file=sys.stderr)


if __name__ == "__main__":
    main()
