# -*- coding: utf-8 -*-
"""Dictionnaire effectif d'un modèle : dictionnaire commun + extensions déclarées dans le manifeste.

Le dictionnaire commun n'est qu'une trame. Le manifeste peut :
  champs          ajouter des champs à une entité, à un module, ou à un groupe ou une liste existants
  modules         créer des modules propres au modèle (avec rôles et champs)
  roles           ajouter des rôles à un module existant
  attributs_roles attacher des champs à une personne en tant qu'elle tient un rôle (parts cédées…)
  libelles        modifier le libellé ou l'aide d'un champ, ou les libellés d'un rôle
Rien n'est supprimé : le formulaire n'affiche que ce que le modèle utilise, et la suppression
empêcherait d'autres modèles de relire les mêmes données.
"""
import copy
import difflib
import re

from schema import DERIVES_PERSONNE

RE_ID = re.compile(r"[a-z][a-z0-9_]*")
TYPES_ELEMENT = {"texte", "texte_long", "entier", "decimal", "montant", "pourcentage", "date", "heure", "duree",
                 "booleen", "telephone", "courriel"}
CLES_LIBELLES_ROLE = {"ms", "fs", "mp", "fp"}


def _tous_les_ids(d):
    ids = set()

    def parcourir(champs):
        for c in champs:
            ids.add(c["id"])
            parcourir(c.get("champs", []))
    for e in d["entites"].values():
        for k in ("champs", "commun", "physique", "morale"):
            parcourir(e.get(k, []))
    for m in d["modules"]:
        ids.add(m["id"])
        parcourir(m["champs"])
        ids.update(r["id"] for r in m["roles"])
    return ids


class Fusion:
    def __init__(self, base, manifeste):
        self.d = copy.deepcopy(base)
        self.ext = manifeste.get("extensions", {}) or {}
        self.erreurs, self.avertissements = [], []
        self.types = {}            # chemin -> type, enregistré dans chaque dossier
        self.ids_communs = _tous_les_ids(base)
        self.modules = {m["id"]: m for m in self.d["modules"]}

    # ------------------------------------------------------------ contrôle d'une définition
    def valider_champ(self, c, lieu):
        ok = True
        if not isinstance(c, dict) or not RE_ID.fullmatch(str(c.get("id", ""))):
            self.erreurs.append(f"{lieu} — identifiant absent ou non conforme (minuscules, chiffres, « _ », sans accent) : {c!r:.80}")
            return False
        lieu = f"{lieu}.{c['id']}"
        if not c.get("libelle"):
            self.erreurs.append(f"{lieu} — libellé manquant")
            ok = False
        t = c.get("type")
        if t not in self.d["types"]:
            self.erreurs.append(f"{lieu} — type inconnu « {t} » ; types : {', '.join(self.d['types'])}")
            return False
        if t == "choix":
            vals = c.get("valeurs") or []
            if not vals or not all(isinstance(v, dict) and RE_ID.fullmatch(str(v.get("id", ""))) and v.get("libelle") for v in vals):
                self.erreurs.append(f"{lieu} — un choix exige des valeurs {{id, libelle}} aux identifiants conformes")
                ok = False
        if t == "reference":
            if c.get("cible") not in self.d["entites"] or c.get("cible") == "adresse":
                self.erreurs.append(f"{lieu} — cible de référence inconnue : {c.get('cible')}")
                ok = False
            if c.get("natures") and not set(c["natures"]) <= {"physique", "morale"}:
                self.erreurs.append(f"{lieu} — natures admises : physique, morale")
                ok = False
        if t == "identifiant" and c.get("validation") and c["validation"] not in self.d["validations"]:
            self.erreurs.append(f"{lieu} — validation inconnue : {c['validation']}")
            ok = False
        if t == "groupe" or (t == "liste" and "champs" in c):
            sous = c.get("champs") or []
            if not sous:
                self.erreurs.append(f"{lieu} — un {t} exige des champs")
                ok = False
            vus = set()
            for s in sous:
                if s.get("id") in vus:
                    self.erreurs.append(f"{lieu} — champ « {s.get('id')} » en double")
                    ok = False
                vus.add(s.get("id"))
                ok = self.valider_champ(s, lieu) and ok
        elif t == "liste" and c.get("element") not in TYPES_ELEMENT:
            self.erreurs.append(f"{lieu} — une liste exige des « champs » ou un « element » simple ({', '.join(sorted(TYPES_ELEMENT))})")
            ok = False
        return ok

    def _marquer(self, c):
        c["extension"] = True
        for s in c.get("champs", []):
            self._marquer(s)

    def _voisins(self, ident, lieu):
        if ident in self.ids_communs:
            return
        proches = difflib.get_close_matches(ident, self.ids_communs, n=3, cutoff=0.8)
        if proches:
            self.avertissements.append(f"extension « {lieu} » : nom proche de {', '.join(proches)} dans le dictionnaire "
                                       f"commun ; si la notion est la même, utiliser l'entrée existante pour préserver "
                                       f"la réutilisation des dossiers")

    # ------------------------------------------------------------ cibles
    def _liste_cible(self, cible):
        """Liste de champs visée par 'personne', 'personne.physique', 'bien_immobilier.cadastre', 'bail.loyer'…"""
        if cible in ("personne", "personne.commun"):
            return self.d["entites"]["personne"]["commun"], "personne"
        if cible in ("personne.physique", "personne.morale"):
            return self.d["entites"]["personne"][cible.split(".")[1]], cible
        tete, *reste = cible.split(".")
        if tete in self.d["entites"] and tete not in ("personne", "adresse"):
            champs = self.d["entites"][tete]["champs"]
        elif tete in self.modules:
            champs = self.modules[tete]["champs"]
        else:
            raise KeyError(f"cible inconnue « {cible} »")
        for seg in reste:
            c = next((x for x in champs if x["id"] == seg), None)
            if c is None or "champs" not in c:
                raise KeyError(f"« {seg} » n'est ni un groupe ni une liste à champs dans « {cible} »")
            champs = c["champs"]
        return champs, cible

    def _noms_personne(self):
        p = self.d["entites"]["personne"]
        return {c["id"] for c in p["commun"] + p["physique"] + p["morale"]} | set(DERIVES_PERSONNE)

    # ------------------------------------------------------------ opérations
    def ajouter_champs(self):
        for cible, defs in (self.ext.get("champs") or {}).items():
            try:
                champs, nom = self._liste_cible(cible)
            except KeyError as e:
                self.erreurs.append(f"extensions.champs — {e.args[0]}")
                continue
            existants = self._noms_personne() if nom.startswith("personne") else {c["id"] for c in champs}
            if not nom.startswith("personne") and cible in self.modules:
                existants |= {r["id"] for r in self.modules[cible]["roles"]}
            for c in defs:
                lieu = f"extensions.champs.{cible}"
                if not self.valider_champ(c, lieu):
                    continue
                if c["id"] in existants:
                    self.erreurs.append(f"{lieu}.{c['id']} — existe déjà : utiliser l'entrée existante")
                    continue
                self._voisins(c["id"], f"{cible}.{c['id']}")
                c = copy.deepcopy(c)
                self._marquer(c)
                champs.append(c)
                existants.add(c["id"])
                self.types[f"{cible}.{c['id']}"] = c["type"]

    def _valider_role(self, r, lieu):
        if not isinstance(r, dict) or not RE_ID.fullmatch(str(r.get("id", ""))):
            self.erreurs.append(f"{lieu} — identifiant de rôle non conforme")
            return False
        lib = r.get("libelles") or {}
        if set(lib) != CLES_LIBELLES_ROLE or not all(lib.values()):
            self.erreurs.append(f"{lieu}.{r['id']} — libellés ms, fs, mp, fp requis (masculin/féminin, singulier/pluriel)")
            return False
        if not re.fullmatch(r"[01]|[01]\.\.(?:[1-9]|n)", str(r.get("cardinalite", ""))):
            self.erreurs.append(f"{lieu}.{r['id']} — cardinalité attendue : 1, 0..1, 1..n, 0..n")
            return False
        if not r.get("natures") or not set(r["natures"]) <= {"physique", "morale"}:
            self.erreurs.append(f"{lieu}.{r['id']} — natures attendues : physique, morale")
            return False
        return True

    def ajouter_modules(self):
        for m in self.ext.get("modules") or []:
            lieu = f"extensions.modules.{m.get('id')}"
            if not RE_ID.fullmatch(str(m.get("id", ""))) or not m.get("libelle"):
                self.erreurs.append(f"{lieu} — identifiant conforme et libellé requis")
                continue
            if m["id"] in self.modules or m["id"] in ("local", "calcul", "option", "choix", "acte"):
                self.erreurs.append(f"{lieu} — ce module existe déjà ou ce nom est réservé : y ajouter des champs plutôt")
                continue
            self._voisins(m["id"], m["id"])
            mod = {"id": m["id"], "libelle": m["libelle"], "description": m.get("description", ""),
                   "roles": [], "champs": [], "extension": True}
            for r in m.get("roles", []):
                if self._valider_role(r, lieu):
                    mod["roles"].append({**copy.deepcopy(r), "extension": True})
            ids = {r["id"] for r in mod["roles"]}
            for c in m.get("champs", []):
                if self.valider_champ(c, lieu):
                    if c["id"] in ids:
                        self.erreurs.append(f"{lieu}.{c['id']} — même nom qu'un rôle ou qu'un autre champ")
                        continue
                    c = copy.deepcopy(c)
                    self._marquer(c)
                    mod["champs"].append(c)
                    ids.add(c["id"])
                    self.types[f"{m['id']}.{c['id']}"] = c["type"]
            self.d["modules"].append(mod)
            self.modules[mod["id"]] = mod

    def ajouter_roles(self):
        for mid, roles in (self.ext.get("roles") or {}).items():
            if mid not in self.modules:
                self.erreurs.append(f"extensions.roles — module inconnu « {mid} »")
                continue
            mod = self.modules[mid]
            pris = {r["id"] for r in mod["roles"]} | {c["id"] for c in mod["champs"]}
            for r in roles:
                if not self._valider_role(r, f"extensions.roles.{mid}"):
                    continue
                if r["id"] in pris:
                    self.erreurs.append(f"extensions.roles.{mid}.{r['id']} — existe déjà")
                    continue
                self._voisins(r["id"], f"{mid}.{r['id']}")
                mod["roles"].append({**copy.deepcopy(r), "extension": True})
                pris.add(r["id"])

    def ajouter_attributs(self):
        noms_personne = self._noms_personne()
        for cle, defs in (self.ext.get("attributs_roles") or {}).items():
            mid, _, rid = cle.partition(".")
            role = next((r for r in self.modules.get(mid, {}).get("roles", []) if r["id"] == rid), None)
            if role is None:
                self.erreurs.append(f"extensions.attributs_roles — rôle inconnu « {cle} »")
                continue
            attrs = role.setdefault("attributs", [])
            for c in defs:
                lieu = f"extensions.attributs_roles.{cle}"
                if not self.valider_champ(c, lieu):
                    continue
                if c["id"] in noms_personne or any(a["id"] == c["id"] for a in attrs):
                    self.erreurs.append(f"{lieu}.{c['id']} — nom déjà pris par un champ de personne ou un autre attribut")
                    continue
                c = copy.deepcopy(c)
                self._marquer(c)
                attrs.append(c)
                self.types[f"{cle}.{c['id']}"] = c["type"]

    def appliquer_libelles(self):
        for chemin, sur in (self.ext.get("libelles") or {}).items():
            tete, *reste = chemin.split(".")
            cible = None
            if tete == "personne" and len(reste) == 1:
                p = self.d["entites"]["personne"]
                cible = next((c for c in p["commun"] + p["physique"] + p["morale"] if c["id"] == reste[0]), None)
            elif tete in self.modules and len(reste) == 1 and any(r["id"] == reste[0] for r in self.modules[tete]["roles"]):
                role = next(r for r in self.modules[tete]["roles"] if r["id"] == reste[0])
                lib = sur.get("libelles", {})
                if not set(lib) <= CLES_LIBELLES_ROLE:
                    self.erreurs.append(f"extensions.libelles.{chemin} — clés admises pour un rôle : ms, fs, mp, fp")
                    continue
                role["libelles"] = {**role["libelles"], **lib}
                continue
            else:
                try:
                    champs, _ = self._liste_cible(".".join([tete] + reste[:-1])) if reste else (None, None)
                    cible = next((c for c in champs if c["id"] == reste[-1]), None) if champs else None
                except KeyError:
                    cible = None
            if cible is None:
                self.erreurs.append(f"extensions.libelles — chemin inconnu « {chemin} »")
                continue
            for k in ("libelle", "aide"):
                if k in sur:
                    cible[k] = sur[k]

    def executer(self):
        inconnues = set(self.ext) - {"champs", "modules", "roles", "attributs_roles", "libelles"}
        if inconnues:
            self.erreurs.append(f"extensions — rubriques inconnues : {', '.join(sorted(inconnues))}")
        self.ajouter_modules()
        self.ajouter_roles()
        self.ajouter_champs()
        self.ajouter_attributs()
        self.appliquer_libelles()
        for m in self.d["modules"]:
            for r in m["roles"]:
                r["_cle"] = f"{m['id']}.{r['id']}"
        self.d["types_extensions"] = self.types
        return self.d
