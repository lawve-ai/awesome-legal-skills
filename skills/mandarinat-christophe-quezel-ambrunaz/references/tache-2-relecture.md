# Tâche 2 — Relecture de documents

> **Environnement** : espace de travail requis pour les commentaires Word (étape 2) et la vérification outillée des références (étape 3) ; un document long se traite par sections, sans limite de pages. Lorsqu'un dossier connecté existe, y écrire le document commenté et le journal au fur et à mesure (reprise). Sans espace de travail (cas résiduel) : seule l'étape 1 est exécutable, sur un document visible dans la conversation ; indiquer que l'activation de « Exécution de code et création de fichiers » permettrait le reste.

## Objectif

Relecture approfondie d'un document juridique académique (article, mémoire, thèse, chapitre d'ouvrage, copie d'étudiant) en trois étapes distinctes et séquentielles :
1. **Relecture linguistique et structurelle** (qualité rédactionnelle)
2. **Vérification des références** (existence, exactitude, conformité)
3. **Analyse de cohérence argumentative et détection d'indices de plagiat/IA**

Chaque étape produit un livrable distinct. L'utilisateur peut demander une seule étape ou l'ensemble.

## Règle fondamentale : ne jamais modifier directement le document

**INTERDIT** de modifier le document source. Toujours :
1. Présenter les modifications proposées sous forme de liste numérotée en Markdown
2. Proposer à l'utilisateur d'intégrer les modifications (commentaires Word ou document miroir)

---

## ÉTAPE 1 — Relecture linguistique et structurelle

> Pour une relecture purement linguistique et stylistique (sans dimension de vérification de références juridiques), la compétence dédiée `relecture-texte-francais` est plus spécialisée et peut être préférée. La présente étape vise la relecture intégrée à un travail juridique, dont la vérification des références (étape 2) est indissociable.

### Catégories d'analyse

**1. Orthographe et grammaire** : accords, conjugaisons, homophones, participes passés.

**2. Lexique et terminologie juridique** :
- Barbarismes et impropriétés : voir `references/barbarismes-et-improprietes.md`
- Erreurs disciplinaires (stipuler/disposer, arrêt/jugement, etc.) : voir `references/erreurs-disciplinaires.md`
- Anglicismes à éviter en contexte académique

**3. Typographie** :
- Espaces insécables avant ; : ? !
- Guillemets français « … » (jamais " ")
- Tirets cadratins pour les incises
- Ponctuation des listes et énumérations

**4. Style académique** :
- Impersonnel ou « nous » (jamais « je » sauf mention explicite de l'auteur)
- Phrases denses et précises, vocabulaire technique rigoureux
- Absence de formulations journalistiques, emphatiques ou familières
- Cohérence du registre de langue

**5. Structure et argumentation** :
- Cohérence du plan (titres sans verbes conjugués, équilibre des parties)
- Progressivité du raisonnement
- Présence des éléments attendus (introduction, problématique, annonce de plan, transitions, conclusion)
- Qualité des transitions

**6. Appareil scientifique** :
- Présence et format des notes de bas de page / notes de fin
- Cohérence du système de citation
- Présence d'une bibliographie

### Livrable étape 1

**Liste numérotée en Markdown** de toutes les erreurs et suggestions, classées par catégorie et par ordre d'apparition dans le document. Chaque entrée contient :
- Localisation (page, paragraphe, ou citation du passage)
- Nature de l'erreur (catégorie)
- Correction proposée
- Justification si non évidente

Proposer ensuite d'intégrer les corrections comme commentaires Word dans le document.

---

## ÉTAPE 2 — Vérification des références

> **Environnement** : espace de travail requis.

### Phase 2.1 — Extraction exhaustive

Parcourir l'intégralité du document. Extraire **toutes** les références juridiques (corps du texte, notes de bas de page, bibliographie, annexes). Amorcer l'extraction par `scripts/extract_references.py --file [document]`, qui détecte automatiquement les références (jurisprudence, articles de codes, lois/décrets, doctrine) et leur localisation, puis compléter manuellement les références non capturées par les motifs.

Pour chaque référence extraite :
- **Localisation** : note n°X, corps p. Y, bibliographie
- **Texte extrait** : citation exacte
- **Type** : JURIS_CASS, JURIS_CE, JURIS_CA_TJ, JURIS_TA_CAA, JURIS_CONST, CODE_ARTICLE, LOI_DECRET, DOCTRINE, SOURCE_ETRANGERE, AUTRE
- **Référence normalisée** : forme canonique selon `references/format-citations.md` + code de certitude (🟢🟡🟠🔴)
- **Priorité** : P1 (citée >3 fois ou dans intro/conclusion), P2 (citée 1-3 fois), P3 (bibliographie uniquement)

**Déduplication** : si la même référence normalisée apparaît à plusieurs emplacements, une seule vérification suffit.

### Phase 2.2 — Vérification

Vérifier chaque référence unique, par ordre de priorité (P1 → P2 → P3).

**Routage par type :**

| Type | Outil primaire | Stratégie | Fallback |
|---|---|---|---|
| JURIS_CASS | `OpenLegi:rechercher_jurisprudence_judiciaire` | N° pourvoi, NUM_AFFAIRE, EXACTE | `LibreJustice:search_decisions` (lexical) puis web_search |
| JURIS_CE | `OpenLegi:rechercher_jurisprudence_administrative` | N° requête, NUM_AFFAIRE, EXACTE | `LibreJustice:search_decisions` (lexical) puis web_search |
| JURIS_CA_TJ | `LibreJustice:search_decisions` (`seat`, ou `mode: "reference"` sur le numéro) puis `get_decision` | Juridiction + n° RG ou objet de la décision | `OpenLegi:rechercher_jurisprudence_judiciaire` puis web_search |
| JURIS_CONST | `OpenLegi:rechercher_decisions_constitutionnelles` | N° décision | `LibreJustice` (`seat: ["CONSTIT"]`) puis web_search |
| JURIS_CEDH_CJUE | `LibreJustice:search_decisions` (`seat: ["CEDH"]` / `["CJUE"]`) | N° de requête ou d'affaire, ou objet | `LegalDataHunter:search` puis web_search |
| CODE_ARTICLE | `rechercher_code` | Code exact + n° article, EXACTE | web_search |
| LOI_DECRET | `rechercher_dans_texte_legal` | N° du texte | web_search |
| DOCTRINE | web_search puis HAL | Auteur + titre court + revue + année | — |
| SOURCE_ETRANGERE | `LegalDataHunter:resolve_reference` | Référence nationale | web_search |

**Statuts :**

| Emoji | Statut | Signification |
|---|---|---|
| ✅ | SOURCE_DIRECTE_CONFORME | Trouvée via OpenLegi, LibreJustice ou site officiel, métadonnées et contenu concordants |
| 🔵 | SOURCE_INDIRECTE_CONFORME | Trouvée via base doctrinale ou source secondaire |
| ⚠️ | ERREUR_CITATION | Trouvée mais divergence notable (date, numéro, juridiction) |
| ❌ | NON_TROUVEE | Non localisée après recherches (≠ fausse) |

**Principe cardinal** : Source non trouvée ≠ source fausse. Ne jamais qualifier une référence de « fausse » — seulement « non trouvée » ou « non vérifiée ».

### Phase 2.3 — Annotation du document miroir

Produire un **document Word miroir** : copie du document source, annoté avec des commentaires Word (`w:comment`) insérés dans le XML pour chaque référence vérifiée.

**Séquence technique :**
1. Copier le document source, décompresser avec `unpack.py`
2. Créer chaque commentaire via `comment.py`
3. Insérer les marqueurs `w:commentRangeStart` / `w:commentRangeEnd` dans `document.xml`
4. Vérifier le Content_Types pour `comments.xml`
5. Recompresser avec `pack.py`

**⚠️ Règle impérative — Commentaires portant sur des notes de bas de page :**
Si le commentaire porte sur une référence ou un élément situé dans une note de bas de page (stockée dans `footnotes.xml`), il **doit impérativement être ancré dans `document.xml`** au niveau de l'appel de note — c'est-à-dire le `<w:r>` contenant le `<w:footnoteReference w:id="N"/>` correspondant — et **non** dans `footnotes.xml`. Le lecteur voit l'appel de note dans le corps du texte ; le commentaire doit y être attaché pour être visible. Le texte du commentaire doit mentionner le numéro de la note concernée (ex. : « Note n° 12 — »).

**Format de chaque commentaire :**
```
[emoji] [Statut]
Réf. normalisée : [forme canonique]
Lien : [URL]
Extrait : [passage pertinent, 2-4 phrases]
```

### Phase 2.4 — Tableau récapitulatif

Ajouter en fin de document miroir un tableau de synthèse avec statistiques (total vérifié, répartition par statut et par type).

### Livrable étape 2

Document miroir annoté. Nommage : `[AAAA-MM-JJ]-miroir-verif-[nom-doc].docx`.

---

## ÉTAPE 3 — Cohérence argumentative et indices de plagiat/IA

### 3.1 Analyse de la cohérence argumentative

Pour les documents académiques substantiels (articles, mémoires, thèses) :

**Vérifier :**
- Les références citées soutiennent-elles réellement l'argument avancé ?
- Les citations sont-elles en contexte (pas tronquées, pas détournées) ?
- La jurisprudence citée est-elle toujours d'actualité (pas renversée) ?
- Les conclusions découlent-elles logiquement des prémisses ?
- Les contrearguments sont-ils traités ?

**Signaler :**
- Références citées mais non pertinentes pour l'argument
- Arguments circulaires ou pétitions de principe
- Contradictions internes
- Lacunes argumentatives (question posée mais non résolue)

### 3.2 Détection d'indices de plagiat ou de génération par IA

**Méthode heuristique uniquement** — aucun outil externe de détection n'est fiable. La détection repose sur des indices, jamais sur des certitudes.

> Voir `references/methode-detection-plagiat-ia.md` pour le protocole détaillé.

**Indices de plagiat** :
- Passages stylistiquement hétérogènes (changement brutal de registre, de qualité, de vocabulaire)
- Références dont le format change brusquement au milieu du document
- web_search de **n-grammes distinctifs** (6-10 mots, en mots-clés, sans guillemets ni opérateur exact — cf. `references/methode-detection-plagiat-ia.md`) puis comparaison du texte des sources retrouvées
- Incohérences entre le niveau de rédaction et le niveau d'analyse

**Indices de génération par IA** :
- Uniformité stylistique excessive (absence de variations naturelles)
- Ponctuation et structure syntaxique trop régulières
- Vocabulaire excessivement policé, absence de marques personnelles
- Références plausibles mais non vérifiables (hallucinations typiques des LLM)
- Absence d'ancrage dans un contexte institutionnel ou personnel précis

**Règles absolues :**
- Présenter TOUJOURS comme « indices » ou « éléments suggestifs », jamais comme certitude
- Ne JAMAIS affirmer qu'un texte est « généré par IA » ou « plagié » — seulement que des indices le suggèrent
- Ne JAMAIS recommander d'outil externe de détection (aucun n'est fiable)
- Contextualiser : un texte très bien écrit n'est pas suspect en soi

### Livrable étape 3

Liste numérotée en Markdown des observations, classées en :
- Problèmes de cohérence argumentative (avec localisation et explication)
- Indices éventuels de plagiat/IA (avec qualification du niveau d'indice : faible/moyen/fort)
- Recommandations

---

## Propositions post-tâche

Après livraison, proposer :
- Intégration des corrections linguistiques (étape 1) dans le document
- Recherche juridique complémentaire sur les points faibles identifiés
- Aide à la réécriture des passages problématiques
