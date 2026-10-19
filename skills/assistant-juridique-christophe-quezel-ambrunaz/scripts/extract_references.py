#!/usr/bin/env python3
"""
extract_references.py — Extraction de références juridiques depuis un document Word ou texte.

Usage :
    python3 scripts/extract_references.py --file document.docx
    python3 scripts/extract_references.py --file document.txt
    python3 scripts/extract_references.py --text "L'article 1240 du code civil..."

Sortie : JSON structuré avec les références détectées et leur localisation.

Note : Pour les PDF, convertir d'abord en texte (via pandoc ou autre) puis passer le texte.
       Le parsing Word utilise le module zipfile pour lire le XML directement.
"""

import argparse
import json
import re
import sys
import os


# Patterns de détection des références juridiques
PATTERNS = {
    "JURIS_CASS": [
        # Cass. civ. 1re, 12 juill. 2023, n° 21-12.345 ; Cass. 2e civ. ; Civ. 2e ;
        # Cass. ass. plén. ; Ch. mixte ; Ch. réunies ; soc., com., crim.
        r"(?:Cass\.?,?\s+)?(?:[Cc]iv\.\s*\d+(?:re|er|e)|\d+(?:re|e)\s+civ\.|[Cc]om\.|[Ss]oc\.|[Cc]rim\.|[Aa]ss\.\s*pl[ée]n\.|[Cc]h\.\s*(?:mixte|r[ée]unies))[,\s]+\d{1,2}(?:er)?\s+\w+\.?\s+\d{4},?\s*n°\s*[A-Z]?\s*\d{2}-\d{2}[\.\s]?\d{3}",
    ],
    "JURIS_CE": [
        r"CE[,\s]+(?:Ass\.|Sect\.|ss-sect\.)?[,\s]*\d{1,2}\s+\w+\.?\s+\d{4},?\s*n°\s*\d{4,7}",
        r"Conseil\s+d['']\s*[EÉ]tat[,\s]+\d{1,2}\s+\w+\.?\s+\d{4}",
    ],
    "JURIS_CONST": [
        r"Cons\.\s*const\.[,\s]+\d{1,2}\s+\w+\.?\s+\d{4},?\s*n°\s*\d{2,4}-\d{2,4}\s*(?:QPC|DC|LP|FNR)?",
    ],
    "JURIS_CA": [
        r"CA\s+[A-ZÀ-Ü][a-zà-ü\-]+(?:\s+[a-zà-ü\-]+)*[,\s]+(?:pôle\s+\d+,?\s*)?(?:ch\.\s*\d+[,\s]+)?\d{1,2}\s+\w+\.?\s+\d{4}",
    ],
    "CODE_ARTICLE": [
        r"[Aa]rt(?:icle)?\.?\s+(?:L\.?\s*|R\.?\s*|D\.?\s*|A\.?\s*)?\d+(?:-\d+)*(?:\s+(?:du\s+)?(?:code\s+|C\.\s*)\w+(?:\s+\w+)*)",
        r"[Aa]rt(?:icle)?\.?\s+(?:L\.?\s*|R\.?\s*|D\.?\s*|A\.?\s*)?\d+(?:-\d+)*\s+(?:C\.\s*(?:civ|pén|com|trav|consom|rur|env|santé|sécu)|CPC|CPP|CJA|CGCT|CSP|CSS)",
    ],
    "LOI_DECRET": [
        r"[Ll]oi\s+n°\s*\d{2,4}-\d{1,5}\s+du\s+\d{1,2}\s+\w+\.?\s+\d{4}",
        r"[Dd][ée]cr(?:et)?\.?\s+n°\s*\d{2,4}-\d{1,5}\s+du\s+\d{1,2}\s+\w+\.?\s+\d{4}",
        r"[Oo]rd(?:onnance)?\.?\s+n°\s*\d{2,4}-\d{1,5}\s+du\s+\d{1,2}\s+\w+\.?\s+\d{4}",
    ],
    "DOCTRINE": [
        # Nom, « Titre », Revue Année, p. X
        r"[A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-Z]\.)+[,\s]+[«\"][^»\"]+[»\"][,\s]+[A-Z][a-zà-ü\.]+(?:\s+[a-zà-ü\.]+)*\s+\d{4}",
        # Nom (Init.), Titre, Éditeur, Année
        r"[A-ZÀ-Ü][a-zà-ü]+\s*\([A-Z][a-z]?\.\)[,\s]+[A-ZÀ-Ü][^,]+,\s*[A-ZÀ-Ü][^,]+,\s*\d{4}",
    ],
    "CEDH": [
        r"CEDH[,\s]+\d{1,2}\s+\w+\.?\s+\d{4}[,\s]+[A-ZÀ-Ü][a-zà-ü]+\s+c[/\.]\s*[A-ZÀ-Ü]",
    ],
    "CJUE": [
        r"CJ(?:UE|CE)[,\s]+\d{1,2}\s+\w+\.?\s+\d{4}[,\s]+(?:aff\.\s*)?C-\d+/\d+",
    ],
}


def extract_text_from_docx(filepath):
    """Extrait le texte d'un fichier .docx (ZIP/XML)."""
    import zipfile
    import xml.etree.ElementTree as ET

    paragraphs = []
    try:
        with zipfile.ZipFile(filepath, "r") as z:
            # Corps du document
            if "word/document.xml" in z.namelist():
                tree = ET.parse(z.open("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                for para in tree.findall(".//w:p", ns):
                    text = "".join(r.text or "" for r in para.findall(".//w:t", ns))
                    if text.strip():
                        paragraphs.append(text)

            # Notes de bas de page
            if "word/footnotes.xml" in z.namelist():
                tree = ET.parse(z.open("word/footnotes.xml"))
                for fn in tree.findall(".//w:footnote", ns):
                    fn_id = fn.get(f"{{{ns['w']}}}id", "")
                    if fn_id in ("0", "-1"):  # Notes système, ignorer
                        continue
                    text = "".join(r.text or "" for r in fn.findall(".//w:t", ns))
                    if text.strip():
                        paragraphs.append(f"[NOTE {fn_id}] {text}")

            # Notes de fin
            if "word/endnotes.xml" in z.namelist():
                tree = ET.parse(z.open("word/endnotes.xml"))
                for en in tree.findall(".//w:endnote", ns):
                    en_id = en.get(f"{{{ns['w']}}}id", "")
                    if en_id in ("0", "-1"):
                        continue
                    text = "".join(r.text or "" for r in en.findall(".//w:t", ns))
                    if text.strip():
                        paragraphs.append(f"[ENDNOTE {en_id}] {text}")
    except Exception as e:
        return None, str(e)

    return paragraphs, None


def extract_references_from_text(text_lines):
    """Détecte les références juridiques dans un texte."""
    references = []
    ref_id_counters = {}

    for line_num, line in enumerate(text_lines):
        # Déterminer la localisation
        loc = "Corps"
        if line.startswith("[NOTE "):
            match = re.match(r"\[NOTE (\d+)\]", line)
            loc = f"Note n°{match.group(1)}" if match else "Note"
            line = re.sub(r"^\[(?:END)?NOTE \d+\]\s*", "", line)
        elif line.startswith("[ENDNOTE "):
            match = re.match(r"\[ENDNOTE (\d+)\]", line)
            loc = f"Note de fin n°{match.group(1)}" if match else "Note de fin"
            line = re.sub(r"^\[(?:END)?NOTE \d+\]\s*", "", line)

        # Chercher les références (sans doublon sur un même segment)
        taken = []
        for ref_type, patterns in PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, line):
                    if any(match.start() < e and match.end() > b for b, e in taken):
                        continue
                    taken.append((match.start(), match.end()))
                    # Générer l'ID
                    prefix_map = {
                        "JURIS_CASS": "J", "JURIS_CE": "J", "JURIS_CONST": "J",
                        "JURIS_CA": "J", "CODE_ARTICLE": "L", "LOI_DECRET": "L",
                        "DOCTRINE": "D", "CEDH": "J", "CJUE": "J",
                    }
                    prefix = prefix_map.get(ref_type, "X")
                    ref_id_counters[prefix] = ref_id_counters.get(prefix, 0) + 1
                    ref_id = f"{prefix}{ref_id_counters[prefix]:02d}"

                    # Extraire le contexte (5 mots avant et après)
                    start = max(0, match.start() - 50)
                    end = min(len(line), match.end() + 50)
                    context = line[start:end].strip()

                    references.append({
                        "id": ref_id,
                        "type": ref_type,
                        "text_extracted": match.group().strip(),
                        "location": loc,
                        "line": line_num + 1,
                        "context": context[:100],
                    })

    return references


def main():
    parser = argparse.ArgumentParser(description="Extraction de références juridiques")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", "-f", help="Fichier Word (.docx) ou texte à analyser")
    group.add_argument("--text", "-t", help="Texte brut à analyser")

    args = parser.parse_args()

    if args.text:
        text_lines = args.text.split("\n")
    elif args.file:
        ext = os.path.splitext(args.file)[1].lower()
        if ext == ".docx":
            text_lines, error = extract_text_from_docx(args.file)
            if error:
                print(json.dumps({"error": f"Erreur lecture DOCX: {error}"}))
                sys.exit(1)
        elif ext in (".txt", ".md"):
            with open(args.file, "r", encoding="utf-8") as f:
                text_lines = f.readlines()
        else:
            print(json.dumps({"error": f"Format non supporté : {ext}. Utilisez .docx, .txt ou .md"}))
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    references = extract_references_from_text(text_lines)

    # Statistiques
    type_counts = {}
    for ref in references:
        t = ref["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    output = {
        "total": len(references),
        "by_type": type_counts,
        "references": references,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
