# Liste blanche du contrôle de bornes v3 (`controle_bornes_v3.py`)

Classes d'écart **écartées par construction** (comptées, non listées) — chaque classe repose sur une règle du SKILL.md ou sur une limite documentée de l'extraction :

| Classe | Effectif (4 sept. 2026) | Fondement |
|---|---|---|
| `ESPACE` | ~1 470 | espaces, sauts de ligne, césures de fin de ligne : artefacts de mise en page |
| `PUCE` | 345 | glyphe de liste de la source (\uf0d8, •, ─, −, →) rendu par une sous-puce markdown `- *…*` ; texte identique |
| `APPEL_NOTE_RETIRE` | 110 | chiffre d'appel de note (1-3 chiffres) collé au texte source, retiré de la citation — SKILL.md §12 |
| `GLYPHE` | 5 | apostrophes courbes ‘ ’ ‚ vs ' ; tiret insécable U+2011 vs `-` : variantes indécidables à l'extraction |

Signaux **conservés dans le rapport** et à confronter : `DEBUT`, `FIN`, `PONCT`, `PONCT_AJOUT/*`, `FIDELITE/*`, `NOTE`.

État au 9 septembre 2026 (v2.5.2) : tous signaux à 0, hors `NON_LOCALISE` 35, `FIDELITE/TEXTE` 8 et `PONCT_QUEUE` 2, en liste blanche ci-dessous.

## Entrées unitaires en liste blanche

**`PONCT_QUEUE` (2)** — clôture `[…]"` d'une citation de second niveau que la source poursuit ; le script lit le guillemet droit comme traîne non retrouvée. index_AMF_2025.md l. 62 (p. 88) et l. 417 (p. 115), vérifiées au rendu de page le 8 septembre 2026.

**`FIDELITE/TEXTE` (8)** — artefacts d'extraction ou conventions de rendu, confrontés le 9 septembre 2026 :
- numéro de page inséré dans le flux (« les - 11 raisons ») : index_AMF_2023.md l. 403 ;
- appel de note collé au mot (« Statement40which ») : index_ESMA_ECEP_2025.md l. 76 ;
- appel de note de tableau « (1) » retiré : index_HCGE_2022.md l. 616 ;
- numéro de note et glyphe de puce insérés (« suivante : 3 − Dès lors ») : index_HCGE_GUIDE_APPLICATION_2024.md l. 207 ;
- guillemets de second niveau : la source emploie ″ ou ‘ … ' là où l'index emploie des guillemets droits (§ 2.3) : index_HCGE_2020.md l. 17, index_HCGE_2025.md l. 91 (2 occurrences).

**`NON_LOCALISE` (35)** — inchangé (voir la liste du 8 septembre 2026).

## Frontières établies au rendu de page — audit du 16 septembre 2026

Ces seize entrées portaient une marque d'omission que l'audit neutre a jugée superflue **après confrontation
à l'image de la page** : la citation ouvre ou ferme sur une frontière réelle (début de puce, début de note,
paragraphe suivant un intertitre, fin d'item, fin de phrase, fermeture des guillemets de la source). Les
marques ont été retirées. `controle_bornes_v3.py` continue de les signaler `DEBUT` ou `FIN` parce qu'il lit
la **couche texte**, où les puces, les intertitres et les bornes de notes disparaissent. En cas de divergence
entre le script et le rendu, **le rendu fait foi** : ne pas relancer `--corriger --elider` sur ces entrées.

| Fichier | Ligne | Signal | Frontière constatée au rendu |
|---|---|---|---|
| index_AMF_2020.md | 223 | DEBUT, FIN | item de liste (cadre légal SRD 2), complet aux deux bornes |
| index_AMF_2021.md | 240 | FIN | la source ferme ses guillemets après « pandémie de Covid-19 » |
| index_AMF_2021.md | 242 | FIN | la source ferme ses guillemets après « en France » |
| index_AMF_2021.md | 765 | DEBUT | début de puce (p. 117) |
| index_AMF_2023.md | 318 | DEBUT | début d'item d'énumération (p. 22) |
| index_AMF_2023.md | 397 | DEBUT | début de la note 9 (p. 10) |
| index_AMF_2025.md | 398 | FIN | fin de phrase (p. 109) |
| index_AMF_2025.md | 399 | DEBUT | paragraphe suivant l'intertitre « 2.2. Diversité, équité et inclusion » (p. 110) |
| index_AMF_CSRD_WAY_FORWARD_2025.md | 19, 112, 322, 379 | FIN | fin de puce ou fin de planche |
| index_AMF_DURABILITE_2024.md | 144 | FIN | fin d'item d'énumération (p. 19) |
| index_ESMA_ECEP_2025.md | 76 | DEBUT | paragraphe suivant l'intertitre « SECTION 2: PRIORITIES RELATED TO SUSTAINABILITY STATEMENTS » (p. 5) |
| index_HCGE_2021.md | 182 | DEBUT | début de puce (p. 13) |

## Signaux de ponctuation en liste blanche (16 septembre 2026)

| Fichier | Ligne | Signal | Motif |
|---|---|---|---|
| index_AMF_2023.md | 438 | PONCT_AJOUT/PAREN | la source imprime « (ESG)25. » : l'index referme la parenthèse et reprend le point qui suit l'appel de note ; le script lit la parenthèse de la source comme une ponctuation non reprise |
| index_AMF_2025.md | 398 | PONCT_AJOUT/SUITE | la citation se clôt sur la fin de phrase (« …supprimée par le législateur. ») ; le script lit la virgule d'un autre segment |
| index_Senat_Rietmann_2025.md | 78 | PONCT_AJOUT/SUITE | la source imprime « 36,13 %9. » : le « % » est dans la citation, le point suit l'appel de note |
| index_AMF_2022.md | 399 | GUILLEMET_INTERNE | la source encadre tout le passage cité (note 73, p. 19) ; l'index le rend avec ses propres guillemets |
| index_AMF_2024.md | 228 | ELISION_SUPERFLUE/FIN | la source poursuit « », intervenue dans le cadre du "point"… » : la marque d'omission est licite (audit du 16 septembre, T28) |
| index_AMF_2025.md | 299 | ELISION_SUPERFLUE/DEBUT | la citation reprend en milieu de phrase « Ces allègements ont finalement été… » |
| index_AMF_CSRD_WAY_FORWARD_2025.md | 190 | ELISION_SUPERFLUE/DEBUT | la source ouvre l'item sur « Good practice observed: » puis enchaîne : la marque est licite |
| index_HCGE_GUIDE_APPLICATION_2024.md | 512 | ELISION_SUPERFLUE/FIN_BLOC | la source poursuit « (conditions internes à l'entreprise ou relatives…) » |
