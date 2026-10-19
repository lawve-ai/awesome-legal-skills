# -*- coding: utf-8 -*-
"""Contrôle du dictionnaire et d'un dossier ; prototype des règles d'accord."""
import json, re, sys, os

ICI = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(ICI, "..", "references", "dictionnaire.json"), encoding="utf-8"))
ERREURS, AVIS = [], []

# ------------------------------------------------------------ sommes de contrôle
def luhn(s):
    t = 0
    for i, c in enumerate(reversed(s)):
        d = int(c)
        if i % 2:
            d *= 2
            d -= 9 if d > 9 else 0
        t += d
    return t % 10 == 0

def iban_ok(s):
    s = s.replace(" ", "").upper()
    r = s[4:] + s[:4]
    n = "".join(str(int(c, 36)) for c in r)
    return int(n) % 97 == 1

def nir_ok(s):
    s = s.replace(" ", "").upper().replace("2A", "19").replace("2B", "18")
    return len(s) == 15 and s.isdigit() and 97 - int(s[:13]) % 97 == int(s[13:])

def tva_ok(s):
    m = re.fullmatch(r"FR(\d{2})(\d{9})", s.replace(" ", ""))
    return bool(m) and int(m.group(1)) == (12 + 3 * (int(m.group(2)) % 97)) % 97

CONTROLES = {
    "siren": lambda s: bool(re.fullmatch(r"\d{9}", s.replace(" ", ""))) and luhn(s.replace(" ", "")),
    "siret": lambda s: bool(re.fullmatch(r"\d{14}", s.replace(" ", ""))) and luhn(s.replace(" ", "")),
    "tva_fr": tva_ok, "iban": iban_ok, "nir": nir_ok,
    "rna": lambda s: bool(re.fullmatch(r"W[0-9A-Z]{9}", s)),
}

def valeur_conforme(c, val, entites_dossier=None):
    t = c["type"]
    if val in (None, ""):
        return True
    if t in ("texte", "texte_long", "telephone"):
        return isinstance(val, str)
    if t == "courriel":
        return isinstance(val, str) and bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", val))
    if t == "entier":
        return isinstance(val, int) and not isinstance(val, bool)
    if t in ("decimal", "pourcentage"):
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    if t == "booleen":
        return isinstance(val, bool)
    if t == "date":
        return isinstance(val, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", val))
    if t == "heure":
        return isinstance(val, str) and bool(re.fullmatch(r"\d{2}:\d{2}", val))
    if t == "montant":
        return isinstance(val, dict) and isinstance(val.get("valeur"), (int, float)) and set(val) <= {"valeur", "devise"}
    if t == "duree":
        return isinstance(val, dict) and isinstance(val.get("valeur"), int) and \
            val.get("unite") in ("jours", "semaines", "mois", "annees")
    if t == "choix":
        return val in [x["id"] for x in c["valeurs"]]
    if t == "identifiant":
        f = CONTROLES.get(c.get("validation"))
        return f(val) if f else isinstance(val, str)
    if t == "reference":
        return isinstance(val, str) and (entites_dossier is None or val in entites_dossier)
    if t == "adresse":
        return isinstance(val, dict)
    return True

# ------------------------------------------------------------ contrôle du schéma
def controler_champs(champs, ou):
    vus = set()
    for c in champs:
        lieu = f"{ou}.{c['id']}"
        if c["id"] in vus:
            ERREURS.append(f"identifiant en double : {lieu}")
        vus.add(c["id"])
        if not re.fullmatch(r"[a-z][a-z0-9_]*", c["id"]):
            ERREURS.append(f"identifiant non conforme : {lieu}")
        if c["type"] not in D["types"]:
            ERREURS.append(f"type inconnu {c['type']} : {lieu}")
        if c["type"] == "choix":
            ids = [x["id"] for x in c.get("valeurs", [])]
            if not ids or len(ids) != len(set(ids)):
                ERREURS.append(f"choix vide ou en double : {lieu}")
        if c["type"] == "reference" and c.get("cible") not in D["entites"]:
            ERREURS.append(f"cible inconnue : {lieu}")
        if c["type"] == "identifiant" and c.get("validation") not in D["validations"]:
            ERREURS.append(f"validation inconnue : {lieu}")
        if "exemple" in c and c["exemple"] != "" and not valeur_conforme(c, c["exemple"]):
            ERREURS.append(f"exemple non conforme : {lieu} = {c['exemple']!r}")
        if c["type"] in ("groupe", "liste") and "champs" in c:
            controler_champs(c["champs"], lieu)
        if c["type"] == "liste" and "champs" not in c and c.get("element") not in D["types"]:
            ERREURS.append(f"liste sans élément : {lieu}")

for nom, e in D["entites"].items():
    for cle in ("champs", "commun", "physique", "morale"):
        if cle in e:
            controler_champs(e[cle], f"entites.{nom}.{cle}")
ids_mod = set()
for m in D["modules"]:
    if m["id"] in ids_mod:
        ERREURS.append(f"module en double : {m['id']}")
    ids_mod.add(m["id"])
    controler_champs(m["champs"], m["id"])
    roles = [r["id"] for r in m["roles"]]
    if len(roles) != len(set(roles)):
        ERREURS.append(f"rôle en double dans {m['id']}")
    for r in m["roles"]:
        if set(r["libelles"]) != {"ms", "fs", "mp", "fp"}:
            ERREURS.append(f"libellés incomplets : {m['id']}.{r['id']}")
    for c in m["champs"]:
        if c["id"] in roles:
            ERREURS.append(f"collision champ/rôle : {m['id']}.{c['id']}")

def compter(champs):
    n = 0
    for c in champs:
        n += 1
        if "champs" in c:
            n += compter(c["champs"])
    return n

nb_entites = sum(compter(e.get(k, [])) for e in D["entites"].values() for k in ("champs", "commun", "physique", "morale"))
nb_modules = sum(compter(m["champs"]) for m in D["modules"])
nb_roles = sum(len(m["roles"]) for m in D["modules"])

# ------------------------------------------------------------ contrôle d'un dossier
MODULES = {m["id"]: m for m in D["modules"]}

def chercher(champs, cle):
    for c in champs:
        if c["id"] == cle:
            return c
    return None

def controler_valeurs(champs, donnees, chemin, entites, inconnus):
    for cle, val in donnees.items():
        c = chercher(champs, cle)
        lieu = f"{chemin}.{cle}"
        if c is None:
            inconnus.append(lieu)
            continue
        if c["type"] == "groupe":
            controler_valeurs(c["champs"], val, lieu, entites, inconnus)
        elif c["type"] == "liste":
            for i, el in enumerate(val):
                if "champs" in c:
                    controler_valeurs(c["champs"], el, f"{lieu}[{i}]", entites, inconnus)
        elif c["type"] == "adresse":
            controler_valeurs(D["entites"]["adresse"]["champs"], val, lieu, entites, inconnus)
        elif not valeur_conforme(c, val, entites):
            ERREURS.append(f"[dossier] valeur non conforme : {lieu} = {val!r}")

def controler_dossier(dos):
    inconnus = []
    entites = set(dos.get("personnes", {})) | set(dos.get("biens", {})) | set(dos.get("vehicules", {})) | set(dos.get("comptes", {}))
    P = D["entites"]["personne"]
    for pid, p in dos.get("personnes", {}).items():
        schema = P["commun"] + P[p["nature"]]
        controler_valeurs(schema, p, f"personnes.{pid}", entites, inconnus)
    for pid, b in dos.get("biens", {}).items():
        controler_valeurs(D["entites"]["bien_immobilier"]["champs"], b, f"biens.{pid}", entites, inconnus)
    for mid, donnees in dos.get("modules", {}).items():
        if mid not in MODULES:
            inconnus.append(f"modules.{mid}")
            continue
        controler_valeurs(MODULES[mid]["champs"], donnees, f"modules.{mid}", entites, inconnus)
    for r, ids in dos.get("roles", {}).items():
        mid, rid = r.split(".")
        defn = next((x for x in MODULES[mid]["roles"] if x["id"] == rid), None)
        if defn is None:
            ERREURS.append(f"[dossier] rôle inconnu : {r}")
            continue
        for i in ids:
            if i not in dos["personnes"]:
                ERREURS.append(f"[dossier] rôle {r} vise une personne absente : {i}")
            elif dos["personnes"][i]["nature"] not in defn["natures"]:
                ERREURS.append(f"[dossier] nature incompatible : {r} ← {i}")
    return inconnus

# ------------------------------------------------------------ prototype d'accord
FORMES = {f["id"]: f for f in chercher(D["entites"]["personne"]["morale"], "forme_juridique")["valeurs"]}

def genre(p):
    if p["nature"] == "physique":
        return {"monsieur": "m", "madame": "f"}[p["civilite"]]
    return p.get("genre_grammatical") or FORMES[p["forme_juridique"]]["genre"]

def designation_courte(p):
    if p["nature"] == "physique":
        civ = {"monsieur": "Monsieur", "madame": "Madame"}[p["civilite"]]
        return f"{civ} {p.get('prenom_usuel') or p['prenoms'].split(',')[0]} {p['nom'].upper()}"
    gen = FORMES[p["forme_juridique"]]["generique"]
    art = "l'" if gen[0] in "aeéiouyAEÉIOUY" else ("le " if genre(p) == "m" else "la ")
    return f"{art}{gen} {p['denomination']}"

def qualite_role(dos, cle):
    mid, rid = cle.split(".")
    defn = next(x for x in MODULES[mid]["roles"] if x["id"] == rid)
    ps = [dos["personnes"][i] for i in dos["roles"][cle]]
    pl = len(ps) > 1
    fem = all(genre(p) == "f" for p in ps)
    return defn["libelles"][("f" if fem else "m") + ("p" if pl else "s")]

if __name__ == "__main__":
    dossier = json.load(open(os.path.join(ICI, "dossier-exemple.json"), encoding="utf-8"))
    inconnus = controler_dossier(dossier)
    print(f"Dictionnaire : {len(D['modules'])} modules, {nb_roles} rôles, "
          f"{nb_entites} champs d'entités, {nb_modules} champs de modules")
    print("Champs inconnus conservés (extensions) :", inconnus or "aucun")
    for cle in dossier["roles"]:
        ds = [designation_courte(dossier["personnes"][i]) for i in dossier["roles"][cle]]; noms = ", ".join(ds[:-1]) + " et " + ds[-1] if len(ds) > 1 else ds[0]
        print(f"  {cle:32} → {noms}, {qualite_role(dossier, cle)}")
    if ERREURS:
        print("\nERREURS :"); [print(" -", e) for e in ERREURS]; sys.exit(1)
    print("\nAucune erreur.")
