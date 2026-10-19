# -*- coding: utf-8 -*-
"""Résolution des chemins contre le dictionnaire, contrôle des rendus, recensement des besoins du formulaire."""
import difflib
from syntaxe import ErreurSyntaxe

TRANSFORMATIONS = {"majuscules", "minuscules", "initiale_majuscule"}
AGREGATS = {"nombre", "accord", "qualite", "enumeration_ou"}
RENDUS_TYPE = {
    "texte": {"tel_quel"}, "texte_long": {"tel_quel"}, "telephone": {"tel_quel"}, "courriel": {"tel_quel"},
    "entier": {"chiffres", "lettres", "ordinal", "ordinal_abrege", "romain"},
    "decimal": {"chiffres", "lettres"},
    "montant": {"chiffres", "lettres", "lettres_puis_chiffres", "chiffres_puis_lettres"},
    "pourcentage": {"chiffres", "lettres"},
    "date": {"longue", "courte", "lettres", "iso"},
    "heure": {"courte", "lettres"},
    "duree": {"chiffres", "lettres"},
    "booleen": {"oui_non"},
    "choix": {"libelle", "long"},
    "identifiant": {"tel_quel", "groupe"},
    "adresse": {"ligne", "bloc"},
    "personne": set(),
    "compteur": {"chiffres", "romain", "romain_minuscule", "lettre", "lettre_majuscule", "lettres", "ordinal",
                 "ordinal_abrege"},
}
RENDU_PAR_DEFAUT = {"duree": "lettres"}

# Valeurs dérivées des personnes et champs dont elles dépendent
DERIVES_PERSONNE = {
    "designation_courte": {"physique": ["civilite", "prenoms", "prenom_usuel", "nom"],
                           "morale": ["forme_juridique", "forme_precisee", "genre_grammatical", "denomination"]},
    "nom_complet": {"physique": ["prenoms", "prenom_usuel", "nom"], "morale": ["denomination"]},
    "designation_complete": {
        "physique": ["civilite", "prenoms", "nom", "date_naissance", "lieu_naissance", "nationalite", "profession",
                     "domicile", "capacite", "representants"],
        "morale": ["forme_juridique", "forme_precisee", "genre_grammatical", "denomination", "capital",
                   "capital_variable", "immatriculation", "siege", "representants_legaux"]},
    "genre": {"physique": ["civilite"], "morale": ["forme_juridique", "genre_grammatical"]},
    "age": {"physique": ["date_naissance"], "morale": []},
    "majeur": {"physique": ["date_naissance"], "morale": []},
}
TYPE_DERIVE = {"designation_courte": "texte", "nom_complet": "texte", "designation_complete": "texte",
               "genre": "texte", "age": "entier", "majeur": "booleen"}
META_BOUCLE = {"#rang": "entier", "#premier": "booleen", "#dernier": "booleen", "#avant_dernier": "booleen",
               "#nombre": "entier"}

FONCTIONS = {  # nom: (arité min, arité max)
    "ajouter_jours": (2, 2), "ajouter_mois": (2, 2), "ajouter_annees": (2, 2), "ajouter_duree": (2, 2),
    "veille": (1, 1), "lendemain": (1, 1), "prorogation": (1, 2),
    "ecart_jours": (2, 2), "ecart_mois": (2, 2), "ecart_annees": (2, 2), "age": (2, 2),
    "somme": (1, 1), "nombre": (1, 1), "min": (1, 9), "max": (1, 9),
    "arrondi": (1, 2), "arrondi_inferieur": (1, 2), "arrondi_superieur": (1, 2), "abs": (1, 1),
    "si": (3, 3), "renseigne": (1, 1), "table": (2, 2), "cumul": (2, 2),
}


class Resolu:
    """Résultat d'une résolution : nature, type, définition, multiplicité."""
    def __init__(self, nature, type_, definition=None, multiple=False, role=None):
        self.nature, self.type, self.definition, self.multiple, self.role = nature, type_, definition, multiple, role


def _proposer(mot, possibles):
    p = difflib.get_close_matches(mot, list(possibles), n=3, cutoff=0.6)
    return f" (voulez-vous dire : {', '.join(p)} ?)" if p else ""


class Schema:
    def __init__(self, dictionnaire, manifeste, decisions):
        self.d = dictionnaire
        self.m = manifeste
        self.modules = {m["id"]: m for m in dictionnaire["modules"]}
        self.entites = dictionnaire["entites"]
        self.locales = {x["id"]: x for x in manifeste.get("locales", [])}
        self.calculs = {x["id"]: x for x in manifeste.get("calculs", [])}
        self.options = decisions["options"]   # id -> libellé
        self.choix = decisions["choix"]       # id -> {libelle, cas: {id: libelle}}
        self.ordre_roles = []
        self.besoins = {"modules": {}, "roles": set(), "entites": {}, "locales": set(), "calculs": set(), "attributs": {}}

    # -- recensement
    def _besoin_module(self, mod, chemin):
        self.besoins["modules"].setdefault(mod, set()).add(tuple(chemin))

    def besoin_personne(self):
        """Toute personne doit pouvoir être nommée et accordée : désignation courte et genre."""
        self._besoin_entite("personne", ["nature"])
        for nat in ("physique", "morale"):
            for f in DERIVES_PERSONNE["designation_courte"][nat] + DERIVES_PERSONNE["genre"][nat]:
                self._besoin_entite("personne", [f])

    def _besoin_entite(self, ent, chemin):
        self.besoins["entites"].setdefault(ent, set()).add(tuple(chemin))

    # -- champs
    @staticmethod
    def _champ(champs, ident):
        for c in champs:
            if c["id"] == ident:
                return c
        return None

    def _champs_personne(self):
        p = self.entites["personne"]
        return p["commun"] + p["physique"] + p["morale"]

    def resoudre(self, segs, portees):
        """portees : {variable: (Resolu de l'élément, fonction de recensement)}"""
        if not segs or not segs[0]:
            raise ErreurSyntaxe("chemin vide")
        tete, reste = segs[0], segs[1:]
        if tete in portees:
            base, recenser = portees[tete]
            if reste and reste[0].startswith("#"):
                if reste[0] not in META_BOUCLE or len(reste) > 1:
                    raise ErreurSyntaxe(f"méta-information de boucle inconnue « {reste[0]} » ; admises : "
                                        + ", ".join(META_BOUCLE))
                return Resolu("valeur", META_BOUCLE[reste[0]])
            return self._parcourir(base, reste, recenser, f"{tete}", getattr(base, "chemin", ()))
        if tete == "local":
            if len(segs) != 2 or segs[1] not in self.locales:
                raise ErreurSyntaxe(f"variable locale non déclarée dans le manifeste : {'.'.join(segs)}"
                                    + _proposer(segs[-1], self.locales))
            self.besoins["locales"].add(segs[1])
            loc = self.locales[segs[1]]
            return Resolu("valeur", loc["type"], loc)
        if tete == "calcul":
            if len(segs) != 2 or segs[1] not in self.calculs:
                raise ErreurSyntaxe(f"calcul non déclaré dans le manifeste : {'.'.join(segs)}"
                                    + _proposer(segs[-1], self.calculs))
            calc = self.calculs[segs[1]]
            if calc.get("element_de"):
                if not any(getattr(b, "liste_cle", None) == calc["element_de"] for b, _ in portees.values()):
                    raise ErreurSyntaxe(f"le calcul « {segs[1]} » est un calcul de ligne : il ne s'emploie qu'à l'intérieur de "
                                        f"[[POUR CHAQUE … DANS {calc['element_de']}]]")
            self.besoins["calculs"].add(segs[1])
            return Resolu("valeur", calc["type"], calc)
        if tete == "option":
            if len(segs) != 2 or segs[1] not in self.options:
                raise ErreurSyntaxe(f"option inconnue : {'.'.join(segs)}" + _proposer(segs[-1], self.options))
            return Resolu("valeur", "booleen")
        if tete == "choix":
            if len(segs) != 2 or segs[1] not in self.choix:
                raise ErreurSyntaxe(f"choix inconnu : {'.'.join(segs)}" + _proposer(segs[-1], self.choix))
            return Resolu("valeur", "choix_document", self.choix[segs[1]])
        if tete in self.modules:
            mod = self.modules[tete]
            if not reste:
                raise ErreurSyntaxe(f"« {tete} » est un module : préciser un champ ou un rôle")
            roles = {r["id"]: r for r in mod["roles"]}
            if reste[0] in roles:
                cle = f"{tete}.{reste[0]}"
                if cle not in self.besoins["roles"]:
                    self.ordre_roles.append(cle)      # ordre de première apparition dans le document
                self.besoins["roles"].add(cle)
                role = roles[reste[0]]
                self.besoin_personne()
                base = Resolu("personne", "personne", None, multiple=True, role=role)
                return self._parcourir(base, reste[1:], lambda ch: self._besoin_entite("personne", ch), cle)
            base = Resolu("groupe", "groupe", {"champs": mod["champs"]})
            return self._parcourir(base, reste, lambda ch, m=tete: self._besoin_module(m, ch), tete)
        possibles = list(self.modules) + ["local", "calcul", "option", "choix"] + list(portees)
        raise ErreurSyntaxe(f"début de chemin inconnu « {tete} »" + _proposer(tete, possibles))

    def _parcourir(self, base, reste, recenser, deja, prefixe=()):
        cour, multiple, chemin = base, base.multiple, list(prefixe)
        for i, seg in enumerate(reste):
            lieu = deja + "." + ".".join(reste[:i + 1])
            if cour.nature == "personne":
                if seg in DERIVES_PERSONNE:
                    for nat in ("physique", "morale"):
                        for f in DERIVES_PERSONNE[seg][nat]:
                            self._besoin_entite("personne", [f])
                    if seg == "designation_complete":   # désignation des représentants
                        for f in DERIVES_PERSONNE["designation_courte"]["physique"] + \
                                DERIVES_PERSONNE["designation_courte"]["morale"]:
                            self._besoin_entite("personne", [f])
                    if i != len(reste) - 1:
                        raise ErreurSyntaxe(f"rien ne peut suivre la valeur dérivée « {seg} » : {lieu}")
                    return Resolu("valeur", TYPE_DERIVE[seg], None, multiple)
                c = self._champ(self._champs_personne(), seg)
                role_def = getattr(cour, "attributs_de", None) or cour.role
                attrs = (role_def or {}).get("attributs", []) if i == 0 else []
                if c is None and self._champ(attrs, seg):
                    c = self._champ(attrs, seg)
                    cle = role_def["_cle"]
                    recenser = lambda ch, k=cle: self.besoins["attributs"].setdefault(k, set()).add(tuple(ch))
                    chemin = [seg]
                    recenser(chemin)
                    cour = self._depuis_champ(c)
                    continue
                if c is None:
                    raise ErreurSyntaxe(f"champ de personne inconnu « {seg} » dans {lieu}"
                                        + _proposer(seg, [x["id"] for x in self._champs_personne()]
                                                    + list(DERIVES_PERSONNE) + [a["id"] for a in attrs]))
                recenser_ent = lambda ch: self._besoin_entite("personne", ch)
                recenser, chemin = recenser_ent, [seg]
                recenser(chemin)
                cour = self._depuis_champ(c)
                continue
            if cour.nature == "entite":
                c = self._champ(cour.definition["champs"], seg)
                if c is None:
                    raise ErreurSyntaxe(f"champ inconnu « {seg} » dans {lieu}"
                                        + _proposer(seg, [x["id"] for x in cour.definition["champs"]]))
                ent = cour.type
                recenser, chemin = (lambda ch, e=ent: self._besoin_entite(e, ch)), [seg]
                recenser(chemin)
                cour = self._depuis_champ(c)
                continue
            if cour.nature in ("groupe", "liste"):
                champs = cour.definition.get("champs")
                if champs is None:
                    raise ErreurSyntaxe(f"liste de valeurs simples : rien ne peut suivre, dans {lieu}")
                c = self._champ(champs, seg)
                if c is None:
                    raise ErreurSyntaxe(f"champ inconnu « {seg} » dans {lieu}" + _proposer(seg, [x["id"] for x in champs]))
                if cour.nature == "liste":
                    multiple = True
                chemin = chemin + [seg]
                recenser(chemin)
                cour = self._depuis_champ(c)
                continue
            if cour.nature == "valeur" and cour.type in ("adresse", "montant", "duree"):
                sous = {"adresse": [x["id"] for x in self.entites["adresse"]["champs"]],
                        "montant": ["valeur", "devise"], "duree": ["valeur", "unite"]}[cour.type]
                if seg not in sous or i != len(reste) - 1:
                    raise ErreurSyntaxe(f"sous-champ inconnu « {seg} » dans {lieu}" + _proposer(seg, sous))
                t = {"valeur": "decimal", "devise": "texte", "unite": "texte"}.get(seg, "texte")
                return Resolu("valeur", t, None, multiple)
            raise ErreurSyntaxe(f"« {reste[i-1] if i else deja} » n'a pas de sous-champ : {lieu}")
        cour.multiple = multiple or cour.multiple
        cour.recenser, cour.chemin = recenser, tuple(chemin)
        if cour.nature == "personne":
            self.besoin_personne()
        if cour.nature == "reference":
            cour = Resolu("personne" if cour.type == "personne" else "entite", cour.type,
                          None if cour.type == "personne" else self.entites[cour.type], cour.multiple)
        return cour

    def element_de(self, res, liste_cle):
        """Élément d'une boucle sur la liste ou le rôle résolu par res : (Resolu, fonction de recensement)."""
        if res.nature == "personne":
            elem = Resolu("personne", "personne")
            elem.chemin = ()
            elem.attributs_de = res.role
            rec = lambda ch: self._besoin_entite("personne", ch)
        elif res.nature == "liste":
            elem = Resolu("groupe", "groupe", res.definition)
            elem.chemin = res.chemin
            rec = res.recenser
        elif res.nature == "entite":
            elem = Resolu("entite", res.type, res.definition)
            elem.chemin = ()
            rec = lambda ch, e=res.type: self._besoin_entite(e, ch)
        else:
            elem = Resolu("valeur", res.type, res.definition)
            elem.chemin = res.chemin
            rec = res.recenser
        elem.liste_cle = liste_cle
        return elem, rec

    def _depuis_champ(self, c):
        t = c["type"]
        if t == "groupe":
            return Resolu("groupe", "groupe", c)
        if t == "liste":
            if "champs" in c:
                return Resolu("liste", "liste", c, True)
            return Resolu("valeur", c["element"], c, True)
        if t == "reference":
            # le parcours suivant s'effectue dans l'entité visée
            return _ReferenceVers(self, c["cible"], c)
        return Resolu("valeur", t, c)

    # -- rendus
    def controler_rendus(self, res, rendus, lieu):
        t = res.type
        if res.nature in ("groupe", "liste"):
            raise ErreurSyntaxe(f"{lieu} désigne un ensemble de champs : préciser le champ à afficher")
        if res.nature == "entite":
            raise ErreurSyntaxe(f"{lieu} désigne une entité : préciser le champ à afficher (par ex. .designation ou .adresse)")
        format_vu = False
        for nom, params in rendus:
            if nom in TRANSFORMATIONS:
                continue
            if nom in AGREGATS:
                if nom == "qualite":
                    if res.role is None:
                        raise ErreurSyntaxe(f"« qualite » ne s'applique qu'à un rôle (module.role) : {lieu}")
                    variantes = res.role.get("variantes", {})
                    if params and params[0] not in variantes:
                        raise ErreurSyntaxe(f"variante de qualité inconnue « {params[0]} » pour {lieu} ; variantes : "
                                            + (", ".join(variantes) or "aucune"))
                    t = "texte"
                elif nom == "accord":
                    if len(params) not in (2, 4):
                        raise ErreurSyntaxe(f"accord : 2 formes (singulier/pluriel) ou 4 formes "
                                            f"(masc. sing./fém. sing./masc. plur./fém. plur.) attendues : {lieu}")
                    t = "texte"
                elif nom == "nombre":
                    t = "entier"
                elif nom == "enumeration_ou":
                    pass
                continue
            if format_vu:
                raise ErreurSyntaxe(f"deux rendus de mise en forme successifs (« {nom} ») : {lieu}")
            permis = RENDUS_TYPE.get(t, set())
            if nom not in permis:
                raise ErreurSyntaxe(f"rendu « {nom} » inapplicable à une valeur de type {t} ({lieu}) ; rendus admis : "
                                    + (", ".join(sorted(permis | TRANSFORMATIONS)) or "transformations seulement"))
            if nom == "long":
                vals = (res.definition or {}).get("valeurs", [])
                if not any("long" in v for v in vals):
                    raise ErreurSyntaxe(f"ce choix n'a pas de forme longue : {lieu}")
            format_vu = True


class _ReferenceVers(Resolu):
    """Champ de référence : se comporte comme l'entité visée pour la suite du parcours."""
    def __init__(self, schema, cible, definition):
        if cible == "personne":
            super().__init__("personne", "personne", definition)
        else:
            super().__init__("entite", cible, schema.entites[cible])
        self.champ_reference = definition
