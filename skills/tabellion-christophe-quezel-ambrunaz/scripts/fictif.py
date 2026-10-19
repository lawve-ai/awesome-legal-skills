# -*- coding: utf-8 -*-
"""Dossier fictif construit à partir du plan du formulaire : valeurs manifestement fictives."""
import copy

ADRESSE = {"numero": "12", "voie": "rue de l'Exemple", "code_postal": "00000", "commune": "Exempleville"}
PHYSIQUES = [("madame", "ESSAI", "Jeanne, Marie", "Jeanne"), ("monsieur", "FICTIF", "Paul, Henri", "Paul"),
             ("madame", "MODELE", "Lucie", "Lucie"), ("monsieur", "EXEMPLE", "Marc", "Marc"),
             ("madame", "SPECIMEN", "Claire", "Claire"), ("monsieur", "MAQUETTE", "Louis", "Louis")]
MORALES = [("sas", "ALPHA ESSAI"), ("sci", "BETA ESSAI"), ("sarl", "GAMMA ESSAI"), ("association", "DELTA ESSAI")]
PAR_TYPE = {
    "texte": "Texte d'essai", "texte_long": "Premier paragraphe d'essai.\nSecond paragraphe d'essai.",
    "entier": 3, "decimal": 12.5, "montant": {"valeur": 1250.5, "devise": "EUR"}, "pourcentage": 3.5,
    "date": "2026-01-15", "heure": "09:30", "duree": {"valeur": 3, "unite": "mois"}, "booleen": True,
    "adresse": ADRESSE, "telephone": "00 00 00 00 00", "courriel": "essai@exemple.invalid",
}
IDENTIFIANTS = {"siren": "000000000", "siret": "00000000000018", "tva_fr": "FR12000000000",
                "iban": "FR7699999000000000000000130", "nir": "100019999999980", "rna": "W000000000"}


def _sans_vides(d):
    return {k: v for k, v in d.items() if v is not None}


class Fabrique:
    def __init__(self, plan):
        self.plan = plan
        self.dossier = {"format": "tabellion-dossier", "personnes": {}, "biens": {}, "vehicules": {}, "comptes": {},
                        "roles": {}, "attributs_roles": {}, "modules": {}, "local": {}, "decisions": {},
                        "valeurs_fictives": ["*"]}
        self.np = self.nm = 0
        self.profondeur = 0

    def valeur(self, c):
        t = c["type"]
        if "exemple" in c:
            return copy.deepcopy(c["exemple"]) if c["exemple"] not in ("", None) else None
        if t == "choix":
            return c["valeurs"][0]["id"]
        if t == "identifiant":
            return IDENTIFIANTS.get(c.get("validation"), "000")
        if t == "adresse":
            return dict(ADRESSE)
        if t == "groupe":
            return _sans_vides({x["id"]: self.valeur(x) for x in c["champs"]})
        if t == "liste":
            if "champs" in c:
                return [_sans_vides({x["id"]: self.valeur(x) for x in c["champs"]}) for _ in range(2)]
            return [f"Élément d'essai {i}" for i in (1, 2)]
        if t == "reference":
            return self.reference(c)
        return copy.deepcopy(PAR_TYPE.get(t, "Essai"))

    def reference(self, c):
        cible = c["cible"]
        if cible == "personne":
            if self.profondeur > 0:      # pas de conjoint du conjoint : une seule génération de renvois
                return None
            natures = c.get("natures", ["physique", "morale"])
            self.profondeur += 1
            try:
                return self.personne("physique" if "physique" in natures else "morale")
            finally:
                self.profondeur -= 1
        coll = {"bien_immobilier": "biens", "vehicule": "vehicules", "compte_bancaire": "comptes"}[cible]
        prefixe = {"bien_immobilier": "B", "vehicule": "V", "compte_bancaire": "C"}[cible]
        ident = f"{prefixe}{len(self.dossier[coll]) + 1}"
        ent = self.plan["entites"].get(cible, {"champs": []})
        self.dossier[coll][ident] = {}
        self.dossier[coll][ident] = _sans_vides({x["id"]: self.valeur(x) for x in ent["champs"]})
        return ident

    def personne(self, nature):
        ident = f"P{len(self.dossier['personnes']) + 1}"
        ent = self.plan["entites"].get("personne", {"commun": [], "physique": [], "morale": []})
        p = {"nature": nature}
        self.dossier["personnes"][ident] = p
        for c in ent["commun"]:
            if c["id"] != "nature":
                p[c["id"]] = self.valeur(c)
        if nature == "physique":
            civ, nom, prenoms, usuel = PHYSIQUES[self.np % len(PHYSIQUES)]
            self.np += 1
            for c in ent["physique"]:
                if c["id"] in ("representants",):
                    continue
                p[c["id"]] = self.valeur(c)
            p.update({"civilite": civ, "nom": nom, "prenoms": prenoms, "prenom_usuel": usuel, "capacite": "majeur_capable"})
            for k in [k for k, v in p.items() if v is None]:
                del p[k]
        else:
            forme, denom = MORALES[self.nm % len(MORALES)]
            self.nm += 1
            for c in ent["morale"]:
                if c["id"] in ("representants_legaux",):
                    continue
                p[c["id"]] = self.valeur(c)
            p.update({"forme_juridique": forme, "denomination": denom})
            for k in [k for k, v in p.items() if v is None]:
                del p[k]
            p.pop("genre_grammatical", None)
            p.pop("forme_precisee", None)
            if any(c["id"] == "representants_legaux" for c in ent["morale"]):
                rep = self.personne("physique")
                p["representants_legaux"] = [{"personne": rep, "qualite": "président" if forme == "sas" else "gérant"}]
        return ident

    def construire(self, modele_id, pluriel=True, role_pluriel=None):
        roles = self.plan["roles"]
        cand_pluriel = role_pluriel or (next((r["cle"] for r in roles if r["cardinalite"].endswith("n") and "physique" in r["natures"]), None)
                                        if pluriel else None)
        cand_morale = next((r["cle"] for r in roles if "morale" in r["natures"] and r["cle"] != cand_pluriel), None)
        for r in roles:
            natures = r["natures"]
            if r["cle"] == cand_pluriel:
                ids = [self.personne("physique"), self.personne("physique")]
                if cand_morale is None and "morale" in natures:
                    ids[1] = self.personne("morale")
            elif r["cle"] == cand_morale:
                ids = [self.personne("morale")]
            else:
                ids = [self.personne("physique" if "physique" in natures else "morale")]
            self.dossier["roles"][r["cle"]] = ids
            if r.get("attributs"):
                self.dossier["attributs_roles"][r["cle"]] = {
                    pid: _sans_vides({a["id"]: self.valeur(a) for a in r["attributs"]}) for pid in ids}
        for m in self.plan["modules"]:
            self.dossier["modules"][m["id"]] = _sans_vides({c["id"]: self.valeur(c) for c in m["champs"]})
        self.dossier["local"][modele_id] = _sans_vides({l["id"]: self.valeur(l) for l in self.plan["locales"]})
        self.dossier["decisions"][modele_id] = {
            "options": {o["id"]: True for o in self.plan["options"]},
            "choix": {c["id"]: c["cas"][0]["id"] for c in self.plan["choix"]},
        }
        return self.dossier


def dossier_fictif(plan, modele_id, version_dictionnaire, types_extensions=None, pluriel=True, role_pluriel=None):
    d = Fabrique(plan).construire(modele_id, pluriel, role_pluriel)
    d["version_dictionnaire"] = version_dictionnaire
    d["types_extensions"] = dict(types_extensions or {})
    return d


def variantes(plan, modele_id, version_dictionnaire, types_extensions=None):
    """Jeu de dossiers couvrant les branches : base, options écartées, chaque cas de chaque choix, singulier."""
    base = dossier_fictif(plan, modele_id, version_dictionnaire, types_extensions)
    out = [("base", base)]
    if plan["options"]:
        d = copy.deepcopy(base)
        d["decisions"][modele_id]["options"] = {o["id"]: False for o in plan["options"]}
        out.append(("options-ecartees", d))
    for c in plan["choix"]:
        for cas in c["cas"][1:]:
            d = copy.deepcopy(base)
            d["decisions"][modele_id]["choix"][c["id"]] = cas["id"]
            out.append((f"choix-{c['id']}-{cas['id']}", d))
    out.append(("singulier", dossier_fictif(plan, modele_id, version_dictionnaire, types_extensions, pluriel=False)))
    premier = next((r["cle"] for r in plan["roles"] if r["cardinalite"].endswith("n") and "physique" in r["natures"]), None)
    for r in plan["roles"][:8]:      # chaque rôle pluriel éprouvé avec deux personnes physiques
        if r["cardinalite"].endswith("n") and "physique" in r["natures"] and r["cle"] != premier:
            out.append((f"pluriel-{r['cle']}", dossier_fictif(plan, modele_id, version_dictionnaire, types_extensions,
                                                             role_pluriel=r["cle"])))
    vides = copy.deepcopy(base)
    for m in vides["modules"].values():
        for k, v in list(m.items()):
            if isinstance(v, list):
                m[k] = []
    out.append(("listes-vides", vides))
    return out[:20]
