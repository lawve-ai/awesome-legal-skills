# -*- coding: utf-8 -*-
"""Compilation d'un modèle balisé : arbre d'exécution, plan du formulaire, rapport de contrôle."""
import base64
import copy
import json
import re
import zipfile
import zlib

from syntaxe import (ErreurSyntaxe, RE_BALISE, analyser_directive, analyser_valeur, analyser_expression,
                     nature_directive, STRUCTURE_OUVRANTE, FERMETURE_DE)
from documents import ecrire
from schema import Schema, FONCTIONS, Resolu
from extensions import Fusion
from documents import (ouvrir, reperer_balises, regrouper, poser_marqueur, remonter, nouveau_marqueur,
                       texte_paragraphe, lire, SEP, ErreurDocument)

def _entree_zip(nom, donnees, compresser=True):
    if compresser:
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        comp = c.compress(donnees) + c.flush()
        return {"nom": nom, "methode": 8, "crc": zlib.crc32(donnees) & 0xFFFFFFFF, "taille": len(donnees),
                "b64": base64.b64encode(comp).decode("ascii")}
    return {"nom": nom, "methode": 0, "crc": zlib.crc32(donnees) & 0xFFFFFFFF, "taille": len(donnees),
            "b64": base64.b64encode(donnees).decode("ascii")}


RE_MARQUEUR = re.compile(r'<tb:m\b[^>]*?\bn="(\d+)"[^>]*/>')
LIBELLES_PARTIES = {"word/document.xml": "corps", "content.xml": "corps", "styles.xml": "en-têtes et pieds de page",
                    "word/footnotes.xml": "notes de bas de page", "word/endnotes.xml": "notes de fin"}


def libelle_partie(nom):
    if nom in LIBELLES_PARTIES:
        return LIBELLES_PARTIES[nom]
    if "header" in nom:
        return "en-tête"
    if "footer" in nom:
        return "pied de page"
    return nom


class Compilation:
    def __init__(self, chemin_modele, dictionnaire, manifeste):
        self.fmt = ouvrir(chemin_modele)
        self.d = dictionnaire
        self.m = manifeste
        self.erreurs, self.avertissements = [], []
        self.meta = {}
        self.n = 0
        self.extensions = {}
        self.inventaire = {"valeurs": {}, "conditions": [], "boucles": [], "compteurs": set(), "ancres": set(),
                           "renvois": set()}

    # ------------------------------------------------------------ pré-passage
    def prepasse(self):
        """Recense options et choix (utilisables dans les conditions avant leur définition)."""
        options, choix = {}, {}
        for partie in self.fmt.parties():
            racine = self.fmt.arbre(partie)
            pile_choix = []
            for p in self.fmt.paragraphes(racine):
                texte = texte_paragraphe(self.fmt, p)
                for m in RE_BALISE.finditer(texte):
                    if m.group(2) is None:
                        continue
                    try:
                        d = analyser_directive(m.group(2))
                    except ErreurSyntaxe:
                        continue      # signalée au passage principal
                    if d["d"] == "OPTION":
                        if d["libelle"] or d["id"] not in options:
                            options[d["id"]] = d["libelle"] or options.get(d["id"]) or d["id"]
                    elif d["d"] == "CHOIX":
                        c = choix.setdefault(d["id"], {"libelle": d["id"], "cas": {}})
                        if d["libelle"]:
                            c["libelle"] = d["libelle"]
                        pile_choix.append(d["id"])
                    elif d["d"] == "CAS" and pile_choix:
                        cas = choix[pile_choix[-1]]["cas"]
                        if d["libelle"] or d["id"] not in cas:
                            cas[d["id"]] = d["libelle"] or cas.get(d["id"]) or d["id"]
                    elif d["d"] == "FIN CHOIX" and pile_choix:
                        pile_choix.pop()
        return {"options": options, "choix": choix}

    # ------------------------------------------------------------ marquage d'un paragraphe
    def _lieu(self, partie, idx, texte):
        extrait = texte.replace(SEP, " ").strip()
        extrait = (extrait[:70] + "…") if len(extrait) > 70 else extrait
        return f"{libelle_partie(partie)}, paragraphe {idx + 1} : « {extrait} »"

    def _nouveau(self, info):
        self.n += 1
        self.meta[self.n] = info
        return self.n

    def _texte_ligne(self, tr):
        return "".join(texte_paragraphe(self.fmt, pp) for pp in self.fmt.paragraphes(tr)).strip()

    def marquer_paragraphe(self, partie, idx, p):
        fmt = self.fmt
        try:
            segs, texte, balises = reperer_balises(fmt, p)
        except ErreurDocument as e:
            self.erreurs.append(f"{self._lieu(partie, idx, texte_paragraphe(fmt, p))} — {e}")
            return
        if not balises:
            return
        lieu = self._lieu(partie, idx, texte)
        hors = texte
        for a, b, brut, _ in reversed(balises):
            hors = hors[:a] + hors[b:]
        hors = hors.replace(SEP, " ").strip()

        # 1. balise de structure seule dans son paragraphe -> niveau bloc (ou ligne de tableau)
        if len(balises) == 1 and not balises[0][3] and not hors:
            brut = balises[0][2]
            if fmt.a_saut_de_section(p):
                self.erreurs.append(f"{lieu} — ce paragraphe porte un saut de section : placer la balise "
                                    f"dans un autre paragraphe")
                return
            parent = p.getparent()
            tr, tbl = fmt.ligne_et_tableau(p)
            if tr is not None and self._texte_ligne(tr) == brut:
                n = self._nouveau({"genre": "dir", "brut": brut[2:-2], "niveau": "ligne", "conteneur": tbl,
                                   "lieu": lieu})
                tbl.replace(tr, nouveau_marqueur(n))
            else:
                n = self._nouveau({"genre": "dir", "brut": brut[2:-2], "niveau": "bloc", "conteneur": parent,
                                   "lieu": lieu})
                parent.replace(p, nouveau_marqueur(n))
            return

        # 2. paragraphe entièrement enveloppé par une structure -> la structure passe au niveau bloc
        if not balises[0][3] and not balises[-1][3] and len(balises) >= 2:
            a0, b0 = balises[0][0], balises[-1][1]
            avant, apres = texte[:a0].replace(SEP, " ").strip(), texte[b0:].replace(SEP, " ").strip()
            nat0 = nature_directive(balises[0][2][2:-2])
            if not avant and not apres and nat0 in STRUCTURE_OUVRANTE and self._ferme_a_la_fin(balises):
                if fmt.a_saut_de_section(p):
                    self.erreurs.append(f"{lieu} — ce paragraphe conditionnel porte un saut de section : le déplacer")
                    return
                parent = p.getparent()
                for (a, b, brut, _) in (balises[-1], balises[0]):
                    regrouper(segs, a, b)
                for (a, b, brut, _) in (balises[-1], balises[0]):
                    seg, dec = self._situer(fmt.segments(p), a)
                    t = lire(seg)
                    ecrire(seg, t[:dec] + t[dec + (b - a):])
                    segs = fmt.segments(p)
                i = parent.index(p)
                n1 = self._nouveau({"genre": "dir", "brut": balises[0][2][2:-2], "niveau": "bloc",
                                    "conteneur": parent, "lieu": lieu})
                n2 = self._nouveau({"genre": "dir", "brut": balises[-1][2][2:-2], "niveau": "bloc",
                                    "conteneur": parent, "lieu": lieu})
                m2 = nouveau_marqueur(n2)
                m2.tail = p.tail
                p.tail = None
                parent.insert(i + 1, m2)
                parent.insert(i, nouveau_marqueur(n1))
                # les balises restantes sont traitées en ligne
                self.marquer_paragraphe(partie, idx, p)
                return

        # 3. balises en ligne
        for a, b, _, _ in balises:
            regrouper(segs, a, b)
        segs = fmt.segments(p)
        emplacements = []
        for a, b, brut, est_valeur in balises:
            seg, dec = self._situer(segs, a)
            emplacements.append((seg, dec, b - a, brut, est_valeur))
        marqueurs = []
        for seg, dec, longueur, brut, est_valeur in reversed(emplacements):
            info = {"genre": "val" if est_valeur else "dir", "brut": brut[2:-2], "niveau": "en_ligne",
                    "conteneur": p, "lieu": lieu}
            n = self._nouveau(info)
            marqueurs.append((poser_marqueur(seg, dec, longueur, n), info))
        for m, info in marqueurs:
            try:
                chaine = remonter(fmt, m, p)
            except ErreurDocument as e:
                self.erreurs.append(f"{lieu} — {e}")
                continue
            if info["genre"] == "val":
                avant, apres = fmt.enveloppe(chaine)
                info["av"], info["ap"] = avant, apres
                info["sp"] = fmt.saut_paragraphe(p)

    @staticmethod
    def _situer(segs, position):
        pos = 0
        for s in segs:
            longueur = 1 if s is None else len(lire(s))
            if s is not None and pos <= position < pos + longueur:
                return s, position - pos
            pos += longueur
        raise ErreurDocument("position de balise introuvable (document atypique)")

    @staticmethod
    def _ferme_a_la_fin(balises):
        pile = []
        for k, (_, _, brut, est_valeur) in enumerate(balises):
            if est_valeur:
                continue
            nat = nature_directive(brut[2:-2])
            if nat in ("SINON SI", "SINON", "CAS") and len(pile) == 1:
                return False      # SINON ou CAS de la structure enveloppante : la structure reste en ligne
            if nat in STRUCTURE_OUVRANTE:
                pile.append(nat)
            elif nat.startswith("FIN "):
                if not pile or FERMETURE_DE[pile[-1]] != nat:
                    return False
                pile.pop()
                if not pile:
                    return k == len(balises) - 1
        return False

    # ------------------------------------------------------------ arbre
    def construire_arbre(self, partie, xml, schema):
        morceaux = RE_MARQUEUR.split(xml)
        racine = {"t": "racine", "n": []}
        pile = [{"noeud": racine, "corps": racine["n"], "info": None, "portees": {}}]

        def ajouter_xml(s):
            if s:
                c = pile[-1]["corps"]
                if c and c[-1]["t"] == "x":
                    c[-1]["s"] += s
                else:
                    c.append({"t": "x", "s": s})

        for k, morceau in enumerate(morceaux):
            if k % 2 == 0:
                ajouter_xml(morceau)
                continue
            info = self.meta[int(morceau)]
            lieu = info["lieu"]
            portees = pile[-1]["portees"]
            try:
                if info["genre"] == "val":
                    pile[-1]["corps"].append(self._noeud_valeur(info, schema, portees))
                    continue
                d = analyser_directive(info["brut"])
                cadre = pile[-1]
                if d["d"] == "NOTE":
                    continue
                if d["d"] in ("SI", "OPTION", "CHOIX", "POUR"):
                    noeud, corps, nouvelles = self._ouvrir(d, schema, portees, lieu)
                    cadre["corps"].append(noeud)
                    pile.append({"noeud": noeud, "corps": corps, "info": info, "d": d["d"],
                                 "portees": {**portees, **nouvelles}})
                    continue
                if len(pile) == 1:
                    raise ErreurSyntaxe(f"« [[{info['brut']}]] » sans structure ouverte")
                ouvert = pile[-1]
                if ouvert["info"]["niveau"] != info["niveau"] or ouvert["info"]["conteneur"] is not info["conteneur"]:
                    raise ErreurSyntaxe(f"« [[{info['brut']}]] » ne se situe pas au même niveau que "
                                        f"« [[{ouvert['info']['brut']}]] » ({ouvert['info']['lieu']}) : une structure "
                                        f"ouverte dans un paragraphe se ferme dans le même paragraphe ; une structure "
                                        f"posée sur des paragraphes entiers se ferme sur un paragraphe entier du même "
                                        f"emplacement (corps, cellule) ; une structure posée sur des lignes de tableau "
                                        f"se ferme sur une ligne du même tableau")
                if d["d"] in ("SINON SI", "SINON"):
                    if ouvert["d"] != "SI" or ouvert["noeud"].get("s") is not None:
                        raise ErreurSyntaxe(f"« [[{d['d']}]] » hors d'un SI, ou après SINON")
                    if d["d"] == "SINON SI":
                        cond = self._valider_expr(d["cond"], schema, portees, lieu)
                        ouvert["noeud"]["b"].append({"c": cond, "n": []})
                        ouvert["corps"] = ouvert["noeud"]["b"][-1]["n"]
                    else:
                        ouvert["noeud"]["s"] = []
                        ouvert["corps"] = ouvert["noeud"]["s"]
                    continue
                if d["d"] == "CAS":
                    if ouvert["d"] != "CHOIX":
                        raise ErreurSyntaxe("« [[CAS]] » hors d'un CHOIX")
                    noeud = ouvert["noeud"]
                    if noeud.get("_avant") is not None:
                        if re.search(r">[^<\s]+<|\{\{", "".join(x.get("s", "") for x in noeud["_avant"])) or \
                                any(x["t"] != "x" for x in noeud["_avant"]):
                            raise ErreurSyntaxe(f"du texte figure entre [[CHOIX {noeud['id']}]] et le premier CAS")
                        noeud["_avant"] = None
                    if d["id"] in noeud["cas"]:
                        raise ErreurSyntaxe(f"CAS « {d['id']} » répété dans le même CHOIX")
                    noeud["cas"][d["id"]] = []
                    ouvert["corps"] = noeud["cas"][d["id"]]
                    continue
                attendu = FERMETURE_DE[ouvert["d"]]
                if d["d"] != attendu:
                    raise ErreurSyntaxe(f"« [[{d['d']}]] » rencontré alors que « [[{attendu}]] » était attendu "
                                        f"pour fermer « [[{ouvert['info']['brut']}]] » ({ouvert['info']['lieu']})")
                if ouvert["d"] == "CHOIX":
                    if not ouvert["noeud"]["cas"]:
                        raise ErreurSyntaxe(f"CHOIX « {ouvert['noeud']['id']} » sans aucun CAS")
                    ouvert["noeud"].pop("_avant", None)
                pile.pop()
            except (ErreurSyntaxe, ErreurDocument) as e:
                self.erreurs.append(f"{lieu} — {e}")
        for cadre in pile[1:]:
            self.erreurs.append(f"{cadre['info']['lieu']} — « [[{cadre['info']['brut']}]] » n'est jamais fermé "
                                f"(« [[{FERMETURE_DE[cadre['d']]}]] » attendu)")
        return racine["n"]

    def _ouvrir(self, d, schema, portees, lieu):
        if d["d"] == "SI":
            cond = self._valider_expr(d["cond"], schema, portees, lieu)
            self.inventaire["conditions"].append({"lieu": lieu})
            n = {"t": "si", "b": [{"c": cond, "n": []}], "s": None}
            return n, n["b"][0]["n"], {}
        if d["d"] == "OPTION":
            n = {"t": "opt", "id": d["id"], "n": []}
            return n, n["n"], {}
        if d["d"] == "CHOIX":
            n = {"t": "ch", "id": d["id"], "cas": {}, "_avant": []}
            return n, n["_avant"], {}
        if d["d"] == "POUR":
            if d["var"] in portees or d["var"] in schema.modules or d["var"] in ("local", "calcul", "option", "choix"):
                raise ErreurSyntaxe(f"nom de variable de boucle déjà utilisé : « {d['var']} »")
            res = schema.resoudre(d["liste"], portees)
            if not res.multiple:
                raise ErreurSyntaxe(f"« {'.'.join(d['liste'])} » n'est pas une liste ni un rôle : rien à répéter")
            elem, rec = schema.element_de(res, ".".join(d["liste"]))
            self.inventaire["boucles"].append({"liste": ".".join(d["liste"]), "lieu": lieu})
            n = {"t": "pour", "v": d["var"], "l": d["liste"], "n": []}
            return n, n["n"], {d["var"]: (elem, rec)}
        raise ErreurSyntaxe(f"structure inattendue « {d['d']} »")

    def _noeud_valeur(self, info, schema, portees):
        v = analyser_valeur(info["brut"])
        commun = {"av": info["av"], "ap": info["ap"], "sp": info["sp"], "r": v["rendus"]}
        if v["v"] == "compteur":
            self.inventaire["compteurs"].add(v["nom"])
            if v["ancre"]:
                if v["ancre"] in self.inventaire["ancres"]:
                    raise ErreurSyntaxe(f"ancre « {v['ancre']} » définie deux fois")
                self.inventaire["ancres"].add(v["ancre"])
            self._controler_rendus_compteur(v["rendus"], info["lieu"])
            return {"t": "cpt", "nom": v["nom"], "ancre": v["ancre"], **commun}
        if v["v"] == "renvoi":
            self.inventaire["renvois"].add(v["ancre"])
            self._controler_rendus_compteur(v["rendus"], info["lieu"])
            return {"t": "ren", "ancre": v["ancre"], **commun}
        res = schema.resoudre(v["p"], portees)
        schema.controler_rendus(res, v["rendus"], info["lieu"])
        cle = ".".join(v["p"])
        self.inventaire["valeurs"].setdefault(cle, 0)
        self.inventaire["valeurs"][cle] += 1
        return {"t": "v", "p": v["p"], **commun}

    @staticmethod
    def _controler_rendus_compteur(rendus, lieu):
        from schema import RENDUS_TYPE, TRANSFORMATIONS
        for nom, _ in rendus:
            if nom not in RENDUS_TYPE["compteur"] | TRANSFORMATIONS:
                raise ErreurSyntaxe(f"rendu « {nom} » inapplicable à un compteur ; admis : "
                                    + ", ".join(sorted(RENDUS_TYPE["compteur"])))

    def _valider_expr(self, e, schema, portees, lieu):
        """Contrôle les chemins et fonctions ; convertit les identifiants nus en littéraux."""
        k = e["k"]
        if k in ("num", "str", "bool"):
            return e
        if k == "chemin":
            res = schema.resoudre(e["p"], portees)
            return e
        if k in ("et", "ou"):
            return {**e, "a": self._valider_expr(e["a"], schema, portees, lieu),
                    "b": self._valider_expr(e["b"], schema, portees, lieu)}
        if k == "non":
            return {**e, "a": self._valider_expr(e["a"], schema, portees, lieu)}
        if k == "est":
            return {**e, "a": self._valider_expr(e["a"], schema, portees, lieu)}
        if k == "fn":
            if e["nom"] not in FONCTIONS:
                raise ErreurSyntaxe(f"fonction inconnue « {e['nom']} » ; fonctions : " + ", ".join(sorted(FONCTIONS)))
            mini, maxi = FONCTIONS[e["nom"]]
            if not mini <= len(e["args"]) <= maxi:
                raise ErreurSyntaxe(f"« {e['nom']} » attend {mini}" + (f" à {maxi}" if maxi != mini else "")
                                    + f" argument(s), {len(e['args'])} fourni(s)")
            if e["nom"] == "table":
                if e["args"][0]["k"] != "str" or e["args"][0]["v"] not in self.m.get("tables", {}):
                    raise ErreurSyntaxe("table(nom, clé) : le nom doit désigner une table déclarée dans le manifeste")
            return {**e, "args": [self._valider_expr(a, schema, portees, lieu) for a in e["args"]]}
        if k == "op":
            a, b = e["a"], e["b"]
            if e["op"] in ("=", "!="):
                for x, y in ((a, b), (b, a)):
                    if y["k"] == "chemin" and len(y["p"]) == 1 and y["p"][0] not in portees and \
                            y["p"][0] not in schema.modules and y["p"][0] not in ("local", "calcul", "option", "choix"):
                        valeurs = self._valeurs_possibles(x, schema, portees)
                        if valeurs is not None and y["p"][0] not in valeurs:
                            raise ErreurSyntaxe(f"valeur « {y['p'][0]} » inconnue ; valeurs possibles : "
                                                + ", ".join(valeurs))
                        y = {"k": "str", "v": y["p"][0]}
                        if x is a:
                            b = y
                        else:
                            a = y
            return {**e, "a": self._valider_expr(a, schema, portees, lieu),
                    "b": self._valider_expr(b, schema, portees, lieu)}
        raise ErreurSyntaxe(f"expression inattendue ({k})")

    @staticmethod
    def _valeurs_possibles(e, schema, portees):
        if e["k"] != "chemin":
            return None
        try:
            res = schema.resoudre(e["p"], portees)
        except ErreurSyntaxe:
            return None
        if res.type == "choix" and res.definition:
            return [v["id"] for v in res.definition["valeurs"]]
        if res.type == "choix_document":
            return list(res.definition["cas"])
        return None

    # ------------------------------------------------------------ manifeste
    def valider_manifeste(self, schema):
        m = self.m
        types = set(self.d["types"])
        for loc in m.get("locales", []):
            if not re.fullmatch(r"[a-z][a-z0-9_]*", loc.get("id", "")):
                self.erreurs.append(f"manifeste — identifiant de variable locale non conforme : {loc.get('id')}")
            if loc.get("type") not in types or loc.get("type") in ("groupe", "reference", "liste"):
                self.erreurs.append(f"manifeste — type inadmis pour la variable locale {loc.get('id')} : {loc.get('type')}")
            if loc.get("type") == "choix" and not loc.get("valeurs"):
                self.erreurs.append(f"manifeste — la variable locale {loc['id']} de type choix n'a pas de valeurs")
        calculs = {}
        for c in m.get("calculs", []):
            lieu = f"manifeste, calcul {c.get('id')}"
            for cle in ("id", "libelle", "type", "expression", "explication"):
                if not c.get(cle):
                    self.erreurs.append(f"{lieu} — champ « {cle} » manquant (l'explication est obligatoire : elle est "
                                        f"affichée à l'utilisateur comme note de calcul)")
            if c.get("type") not in types:
                self.erreurs.append(f"{lieu} — type inconnu : {c.get('type')}")
            try:
                portees = {}
                if c.get("element_de"):
                    # calcul de ligne : « element » désigne l'élément courant de la liste ou du rôle
                    from syntaxe import segments
                    res = schema.resoudre(segments(c["element_de"]), {})
                    if not res.multiple:
                        raise ErreurSyntaxe(f"element_de « {c['element_de']} » n'est ni une liste ni un rôle")
                    portees = {"element": schema.element_de(res, c["element_de"])}
                calculs[c["id"]] = self._valider_expr(analyser_expression(c["expression"]), schema, portees, lieu)
            except (ErreurSyntaxe, KeyError) as e:
                self.erreurs.append(f"{lieu} — {e}")
        controles = []
        for c in m.get("controles", []):
            lieu = f"manifeste, contrôle « {c.get('message', '?')} »"
            try:
                controles.append({"c": self._valider_expr(analyser_expression(c["expression"]), schema, {}, lieu),
                                  "message": c["message"], "bloquant": bool(c.get("bloquant", True))})
            except (ErreurSyntaxe, KeyError) as e:
                self.erreurs.append(f"{lieu} — {e}")
        for nom, t in m.get("tables", {}).items():
            for cle in ("libelle", "source", "date_gel", "valeurs"):
                if cle not in t:
                    self.erreurs.append(f"manifeste, table {nom} — champ « {cle} » manquant")
        return calculs, controles

    # ------------------------------------------------------------ ensemble
    def executer(self):
        fmt = self.fmt
        if fmt.suivi_modifications():
            self.erreurs.append("le document contient des modifications suivies : les accepter ou les refuser "
                                "toutes avant le balisage")
            return None
        if fmt.commentaires():
            self.avertissements.append("le document contient des commentaires : ils seront reproduits dans chaque "
                                       "document généré ; les supprimer s'ils ne doivent pas y figurer")
        fusion = Fusion(self.d, self.m)
        self.d = fusion.executer()
        self.erreurs += fusion.erreurs
        self.avertissements += fusion.avertissements
        self.extensions = fusion.types
        decisions = self.prepasse()
        schema = Schema(self.d, self.m, decisions)
        calculs, controles = self.valider_manifeste(schema)
        parties_ir = []
        for partie in fmt.parties():
            racine = fmt.arbre(partie)
            for idx, p in enumerate(list(fmt.paragraphes(racine))):
                if p.getparent() is None or p.getroottree().getroot() is not racine:
                    continue   # paragraphe déjà retiré avec sa ligne
                self.marquer_paragraphe(partie, idx, p)
            xml = fmt.serialiser(partie).decode("utf-8")
            if "<tb:m" not in xml:
                continue
            parties_ir.append({"nom": partie, "arbre": self.construire_arbre(partie, xml, schema)})
        for r in self.inventaire["renvois"] - self.inventaire["ancres"]:
            self.erreurs.append(f"renvoi vers l'ancre « {r} », qui n'est définie par aucun compteur")
        brut = []
        traitees = {x["nom"] for x in parties_ir}
        with open(fmt.chemin, "rb") as flux:
            for info in fmt.zip.infolist():
                if info.filename in traitees:
                    brut.append({"nom": info.filename, "gabarit": True})
                    continue
                donnees = fmt.zip.read(info.filename)
                anonymise = self._anonymiser_metadonnees(info.filename, donnees)
                if anonymise != donnees or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) \
                        or info.filename == "mimetype":
                    brut.append(_entree_zip(info.filename, anonymise, info.filename != "mimetype"))
                    continue
                # recopie des octets compressés d'origine : aucune décompression dans le navigateur
                flux.seek(info.header_offset)
                entete = flux.read(30)
                debut = info.header_offset + 30 + int.from_bytes(entete[26:28], "little") + int.from_bytes(entete[28:30], "little")
                flux.seek(debut)
                brut.append({"nom": info.filename, "methode": info.compress_type, "crc": info.CRC,
                             "taille": info.file_size, "b64": base64.b64encode(flux.read(info.compress_size)).decode("ascii")})
        modele = {
            "format": fmt.nom,
            "titre": self.m.get("titre", "Modèle"),
            "id": self.m.get("id", "modele"),
            "version_modele": str(self.m.get("version", "1")),
            "version_dictionnaire": self.d["version"],
            "date_gel": self.m.get("date_gel"),
            "parametres": {"orthographe_nombres": "traditionnelle", "centimes": "si_non_nuls",
                           "accord_pluriel": "masculin_l_emporte", **self.m.get("parametres", {})},
            "parties": parties_ir,
            "fichiers": brut,
            "calculs": {c["id"]: {"e": calculs.get(c["id"]), "type": c["type"], "libelle": c["libelle"],
                                  "element_de": c.get("element_de")}
                        for c in self.m.get("calculs", [])},
            "types_extensions": self.extensions,
            "controles": controles,
            "tables": self.m.get("tables", {}),
            "locales": self.m.get("locales", []),
            "decisions": decisions,
        }
        plan = self.plan(schema, decisions)
        return modele, plan

    def _anonymiser_metadonnees(self, nom, donnees):
        if nom in ("docProps/core.xml", "meta.xml", "docProps/app.xml"):
            s = donnees.decode("utf-8")
            avant = s
            s = re.sub(r"(<dc:creator>)[^<]*(</dc:creator>)", r"\1\2", s)
            s = re.sub(r"(<cp:lastModifiedBy>)[^<]*(</cp:lastModifiedBy>)", r"\1\2", s)
            s = re.sub(r"(<meta:initial-creator>)[^<]*(</meta:initial-creator>)", r"\1\2", s)
            s = re.sub(r"(<Company>)[^<]*(</Company>)", r"\1\2", s)
            s = re.sub(r"(<Manager>)[^<]*(</Manager>)", r"\1\2", s)
            if s != avant:
                self.avertissements.append(f"métadonnées d'auteur effacées ({nom})")
            return s.encode("utf-8")
        return donnees

    # ------------------------------------------------------------ plan du formulaire
    @staticmethod
    def _filtrer(champs, chemins):
        out = []
        for c in champs:
            sous = {t[1:] for t in chemins if t and t[0] == c["id"] and len(t) > 1}
            if (c["id"],) not in chemins and not sous:
                continue
            c2 = copy.deepcopy(c)
            if "champs" in c and sous:
                c2["champs"] = Compilation._filtrer(c["champs"], sous)
            out.append(c2)
        return out

    def plan(self, schema, decisions):
        b = schema.besoins
        modules = []
        for m in self.d["modules"]:
            if m["id"] in b["modules"]:
                modules.append({"id": m["id"], "libelle": m["libelle"], "champs": self._filtrer(m["champs"], b["modules"][m["id"]])})
        roles = []
        for cle in schema.ordre_roles:
            mod, rid = cle.split(".")
            r = next(x for x in schema.modules[mod]["roles"] if x["id"] == rid)
            roles.append({"cle": cle, "libelle": r["libelles"]["ms"], **{k: r[k] for k in ("libelles", "cardinalite", "natures")},
                          "attributs": self._filtrer(r.get("attributs", []), b["attributs"].get(cle, set()))})
        entites = {}
        for ent, chemins in b["entites"].items():
            e = self.d["entites"][ent]
            if ent == "personne":
                entites[ent] = {k: self._filtrer(e[k], chemins) for k in ("commun", "physique", "morale")}
            else:
                entites[ent] = {"champs": self._filtrer(e["champs"], chemins), "libelle": e["libelle"],
                                "prefixe": e["prefixe_identifiant"]}
        locales = [x for x in self.m.get("locales", []) if x["id"] in b["locales"]]
        return {
            "modules": modules, "roles": roles, "entites": entites, "locales": locales,
            "options": [{"id": k, "libelle": v} for k, v in decisions["options"].items()],
            "choix": [{"id": k, "libelle": v["libelle"], "cas": [{"id": i, "libelle": l} for i, l in v["cas"].items()]}
                      for k, v in decisions["choix"].items()],
            "calculs": [{k: c.get(k) for k in ("id", "libelle", "type", "explication", "source", "element_de")}
                        for c in self.m.get("calculs", [])],
            "aides": self.m.get("aides", {}),
        }


def rapport_markdown(comp, plan):
    L = []
    if comp.erreurs:
        L.append(f"## Erreurs ({len(comp.erreurs)})\n")
        L += [f"- {e}" for e in comp.erreurs]
        L.append("")
    if comp.avertissements:
        L.append("## Avertissements\n")
        L += [f"- {a}" for a in comp.avertissements]
        L.append("")
    if plan:
        L.append("## Inventaire\n")
        if comp.extensions:
            L.append(f"- Extensions du dictionnaire : {', '.join(f'{k} ({v})' for k, v in comp.extensions.items())}")
        L.append(f"- Valeurs distinctes : {len(comp.inventaire['valeurs'])}")
        L.append(f"- Conditions : {len(comp.inventaire['conditions'])} ; boucles : {len(comp.inventaire['boucles'])}")
        L.append(f"- Options : {', '.join(o['libelle'] for o in plan['options']) or 'aucune'}")
        L.append(f"- Choix : {', '.join(c['libelle'] + ' (' + ', '.join(x['libelle'] for x in c['cas']) + ')' for c in plan['choix']) or 'aucun'}")
        L.append(f"- Rôles : {', '.join(r['cle'] for r in plan['roles']) or 'aucun'}")
        L.append(f"- Compteurs : {', '.join(sorted(comp.inventaire['compteurs'])) or 'aucun'} ; "
                 f"renvois : {', '.join(sorted(comp.inventaire['renvois'])) or 'aucun'}")
        L.append("")
        L.append("| Chemin | Occurrences |\n|---|---|")
        for k, v in sorted(comp.inventaire["valeurs"].items()):
            L.append(f"| `{k}` | {v} |")
    return "\n".join(L)
