# Guide d'utilisation OpenLegi

<!-- NOYAU-ANTIHALLUCINATION v4 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills (script sync-noyau.sh). -->

## Présentation

OpenLegi est un serveur MCP (Model Context Protocol) offrant un accès direct aux bases de données officielles de Legifrance. Il constitue la **source prioritaire** de cette compétence pour les textes normatifs, le Journal officiel et les conventions collectives, ainsi que la **source unique du lien Légifrance** exigé pour toute référence citée. Pour la *recherche* de jurisprudence, la première intention appartient désormais à LibreJustice (voir ci-dessous).

**Principe fondamental** : Toute source accédée via OpenLegi est considérée comme **fiable** (données officielles Legifrance). La vérification anti-hallucination porte alors sur l'adéquation entre le résultat et l'usage qu'on en fait, non sur la fiabilité de la source elle-même.

**Articulation avec LibreJustice** — depuis l'intégration du MCP LibreJustice (`references/guide-librejustice.md`), la répartition est la suivante :

- **recherche** de jurisprudence par problème, notion ou situation de fait, et jurisprudence du fond, CNDA, CEDH, CJUE : **LibreJustice** en première intention (moteur sémantique, filtres structurés, sort en voie de recours) ;
- **recherche par référence exacte** (numéro de pourvoi, de requête, numéro d'article), **lien Légifrance**, **état juridique**, **JORF** et **conventions collectives** : **OpenLegi**, qui reste la source officielle et l'unique fournisseur du lien Légifrance exigé par la règle du lien officiel.

Toute décision trouvée par LibreJustice et destinée à être citée est donc repassée par OpenLegi (`rechercher_jurisprudence_judiciaire` / `_administrative`, `champ: "NUM_AFFAIRE"`, `type_recherche: "EXACTE"`) pour en extraire le lien Légifrance ; à défaut de diffusion sur Légifrance (nombreuses décisions du fond, CNDA), le lien `librejustice.fr` est conservé et la source mentionnée.

## Disponibilité et chargement

### Détection
Au début de chaque tâche nécessitant des recherches dans les bases officielles, charger les outils OpenLegi via `tool_search` avec une requête comme « OpenLegi legifrance ».

### Si OpenLegi est indisponible
- Basculer intégralement sur **web_search** avec les sources fiables (voir `sources-fiables.md`)
- Informer l'utilisateur : « Les outils OpenLegi ne sont pas disponibles dans cette session. La recherche s'effectue via web_search sur les sources officielles. Les résultats peuvent être moins précis. »
- **Ne jamais bloquer la tâche** : l'indisponibilité d'OpenLegi ne doit pas empêcher l'exécution de la compétence.

## Outils disponibles (18)

### 1. `OpenLegi:lister_codes_juridiques`
**Usage** : Obtenir la liste complète des 67 codes juridiques disponibles.
**Paramètres** : Aucun.
**Quand l'utiliser** : Pour identifier le nom exact d'un code avant d'utiliser `rechercher_code` (le nom doit être EXACT).

### 2. `OpenLegi:rechercher_code`
**Usage** : Rechercher des articles au sein d'un code juridique spécifique.
**Paramètres** :
- `code_name` (obligatoire) : Nom exact du code (utiliser `lister_codes_juridiques` si doute)
- `search` (obligatoire) : Termes de recherche
- `champ` : ALL (défaut), TITLE, NUM_ARTICLE, ARTICLE, TEXTE
- `page_number`, `page_size` : Pagination
- `sort` : PERTINENCE (défaut), DATE_ASC, DATE_DESC
- `type_recherche` : TOUS_LES_MOTS_DANS_UN_CHAMP (défaut), EXACTE, UN_DES_MOTS, AUCUN_DES_MOTS, AUCUNE_CORRESPONDANCE_A_CETTE_EXPRESSION

**Données retournées** :
- Identifiant article (LEGIARTI), CID article
- **État juridique** (VIGUEUR, ABROGE, etc.) — **EXPLOITER SYSTÉMATIQUEMENT** pour la vérification temporelle
- **Date début vigueur**, **Date fin vigueur** — idem
- Numéro d'article, chemin complet dans le code
- Texte intégral de l'article
- Articles cités
- **Lien Légifrance** (à extraire et reproduire dans le livrable, sans transformation)

**Astuce** : Pour rechercher un article par numéro exact, utiliser `champ: "NUM_ARTICLE"` et `type_recherche: "EXACTE"`.

### 3. `OpenLegi:rechercher_jurisprudence_judiciaire`
**Usage** : Rechercher dans la jurisprudence judiciaire (Cour de cassation, cours d'appel).
**Paramètres** :
- `search` (obligatoire) : Termes de recherche
- `champ` : ALL, TITLE, ABSTRACTS, TEXTE, NUM_AFFAIRE
- `juridiction_judiciaire` : Filtre par juridiction (tableau JSON)
- `publication_bulletin` : Filtre par publication au Bulletin
- `panorama` : `true` pour métadonnées uniquement (évite les textes intégraux volumineux)
- `page_number`, `page_size` : Pagination
- `sort` : PERTINENCE (défaut), DATE_ASC, DATE_DESC

**Données retournées** :
- Identifiant (JURITEXT), juridiction, formation, nature
- Numéro d'affaire, date de décision, solution
- Plan de classement, résumé, textes cités
- Texte intégral (sauf si `panorama: true`)
- **Lien Légifrance** (à extraire et reproduire dans le livrable, sans transformation)

**Astuce** : Pour rechercher par numéro de pourvoi, utiliser `champ: "NUM_AFFAIRE"` et `type_recherche: "EXACTE"`.

### 4. `OpenLegi:rechercher_jurisprudence_administrative`
**Usage** : Rechercher dans la jurisprudence administrative (Conseil d'État, CAA, TA).
**Paramètres** : Similaires à jurisprudence judiciaire, avec en plus :
- `publication_recueil` : Filtre par publication au Recueil Lebon
**Données retournées** : Structure identique, avec identifiant CETATEXT.
**Tri** : PERTINENCE (défaut), DATE_ASC, DATE_DESC

### 5. `OpenLegi:rechercher_decisions_constitutionnelles`
**Usage** : Rechercher les décisions du Conseil constitutionnel.
**Paramètres** : Similaires, avec `panorama` disponible.
**Tri** : PERTINENCE, DATE_ASC, DATE_DESC

### 6. `OpenLegi:rechercher_decisions_cnil`
**Usage** : Rechercher les décisions de la CNIL.
**Paramètres** : Similaires, avec `nature_delib` pour filtrer par type de délibération.
**Tri** : PERTINENCE, DATE_ASC, DATE_DESC

### 7. `OpenLegi:rechercher_dans_texte_legal`
**Usage** : Rechercher dans la base LODA (Lois, Ordonnances, Décrets, Arrêtés).
**Paramètres** :
- `search` (obligatoire) : Termes de recherche
- `text_id` : Identifiant d'un texte spécifique pour rechercher à l'intérieur
- `champ`, `page_number`, `page_size`
- `sort` : PERTINENCE, PUBLICATION_DATE_DESC, PUBLICATION_DATE_ASC, SIGNATURE_DATE_DESC, SIGNATURE_DATE_ASC
- `type_recherche`

**⚠️ ATTENTION** : Les paramètres de tri diffèrent de ceux des codes et de la jurisprudence.

### 8. `OpenLegi:recherche_journal_officiel`
**Usage** : Rechercher dans le Journal Officiel de la République Française.
**Paramètres** :
- `search` (obligatoire) : Termes de recherche
- `max_results` : Nombre maximum de résultats
- `text_types` : Filtre par type de texte (tableau JSON, ex : `["LOI", "DECRET"]`). Voir `lister_natures_textes_jorf`
- `emetteurs`, `ministeres` : Filtres par émetteur/ministère
- `date_publication` : Filtre par date
- `sort` : PERTINENCE, SIGNATURE_DATE_DESC, SIGNATURE_DATE_ASC, PUBLI_DATE_DESC, PUBLI_DATE_ASC
- `champ`, `type_recherche`

**ATTENTION CRITIQUE** : Appliquer systématiquement la Règle 5 du SKILL.md (qualification des sources JORF). Vérifier la nature de chaque document et qualifier sa portée juridique.

### 9. `OpenLegi:dernier_journal_officiel`
**Usage** : Obtenir les derniers Journaux Officiels publiés.
**Paramètres** :
- `nb_jo` : Nombre de JO à retourner
- `llm_formatter` : Formatage optimisé pour LLM

### 10. `OpenLegi:lister_natures_textes_jorf`
**Usage** : Lister les 86 natures de textes disponibles au JORF.
**Quand l'utiliser** : Pour identifier les valeurs valides du paramètre `text_types` de `recherche_journal_officiel`.

### 11. `OpenLegi:lister_emetteurs_jorf`
**Usage** : Lister les émetteurs/autorités disponibles pour les recherches JORF.
**Quand l'utiliser** : Pour filtrer les recherches JORF par émetteur spécifique.

### 12. `OpenLegi:rechercher_conventions_collectives`
**Usage** : Rechercher dans les conventions collectives (base KALI).
**Paramètres** : Similaires à `rechercher_dans_texte_legal`, avec `panorama` disponible.
**Tri** : PERTINENCE, DATE_ASC, DATE_DESC

### 13. `OpenLegi:rechercher_jurisprudence_financiere`

Cour des comptes, chambres régionales et territoriales des comptes, CDBF (décisions historiques), Cour d'appel financière. Paramètres analogues à la jurisprudence judiciaire (`search`, `champ`, `type_recherche`, `juridiction` : `COURS_COMPTES`, `CHAMBRES_COMPTES`, `CDBF`, `COURS_APPEL_FINANCIERE`, `publication_recueil`, `sort`, `date_debut` / `date_fin`, `panorama`). Identifiants `JUFITEXT`. `champ: "NUM_AFFAIRE"` n'est exact qu'avec `type_recherche: "EXACTE"`.

### 14 à 18. Lecture intégrale par identifiant

| Outil | Identifiant | Fonds |
|---|---|---|
| `OpenLegi:get_decision_judiciaire` | `JURITEXT…` | Cour de cassation, cours d'appel, tribunaux |
| `OpenLegi:get_decision_administrative` | `CETATEXT…` | Conseil d'État, CAA, TA |
| `OpenLegi:get_decision_constitutionnelle` | `CONSTEXT…` | Conseil constitutionnel |
| `OpenLegi:get_decision_financiere` | `JUFITEXT…` | juridictions financières |
| `OpenLegi:get_decision_cnil` | `CNILTEXT…` | CNIL |

Flux en deux temps : recherche (qui retourne l'identifiant), puis lecture intégrale (texte, métadonnées, lien Légifrance). C'est le canal nominal du content-matching et de la vérification d'un identifiant cité (`scripts/verify_links.py --extract-ids` indique l'outil adéquat).

## Extraction du lien Légifrance par type de réponse

Toute réponse OpenLegi contient un lien Légifrance dans ses métadonnées. Ce lien est l'**unique source légitime** du lien à reproduire dans le livrable : il n'est jamais reconstruit de mémoire ni par analogie. Le tableau ci-dessous récapitule, par outil OpenLegi, le pattern d'URL attendu et le champ de la réponse où le trouver.

| Outil OpenLegi | Pattern d'URL attendu | Identifiant pivot |
|---|---|---|
| `rechercher_code` | `https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI…` | `LEGIARTI…` ou `CID article` |
| `rechercher_jurisprudence_judiciaire` | `https://www.legifrance.gouv.fr/juri/id/JURITEXT…` | `JURITEXT…` |
| `rechercher_jurisprudence_administrative` | `https://www.legifrance.gouv.fr/ceta/id/CETATEXT…` | `CETATEXT…` |
| `rechercher_decisions_constitutionnelles` | `https://www.legifrance.gouv.fr/jorf/id/JORFTEXT…` ou page dédiée | `JORFTEXT…` |
| `rechercher_decisions_cnil` | `https://www.legifrance.gouv.fr/cnil/id/CNILTEXT…` | `CNILTEXT…` |
| `rechercher_dans_texte_legal` (LODA) | `https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI…` ou `…/loda/id/LEGITEXT…` | `LEGIARTI…` ou `LEGITEXT…` |
| `recherche_journal_officiel` | `https://www.legifrance.gouv.fr/jorf/id/JORFTEXT…` | `JORFTEXT…` |
| `rechercher_conventions_collectives` (KALI) | `https://www.legifrance.gouv.fr/conv_coll/id/KALITEXT…` | `KALITEXT…` |

**Règle d'extraction** :

1. Identifier dans la réponse OpenLegi le champ « Lien Légifrance » (ou équivalent).
2. Reproduire le lien **textuellement**, sans modification.
3. Ne **jamais** construire un lien à partir d'un identifiant deviné, ni transposer un identifiant d'une session antérieure.

**En cas de lien manquant dans la réponse OpenLegi** : signaler la référence comme « à vérifier » ou la convertir en formulation impersonnelle (cf. `references/principes-cardinaux.md`).

## Paramètres de tri — Récapitulatif

| Base | Tris disponibles |
|------|-----------------|
| Codes (`rechercher_code`) | PERTINENCE, DATE_ASC, DATE_DESC |
| Jurisprudence judiciaire | PERTINENCE, DATE_ASC, DATE_DESC |
| Jurisprudence administrative | PERTINENCE, DATE_ASC, DATE_DESC |
| Décisions constitutionnelles | PERTINENCE, DATE_ASC, DATE_DESC |
| Décisions CNIL | PERTINENCE, DATE_ASC, DATE_DESC |
| LODA (`rechercher_dans_texte_legal`) | PERTINENCE, PUBLICATION_DATE_DESC/ASC, SIGNATURE_DATE_DESC/ASC |
| JORF (`recherche_journal_officiel`) | PERTINENCE, SIGNATURE_DATE_DESC/ASC, PUBLI_DATE_DESC/ASC |
| Conventions collectives | PERTINENCE, DATE_ASC, DATE_DESC |

**⚠️** Utiliser un tri invalide provoque une erreur explicite. En cas de doute, utiliser PERTINENCE (toujours valide).

## Stratégies de recherche optimales

### Recherche d'un article de code précis
1. `rechercher_code` avec `code_name` exact + `search` = numéro d'article + `champ: "NUM_ARTICLE"` + `type_recherche: "EXACTE"`
2. Vérifier l'état juridique (VIGUEUR/ABROGE) et les dates dans les métadonnées
3. Si article introuvable dans un code : vérifier le nom exact du code via `lister_codes_juridiques`
4. **Extraire le lien Légifrance** de la réponse et le reproduire dans le livrable.

### Recherche jurisprudentielle thématique
1. `rechercher_jurisprudence_judiciaire` (ou `_administrative`) avec mots-clés thématiques + `sort: "DATE_DESC"` pour les décisions récentes
2. Pour une recherche de volume : utiliser `panorama: true` pour obtenir les métadonnées sans les textes intégraux
3. Compléter avec `web_search` sur Judilibre ou Arianeweb pour les décisions non trouvées

### Recherche d'un arrêt précis par numéro
1. `rechercher_jurisprudence_judiciaire` avec `champ: "NUM_AFFAIRE"` + `type_recherche: "EXACTE"` + `search` = numéro de pourvoi
2. Si introuvable : tenter web_search sur Judilibre ou Legifrance
3. **Vérifier la concordance** entre le numéro recherché et la décision retournée (dans le contenu même de la réponse) — précaution essentielle, l'incident-type étant la confusion entre deux arrêts portant un numéro voisin.

### Veille juridique sur le JORF
1. `recherche_journal_officiel` avec termes de recherche + `sort: "PUBLI_DATE_DESC"` + filtre `text_types` selon les besoins
2. Pour les textes normatifs uniquement : `text_types: ["LOI", "DECRET", "ORDONNANCE", "ARRETE"]`
3. **Toujours qualifier la nature** du document retourné (Règle 5 du SKILL.md)

### Recherche de textes légaux (LODA)
1. `rechercher_dans_texte_legal` avec termes + `sort: "PUBLICATION_DATE_DESC"` pour les plus récents
2. Si identifiant texte connu : utiliser `text_id` pour rechercher à l'intérieur d'un texte spécifique

## Gestion des erreurs

### Erreurs de tri
Si message d'erreur « Tri 'X' invalide » : vérifier le tableau des tris ci-dessus et utiliser le tri correct pour la base concernée.

### Erreurs de nom de code
Si message d'erreur sur le nom du code : utiliser `lister_codes_juridiques` pour obtenir le nom exact.

### Résultats vides
- Vérifier l'orthographe et les termes de recherche
- Essayer avec `type_recherche: "UN_DES_MOTS"` (plus permissif)
- Élargir le champ de recherche (`champ: "ALL"`)
- Basculer sur web_search en complément

### Erreur de connexion
Si OpenLegi est totalement inaccessible :
- Signaler à l'utilisateur
- Basculer sur web_search + sources fiables
- Ne pas bloquer l'exécution de la tâche

## Intégration avec les règles de la compétence

### Anti-hallucination

- Les résultats OpenLegi proviennent directement de Legifrance : **source fiable**.
- La vérification porte sur l'**adéquation** (est-ce le bon texte pour le bon usage ?), le **statut temporel** (le texte est-il en vigueur ?) et la **traçabilité du lien** (le lien Légifrance reproduit dans le livrable provient-il bien de la réponse OpenLegi obtenue dans la session courante ?).
- L'interdiction d'inventer des références reste absolue : utiliser OpenLegi pour trouver, jamais pour « confirmer » une référence imaginée.
- L'interdiction de reconstruire un lien Légifrance de mémoire est également absolue. Le lien est extrait de la réponse OpenLegi, et de nulle part ailleurs.
- Avant toute livraison, exécuter la `references/checklist-pre-livraison.md` : tableau de vérification généré depuis le journal de références et remis en document séparé. OpenLegi est le **canal nominal** de vérification des identifiants Légifrance (`scripts/verify_links.py --extract-ids` indique l'outil à appeler pour chacun), Légifrance refusant les requêtes HTTP automatisées. La livraison est conditionnée à la formule de clôture.

### Renumérotations et modifications fréquentes

Les codes et textes consolidés évoluent constamment. La skill ne peut **en aucun cas** présumer de la stabilité d'un numéro d'article ou d'une rédaction, même pour les articles « ultra-classiques » :

- Les anciens articles 1382 et 1384 du Code civil sont devenus 1240 et 1242 par l'ordonnance n° 2016-131 du 10 février 2016 — <https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000032004939>.
- L'article 1242 al. 4 C. civ. (responsabilité parentale) a été substantiellement modifié par la loi n° 2025-568 du 23 juin 2025 — <https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051782996>.
- Les recodifications successives produisent des renumérotations analogues dans tous les codes.

**Vérifier systématiquement** la rédaction en vigueur via `rechercher_code` (état juridique, date début/fin vigueur). Mentionner explicitement la version applicable lorsque le texte a connu des modifications récentes susceptibles d'affecter le raisonnement.

### Applicabilité temporelle (Règle 4 du SKILL.md)

- **Exploiter systématiquement** les métadonnées « État juridique », « Date début vigueur », « Date fin vigueur » retournées par OpenLegi.
- Ne jamais citer un article sans avoir vérifié ces champs.

### Qualification JORF (Règle 5 du SKILL.md)

- **Vérifier systématiquement** la nature du document dans les résultats de `recherche_journal_officiel`.
- Qualifier la portée juridique dans la citation (normatif vs travaux parlementaires vs administratif).
