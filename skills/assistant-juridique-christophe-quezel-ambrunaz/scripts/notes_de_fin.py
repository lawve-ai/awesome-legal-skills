#!/usr/bin/env python3
"""
notes_de_fin.py — Notes de fin à numérotation arabe continue dans un .docx.

Les livrables de la skill exigent des notes de fin (jamais de notes de bas de
page), numérotées en chiffres arabes. Deux difficultés récurrentes :
  - pandoc (Markdown -> .docx) produit des notes de BAS DE PAGE ;
  - Word numérote par défaut les notes de fin en chiffres romains minuscules
    (i, ii, iii), notamment dans les fichiers produits par docx-js.

Ce script :
  1. convertit toutes les notes de bas de page en notes de fin (footnotes.xml
     -> endnotes.xml, appels w:footnoteReference -> w:endnoteReference, styles
     d'appel conservés) ;
  2. impose la numérotation décimale des notes de fin dans chaque section
     (w:endnotePr/w:numFmt = decimal) et dans settings.xml ;
  3. signale les appels multiples à une même note (qui produisent des notes
     fantômes) : préférer un renvoi « préc. note n ».

Usage :
  python3 notes_de_fin.py entree.docx [sortie.docx]
  (sans sortie : le fichier d'entrée est réécrit)

Sortie JSON : nombre de notes converties, appels multiples détectés.
"""

import json
import re
import shutil
import sys
import tempfile
import zipfile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ENDNOTES_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes"
)
ENDNOTES_CT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"
)


def _read(z, name):
    try:
        return z.read(name).decode("utf-8")
    except KeyError:
        return None


def _endnote_pr_block():
    return '<w:endnotePr><w:numFmt w:val="decimal"/></w:endnotePr>'


def _fix_sectpr(xml):
    """Insère ou corrige w:endnotePr (numFmt decimal) dans chaque w:sectPr,
    à la place prévue par le schéma (après header/footerReference et
    footnotePr, avant tout autre élément)."""

    def repl(m):
        sect = m.group(0)
        if "<w:endnotePr" in sect:
            sect = re.sub(r"<w:endnotePr>.*?</w:endnotePr>|<w:endnotePr/>",
                          _endnote_pr_block(), sect, flags=re.S)
            return sect
        open_tag_end = sect.index(">") + 1
        if sect[open_tag_end - 2] == "/":  # <w:sectPr/>
            return "<w:sectPr>" + _endnote_pr_block() + "</w:sectPr>"
        body = sect[open_tag_end:]
        # position après les éléments qui doivent précéder endnotePr
        pos = 0
        for pat in (r"<w:headerReference[^>]*/>", r"<w:footerReference[^>]*/>",
                    r"<w:footnotePr>.*?</w:footnotePr>"):
            for mm in re.finditer(pat, body, flags=re.S):
                pos = max(pos, mm.end())
        body = body[:pos] + _endnote_pr_block() + body[pos:]
        return sect[:open_tag_end] + body

    return re.sub(r"<w:sectPr\b[^>]*/>|<w:sectPr\b.*?</w:sectPr>", repl, xml,
                  flags=re.S)


def _fix_settings(xml):
    if xml is None:
        return None
    block = ('<w:endnotePr><w:numFmt w:val="decimal"/>'
             '<w:endnote w:id="-1"/><w:endnote w:id="0"/></w:endnotePr>')
    if "<w:endnotePr" in xml:
        xml = re.sub(r"<w:endnotePr>.*?</w:endnotePr>", block, xml, flags=re.S)
        return xml
    # endnotePr suit footnotePr s'il existe ; sinon avant w:compat / rsids
    if "</w:footnotePr>" in xml:
        return xml.replace("</w:footnotePr>", "</w:footnotePr>" + block, 1)
    for anchor in ("<w:compat", "<w:rsids", "<m:mathPr", "<w:themeFontLang",
                   "<w:clrSchemeMapping", "<w:decimalSymbol", "<w:listSeparator"):
        i = xml.find(anchor)
        if i != -1:
            return xml[:i] + block + xml[i:]
    return xml.replace("</w:settings>", block + "</w:settings>")


def convert(src, dst):
    report = {"converted_footnotes": 0, "endnotes_total": 0,
              "multiple_calls": [], "output": dst}
    tmp = tempfile.mktemp(suffix=".docx")
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        doc = _read(zin, "word/document.xml")
        foot = _read(zin, "word/footnotes.xml")
        endn = _read(zin, "word/endnotes.xml")
        rels = _read(zin, "word/_rels/document.xml.rels")
        foot_rels = _read(zin, "word/_rels/footnotes.xml.rels")
        endn_rels = _read(zin, "word/_rels/endnotes.xml.rels")
        ctypes = _read(zin, "[Content_Types].xml")
        settings = _read(zin, "word/settings.xml")

        real_foot_ids = []
        if foot:
            real_foot_ids = [i for i in re.findall(r'<w:footnote\b[^>]*w:id="(-?\d+)"', foot)
                             if int(i) > 0]
        if real_foot_ids:
            if endn and re.search(r'<w:endnote\b[^>]*w:id="[1-9]', endn):
                raise SystemExit("Le document contient déjà des notes de fin et des "
                                 "notes de bas de page : conversion ambiguë, abandon.")
            new_endn = foot
            new_endn = new_endn.replace("<w:footnotes", "<w:endnotes").replace(
                "</w:footnotes>", "</w:endnotes>")
            new_endn = re.sub(r"<w:footnote\b", "<w:endnote", new_endn)
            new_endn = new_endn.replace("</w:footnote>", "</w:endnote>")
            new_endn = new_endn.replace("<w:footnoteRef/>", "<w:endnoteRef/>")
            new_endn = new_endn.replace('w:val="FootnoteText"', 'w:val="EndnoteText"') \
                if 'EndnoteText' in (_read(zin, "word/styles.xml") or "") else new_endn
            new_endn = new_endn.replace('w:val="FootnoteReference"', 'w:val="EndnoteReference"') \
                if 'EndnoteReference' in (_read(zin, "word/styles.xml") or "") else new_endn
            # séparateurs requis
            if 'w:id="-1"' not in new_endn:
                sep = ('<w:endnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:endnote>'
                       '<w:endnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:endnote>')
                new_endn = re.sub(r"(<w:endnotes\b[^>]*>)", r"\1" + sep, new_endn, count=1)
            endn = new_endn
            doc = doc.replace("<w:footnoteReference ", "<w:endnoteReference ")
            doc = doc.replace('w:val="FootnoteReference"', 'w:val="EndnoteReference"') \
                if 'EndnoteReference' in (_read(zin, "word/styles.xml") or "") else doc
            # footnotes.xml réduit aux séparateurs
            foot = re.sub(r'<w:footnote\b(?![^>]*w:id="-?[01]")[^>]*>.*?</w:footnote>', "",
                          foot, flags=re.S)
            report["converted_footnotes"] = len(real_foot_ids)
            if endn and "endnotes.xml" not in (rels or ""):
                rid = "rIdEndnotes1"
                rels = rels.replace("</Relationships>",
                                    f'<Relationship Id="{rid}" Type="{ENDNOTES_REL_TYPE}" '
                                    f'Target="endnotes.xml"/></Relationships>')
            if "/word/endnotes.xml" not in ctypes:
                ctypes = ctypes.replace("</Types>",
                                        f'<Override PartName="/word/endnotes.xml" '
                                        f'ContentType="{ENDNOTES_CT}"/></Types>')

        # Les liens, images et autres objets d'une note sont des relations
        # (r:id) propres à la partie qui contient la note. Les notes converties
        # conservent leurs r:id : il faut donc reporter les relations de
        # footnotes.xml vers endnotes.xml, faute de quoi Word déclare le
        # fichier corrompu.
        if real_foot_ids and foot_rels:
            used = set(re.findall(r'r:(?:id|embed|link)="([^"]+)"', endn or ""))
            src_rel = {m.group(1): m.group(0) for m in
                       re.finditer(r'<Relationship\b[^>]*\bId="([^"]+)"[^>]*/>', foot_rels)}
            if endn_rels is None:
                endn_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                             '<Relationships xmlns="http://schemas.openxmlformats.org/'
                             'package/2006/relationships"></Relationships>')
            have = set(re.findall(r'\bId="([^"]+)"', endn_rels))
            add = "".join(src_rel[i] for i in sorted(used) if i in src_rel and i not in have)
            endn_rels = endn_rels.replace("</Relationships>", add + "</Relationships>")
            missing = sorted(i for i in used if i not in src_rel and i not in have)
            report["relations_reportees"] = len(add and re.findall(r"<Relationship\b", add))
            if missing:
                report["relations_introuvables"] = missing

        doc = _fix_sectpr(doc)
        settings = _fix_settings(settings)

        calls = re.findall(r'<w:endnoteReference\b[^>]*w:id="(\d+)"', doc)
        seen = {}
        for c in calls:
            seen[c] = seen.get(c, 0) + 1
        report["multiple_calls"] = [k for k, v in seen.items() if v > 1]
        report["endnotes_total"] = len(set(calls))

        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for n in names:
                if n == "word/document.xml":
                    data = doc
                elif n == "word/footnotes.xml" and foot is not None:
                    data = foot
                elif n == "word/endnotes.xml" and endn is not None:
                    data = endn
                elif n == "word/_rels/document.xml.rels" and rels is not None:
                    data = rels
                elif n == "[Content_Types].xml":
                    data = ctypes
                elif n == "word/settings.xml" and settings is not None:
                    data = settings
                elif n == "word/_rels/endnotes.xml.rels" and endn_rels is not None:
                    continue
                else:
                    zout.writestr(zin.getinfo(n), zin.read(n))
                    written.add(n)
                    continue
                zout.writestr(n, data.encode("utf-8"))
                written.add(n)
            if endn is not None and "word/endnotes.xml" not in written:
                zout.writestr("word/endnotes.xml", endn.encode("utf-8"))
            if endn_rels is not None:
                zout.writestr("word/_rels/endnotes.xml.rels", endn_rels.encode("utf-8"))
    shutil.move(tmp, dst)
    return report


def verifier_relations(path):
    """Contrôle d'intégrité : tout r:id employé dans le corps, les notes de
    fin et les notes de bas de page doit être déclaré dans la table de
    relations de la même partie. Retourne la liste des anomalies."""
    anomalies = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for part in ("word/document.xml", "word/endnotes.xml", "word/footnotes.xml"):
            if part not in names:
                continue
            xml = z.read(part).decode("utf-8")
            used = set(re.findall(r'r:(?:id|embed|link)="([^"]+)"', xml))
            if not used:
                continue
            rels_name = part.replace("word/", "word/_rels/") + ".rels"
            rels = z.read(rels_name).decode("utf-8") if rels_name in names else ""
            have = set(re.findall(r'\bId="([^"]+)"', rels))
            for rid in sorted(used - have):
                anomalies.append(f"{part} : relation {rid} absente de {rels_name}")
    return anomalies


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 2)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src
    rep = convert(src, dst)
    anomalies = verifier_relations(dst)
    if anomalies:
        rep["ERREUR_integrite"] = anomalies
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        print("Fichier invalide pour Word : ne pas le livrer.", file=sys.stderr)
        sys.exit(1)
    rep["integrite_relations"] = "ok"
    if rep["multiple_calls"]:
        rep["avertissement"] = ("Appels multiples à une même note : remplacer les appels "
                                "répétés par un renvoi « préc. note n » pour éviter des notes "
                                "fantômes.")
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
