# -*- coding: utf-8 -*-
"""Génère la version lisible (Markdown) du dictionnaire depuis le JSON canonique."""
import json, os

ICI = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(ICI, "..", "references", "dictionnaire.json"), encoding="utf-8"))
L = []
w = L.append

def type_lisible(c):
    t = c["type"]
    if t == "choix":
        vals = [x["libelle"] for x in c["valeurs"]]
        return "choix : " + " / ".join(vals[:8]) + (" / …" if len(vals) > 8 else "")
    if t == "reference":
        n = c.get("natures")
        return f"renvoi → {c['cible']}" + (f" ({', '.join(n)})" if n else "")
    if t == "identifiant":
        return f"identifiant ({c['validation']})"
    if t == "liste" and "element" in c:
        return f"liste de {c['element']}"
    return t

def notes(c):
    n = []
    if c.get("sensible"):
        n.append("**sensible**")
    if c.get("aide"):
        n.append(c["aide"])
    return " ".join(n)

def table(champs, prefixe=""):
    for c in champs:
        chemin = f"{prefixe}{c['id']}"
        w(f"| `{chemin}` | {c['libelle']} | {type_lisible(c)} | {notes(c)} |")
        if "champs" in c:
            table(c["champs"], chemin + ("[]." if c["type"] == "liste" else "."))

def entete():
    w("| Chemin | Libellé | Type | Remarques |")
    w("|---|---|---|---|")

w(f"# {D['nom']}")
w("")
w(f"Version {D['version']} du {D['date']}, {D['statut']}. Document généré depuis `dictionnaire.json`, "
  "qui fait foi ; ne pas modifier ce fichier à la main.")
w("")
w("## Conventions")
w("")
for k, txt in D["conventions"].items():
    titres = {"identifiants": "Identifiants", "chemins": "Chemins", "personnes_et_roles": "Personnes et rôles",
              "accords": "Accords", "termes_definis": "Termes définis",
              "absence_de_regles_de_droit": "Absence de règles de droit", "champs_sensibles": "Champs sensibles",
              "valeurs_fictives": "Valeurs fictives", "variables_locales": "Variables locales", "trame": "Un dictionnaire-trame", "attributs_de_role": "Attributs de rôle",
              "compatibilite": "Compatibilité", "une_instance_par_module": "Une instance par module"}
    w(f"- **{titres.get(k, k)}** : {txt}")
w("")
w("## Format du dossier (.json de l'utilisateur)")
w("")
for k, txt in D["format_dossier"]["cles"].items():
    w(f"- `{k}` : {txt}")
w("")
w("## Types")
w("")
w("| Type | Description | Rendus |")
w("|---|---|---|")
for t, d in D["types"].items():
    w(f"| `{t}` | {d['description']} | {', '.join(d.get('rendus', []))} |")
w("")
w("Contrôles des identifiants :")
w("")
for k, txt in D["validations"].items():
    w(f"- `{k}` : {txt}")
w("")
w("## Entités")
for nom, e in D["entites"].items():
    w("")
    w(f"### {e['libelle']} (`{nom}`)" + (f", identifiants {e['prefixe_identifiant']}1, {e['prefixe_identifiant']}2…" if "prefixe_identifiant" in e else ""))
    w("")
    for partie, titre in (("commun", "Champs communs"), ("physique", "Personne physique"),
                          ("morale", "Personne morale"), ("champs", None)):
        if partie in e:
            if titre:
                w(f"**{titre}**")
                w("")
            entete()
            table(e[partie])
            w("")
    if "derives" in e:
        w("**Valeurs dérivées** (calculées par le formulaire, jamais saisies)")
        w("")
        for d in e["derives"]:
            w(f"- `{d['id']}` : {d['regle']}")
        w("")
w("## Modules")
for m in D["modules"]:
    w("")
    w(f"### {m['libelle']} (`{m['id']}`)")
    w("")
    w(m["description"])
    w("")
    w("**Rôles**")
    w("")
    w("| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |")
    w("|---|---|---|---|---|---|---|")
    for r in m["roles"]:
        l = r["libelles"]
        extra = ""
        if "variantes" in r:
            extra = " ; variantes : " + ", ".join(r["variantes"])
        w(f"| `{m['id']}.{r['id']}` | {l['ms']} | {l['fs']} | {l['mp']} | {l['fp']} | {r['cardinalite']} | "
          f"{', '.join(r['natures'])}{extra} |")
    w("")
    w("**Champs**")
    w("")
    entete()
    table(m["champs"], m["id"] + ".")
    w("")
    if m.get("controles"):
        w("**Contrôles de cohérence**")
        w("")
        for c in m["controles"]:
            w(f"- {c}")
        w("")
    if m.get("points_a_trancher"):
        w("**Questions à poser au balisage si le modèle calcule ou applique une règle**")
        w("")
        for c in m["points_a_trancher"]:
            w(f"- {c}")
        w("")
w("## Modules prévus")
w("")
w(", ".join(f"`{x}`" for x in D["modules_prevus"]) + ".")
w("")

open(os.path.join(ICI, "..", "references", "dictionnaire.md"), "w", encoding="utf-8").write("\n".join(L))
print(len(L), "lignes")
