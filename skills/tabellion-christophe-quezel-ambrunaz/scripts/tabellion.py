#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tabellion — transformer un modèle .docx/.odt en formulaire HTML hors ligne.

Commandes
  analyser  MODELE                      relevé numéroté des paragraphes et indices de balisage
  baliser   MODELE PLAN.json SORTIE     applique un plan de balisage (balises surlignées)
  compiler  MODELE_BALISE MANIFESTE.json REPERTOIRE
                                        contrôle et compile ; écrit modele.json, plan.json, rapport.md
  formulaire REPERTOIRE FICHIER.html    construit le formulaire autonome
  tester    REPERTOIRE                  génère les variantes fictives et contrôle les documents produits
  tout      MODELE_BALISE MANIFESTE.json REPERTOIRE FICHIER.html
                                        compiler + tester + formulaire
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI)

from lxml import etree  # noqa: E402

from compilateur import Compilation, rapport_markdown  # noqa: E402
from balisage import analyser, baliser  # noqa: E402
from fictif import dossier_fictif, variantes  # noqa: E402


def dictionnaire():
    with open(os.path.join(RACINE, "references", "dictionnaire.json"), encoding="utf-8") as f:
        return json.load(f)


def ecrire_json(chemin, obj):
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def lire_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ commandes
def cmd_analyser(modele):
    infos, texte = analyser(modele)
    print(f"Format : {infos['format']} ; parties balisables : {', '.join(infos['parties'])}")
    for a in infos["alertes"]:
        print(f"ALERTE : {a}")
    if infos["indices"]:
        print("Indices : " + "; ".join(f"{k} ({v})" for k, v in infos["indices"].items()))
    print("-" * 72)
    print(texte)
    return 0


def cmd_baliser(modele, plan, sortie):
    compte_rendu, erreurs = baliser(modele, lire_json(plan), sortie)
    for c in compte_rendu:
        print("✓ " + c)
    for e in erreurs:
        print("✗ " + e)
    print(f"Document balisé : {sortie}")
    return 1 if erreurs else 0


def cmd_compiler(modele, manifeste, rep):
    os.makedirs(rep, exist_ok=True)
    d = dictionnaire()
    m = lire_json(manifeste)
    comp = Compilation(modele, d, m)
    res = comp.executer()
    plan = res[1] if res else None
    rapport = rapport_markdown(comp, plan)
    with open(os.path.join(rep, "rapport.md"), "w", encoding="utf-8") as f:
        f.write(rapport)
    print(rapport)
    if comp.erreurs or not res:
        print(f"\n{len(comp.erreurs)} erreur(s) : corriger le balisage ou le manifeste, puis recompiler.")
        return 1
    modele_c, plan = res
    ecrire_json(os.path.join(rep, "dictionnaire.json"), comp.d)   # dictionnaire effectif (commun + extensions)
    ecrire_json(os.path.join(rep, "modele.json"), modele_c)
    ecrire_json(os.path.join(rep, "plan.json"), plan)
    ecrire_json(os.path.join(rep, "essai.json"), dossier_fictif(plan, modele_c["id"], d["version"], comp.extensions))
    print(f"\nCompilation réussie : {rep}/modele.json, plan.json, essai.json")
    return 0


def _script_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def dictionnaire_effectif(rep):
    chemin = os.path.join(rep, "dictionnaire.json")
    return lire_json(chemin) if os.path.exists(chemin) else dictionnaire()


def cmd_formulaire(rep, sortie):
    d = dictionnaire_effectif(rep)
    modele, plan, essai = (lire_json(os.path.join(rep, n)) for n in ("modele.json", "plan.json", "essai.json"))
    with open(os.path.join(RACINE, "assets", "formulaire.html"), encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(RACINE, "assets", "moteur.js"), encoding="utf-8") as f:
        moteur = f.read()
    titre = modele["titre"].replace("&", "&amp;").replace("<", "&lt;")
    for cle, val in (("__TITRE__", titre), ("__DICTIONNAIRE__", _script_json(d)), ("__MODELE__", _script_json(modele)),
                     ("__PLAN__", _script_json(plan)), ("__ESSAI__", _script_json(essai))):
        if html.count(cle) != 1:
            raise SystemExit(f"gabarit de formulaire altéré : {cle}")
        html = html.replace(cle, val)
    if html.count("__MOTEUR__") != 1:
        raise SystemExit("gabarit de formulaire altéré : __MOTEUR__")
    html = html.replace("__MOTEUR__", moteur)
    with open(sortie, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Formulaire : {sortie} ({os.path.getsize(sortie) // 1024} Ko)")
    return 0


def _controle_document(chemin, fmt):
    """Ouvre le zip, analyse chaque partie XML ; renvoie la liste des anomalies."""
    anomalies = []
    try:
        with zipfile.ZipFile(chemin) as z:
            noms = z.namelist()
            if fmt == "odt" and noms[0] != "mimetype":
                anomalies.append("odt : « mimetype » n'est pas la première entrée")
            for n in noms:
                if n.endswith(".xml") or n.endswith(".rels"):
                    try:
                        etree.fromstring(z.read(n))
                    except etree.XMLSyntaxError as e:
                        anomalies.append(f"XML mal formé dans {n} : {e}")
    except zipfile.BadZipFile as e:
        anomalies.append(f"archive illisible : {e}")
    return anomalies


def cmd_tester(rep, pdf=True):
    d = dictionnaire_effectif(rep)
    modele, plan = lire_json(os.path.join(rep, "modele.json")), lire_json(os.path.join(rep, "plan.json"))
    fmt = modele["format"]
    rep_tests = os.path.join(rep, "tests")
    shutil.rmtree(rep_tests, ignore_errors=True)
    os.makedirs(rep_tests)
    chemin_dico = os.path.join(rep_tests, "_dictionnaire.json")
    ecrire_json(chemin_dico, d)
    lignes, echecs = ["| Variante | Manquants | Remarques | Contrôles non respectés | Anomalies |", "|---|---|---|---|---|"], 0
    for nom, dos in variantes(plan, modele["id"], d["version"], modele.get("types_extensions", {})):
        cd = os.path.join(rep_tests, f"{nom}.dossier.json")
        ecrire_json(cd, dos)
        sortie = os.path.join(rep_tests, f"{nom}.{fmt}")
        rapport = os.path.join(rep_tests, f"{nom}.rapport.json")
        r = subprocess.run(["node", os.path.join(ICI, "rendre.js"), os.path.join(rep, "modele.json"), chemin_dico, cd,
                            sortie, rapport], capture_output=True, text=True)
        if r.returncode:
            echecs += 1
            lignes.append(f"| {nom} | — | — | — | moteur en erreur : {r.stderr.strip().splitlines()[-1] if r.stderr else '?'} |")
            continue
        rr = lire_json(rapport)
        anomalies = _controle_document(sortie, fmt)
        for motif in ("{{", "}}", "[[", "]]"):
            if motif in rr["apercu"]:
                anomalies.append(f"délimiteur « {motif} » resté dans le texte")
        with open(os.path.join(rep_tests, f"{nom}.apercu.txt"), "w", encoding="utf-8") as f:
            f.write(rr["apercu"])
        ctl = [c["message"] for c in rr["controles"] if not c["respecte"]]
        if anomalies:
            echecs += 1
        lignes.append(f"| {nom} | {len(rr['manquants'])} | {len(rr['alertes'])} | {'; '.join(ctl) or '—'} | "
                      f"{'; '.join(anomalies) or '—'} |")
    if pdf and shutil.which("soffice"):
        base = os.path.join(rep_tests, f"base.{fmt}")
        profil = tempfile.mkdtemp()
        r = subprocess.run(["soffice", f"-env:UserInstallation=file://{profil}", "--headless", "--convert-to", "pdf",
                            "--outdir", rep_tests, base], capture_output=True, text=True, timeout=180)
        ok = os.path.exists(os.path.join(rep_tests, "base.pdf"))
        lignes.append(f"\nOuverture par LibreOffice et conversion en PDF de la variante de base : {'réussie' if ok else 'ÉCHEC'}")
        if not ok:
            echecs += 1
    texte = "\n".join(lignes)
    with open(os.path.join(rep, "rapport-tests.md"), "w", encoding="utf-8") as f:
        f.write(texte)
    print(texte)
    print(f"\n{'Aucune anomalie.' if not echecs else str(echecs) + ' variante(s) en anomalie.'} Fichiers : {rep_tests}")
    return 1 if echecs else 0


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "aide"):
        print(__doc__)
        return 0
    c, a = argv[1], argv[2:]
    if c == "analyser" and len(a) == 1:
        return cmd_analyser(*a)
    if c == "baliser" and len(a) == 3:
        return cmd_baliser(*a)
    if c == "compiler" and len(a) == 3:
        return cmd_compiler(*a)
    if c == "formulaire" and len(a) == 2:
        return cmd_formulaire(*a)
    if c == "tester" and len(a) in (1, 2):
        return cmd_tester(a[0], pdf=not (len(a) == 2 and a[1] == "--sans-pdf"))
    if c == "tout" and len(a) == 4:
        r = cmd_compiler(a[0], a[1], a[2])
        if r:
            return r
        r = cmd_tester(a[2])
        cmd_formulaire(a[2], a[3])
        return r
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
