#!/usr/bin/env python3
# extraire_corpus.py — Prépare le corpus page par page pour `controle_citations_v2.py`.
#
# RAISON D'ÊTRE. L'extraction était jusqu'ici une étape manuelle, décrite en commentaire
# dans le script de contrôle. Elle porte pourtant un piège coûteux : `pdftotext -layout`
# entrelace les deux colonnes des rapports AMF et fabrique des centaines de faux
# « INTROUVABLE » (265 constatés le 10 juillet 2026). La règle est donc câblée ici, et
# non plus confiée à la mémoire de l'opérateur : **aucun appel n'utilise `-layout`**.
#
# Deux formats de source coexistent et sont traités automatiquement :
#   - archives ZIP (magic PK\x03\x04) : une paire N.txt + N.jpeg par page, déjà en ordre
#     de lecture — décompressées telles quelles ;
#   - vrais PDF (magic %PDF) : `pdftotext` SANS `-layout`, en une passe, découpé sur le
#     saut de page (\f) en N.txt.
#
# Sortie : CORPUS/<CLE>/N.txt, où N est l'index physique de page (1-based). Les décalages
# entre pagination physique et pagination imprimée sont auto-détectés par le contrôle.
#
# USAGE : python3 scripts/extraire_corpus.py [--corpus /home/claude/tests] [--force]

import os, sys, glob, shutil, zipfile, subprocess

CORPUS = '/home/claude/tests'

# clé de corpus -> chemins candidats, par ordre de préférence
SOURCES = {
    'AMF_2020':        ['/mnt/project/AMF_2020.pdf'],
    'AMF_2021_UP':     ['/mnt/user-data/uploads/AMF_2021_compressed.pdf', '/mnt/project/AMF_2021_compressed.pdf'],
    'AMF_2022':        ['/mnt/project/AMF_2022.pdf'],
    'AMF_2023':        ['/mnt/project/AMF_2023.pdf'],
    'AMF_2024':        ['/mnt/project/AMF_2024.pdf'],
    'AMF_2025_UP':     ['/mnt/user-data/uploads/AMF_2025.pdf', '/mnt/project/AMF_2025.pdf'],
    'HCGE_2020':       ['/mnt/project/Rapport_HCGE_2020_compressed.pdf'],
    'HCGE_2021':       ['/mnt/project/Rapport_HCGE_2021_compressed.pdf'],
    'HCGE_2022':       ['/mnt/project/Rapport_HCGE_2022_compressed.pdf'],
    'HCGE_2023':       ['/mnt/user-data/uploads/HCGE_2023.pdf', '/mnt/user-data/uploads/15661-hcge-2024-rapport-hcge-2023-fr-0212.pdf', '/mnt/project/HCGE_2023.pdf'],
    'HCGE_2024':       ['/mnt/project/16213hcgerapport2024frhd_compressed.pdf'],
    'HCGE_2025':       ['/mnt/project/17165hcgerapport2025frvfinale_compressed.pdf'],
    'CODE':            ['/mnt/project/Code_AFEP_MEDEF_decembre_2022.pdf'],
    'ESMA_UP':         ['/mnt/project/ESMA_PRIORITE__2025.pdf'],
    'SENAT':           ['/mnt/user-data/uploads/r24-808-11.pdf', '/mnt/project/r24-808-11.pdf'],
    'GUIDE24':         ['/mnt/user-data/uploads/2024_Guide_Mars.pdf', '/mnt/project/2024_Guide_Mars.pdf'],
    'GUIDE25':         ['/mnt/user-data/uploads/17072-2025-guide-decembre-2025.pdf', '/mnt/project/17072-2025-guide-decembre-2025.pdf'],
    'DOC2102':         ['/mnt/user-data/uploads/2021-02-decembre-2024.pdf', '/mnt/project/2021-02-decembre-2024.pdf'],
    'DURABILITE_2024': ['/mnt/project/AMF_DURABILITE__2024.pdf'],
    'DOC2508':         ['/mnt/project/amfrecommandationdoc202508arretedescomptes2025.pdf'],
    'CSRD':            ['/mnt/project/amf_study_csrd_reporting_the_way_forward_2025_2.pdf'],
    'EUROPLACE':       ['/mnt/project/link_php.pdf'],
}

def magic(p):
    with open(p, 'rb') as f:
        h = f.read(4)
    return 'zip' if h == b'PK\x03\x04' else ('pdf' if h == b'%PDF' else '?')

def extraire_zip(src, dst):
    with zipfile.ZipFile(src) as z:
        z.extractall(dst)
    # aplatit un éventuel sous-répertoire unique
    ent = [e for e in os.listdir(dst) if not e.startswith('.')]
    if len(ent) == 1 and os.path.isdir(os.path.join(dst, ent[0])):
        sub = os.path.join(dst, ent[0])
        for f in os.listdir(sub):
            shutil.move(os.path.join(sub, f), os.path.join(dst, f))
        os.rmdir(sub)
    return len(glob.glob(dst + '/*.txt'))

def extraire_pdf(src, dst):
    # RÈGLE CÂBLÉE : jamais -layout (entrelacement des colonnes AMF).
    r = subprocess.run(['pdftotext', src, '-'], capture_output=True, text=True, errors='ignore')
    if r.returncode != 0:
        raise RuntimeError('pdftotext a échoué sur ' + src)
    pages = r.stdout.split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    for i, p in enumerate(pages, 1):
        open(os.path.join(dst, f'{i}.txt'), 'w', encoding='utf-8').write(p)
    return len(pages)

def main():
    corpus = CORPUS
    force = '--force' in sys.argv
    if '--corpus' in sys.argv:
        corpus = sys.argv[sys.argv.index('--corpus') + 1]
    os.makedirs(corpus, exist_ok=True)

    faits, absents = [], []
    for cle, cands in sorted(SOURCES.items()):
        dst = os.path.join(corpus, cle)
        if os.path.isdir(dst) and glob.glob(dst + '/*.txt') and not force:
            faits.append((cle, len(glob.glob(dst + '/*.txt')), 'déjà extrait'))
            continue
        src = next((c for c in cands if os.path.exists(c)), None)
        if src is None:
            absents.append(cle)
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst, exist_ok=True)
        fmt = magic(src)
        n = extraire_zip(src, dst) if fmt == 'zip' else extraire_pdf(src, dst)
        faits.append((cle, n, fmt + ' — ' + os.path.basename(src)))

    for cle, n, o in faits:
        print(f'{cle:<18} {n:>4} pages   {o}')
    if absents:
        print('\nSOURCES ABSENTES (citations NON VÉRIFIABLES) : ' + ', '.join(absents))
    print(f'\n{len(faits)} document(s) prêts dans {corpus}')

if __name__ == '__main__':
    main()
