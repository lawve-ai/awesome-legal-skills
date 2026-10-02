#!/usr/bin/env python3
# normaliser_guillemets.py — applique la convention du §12 : le second niveau de citation
# se restitue en guillemets droits " … ", le premier niveau reste en « … ».
#
# MÉTHODE. Automate de profondeur sur le fichier entier (et non ligne par ligne : les
# citations en liste à puces s'étendent sur plusieurs lignes). Sur « la profondeur monte,
# sur » elle descend. Seuls les guillemets ouvrant ou fermant à une profondeur >= 2 sont
# convertis. Deux paires successives non imbriquées (« A » et « B ») ne sont pas touchées.
#
# GARDE-FOUS. Aucun caractère autre que « et » n'est modifié : le script vérifie, après
# transformation, que le texte privé de tous les guillemets (français et droits) est
# rigoureusement identique à l'original privé des siens. Il refuse d'écrire sinon.
#
# USAGE : python3 scripts/normaliser_guillemets.py [--dry-run]

import sys, glob, os

BUILD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def normaliser(txt):
    out, prof, n = [], 0, 0
    for c in txt:
        if c == '\u00ab':
            prof += 1
            if prof >= 2: out.append('"'); n += 1; continue
        elif c == '\u00bb':
            if prof >= 2: out.append('"'); n += 1; prof -= 1; continue
            prof = max(0, prof - 1)
        out.append(c)
    return ''.join(out), n, prof

def sans_guillemets(s):
    return s.replace('\u00ab', '').replace('\u00bb', '').replace('"', '')

def main():
    dry = '--dry-run' in sys.argv
    total, fichiers = 0, 0
    for f in sorted(glob.glob(BUILD + '/*.md')):
        b = os.path.basename(f)
        if b in ('CHANGELOG.md', 'README.md', 'NOTICES.md', 'VERIFICATION.md', 'SKILL.md', 'INDEX_MAITRE.md'):
            continue
        src = open(f, encoding='utf-8').read()
        new, n, prof_finale = normaliser(src)
        if n == 0:
            continue
        # garde-fou 1 : aucun caractère hors guillemets n'a bougé
        assert sans_guillemets(src) == sans_guillemets(new), f'ALTÉRATION DE TEXTE dans {b}'
        # garde-fou 2 : la profondeur retombe à zéro (guillemets appariés sur le fichier)
        if prof_finale != 0:
            print(f'  !! {b} : profondeur finale {prof_finale} — guillemets non appariés, FICHIER IGNORÉ')
            continue
        # garde-fou 3 : plus aucun guillemet français de second niveau ne subsiste
        _, reste, _ = normaliser(new)
        assert reste == 0, f'{b} : normalisation incomplète'
        print(f'{b:<45} {n:>4} guillemets convertis')
        total += n; fichiers += 1
        if not dry:
            open(f, 'w', encoding='utf-8').write(new)
    print(f'\n{total} guillemets de second niveau convertis dans {fichiers} fichier(s)'
          + (' [DRY-RUN, rien écrit]' if dry else ''))

if __name__ == '__main__':
    main()
