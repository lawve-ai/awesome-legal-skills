# -*- coding: utf-8 -*-
"""Syntaxe des balises tabellion : analyse lexicale et syntaxique.

Balises de valeur   {{ chemin | rendu | rendu:paramètres }}
                    {{ compteur nom [ancre=identifiant] | rendu }}
                    {{ renvoi identifiant | rendu }}
Balises de structure [[SI condition]] [[SINON SI condition]] [[SINON]] [[FIN SI]]
                    [[OPTION id "Libellé"]] [[FIN OPTION]]
                    [[CHOIX id "Libellé"]] [[CAS id "Libellé"]] [[FIN CHOIX]]
                    [[POUR CHAQUE variable DANS chemin]] [[FIN POUR]]
                    [[NOTE texte libre]]

Les arbres d'expressions produits ici sont évalués par le moteur JavaScript ;
aucune expression n'est évaluée en Python, sauf pour les tests.
"""
import re
import unicodedata

RE_BALISE = re.compile(r"\{\{(.*?)\}\}|\[\[(.*?)\]\]", re.S)

GUILLEMETS = {"“": '"', "”": '"', "«": '"', "»": '"', "„": '"', "‟": '"', "″": '"'}
ESPACES = {" ": " ", " ": " ", " ": " ", " ": " ", "\t": " "}


class ErreurSyntaxe(Exception):
    pass


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normaliser(contenu):
    """Neutralise les transformations de Word : guillemets typographiques, espaces insécables."""
    for a, b in GUILLEMETS.items():
        contenu = contenu.replace(a, b)
    for a, b in ESPACES.items():
        contenu = contenu.replace(a, b)
    return contenu.strip()


# ------------------------------------------------------------------ lexique
MOTS_CLES = {"SI", "SINON", "FIN", "OPTION", "CHOIX", "CAS", "POUR", "CHAQUE", "DANS", "NOTE",
             "ET", "OU", "NON", "EST", "PLURIEL", "SINGULIER", "FEMININ", "MASCULIN", "PERSONNE",
             "MORALE", "PHYSIQUE", "RENSEIGNE", "RENSEIGNEE", "VIDE", "VRAI", "FAUX", "COMPTEUR",
             "RENVOI"}

RE_JETON = re.compile(r"""
    (?P<nombre>\d+(?:[.,]\d+)?)
  | (?P<chaine>"[^"]*"|'[^']*')
  | (?P<op><=|>=|!=|≠|≤|≥|=|<|>|\+|-|\*|/|\(|\)|,|\|)
  | (?P<mot>[A-Za-zÀ-ÖØ-öø-ÿ_][A-Za-zÀ-ÖØ-öø-ÿ0-9_]*(?:(?:\.|\#)[A-Za-zÀ-ÖØ-öø-ÿ_][A-Za-zÀ-ÖØ-öø-ÿ0-9_]*)*)
  | (?P<espace>\s+)
""", re.X)


def lexer(s):
    jetons, i = [], 0
    while i < len(s):
        m = RE_JETON.match(s, i)
        if not m:
            raise ErreurSyntaxe(f"caractère inattendu « {s[i]} » dans « {s} »")
        i = m.end()
        genre = m.lastgroup
        val = m.group(genre)
        if genre == "espace":
            continue
        if genre == "mot":
            cle = sans_accents(val).upper()
            if cle in MOTS_CLES and "." not in val and "#" not in val:
                jetons.append(("mc", cle))
                continue
            jetons.append(("chemin", val))
        elif genre == "chaine":
            jetons.append(("chaine", val[1:-1]))
        elif genre == "nombre":
            jetons.append(("nombre", float(val.replace(",", "."))))
        else:
            jetons.append(("op", {"≠": "!=", "≤": "<=", "≥": ">="}.get(val, val)))
    return jetons


def chemin_normalise(brut):
    """Chemin en minuscules ; signale les accents (identifiants sans diacritiques)."""
    if sans_accents(brut) != brut:
        raise ErreurSyntaxe(f"le chemin « {brut} » contient des accents : les identifiants n'en comportent pas "
                            f"(essayez « {sans_accents(brut).lower()} »)")
    return brut.lower()


def segments(chemin):
    """'piece#rang' -> ['piece', '#rang'] ; 'a.b.c' -> ['a','b','c']."""
    out = []
    for partie in chemin.split("."):
        if "#" in partie:
            base, *metas = partie.split("#")
            out.append(base)
            out.extend("#" + m for m in metas)
        else:
            out.append(partie)
    return out


# ------------------------------------------------------------------ expressions
class Analyseur:
    """Descente récursive. Grammaire :
       ou      := et ('OU' et)*
       et      := non ('ET' non)*
       non     := 'NON' non | comp
       comp    := somme (opcomp somme | 'EST' ['NON'] predicat)?
       somme   := produit (('+'|'-') produit)*
       produit := unaire (('*'|'/') unaire)*
       unaire  := '-' unaire | atome
       atome   := nombre | chaine | 'VRAI' | 'FAUX' | chemin | chemin '(' args ')' | '(' ou ')'
    """
    PREDICATS = {"PLURIEL", "SINGULIER", "FEMININ", "MASCULIN", "RENSEIGNE", "RENSEIGNEE", "VIDE",
                 "PERSONNE MORALE", "PERSONNE PHYSIQUE", "VRAI", "FAUX"}

    def __init__(self, jetons, source):
        self.j, self.i, self.source = jetons, 0, source

    def voir(self, decalage=0):
        k = self.i + decalage
        return self.j[k] if k < len(self.j) else (None, None)

    def prendre(self, genre=None, valeur=None):
        g, v = self.voir()
        if g is None or (genre and g != genre) or (valeur is not None and v != valeur):
            attendu = valeur or genre or "un élément"
            raise ErreurSyntaxe(f"« {attendu} » attendu dans « {self.source} »")
        self.i += 1
        return v

    def fin(self):
        if self.i != len(self.j):
            raise ErreurSyntaxe(f"éléments en trop après « {self.j[self.i][1]} » dans « {self.source} »")

    def ou(self):
        a = self.et()
        while self.voir() == ("mc", "OU"):
            self.i += 1
            a = {"k": "ou", "a": a, "b": self.et()}
        return a

    def et(self):
        a = self.non()
        while self.voir() == ("mc", "ET"):
            self.i += 1
            a = {"k": "et", "a": a, "b": self.non()}
        return a

    def non(self):
        if self.voir() == ("mc", "NON"):
            self.i += 1
            return {"k": "non", "a": self.non()}
        return self.comp()

    def comp(self):
        a = self.somme()
        g, v = self.voir()
        if g == "op" and v in ("=", "!=", "<", ">", "<=", ">="):
            self.i += 1
            return {"k": "op", "op": v, "a": a, "b": self.somme()}
        if (g, v) == ("mc", "EST"):
            self.i += 1
            neg = False
            if self.voir() == ("mc", "NON"):
                self.i += 1
                neg = True
            g2, p = self.voir()
            if g2 != "mc":
                raise ErreurSyntaxe(f"prédicat attendu après EST dans « {self.source} »")
            self.i += 1
            if p == "PERSONNE":
                p = "PERSONNE " + self.prendre("mc")
            if p not in self.PREDICATS:
                raise ErreurSyntaxe(f"prédicat inconnu « {p} » ; prédicats admis : "
                                    + ", ".join(sorted(self.PREDICATS)))
            p = {"RENSEIGNEE": "RENSEIGNE"}.get(p, p)
            return {"k": "est", "a": a, "pred": p, "neg": neg}
        return a

    def somme(self):
        a = self.produit()
        while self.voir()[0] == "op" and self.voir()[1] in ("+", "-"):
            op = self.prendre()
            a = {"k": "op", "op": op, "a": a, "b": self.produit()}
        return a

    def produit(self):
        a = self.unaire()
        while self.voir()[0] == "op" and self.voir()[1] in ("*", "/"):
            op = self.prendre()
            a = {"k": "op", "op": op, "a": a, "b": self.unaire()}
        return a

    def unaire(self):
        if self.voir() == ("op", "-"):
            self.i += 1
            return {"k": "op", "op": "-", "a": {"k": "num", "v": 0}, "b": self.unaire()}
        return self.atome()

    def atome(self):
        g, v = self.voir()
        if g == "nombre":
            self.i += 1
            return {"k": "num", "v": v}
        if g == "chaine":
            self.i += 1
            return {"k": "str", "v": v}
        if (g, v) in (("mc", "VRAI"), ("mc", "FAUX")):
            self.i += 1
            return {"k": "bool", "v": v == "VRAI"}
        if (g, v) == ("op", "("):
            self.i += 1
            e = self.ou()
            self.prendre("op", ")")
            return e
        if g == "chemin":
            self.i += 1
            if self.voir() == ("op", "("):
                self.i += 1
                args = []
                if self.voir() != ("op", ")"):
                    args.append(self.ou())
                    while self.voir() == ("op", ","):
                        self.i += 1
                        args.append(self.ou())
                self.prendre("op", ")")
                return {"k": "fn", "nom": chemin_normalise(v), "args": args}
            return {"k": "chemin", "p": segments(chemin_normalise(v))}
        raise ErreurSyntaxe(f"expression incomplète dans « {self.source} »")


def analyser_expression(texte):
    texte = normaliser(texte)
    a = Analyseur(lexer(texte), texte)
    e = a.ou()
    a.fin()
    return e


# ------------------------------------------------------------------ balises
STRUCTURE_OUVRANTE = {"SI", "OPTION", "CHOIX", "POUR"}
STRUCTURE_INTERMEDIAIRE = {"SINON SI", "SINON", "CAS"}
STRUCTURE_FERMANTE = {"FIN SI", "FIN OPTION", "FIN CHOIX", "FIN POUR"}
FERMETURE_DE = {"SI": "FIN SI", "OPTION": "FIN OPTION", "CHOIX": "FIN CHOIX", "POUR": "FIN POUR"}


def nature_directive(contenu):
    """Nature d'une balise [[…]] sans analyse complète (pour le classement des paragraphes)."""
    mots = sans_accents(normaliser(contenu)).upper().split()
    if not mots:
        return "?"
    if mots[0] == "FIN" and len(mots) > 1:
        return "FIN " + mots[1]
    if mots[0] == "SINON" and len(mots) > 1 and mots[1] == "SI":
        return "SINON SI"
    return mots[0]


def _identifiant_et_libelle(reste, source):
    m = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:"([^"]*)")?\s*', reste)
    if not m:
        raise ErreurSyntaxe(f"identifiant (sans accent ni espace), puis libellé facultatif entre guillemets, "
                            f"attendus dans « {source} »")
    return m.group(1).lower(), (m.group(2) or "").strip()


def analyser_directive(contenu):
    src = normaliser(contenu)
    nature = nature_directive(src)
    mots = src.split(None, 1)
    if nature == "SI":
        return {"d": "SI", "cond": analyser_expression(src.split(None, 1)[1] if len(mots) > 1 else "")}
    if nature == "SINON SI":
        reste = re.split(r"(?i)^\s*sinon\s+si\s+", src, maxsplit=1)[-1]
        return {"d": "SINON SI", "cond": analyser_expression(reste)}
    if nature in ("SINON", "FIN SI", "FIN OPTION", "FIN CHOIX", "FIN POUR"):
        attendu = nature.split()
        if [sans_accents(x).upper() for x in src.split()] != attendu:
            raise ErreurSyntaxe(f"« [[{nature}]] » ne prend aucun argument (lu : « {src} »)")
        return {"d": nature}
    if nature in ("OPTION", "CHOIX", "CAS"):
        if len(mots) < 2:
            raise ErreurSyntaxe(f"identifiant attendu après {nature}")
        ident, libelle = _identifiant_et_libelle(mots[1], src)
        return {"d": nature, "id": ident, "libelle": libelle}
    if nature == "POUR":
        m = re.fullmatch(r"(?i)pour\s+chaque\s+([A-Za-z_][A-Za-z0-9_]*)\s+dans\s+(\S+)", src)
        if not m:
            raise ErreurSyntaxe(f"forme attendue : [[POUR CHAQUE variable DANS chemin]] (lu : « {src} »)")
        var = m.group(1).lower()
        return {"d": "POUR", "var": var, "liste": segments(chemin_normalise(m.group(2)))}
    if nature == "NOTE":
        return {"d": "NOTE"}
    raise ErreurSyntaxe(f"mot-clé inconnu en tête de « [[{src}]] » ; mots-clés admis : SI, SINON SI, SINON, "
                        f"FIN SI, OPTION, FIN OPTION, CHOIX, CAS, FIN CHOIX, POUR CHAQUE, FIN POUR, NOTE")


def analyser_valeur(contenu):
    """{{ … }} -> {'v': ..., 'rendus': [(nom, [params])]}"""
    src = normaliser(contenu)
    morceaux = [m.strip() for m in src.split("|")]
    tete, rendus = morceaux[0], []
    for r in morceaux[1:]:
        if not r:
            raise ErreurSyntaxe(f"rendu vide après « | » dans « {src} »")
        nom, _, params = r.partition(":")
        nom = sans_accents(nom.strip()).lower()
        rendus.append([nom, [p.strip() for p in params.split("/")] if params else []])
    mots = tete.split()
    if mots and sans_accents(mots[0]).upper() == "COMPTEUR":
        m = re.fullmatch(r"(?i)compteur\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+ancre\s*=\s*([A-Za-z_][A-Za-z0-9_]*))?", tete)
        if not m:
            raise ErreurSyntaxe(f"forme attendue : {{{{compteur nom}}}} ou {{{{compteur nom ancre=identifiant}}}} (lu : « {src} »)")
        return {"v": "compteur", "nom": m.group(1).lower(), "ancre": (m.group(2) or "").lower() or None, "rendus": rendus}
    if mots and sans_accents(mots[0]).upper() == "RENVOI":
        m = re.fullmatch(r"(?i)renvoi\s+([A-Za-z_][A-Za-z0-9_]*)", tete)
        if not m:
            raise ErreurSyntaxe(f"forme attendue : {{{{renvoi identifiant}}}} (lu : « {src} »)")
        return {"v": "renvoi", "ancre": m.group(1).lower(), "rendus": rendus}
    if len(mots) != 1:
        raise ErreurSyntaxe(f"un seul chemin attendu avant le premier « | » dans « {src} »")
    # Word met parfois une capitale en début de paragraphe : {{Bail.loyer}} -> bail.loyer
    return {"v": "chemin", "p": segments(chemin_normalise(tete)), "rendus": rendus}
