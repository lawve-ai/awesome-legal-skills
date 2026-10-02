#!/usr/bin/env python3
"""
verifier_verbatim.py : vérifie que chaque extrait du dossier se retrouve mot
pour mot dans le texte source enregistré pendant la collecte.

Usage :
    python3 verifier_verbatim.py dossier.json [--racine DIR] [--seuil 0.9]
                                              [--rapport rapport.md] [--sobre]

Pour chaque document reproduit (ni "a_completer": true, ni "nature": "notice"),
le JSON doit indiquer le fichier source :
    "source": { "fichier": "sources/cass_civ1_1962_lunus.txt", ... }
Le chemin est relatif à --racine (par défaut, le dossier du JSON).

Méthode. Le contenu est découpé en segments à chaque paragraphe et à chaque
marque de coupe « (…) », « (...) », « […] ». Les insertions entre crochets
(ex. « [la Cour] ») sont écartées. Texte et source sont normalisés (casse,
accents, apostrophes, guillemets, espaces, ponctuation), puis chaque segment
est comparé à la source par séquences de quatre mots : la couverture est la
part des mots du segment appartenant à une séquence présente dans la source.

Verdict par segment :
    conforme       couverture >= 0,98
    écart mineur   couverture >= seuil (0,9 par défaut) : souvent une coquille,
                   une typographie ou un mot ajouté, à regarder
    non conforme   couverture < seuil : paraphrase, réécriture ou mauvaise source

Le script affiche les passages introuvables dans la source. Code de sortie 1
s'il reste un segment non conforme ou une source manquante, 0 sinon.

--sobre n'affiche que les compteurs et les numéros de documents, sans citer
les passages : à utiliser en mode aveugle si l'on ne veut rien montrer du
contenu dans la conversation.
"""

import argparse
import json
import os
import re
import sys
import unicodedata

N = 4
COUPE = re.compile(r"\(\s*(?:…|\.\.\.)\s*\)|\[\s*(?:…|\.\.\.)\s*\]")
INSERTION = re.compile(r"\[[^\]]*\]")


def normaliser(texte):
    t = unicodedata.normalize("NFKC", texte)
    t = t.replace("œ", "oe").replace("Œ", "oe").replace("æ", "ae").replace("Æ", "ae")
    t = t.replace("\u00ad", "")
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"\w+", t)


def segments(contenu):
    for para in contenu or []:
        for morceau in COUPE.split(INSERTION.sub(" ", str(para))):
            mots = normaliser(morceau)
            if mots:
                yield morceau.strip(), mots


def couverture(mots, ngrams_source, texte_source):
    if len(mots) < N:
        trouve = (" " + " ".join(mots) + " ") in texte_source
        return (1.0 if trouve else 0.0), ([] if trouve else [(0, len(mots))])
    couvert = [False] * len(mots)
    for i in range(len(mots) - N + 1):
        if tuple(mots[i:i + N]) in ngrams_source:
            for j in range(i, i + N):
                couvert[j] = True
    trous, debut = [], None
    for i, c in enumerate(couvert + [True]):
        if not c and debut is None:
            debut = i
        elif c and debut is not None:
            trous.append((debut, i))
            debut = None
    return sum(couvert) / len(mots), trous


def main():
    ap = argparse.ArgumentParser(description="Contrôle du verbatim des extraits")
    ap.add_argument("dossier")
    ap.add_argument("--racine")
    ap.add_argument("--seuil", type=float, default=0.9)
    ap.add_argument("--rapport")
    ap.add_argument("--sobre", action="store_true")
    args = ap.parse_args()

    with open(args.dossier, encoding="utf-8") as f:
        d = json.load(f)
    racine = args.racine or os.path.dirname(os.path.abspath(args.dossier))

    lignes = ["# Contrôle du verbatim", ""]
    bilan = {"conforme": 0, "écart mineur": 0, "non conforme": 0}
    sources_manquantes, docs_en_defaut, notices = [], [], []

    for doc in d.get("documents", []):
        n = doc.get("n", "?")
        if doc.get("a_completer") or doc.get("nature") == "notice":
            notices.append(n)
            continue
        fichier = (doc.get("source") or {}).get("fichier")
        chemin = os.path.join(racine, fichier) if fichier else None
        if not chemin or not os.path.exists(chemin):
            sources_manquantes.append(n)
            lignes.append(f"## Document {n} : source absente ({fichier or 'champ source.fichier vide'})")
            lignes.append("")
            continue
        with open(chemin, encoding="utf-8", errors="replace") as f:
            mots_source = normaliser(f.read())
        ngrams = {tuple(mots_source[i:i + N]) for i in range(len(mots_source) - N + 1)}
        texte_source = " " + " ".join(mots_source) + " "

        details, pire = [], "conforme"
        for brut, mots in segments(doc.get("contenu")):
            cov, trous = couverture(mots, ngrams, texte_source)
            if cov >= 0.98:
                verdict = "conforme"
            elif cov >= args.seuil:
                verdict = "écart mineur"
            else:
                verdict = "non conforme"
            bilan[verdict] += 1
            if verdict != "conforme":
                ordre = ["conforme", "écart mineur", "non conforme"]
                if ordre.index(verdict) > ordre.index(pire):
                    pire = verdict
                if not args.sobre:
                    extraits = []
                    for a, b in trous[:3]:
                        bout = " ".join(mots[max(0, a - 3):min(len(mots), b + 3)])
                        if b - a > 15:
                            bout = " ".join(mots[max(0, a - 3):a + 12]) + " …"
                        extraits.append(f"« {bout} »")
                    debut_seg = " ".join(brut.split()[:10])
                    details.append(f"- {verdict} ({cov:.0%}), segment commençant par « {debut_seg} … » : "
                                   f"introuvable dans la source : {' ; '.join(extraits)}")
        if pire != "conforme":
            docs_en_defaut.append((n, pire))
            lignes.append(f"## Document {n} : {pire}")
            lignes.extend(details if details else ["- détail masqué (--sobre)"])
            lignes.append("")

    lignes.insert(2, f"Segments conformes : {bilan['conforme']} ; écarts mineurs : {bilan['écart mineur']} ; "
                     f"non conformes : {bilan['non conforme']}.")
    lignes.insert(3, f"Sources manquantes : {', '.join(map(str, sources_manquantes)) or 'aucune'}. "
                     f"Notices et emplacements non contrôlés : {', '.join(map(str, notices)) or 'aucun'}.")
    lignes.insert(4, "")

    sortie = "\n".join(lignes)
    print(sortie)
    if args.rapport:
        with open(args.rapport, "w", encoding="utf-8") as f:
            f.write(sortie + "\n")

    if sources_manquantes or bilan["non conforme"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
