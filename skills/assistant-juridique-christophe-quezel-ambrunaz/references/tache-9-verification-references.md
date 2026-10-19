# Tâche 9 — Vérification des références

> **Environnement** : espace de travail requis (document miroir annoté par édition XML du .docx). Lorsqu'un dossier connecté existe, y écrire le miroir au fur et à mesure (reprise dans une autre conversation) ; à défaut, remettre le miroir en fin de tâche et, pour un document long, des versions intermédiaires. Pour plus de 15 références, répartir le contrôle de concordance entre vérificateurs indépendants (sous-agents) lorsque l'outil existe. Sans espace de travail (cas résiduel) : indiquer que l'activation de « Exécution de code et création de fichiers » permettrait la tâche, et proposer une vérification en tableau dans la conversation.

## Objectif

Vérifier l'existence et l'exactitude de toutes les références juridiques contenues dans un document. Produire un **document Word miroir** du document original, annoté avec des commentaires indiquant le résultat de chaque vérification.

## ⛔ Interdit absolu — Format du livrable

**Ne JAMAIS produire un rapport de synthèse autonome, un document « à propos » des références, ni un document récapitulatif indépendant du texte original.** Le livrable est EXCLUSIVEMENT le document source (ou sa conversion Word) dont le texte intégral est conservé, annoté par des **commentaires Word** (`w:comment`) insérés dans le XML du document. Si le fichier livré ne contient pas (a) l'intégralité du texte original et (b) des commentaires Word attachés aux passages contenant les références, le livrable est non conforme et doit être refait.

Le tableau récapitulatif (Phase 4) est ajouté **en fin du document miroir**, après le texte original — il ne constitue jamais le livrable à lui seul.

## Principe cardinal

**Source non trouvée ≠ source fausse.** Raisons légitimes d'absence : accès payant, pré-numérisation (avant ~2000), erreur mineure de citation, couverture incomplète des bases Legifrance. Ne jamais qualifier une référence de « fausse » — seulement « non trouvée » ou « non vérifiée ».

## Processus

### Phase 0 — Préparation du document

**EXÉCUTER :**
1. Identifier le document source dans le dossier de travail
2. Si PDF : convertir en Word via `soffice.py --headless --convert-to docx` (le document miroir sera un Word annoté)
3. Si Word : travailler directement sur une copie
4. Décompresser le document avec `python scripts/office/unpack.py [source].docx unpacked/`
5. Le fichier miroir sera reconstruit à partir de ce répertoire `unpacked/` en fin de processus

**⚠️ Le document miroir est le document source lui-même, augmenté de commentaires Word. Ce n'est PAS un nouveau document créé ex nihilo via docx-js.**

### Phase 1 — Extraction exhaustive

Parcourir l'intégralité du document. Extraire **toutes** les références juridiques (corps du texte, notes de bas de page, bibliographie, annexes). Amorcer l'extraction par `scripts/extract_references.py --file [document]`, qui détecte automatiquement les références (jurisprudence, articles de codes, lois/décrets, doctrine) et leur localisation, puis compléter manuellement les références non capturées par les motifs.

Pour chaque référence extraite, constituer un enregistrement :
- **Localisation** : note n°X, corps p. Y, bibliographie
- **Texte extrait** : citation exacte (5-15 mots)
- **Type** : JURIS_CASS, JURIS_CE, JURIS_CA_TJ, JURIS_TA_CAA, JURIS_CONST, CODE_ARTICLE, LOI_DECRET, DOCTRINE, SOURCE_ETRANGERE, AUTRE
- **Référence normalisée** : forme canonique selon `references/format-citations.md` + code de certitude (🟢🟡🟠🔴)
- **Priorité** : P1 (citée >3 fois ou dans intro/conclusion), P2 (citée 1-3 fois), P3 (bibliographie uniquement)

**Déduplication** : si la même référence normalisée apparaît à plusieurs emplacements, une seule vérification suffit. Résultat propagé à toutes les occurrences.

### Phase 2 — Vérification

Vérifier chaque référence unique (après déduplication), par ordre de priorité (P1 → P2 → P3).

**Routage par type :**

| Type | Outil primaire | Stratégie de requête | Fallback |
|---|---|---|---|
| JURIS_CASS | `rechercher_jurisprudence_judiciaire` | Numéro de pourvoi, champ NUM_AFFAIRE, EXACTE | web_search |
| JURIS_CE | `rechercher_jurisprudence_administrative` | Numéro de requête, champ NUM_AFFAIRE, EXACTE | web_search |
| JURIS_CA_TJ | `LibreJustice:search_decisions` (`seat`, ou `mode: "reference"` sur le numéro) puis `get_decision` | Juridiction + n° RG, ou objet de la décision | `OpenLegi:rechercher_jurisprudence_judiciaire` puis web_search |
| JURIS_TA_CAA | `LibreJustice:search_decisions` (`seat: ["TA","CAA"]`) puis `get_decision` | Juridiction + n° requête, ou objet | `OpenLegi:rechercher_jurisprudence_administrative` puis web_search |
| JURIS_CONST | `OpenLegi:rechercher_decisions_constitutionnelles` | Numéro de décision | `LibreJustice` (`seat: ["CONSTIT"]`) puis web_search |
| JURIS_CEDH_CJUE | `LibreJustice:search_decisions` (`seat: ["CEDH"]` / `["CJUE"]`) | N° de requête ou d'affaire, ou objet | `LegalDataHunter:search` puis web_search |
| CODE_ARTICLE | `rechercher_code` | Code exact + numéro article, champ NUM_ARTICLE, EXACTE | web_search |
| LOI_DECRET | `rechercher_dans_texte_legal` | Numéro du texte | web_search |
| DOCTRINE | `doctrine_search.py` (HAL + OpenAlex + Isidore) puis web_search | Auteur + titre court, ou DOI ; identifiant vérifiable attendu | web_search |
| SOURCE_ETRANGERE | web_search | Recherche par identifiant disponible | — |

**Séquence de fallback** : OpenLegi (reformuler la requête si échec) → **LibreJustice** (`search_decisions` en régime lexical, citation ou intitulé entre guillemets ; `search_norms` pour un article dont le numéro paraît erroné) → web_search → si toujours négatif : statut NON_TROUVEE.

**Apport propre de LibreJustice à la vérification** :

- il retrouve des décisions **non diffusées sur Légifrance** (juridictions du fond, CNDA), ce qui évite de classer NON_TROUVEE une référence réelle mais non légifrancisée — le lien `librejustice.fr` est alors porté, source mentionnée ;
- la recherche sémantique retrouve une décision dont **le numéro cité est erroné** mais dont l'objet est décrit ;
- `get_decision` fournit `appellateFate` et `caseChronology` : une décision réellement existante mais **infirmée ou cassée**, invoquée comme état du droit, relève d'ERREUR_CITATION et non de la conformité ;
- `get_norm` avec `date` établit si la **rédaction citée** correspond à celle applicable à la date pertinente.

Réserve : la vérification se fait sur le texte intégral retourné par `get_decision` / `get_norm`, jamais sur un `aiSummary` ni sur un `snippet`.

**Pour chaque référence vérifiée, déterminer le statut :**

| Emoji | Statut | Signification |
|---|---|---|
| ✅ | SOURCE_DIRECTE_CONFORME | Trouvée via OpenLegi, LibreJustice ou site officiel, métadonnées concordantes et contenu concordant |
| 🔵 | SOURCE_INDIRECTE_CONFORME | Trouvée via base doctrinale ou source secondaire |
| ⚠️ | ERREUR_CITATION | Trouvée mais divergence notable (date, numéro, juridiction, contenu) |
| ❌ | NON_TROUVEE | Non localisée après recherches (≠ fausse) |

**Validation des métadonnées** (jurisprudence OpenLegi / LibreJustice) :
- Juridiction : correspondance exacte
- Date : tolérance ±1 jour
- Numéro de pourvoi/requête : correspondance stricte
- Si divergence : statut ERREUR_CITATION, documenter l'écart dans le commentaire

### Phase 3 — Annotation du document miroir (commentaires Word)

**⚠️ Cette phase utilise l'édition XML du document décompressé (cf. skill docx, section « Editing Existing Documents »). Ne PAS créer un nouveau document via docx-js.**

**Séquence technique obligatoire :**

1. **Créer chaque commentaire** via le script `comment.py` du skill docx :
   ```bash
   python scripts/comment.py unpacked/ [id] "[texte du commentaire pré-échappé XML]"
   ```
   - `[id]` : identifiant numérique unique (0, 1, 2…), incrémenté pour chaque commentaire
   - Le texte du commentaire doit être pré-échappé (XML entities : `&amp;`, `&#x2019;`, etc.)

2. **Insérer les marqueurs** dans `unpacked/word/document.xml` autour du passage contenant la référence :
   ```xml
   <w:commentRangeStart w:id="[id]"/>
   <!-- passage existant du document contenant la référence -->
   <w:commentRangeEnd w:id="[id]"/>
   <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="[id]"/></w:r>
   ```
   - Les marqueurs `w:commentRangeStart` et `w:commentRangeEnd` sont des **frères** (`siblings`) de `<w:r>`, jamais à l'intérieur d'un `<w:r>`.
   - Utiliser l'outil `str_replace` pour insérer les marqueurs dans le XML — **ne pas écrire de script Python** pour cette étape.

   **⚠️ Règle impérative — Références situées dans des notes de bas de page :**
   Si la référence à commenter se trouve dans une note de bas de page (stockée dans `footnotes.xml`), le commentaire **doit impérativement être ancré dans `document.xml`** au niveau de l'appel de note — c'est-à-dire le `<w:r>` contenant le `<w:footnoteReference w:id="N"/>` correspondant — et **non** dans `footnotes.xml`. Le lecteur voit l'appel de note dans le corps du texte, pas la note ; c'est donc à ce niveau que le commentaire doit être attaché pour être visible. Le texte du commentaire doit mentionner le numéro de la note concernée (ex. : « Note n° 12 — »).

3. **Enregistrer le content type** — Le script `comment.py` ne le fait pas automatiquement. Vérifier que `[Content_Types].xml` (à la racine du répertoire `unpacked/`) contient l'Override pour `comments.xml`. Si absent, l'ajouter :
   ```bash
   # Vérifier
   grep -q "comments+xml" unpacked/\[Content_Types\].xml && echo "OK" || echo "MANQUANT"
   ```
   Si MANQUANT, insérer via `str_replace` dans `unpacked/[Content_Types].xml`, juste avant `</Types>` :
   ```xml
   <Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>
   ```
   **Sans cette entrée, Word ignore silencieusement tous les commentaires — le fichier `comments.xml` est présent mais invisible.**

4. **Recompresser** le document :
   ```bash
   python scripts/office/pack.py unpacked/ [AAAA-MM-JJ]-miroir-verif-[nom-doc].docx --original [source].docx
   ```

**Format du texte de chaque commentaire :**
```
[emoji] [Statut]
Réf. normalisée : [forme canonique]
Lien : [URL vers la source — Legifrance, HAL, Cairn, etc.]
Extrait : [passage pertinent de la source, 2-4 phrases, ou résumé si texte long]
```

**Exemples :**

```
✅ SOURCE_DIRECTE_CONFORME
Réf. normalisée : Cass. Ass. plén., 9 mai 1984, n° 79-16.612
Lien : https://www.legifrance.gouv.fr/juri/id/JURITEXT000007013411
Extrait : « Attendu que nul ne peut réclamer d'un tiers la réparation de son propre dommage en invoquant un droit dont il ne peut justifier la titularité… » — Revirement sur les concubins et l'action en réparation.
```

```
⚠️ ERREUR_CITATION
Réf. normalisée : Cass. civ. 1re, 20 sept. 2017, n° 16-19.109
Note : Le document cite « Cass. civ. 1re, 20 sept. 2017, n° 16-19.019 » — le numéro de pourvoi exact est 16-19.109.
Lien : https://www.legifrance.gouv.fr/juri/id/JURITEXT000035617604
Extrait : Arrêt relatif à l'articulation entre régime des produits défectueux et droit commun.
```

```
❌ NON_TROUVEE
Réf. normalisée : CA Lyon, 3e ch., 12 mars 2019, n° RG 17/05432 🟡
Note : Non localisée sur Legifrance ni par web_search. Possibles raisons : décision non numérisée, erreur de numéro RG, ou base incomplète pour cette juridiction et cette période.
```

### Phase 4 — Tableau récapitulatif

Ajouter en fin de document miroir un tableau de synthèse :

| N° | Localisation | Référence normalisée | Statut | Remarque |
|---|---|---|---|---|
| 1 | Note 1 | Cass. civ. 1re, 12 juill. 2023, n° 21-12.345 | ✅ | — |
| 2 | Note 3 | Art. 1240 C. civ. | ✅ | En vigueur depuis 1er oct. 2016 |
| … | … | … | … | … |

Statistiques en fin de tableau :
- Total des références vérifiées
- Répartition par statut (✅ / 🔵 / ⚠️ / ❌)
- Répartition par type (jurisprudence / textes / doctrine)

### Persistance d'une conversation à l'autre (dossier connecté)

Lorsqu'un dossier connecté existe, le document miroir y est écrit au fur et à mesure. Si la session s'interrompt :
- Le document miroir partiel persiste dans le dossier du Project
- À la reprise, détecter le document miroir existant (préfixe `miroir-verif-`)
- Identifier les références déjà annotées (commentaires présents) et celles restant à traiter
- Poursuivre à partir de la première référence non annotée

### Couplage avec la tâche 10

Si les tâches 9 et 10 sont exécutées simultanément, les commentaires de vérification (cette tâche) et les commentaires d'harmonisation (tâche 10) coexistent dans le même document miroir. Les distinguer par le préfixe :
- `[✅/🔵/⚠️/❌]` pour la vérification
- `[📐]` pour l'harmonisation (voir tâche 10)

## Livraison

### Phase 5 — Auto-vérification avant livraison

**Avant de livrer le fichier miroir, vérifier impérativement que les trois conditions cumulatives sont remplies :**

1. **Texte intégral** : le document miroir contient l'intégralité du texte du document source (vérifier par comparaison de longueur ou sondage de passages)
2. **Commentaires Word** : le fichier `unpacked/word/comments.xml` existe et contient au moins un `<w:comment>` par référence vérifiée
3. **Marqueurs dans le texte** : le fichier `unpacked/word/document.xml` contient des `<w:commentRangeStart>` et `<w:commentRangeEnd>` correspondant à chaque commentaire

**Si l'une de ces conditions n'est pas remplie, le livrable est non conforme. Ne pas livrer — corriger d'abord.**

Commande de contrôle rapide :
```bash
grep -c "w:comment " unpacked/word/comments.xml
grep -c "w:commentRangeStart" unpacked/word/document.xml
```
Les deux nombres doivent être ≥ au nombre de références vérifiées.

### Nommage

Nommage : `[AAAA-MM-JJ]-miroir-verif-[nom-doc].docx`
Si couplé avec tâche 10 : `[AAAA-MM-JJ]-miroir-verif-harmo-[nom-doc].docx`
