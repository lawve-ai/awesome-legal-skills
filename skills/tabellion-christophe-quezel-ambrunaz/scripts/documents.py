# -*- coding: utf-8 -*-
"""Lecture et normalisation des documents .docx et .odt.

Principe : chaque balise est d'abord réunie dans un seul nœud de texte (Word la
fragmente souvent entre plusieurs « runs »), puis remplacée par un marqueur
remonté au niveau du paragraphe en scindant ses ancêtres (run, lien, span).
Entre deux marqueurs d'un même paragraphe ne figurent ainsi que des éléments
complets : supprimer ce qui les sépare laisse toujours un XML bien formé.
"""
import copy
import re
import zipfile
from lxml import etree

from syntaxe import RE_BALISE

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
}
TB = "urn:tabellion"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
SEP = "\x00"   # séparateur : tabulation, saut de ligne, note… ; aucune balise ne peut le franchir


def q(prefixe, nom):
    return "{%s}%s" % (NS[prefixe], nom)


class ErreurDocument(Exception):
    pass


def retirer_xmlns(s):
    return re.sub(r'\s+xmlns(?::[\w.-]+)?="[^"]*"', "", s)


def nom_qualifie(elem, cle):
    """'{uri}local' -> 'prefixe:local' selon les espaces de noms visibles de l'élément."""
    if cle == XML_SPACE:
        return "xml:space"
    if cle.startswith("{"):
        uri, local = cle[1:].split("}")
        for p, u in elem.nsmap.items():
            if u == uri and p:
                return f"{p}:{local}"
        raise ErreurDocument(f"espace de noms sans préfixe : {uri}")
    return cle


def echapper_attr(v):
    return v.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def balise_ouvrante(elem, attributs=None):
    nom = nom_qualifie(elem, elem.tag)
    attrs = elem.attrib if attributs is None else attributs
    s = "".join(f' {nom_qualifie(elem, k)}="{echapper_attr(v)}"' for k, v in attrs.items())
    return f"<{nom}{s}>"


def balise_fermante(elem):
    return f"</{nom_qualifie(elem, elem.tag)}>"


# =================================================================== formats
class Format:
    nom = None
    parties_balisables = []

    def __init__(self, chemin):
        self.chemin = chemin
        self.zip = zipfile.ZipFile(chemin)
        self.noms = self.zip.namelist()
        self.arbres = {}

    def parties(self):
        return [n for n in self.noms if any(re.fullmatch(m, n) for m in self.parties_balisables)]

    def arbre(self, partie):
        if partie not in self.arbres:
            parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False, resolve_entities=False,
                                     huge_tree=True)
            self.arbres[partie] = etree.fromstring(self.zip.read(partie), parser)
        return self.arbres[partie]

    def serialiser(self, partie):
        return etree.tostring(self.arbres[partie], xml_declaration=True, encoding="UTF-8", standalone=True)


class Docx(Format):
    nom = "docx"
    parties_balisables = [r"word/document\.xml", r"word/header\d*\.xml", r"word/footer\d*\.xml",
                          r"word/footnotes\.xml", r"word/endnotes\.xml"]
    P = q("w", "p")
    PROPRIETES = {q("w", "r"): [q("w", "rPr")], q("w", "smartTag"): [q("w", "smartTagPr")],
                  q("w", "customXml"): [q("w", "customXmlPr")], q("w", "hyperlink"): [],
                  q("w", "t"): [], q("w", "bdo"): [], q("w", "dir"): []}
    SEPARATEURS = {q("w", n) for n in ("tab", "br", "cr", "sym", "noBreakHyphen", "softHyphen", "footnoteReference",
                                       "endnoteReference", "fldChar")}
    EXCLUS = {q("w", n) for n in ("del", "delText", "instrText", "drawing", "pict", "object", "commentReference")} | \
             {"{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"}

    def paragraphes(self, racine):
        return list(racine.iter(self.P))

    def segments(self, p):
        out = []

        def parcourir(e):
            for c in e:
                if not isinstance(c.tag, str):
                    continue
                if c.tag == self.P:
                    continue
                if c.tag == q("w", "t"):
                    out.append((c, "text"))
                elif c.tag in self.SEPARATEURS or c.tag in self.EXCLUS:
                    out.append(None)
                else:
                    parcourir(c)
        parcourir(p)
        return out

    def ligne_et_tableau(self, p):
        tc = p.getparent()
        if tc is None or tc.tag != q("w", "tc"):
            return None, None
        tr = tc.getparent()
        if tr is None or tr.tag != q("w", "tr"):
            return None, None
        return tr, tr.getparent()

    def proprietes_paragraphe(self, p):
        return p.find(q("w", "pPr"))

    def a_saut_de_section(self, p):
        ppr = p.find(q("w", "pPr"))
        return ppr is not None and ppr.find(q("w", "sectPr")) is not None

    def nouveau_texte(self, modele):
        t = etree.Element(q("w", "t"))
        t.set(XML_SPACE, "preserve")
        return t

    def apres_scission(self, gauche, droite):
        for e in (gauche, droite):
            if e is not None and e.tag == q("w", "t"):
                e.set(XML_SPACE, "preserve")

    def enveloppe(self, chaine):
        """Ouverture/fermeture des ancêtres d'une valeur (de l'extérieur vers l'intérieur)."""
        avant, apres = "", ""
        for e in chaine:
            if e.tag == q("w", "t"):
                avant += '<w:t xml:space="preserve">'
                apres = "</w:t>" + apres
                continue
            props = ""
            for pt in self.PROPRIETES.get(e.tag, []):
                pe = e.find(pt)
                if pe is not None:
                    pe = copy.deepcopy(pe)
                    for h in pe.findall(q("w", "highlight")):   # surlignage du balisage : jamais reproduit
                        pe.remove(h)
                    props += retirer_xmlns(etree.tostring(pe, encoding="unicode"))
            avant += balise_ouvrante(e) + props
            apres = balise_fermante(e) + apres
        return avant, apres

    def saut_paragraphe(self, p):
        ppr = p.find(q("w", "pPr"))
        s = ""
        if ppr is not None:
            ppr = copy.deepcopy(ppr)
            for t in ("sectPr", "numPr"):
                for x in ppr.findall(q("w", t)):
                    ppr.remove(x)
            s = retirer_xmlns(etree.tostring(ppr, encoding="unicode"))
        return "</w:p><w:p>" + s

    def suivi_modifications(self):
        for partie in self.parties():
            racine = self.arbre(partie)
            for t in ("ins", "del", "moveFrom", "moveTo"):
                if racine.find(".//" + q("w", t)) is not None:
                    return True
        return False

    def commentaires(self):
        return "word/comments.xml" in self.noms


class Odt(Format):
    nom = "odt"
    parties_balisables = [r"content\.xml", r"styles\.xml"]
    P = {q("text", "p"), q("text", "h")}
    PROPRIETES = {q("text", "span"): [], q("text", "a"): [], q("text", "meta"): []}
    SEPARATEURS = {q("text", n) for n in ("s", "tab", "line-break", "note", "annotation", "annotation-end",
                                          "sequence", "page-number", "date", "time")} | \
                  {q("draw", "frame"), q("draw", "a"), q("office", "annotation")}
    TRANSPARENTS = {q("text", n) for n in ("bookmark", "bookmark-start", "bookmark-end", "soft-page-break",
                                           "reference-mark", "reference-mark-start", "reference-mark-end",
                                           "alphabetical-index-mark", "toc-mark")}

    def paragraphes(self, racine):
        return [e for e in racine.iter() if e.tag in self.P]

    def segments(self, p):
        out = []

        def parcourir(e):
            if e.text:
                out.append((e, "text"))
            elif e.tag in self.PROPRIETES or e.tag in self.P:
                out.append((e, "text"))
            for c in e:
                if not isinstance(c.tag, str):
                    out.append((c, "tail"))
                    continue
                if c.tag in self.SEPARATEURS:
                    out.append(None)
                elif c.tag in self.TRANSPARENTS:
                    pass
                elif c.tag in self.P:
                    out.append(None)
                else:
                    parcourir(c)
                out.append((c, "tail"))
        parcourir(p)
        return out

    def ligne_et_tableau(self, p):
        cell = p.getparent()
        if cell is None or cell.tag != q("table", "table-cell"):
            return None, None
        tr = cell.getparent()
        if tr is None or tr.tag != q("table", "table-row"):
            return None, None
        return tr, tr.getparent()

    def proprietes_paragraphe(self, p):
        return None

    def a_saut_de_section(self, p):
        return False

    def nouveau_texte(self, modele):
        return None

    def apres_scission(self, gauche, droite):
        pass

    def enveloppe(self, chaine):
        avant, apres = "", ""
        for e in chaine:
            if e.tag == q("text", "span") and e.get(q("text", "style-name"), "").startswith("TbBalise"):
                continue
            attrs = {k: v for k, v in e.attrib.items() if not k.endswith("}id") and k != "{http://www.w3.org/XML/1998/namespace}id"}
            avant += balise_ouvrante(e, attrs)
            apres = balise_fermante(e) + apres
        return avant, apres

    def saut_paragraphe(self, p):
        garder = {q("text", "style-name"), q("text", "class-names"), q("text", "cond-style-name"),
                  q("text", "outline-level")}
        attrs = {k: v for k, v in p.attrib.items() if k in garder}
        return balise_fermante(p) + balise_ouvrante(p, attrs)

    def suivi_modifications(self):
        racine = self.arbre("content.xml")
        return racine.find(".//" + q("text", "tracked-changes")) is not None and \
            len(racine.find(".//" + q("text", "tracked-changes"))) > 0

    def commentaires(self):
        return self.arbre("content.xml").find(".//" + q("office", "annotation")) is not None


def ouvrir(chemin):
    with zipfile.ZipFile(chemin) as z:
        noms = z.namelist()
    if "word/document.xml" in noms:
        return Docx(chemin)
    if "content.xml" in noms:
        return Odt(chemin)
    raise ErreurDocument("format non reconnu : seuls les fichiers .docx et .odt sont traités")


# =================================================================== texte d'un paragraphe
def texte_segments(segs):
    morceaux = []
    for s in segs:
        if s is None:
            morceaux.append(SEP)
        else:
            e, cote = s
            morceaux.append((e.text if cote == "text" else e.tail) or "")
    return morceaux


def lire(seg):
    e, cote = seg
    return (e.text if cote == "text" else e.tail) or ""


def ecrire(seg, valeur):
    e, cote = seg
    if cote == "text":
        e.text = valeur
    else:
        e.tail = valeur


def texte_paragraphe(fmt, p):
    return "".join(texte_segments(fmt.segments(p))).replace(SEP, " ")


def reperer_balises(fmt, p):
    """Liste des balises du paragraphe [(debut, fin, brut, est_valeur)] et contrôle des fragments isolés."""
    segs = fmt.segments(p)
    texte = "".join(texte_segments(segs))
    trouvees = []
    for m in RE_BALISE.finditer(texte):
        brut = m.group(0)
        if SEP in brut:
            raise ErreurDocument(f"balise interrompue par une tabulation, un saut de ligne ou une note : « {brut.replace(SEP, '⏎')} »")
        trouvees.append((m.start(), m.end(), brut, m.group(1) is not None))
    reste = RE_BALISE.sub(lambda m: " " * len(m.group(0)), texte)
    for motif in ("{{", "}}", "[[", "]]"):
        if motif in reste:
            i = reste.index(motif)
            raise ErreurDocument(f"délimiteur « {motif} » orphelin près de « {texte[max(0, i-30):i+30].replace(SEP, ' ')} »")
    return segs, texte, trouvees


def regrouper(segs, debut, fin):
    """Réunit le texte [debut, fin) dans le segment qui contient debut ; renvoie (segment, decalage)."""
    pos, emplacements = 0, []
    for s in segs:
        longueur = 1 if s is None else len(lire(s))
        emplacements.append((pos, pos + longueur, s))
        pos += longueur
    i = next(k for k, (a, b, s) in enumerate(emplacements) if s is not None and a <= debut < b)
    a_i, b_i, s_i = emplacements[i]
    if fin <= b_i:
        return s_i, debut - a_i
    texte_i = lire(s_i)
    morceau = texte_i[debut - a_i:]
    for k in range(i + 1, len(emplacements)):
        a, b, s = emplacements[k]
        t = lire(s)
        if fin <= b:
            morceau += t[:fin - a]
            ecrire(s, t[fin - a:])
            break
        morceau += t
        ecrire(s, "")
    ecrire(s_i, texte_i[:debut - a_i] + morceau)
    return s_i, debut - a_i


# =================================================================== marqueurs
def nouveau_marqueur(n):
    m = etree.Element("{%s}m" % TB, nsmap={"tb": TB})
    m.set("n", str(n))
    return m


def poser_marqueur(seg, decalage, longueur, n):
    """Remplace le texte de la balise par un marqueur placé dans l'arbre."""
    e, cote = seg
    texte = lire(seg)
    avant, apres = texte[:decalage], texte[decalage + longueur:]
    m = nouveau_marqueur(n)
    if cote == "text":
        e.text = avant
        e.insert(0, m)
    else:
        e.tail = avant
        parent = e.getparent()
        parent.insert(parent.index(e) + 1, m)
    m.tail = apres or None
    return m


def _vide(fmt, e):
    if e.text:
        return False
    props = set(fmt.PROPRIETES.get(e.tag, []))
    return all(isinstance(c.tag, str) and c.tag in props for c in e)


def remonter(fmt, marqueur, paragraphe):
    """Scinde les ancêtres jusqu'à ce que le marqueur soit enfant direct du paragraphe.
    Renvoie la chaîne des ancêtres traversés (de l'extérieur vers l'intérieur)."""
    chaine = []
    while marqueur.getparent() is not paragraphe:
        P = marqueur.getparent()
        if P.tag not in fmt.PROPRIETES:
            local = etree.QName(P).localname
            raise ErreurDocument(f"balise placée dans un élément « {local} » (champ, contrôle de contenu, "
                                 f"révision…) : la déplacer hors de cet élément")
        chaine.insert(0, P)
        idx = P.index(marqueur)
        P2 = etree.Element(P.tag, attrib=dict(P.attrib))
        for pt in fmt.PROPRIETES[P.tag]:
            pe = P.find(pt)
            if pe is not None:
                P2.append(copy.deepcopy(pe))
        P2.text = marqueur.tail
        marqueur.tail = None
        for sib in list(P)[idx + 1:]:
            P2.append(sib)
        P.remove(marqueur)
        gp = P.getparent()
        pi = gp.index(P)
        gp.insert(pi + 1, marqueur)
        gp.insert(pi + 2, P2)
        P2.tail, P.tail = P.tail, None
        fmt.apres_scission(P, P2)
        if _vide(fmt, P2):
            marqueur.tail = (marqueur.tail or "") + (P2.tail or "") or None
            gp.remove(P2)
        if _vide(fmt, P):
            gp.remove(P)          # P.tail a été transféré à P2 : rien n'est perdu
    return chaine
