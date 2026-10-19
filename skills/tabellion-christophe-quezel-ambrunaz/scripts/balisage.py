# -*- coding: utf-8 -*-
"""Relevé d'un modèle (analyser) et application d'un plan de balisage (baliser)."""
import copy
import json
import re
import shutil
import zipfile

from lxml import etree

from documents import (ouvrir, q, NS, SEP, texte_paragraphe, texte_segments, regrouper, poser_marqueur, remonter,
                       ErreurDocument, XML_SPACE, lire)
from syntaxe import RE_BALISE

CODES_PARTIES = [(r"word/document\.xml", "D"), (r"content\.xml", "D"), (r"styles\.xml", "S"),
                 (r"word/header(\d*)\.xml", "E"), (r"word/footer(\d*)\.xml", "P"),
                 (r"word/footnotes\.xml", "N"), (r"word/endnotes\.xml", "NF")]
ORDRE_RPR = ["rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike", "outline", "shadow",
             "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing", "w", "kern",
             "position", "sz", "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs",
             "em", "lang", "eastAsianLayout", "specVanish", "oMath", "rPrChange"]
JAUNE, CYAN = "yellow", "cyan"


def code_partie(nom):
    for motif, code in CODES_PARTIES:
        m = re.fullmatch(motif, nom)
        if m:
            return code + (m.group(1) if m.groups() and m.group(1) else "")
    return nom


def index_paragraphes(fmt):
    """{'D12': (partie, element)} dans l'ordre du document."""
    idx = {}
    for partie in fmt.parties():
        racine = fmt.arbre(partie)
        code = code_partie(partie)
        for i, p in enumerate(fmt.paragraphes(racine), start=1):
            idx[f"{code}{i}"] = (partie, p)
    return idx


# =================================================================== analyser
INDICES = [
    (r"(?i)^\s*(article|art\.)\s+\d+", "numérotation manuelle d'article"),
    (r"(?i)\b(?:à|a) l'article\s+\d+|\bcf\.?\s+(?:article|art\.)\s*\d+|\bci-(?:dessus|dessous|après)\b", "renvoi interne"),
    (r"\((?:e|s|es|x|ne|nes|ère|ères|euse|rice|trice)\)", "accord à baliser"),
    (r"…{2,}|\.{4,}|_{3,}|X{3,}|\[\s*\]|\[\s*…\s*\]|<\s*>", "emplacement à remplir"),
    (r"\b\d{1,2}(?:er)?\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}|\b\d{2}/\d{2}/\d{4}\b", "date"),
    (r"\d[\d\s  .]*(?:,\d+)?\s*(?:€|euros?\b|EUR\b)", "montant"),
]


def analyser(chemin):
    fmt = ouvrir(chemin)
    lignes, infos = [], {"format": fmt.nom, "parties": fmt.parties(), "alertes": []}
    if fmt.suivi_modifications():
        infos["alertes"].append("MODIFICATIONS SUIVIES présentes : demander à l'utilisateur de les accepter ou refuser avant tout balisage.")
    if fmt.commentaires():
        infos["alertes"].append("Commentaires présents : ils seraient reproduits dans chaque document généré.")
    for nom in fmt.parties():
        r = fmt.arbre(nom)
        if fmt.nom == "docx":
            champs = [t.text for t in r.iter(q("w", "instrText")) if t.text and t.text.strip()]
            champs += [e.get(q("w", "instr")) for e in r.iter(q("w", "fldSimple"))]
            if champs:
                infos["alertes"].append(f"Champs Word dans {nom} : " + "; ".join(sorted({c.strip()[:40] for c in champs})))
            if r.find(".//" + q("w", "sdt")) is not None:
                infos["alertes"].append(f"Contrôles de contenu dans {nom} : ne pas y placer de balises.")
            if r.find(".//" + q("w", "txbxContent")) is not None:
                infos["alertes"].append(f"Zones de texte dans {nom} : leurs paragraphes sont relevés ; vérifier le rendu.")
    idx = index_paragraphes(fmt)
    compte = {}
    for code, (partie, p) in idx.items():
        texte = "".join(texte_segments(fmt.segments(p))).replace(SEP, "⇥")
        if not texte.strip():
            continue
        drapeaux = []
        if fmt.nom == "docx":
            ppr = p.find(q("w", "pPr"))
            if ppr is not None:
                st = ppr.find(q("w", "pStyle"))
                if st is not None:
                    drapeaux.append(st.get(q("w", "val")))
                if ppr.find(q("w", "numPr")) is not None:
                    drapeaux.append("liste numérotée")
        else:
            if p.get(q("text", "style-name")):
                drapeaux.append(p.get(q("text", "style-name")))
            if p.getparent() is not None and p.getparent().tag == q("text", "list-item"):
                drapeaux.append("liste")
        tr, tbl = fmt.ligne_et_tableau(p)
        if tr is not None:
            lignes_t = [x for x in tbl if x.tag == tr.tag]
            cellules = [x for x in tr if isinstance(x.tag, str) and x.tag == p.getparent().tag]
            drapeaux.append(f"tableau, ligne {lignes_t.index(tr) + 1 if tr in lignes_t else '?'}, "
                            f"cellule {cellules.index(p.getparent()) + 1}")
        trouves = []
        for motif, nom_indice in INDICES:
            if re.search(motif, texte):
                trouves.append(nom_indice)
                compte[nom_indice] = compte.get(nom_indice, 0) + 1
        if RE_BALISE.search(texte):
            trouves.append("balises déjà présentes")
        tete = f"[{code}]" + (f" ({'; '.join(drapeaux)})" if drapeaux else "")
        lignes.append(tete + (f" ⟨{', '.join(trouves)}⟩" if trouves else "") + "\n    " + texte)
    infos["indices"] = compte
    return infos, "\n".join(lignes)


# =================================================================== baliser
def _surligner_rpr(rpr, couleur):
    for h in rpr.findall(q("w", "highlight")):
        rpr.remove(h)
    h = etree.Element(q("w", "highlight"))
    h.set(q("w", "val"), couleur)
    rang = ORDRE_RPR.index("highlight")
    for i, c in enumerate(rpr):
        local = etree.QName(c).localname
        if local in ORDRE_RPR and ORDRE_RPR.index(local) > rang:
            rpr.insert(i, h)
            return
    rpr.append(h)


def _style_odt(fmt):
    racine = fmt.arbre("content.xml")
    auto = racine.find(q("office", "automatic-styles"))
    if auto is None:
        auto = etree.Element(q("office", "automatic-styles"))
        racine.insert(1, auto)
    for nom, couleur in (("TbBaliseV", "#ffff00"), ("TbBaliseS", "#00ffff")):
        if auto.find(f"{q('style', 'style')}[@{q('style', 'name')}='{nom}']") is not None:
            continue
        st = etree.SubElement(auto, q("style", "style"))
        st.set(q("style", "name"), nom)
        st.set(q("style", "family"), "text")
        tp = etree.SubElement(st, q("style", "text-properties"))
        tp.set(q("fo", "background-color"), couleur)


def _element_balise(fmt, chaine, texte, est_structure):
    """Construit l'élément (run ou span) portant le texte de la balise, surligné."""
    if fmt.nom == "docx":
        r = etree.Element(q("w", "r"))
        modele_r = next((e for e in chaine if e.tag == q("w", "r")), None)
        rpr = copy.deepcopy(modele_r.find(q("w", "rPr"))) if modele_r is not None and modele_r.find(q("w", "rPr")) is not None \
            else etree.Element(q("w", "rPr"))
        _surligner_rpr(rpr, CYAN if est_structure else JAUNE)
        r.append(rpr)
        t = etree.SubElement(r, q("w", "t"))
        t.set(XML_SPACE, "preserve")
        t.text = texte
        return r
    externe = None
    interne = None
    for e in chaine:
        c = etree.Element(e.tag, attrib=dict(e.attrib))
        if externe is None:
            externe = c
        else:
            interne.append(c)
        interne = c
    span = etree.Element(q("text", "span"))
    span.set(q("text", "style-name"), "TbBaliseS" if est_structure else "TbBaliseV")
    span.text = texte
    if externe is None:
        return span
    interne.append(span)
    return externe


def _remplacer_dans(fmt, p, texte_cherche, nouveau, occurrence=None):
    """Remplace une (ou toutes les) occurrence(s) de texte_cherche dans le paragraphe ; renvoie le nombre."""
    segs = fmt.segments(p)
    plat = "".join(texte_segments(segs))
    positions = [m.start() for m in re.finditer(re.escape(texte_cherche), plat)]
    if occurrence is not None:
        if occurrence > len(positions):
            raise ErreurDocument(f"occurrence {occurrence} de « {texte_cherche} » introuvable "
                                 f"({len(positions)} occurrence(s) dans ce paragraphe)")
        positions = [positions[occurrence - 1]]
    for debut in reversed(positions):
        segs = fmt.segments(p)
        regrouper(segs, debut, debut + len(texte_cherche))
        segs = fmt.segments(p)
        pos = 0
        for s in segs:
            longueur = 1 if s is None else len(lire(s))
            if s is not None and pos <= debut < pos + longueur:
                seg, dec = s, debut - pos
                break
            pos += longueur
        m = poser_marqueur(seg, dec, len(texte_cherche), 0)
        chaine = remonter(fmt, m, p)
        if nouveau:
            el = _element_balise(fmt, chaine, nouveau, nouveau.lstrip().startswith("[["))
            el.tail = m.tail
            p.replace(m, el)
        else:
            parent = m.getparent()
            prec = m.getprevious()
            if prec is not None:
                prec.tail = (prec.tail or "") + (m.tail or "")
            else:
                parent.text = (parent.text or "") + (m.tail or "")
            parent.remove(m)
    return len(positions)


def _paragraphe_directive(fmt, reference, texte):
    if fmt.nom == "docx":
        p = etree.Element(q("w", "p"))
        r = _element_balise(fmt, [], texte, True)
        p.append(r)
        return p
    p = etree.Element(q("text", "p"))
    p.append(_element_balise(fmt, [], texte, True))
    return p


def _ligne_directive(fmt, tr, texte):
    nouvelle = copy.deepcopy(tr)
    cell_tag = q("w", "tc") if fmt.nom == "docx" else q("table", "table-cell")
    premiere = True
    for cell in [c for c in nouvelle if isinstance(c.tag, str) and c.tag == cell_tag]:
        garder = []
        for enfant in list(cell):
            if fmt.nom == "docx" and enfant.tag == q("w", "tcPr"):
                continue
            cell.remove(enfant)
        p = _paragraphe_directive(fmt, None, texte) if premiere else \
            (etree.Element(q("w", "p")) if fmt.nom == "docx" else etree.Element(q("text", "p")))
        cell.append(p)
        premiere = False
    if fmt.nom == "docx":
        trpr = nouvelle.find(q("w", "trPr"))
        if trpr is not None:
            for h in trpr.findall(q("w", "tblHeader")):
                trpr.remove(h)
    return nouvelle


def baliser(entree, plan, sortie):
    fmt = ouvrir(entree)
    if fmt.nom == "odt":
        _style_odt(fmt)
    idx = index_paragraphes(fmt)
    compte_rendu, erreurs = [], []

    def para(code):
        if code not in idx:
            raise ErreurDocument(f"paragraphe {code} inconnu")
        return idx[code][1]

    # résolution préalable : les références visent le document d'origine
    ops = []
    for k, op in enumerate(plan.get("operations", [])):
        try:
            o = dict(op)
            for cle in ("paragraphe", "de", "a", "jusqua"):
                if cle in o:
                    o["_" + cle] = para(o[cle])
            ops.append((k, o))
        except ErreurDocument as e:
            erreurs.append(f"opération {k + 1} : {e}")

    for k, o in ops:
        try:
            nature = o["op"]
            if nature == "remplacer":
                n = _remplacer_dans(fmt, o["_paragraphe"], o["texte"], o.get("par", ""), o.get("occurrence", 1))
                compte_rendu.append(f"{o['paragraphe']} : « {o['texte']} » → {o.get('par', '(supprimé)')}")
            elif nature == "remplacer_partout":
                total = 0
                for code, (partie, p) in idx.items():
                    if p.getparent() is None:
                        continue
                    if o["texte"] in texte_paragraphe(fmt, p).replace(" ", " ") or o["texte"] in "".join(texte_segments(fmt.segments(p))):
                        total += _remplacer_dans(fmt, p, o["texte"], o.get("par", ""))
                compte_rendu.append(f"partout : « {o['texte']} » → {o.get('par', '(supprimé)')} ({total} occurrence(s))")
                if total == 0:
                    erreurs.append(f"opération {k + 1} : « {o['texte']} » introuvable")
            elif nature in ("inserer_avant", "inserer_apres"):
                p = o["_paragraphe"]
                nouveau = _paragraphe_directive(fmt, p, o["texte"])
                parent = p.getparent()
                parent.insert(parent.index(p) + (0 if nature == "inserer_avant" else 1), nouveau)
                compte_rendu.append(f"{o['paragraphe']} : {o['texte']} inséré {'avant' if nature == 'inserer_avant' else 'après'}")
            elif nature == "entourer":
                p1, p2 = o["_de"], o["_a"]
                if p1.getparent() is not p2.getparent():
                    raise ErreurDocument("les paragraphes de début et de fin ne sont pas dans le même emplacement "
                                         "(corps, cellule) : entourer des paragraphes d'un même niveau")
                parent = p1.getparent()
                parent.insert(parent.index(p1), _paragraphe_directive(fmt, p1, o["ouverture"]))
                parent.insert(parent.index(p2) + 1, _paragraphe_directive(fmt, p2, o["fermeture"]))
                compte_rendu.append(f"{o['de']}–{o['a']} : {o['ouverture']} … {o['fermeture']}")
            elif nature == "entourer_lignes":
                tr1, tbl1 = fmt.ligne_et_tableau(o["_paragraphe"])
                tr2, tbl2 = fmt.ligne_et_tableau(o.get("_jusqua", o["_paragraphe"]))
                if tr1 is None or tbl1 is not tbl2:
                    raise ErreurDocument("entourer_lignes : les paragraphes doivent être dans des lignes d'un même tableau")
                tbl1.insert(tbl1.index(tr1), _ligne_directive(fmt, tr1, o["ouverture"]))
                tbl1.insert(tbl1.index(tr2) + 1, _ligne_directive(fmt, tr2, o["fermeture"]))
                compte_rendu.append(f"lignes {o['paragraphe']}–{o.get('jusqua', o['paragraphe'])} : {o['ouverture']} … {o['fermeture']}")
            else:
                raise ErreurDocument(f"opération inconnue « {nature} »")
        except (ErreurDocument, KeyError, StopIteration) as e:
            erreurs.append(f"opération {k + 1} ({o.get('op')}) : {e}")

    with zipfile.ZipFile(entree) as zin, zipfile.ZipFile(sortie, "w") as zout:
        for info in zin.infolist():
            if info.filename in fmt.arbres:
                donnees = fmt.serialiser(info.filename)
            else:
                donnees = zin.read(info.filename)
            compression = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(info, donnees, compress_type=compression)
    return compte_rendu, erreurs
