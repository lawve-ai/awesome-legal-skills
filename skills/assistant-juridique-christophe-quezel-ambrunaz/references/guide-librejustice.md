# Guide d'utilisation LibreJustice

<!-- GUIDE-LIBREJUSTICE v2 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills : toute modification doit être répercutée à l'identique dans l'autre (script sync-noyau.sh). Schéma des outils vérifié le 27 septembre 2026. -->

## Sommaire

1. Présentation et disponibilité
2. Corpus
3. Outils (5)
4. Ce qui n'est jamais citable
5. Liens et citation
6. Articulation avec les autres sources
7. Facettes et prudence statistique
8. Séquence de recherche recommandée
9. Limites

## 1. Présentation et disponibilité

**LibreJustice** (`librejustice.fr`) est un connecteur donnant accès à un moteur de recherche jurisprudentielle **sémantique et lexical** couvrant l'ensemble des ordres juridictionnels français, les juridictions spécialisées et les deux cours européennes, ainsi qu'à un référentiel de **textes normatifs versionnés** (consultation à une date donnée). C'est la **source de première intention pour la jurisprudence** ; OpenLegi (Légifrance) demeure la source du **lien officiel** et de la recherche par référence exacte.

Le corpus provient des bases publiques de diffusion (Judilibre, ArianeWeb, open data de la justice administrative, HUDOC, CURIA, sites institutionnels). La vigilance porte donc sur l'**adéquation entre le contenu lu et l'usage qui en est fait**.

Les outils peuvent être différés : les charger par une recherche d'outils (« librejustice », « search_decisions ») avant de conclure à leur absence. Les noms et paramètres ci-dessous datent du 27 septembre 2026 ; en cas d'écart, **le schéma exposé par l'outil prévaut** sur ce guide.

**Si LibreJustice est indisponible** : OpenLegi pour la jurisprudence judiciaire, administrative, constitutionnelle, financière et CNIL (mots-clés seulement, sans contrôle automatique du sort en appel) ; LegalDataHunter puis recherche web (hudoc.echr.coe.int, curia.europa.eu) pour la CEDH, la CJUE et le droit étranger. Le signaler en une phrase ; ne jamais bloquer la tâche.

## 2. Corpus

| Ensemble | Détail | Couvert |
|---|---|---|
| Ordre judiciaire | Cour de cassation (`CC`), cours d'appel (`CA`), tribunaux judiciaires (`TJ`), tribunaux des activités économiques (`TCOM`) | oui |
| Ordre administratif | Conseil d'État (`CE`), cours administratives d'appel (`CAA`), tribunaux administratifs (`TA`) | oui |
| Juridictions spécialisées | Conseil constitutionnel (`CONSTIT`), Tribunal des conflits (`TC`), CNDA (`CNDA`), sanctions CNIL (`CNIL`) | oui |
| Juridictions européennes | CEDH (`CEDH`), CJUE (`CJUE`) | oui |
| Textes normatifs | codes et lois français (toutes versions), codes étrangers curés, droit de l'UE, traités | oui |
| Journal officiel, conventions collectives (KALI) | — | **non** → OpenLegi |
| Doctrine | — | **non** → `scripts/doctrine_search.py`, HAL, recherche web |
| Statistiques jurisprudentielles | — | **non** → Themia |

## 3. Outils (5)

### `search_decisions` — recherche de décisions

`query` (français, 512 caractères) : deux régimes, à ne pas mélanger.
- **Descriptif** (par défaut) : problème, notion, situation de fait ; le moteur gère synonymes et reformulations.
- **Exact** : guillemets ou opérateurs `ET` / `OU` / `SAUF` → appariement par mots-clés sur toute la requête. Indispensable pour une entité nommée, une formule consacrée ou **le sens d'une solution** : l'appariement sémantique ignore les négations (« n'est pas tenu » se classe comme « est tenu »).

Filtres (valeurs en OU à l'intérieur d'un filtre, ET entre filtres) :

| Filtre | Contenu |
|---|---|
| `seat` | **juridiction et formation**, en chemin pointé du type vers la chambre : `CC` (Cour de cassation entière), `CC.C1_CIVILE`, `CE`, `CONSTIT`, `CA.PARIS`, `CA.PARIS.P5.C3`, `TJ.LYON.SOCIALE`, `TA.MARSEILLE.C5`, `CNDA`, `CEDH`, `CJUE`… Un chemin couvre tout ce qui est en dessous : commencer par le type et descendre en reprenant les chemins de `facets.seat`. (Remplace les anciens filtres `jurisdiction_type`, `jurisdiction_code` et `chamber`.) |
| `legal_domain` | arbre à 9 racines (`CIVIL`, `COMMERCIAL`, `PUBLIC`, `SOCIAL`, `FISCAL`, `PROPRIETE_INTELLECTUELLE`, `EUROPEEN`, `CRIMINEL`, `CONSTITUTIONNEL`) et leurs feuilles (`CIVIL_DROIT_RESPONSABILITE`, `CIVIL_DROIT_LOCATIF`…) ; une racine couvre ses feuilles |
| `legal_instrument` | décisions visant un code ou une loi : slug (`code-civil`) ou nom exact |
| `legal_article` | clé composite `<instrument>\|<article>` : `code-civil\|1240`, `code-de-justice-administrative\|L761-1` (préfixe obligatoire) |
| `publication` | ordre judiciaire : `PUBLIE_RAPPORT` (signal le plus fort), `PUBLIE_BULLETIN`, `LETTRE_CHAMBRE`, `COMMUNIQUE`, `INEDIT_BULLETIN` ; ordre administratif : `PUBLIE_LEBON`, `MENTIONNE_LEBON`, `INEDIT_LEBON`. Les juridictions du fond ne portent aucune mention de publication. (Remplace l'ancien filtre `significance` : pour remonter d'abord les décisions importantes, filtrer sur `PUBLIE_RAPPORT`, `PUBLIE_BULLETIN`, `LETTRE_CHAMBRE`, `PUBLIE_LEBON`.) |
| `solution` | `REJET`, `IRRECEVABILITE`, `DESISTEMENT`, `NON_LIEU_A_STATUER`, `CONFIRMATION`, `INFIRMATION`, `INFIRMATION_PARTIELLE`, `REFORMATION`, `CASSATION`, `CASSATION_PARTIELLE`, `ANNULATION`, `CONFORMITE`, `NON_CONFORMITE`, `INELIGIBILITE`, `SATISFACTION_TOTALE`, `SATISFACTION_PARTIELLE`, `AUTRE` |
| `procedure` | `REFERE_SUSPENSION`, `REFERE_LIBERTE`, `REFERE_MESURES_UTILES`, `REFERE_PRECONTRACTUEL`, `REFERE_PROVISION`, `REFERE_CIVIL`, `FILTRAGE_R222_1`, `PAPC`, `QPC`, `QUESTION_PREJUDICIELLE_CJUE`, `RECOURS_REVISION`, `TIERCE_OPPOSITION`, `RECTIFICATION_INTERPRETATION` (absent = procédure ordinaire) |
| `office` | `JLD`, `JAF`, `JCP`, `JEX`, `JUGE_ENFANTS`, `PREMIER_PRESIDENT`, `MAGISTRAT_DESIGNE`, `PRESIDENT_SECTION_CONTENTIEUX`, `JUGE_EXPROPRIATION` (absent = formation ordinaire) |
| `date_from` / `date_to` | `AAAA-MM-JJ`, inclusives |
| `mode` | `auto` (défaut, à conserver), `lexical` (tous les termes requis : une réponse vide est alors une réponse), `semantic`, **`reference`** (recherche par identité : numéro d'affaire, nom de l'affaire, ou juridiction + date — utile pour retrouver une décision citée) |
| `sort` | `relevance` (défaut), `date_desc`, `date_asc` |
| `ai_rerank` | `true` par défaut ; le conserver |
| `limit` | 1 à 20 (défaut 10) |

Réponse : bloc `facets` (par filtre, effectif de chaque valeur **sous la requête courante**) et `hits` (`title`, `url` `https://librejustice.fr/decision/…`, date, numéros, `seat`, `legalDomain`, `solution`, publication, aperçu `aiSummary` ou `snippet`). Les clés de facettes et les métadonnées des hits se réinjectent **verbatim** dans les filtres. Une valeur inconnue échoue en renvoyant les valeurs valides voisines : se laisser corriger plutôt qu'abandonner le filtre.

### `get_decision` — lecture d'une décision

Paramètre : `url` (hit de recherche ou lien cité). Retourne :
- le **texte intégral**, avec liens vers les articles visés (`/norm/…`, à ouvrir par `get_norm`) et les décisions citées (`/decision/…`) ;
- **`appellateFate`** — sort de *cette* décision en voie de recours (`INFIRMATION` : elle ne fait plus autorité ; `CONFIRMATION`). À lire avant toute citation comme autorité ;
- **`caseChronology`** — décisions antérieures et postérieures de la même affaire connues du corpus ;
- **`commentaires`** — conclusions du rapporteur public, documents de la juridiction : contexte, jamais la décision ; citer le texte de la décision, non un commentaire.

L'absence de `appellateFate` ou de `caseChronology` ne prouve pas l'absence de recours : ne jamais écrire « décision définitive » sur ce seul fondement.

### `search_norms` — retrouver un article

Pour un article dont on connaît l'objet, la formulation, ou le numéro sans le code. Paramètres : `query` (français, descriptif) ; `code` (slug ou nom exact) ; `jurisdiction` (ISO alpha-2 : `FR`, `SN`, `MA`… ; `UE` ; `INTL`) ; `date` (versions en vigueur à cette date) ; `limit` (1-20). Réponse : liste avec extraits surlignés, `total` exact, `facets` (`code`, `jurisdiction`). Enchaîner sur `get_norm` avec l'`url` du résultat.

### `get_norm` — lire un texte à une date donnée

Paramètres : `url` (`https://librejustice.fr/norm/{juridiction}/{code}/{article}` : `fr/code-civil/1240`, `fr/code-de-justice-administrative/l761-1`, `eu/…`, `intl/…` ; clé d'article en minuscules) **ou** `code` + `article` **ou** `textId` (identifiant Légifrance : LEGIARTI, JORFARTI, KALIARTI, LEGITEXT, JORFTEXT, LEGISCTA) ; `date` (`AAAA-MM-JJ`, omise = version en vigueur).

Retourne la version en vigueur à la date demandée : texte, statut, dates de validité, **chronologie de toutes les versions**, liens vers les articles cités (servis à la même date), commentaires ancrés sur l'article. C'est l'outil de la **vérification temporelle** ; toujours indiquer la version citée. Le paramètre `textId` permet de lire directement un article à partir de l'identifiant Légifrance extrait d'une réponse OpenLegi.

### `list_my_activity` — activité du compte

`kind` : `searches`, `bookmarks`, `readingHistory`, `all` ; `limit` 1-100. Outil de continuité (reprendre un dossier, retrouver une décision consultée). Dans `readingHistory`, `lastSource == "web"` signale une lecture effective par l'utilisateur ; `"mcp"`, une ouverture par le connecteur seulement. Requiert un compte connecté.

## 4. Ce qui n'est jamais citable

Les aperçus de `search_decisions` orientent la sélection ; ils ne fondent jamais une affirmation.
- **`aiSummary`** : paraphrase produite par un modèle — jamais citable comme les termes de la juridiction, ni entre guillemets, ni pour énoncer ce qu'une décision juge.
- **`snippet`** : passage verbatim, mais celui où les mots-clés ont été appariés — il peut relever des moyens des parties, de la décision attaquée ou de l'exposé du litige.

Avant toute citation : `get_decision`, puis content-matching sur les motifs et le dispositif. Citer d'après un aperçu est une hallucination par mauvaise attribution, au même titre qu'une attribution énonciative erronée en cassation.

## 5. Liens et citation

| Situation | Lien à porter |
|---|---|
| Décision ou texte **diffusé sur Légifrance** (Cass., CE, CC, CNIL, codes, lois) | **Lien Légifrance**, extrait d'une réponse OpenLegi ; le lien LibreJustice peut être ajouté en second |
| Décision **non diffusée sur Légifrance** (nombreuses décisions du fond, CNDA) | lien `https://librejustice.fr/decision/…`, source mentionnée, après tentative OpenLegi par numéro |
| CEDH, CJUE | lien HUDOC / CURIA ; LibreJustice en complément |

Règle de conversion : une décision identifiée par LibreJustice et destinée à la citation est repassée par OpenLegi (`champ: "NUM_AFFAIRE"`, `type_recherche: "EXACTE"`) pour en extraire le lien Légifrance. Jamais de lien reconstruit de mémoire.

## 6. Articulation avec les autres sources

| Besoin | Première intention |
|---|---|
| Jurisprudence par problème, notion, situation de fait | LibreJustice `search_decisions` |
| Jurisprudence du fond, d'une juridiction ou d'une chambre précise | LibreJustice (`seat`) |
| CNDA, Conseil constitutionnel, sanctions CNIL, CEDH, CJUE | LibreJustice |
| Décision citée à retrouver (numéro, nom d'affaire) | LibreJustice `mode: "reference"` ou OpenLegi (référence exacte) |
| Lien officiel, état juridique, JORF, conventions collectives | OpenLegi |
| Rédaction d'un article à une date donnée | LibreJustice `get_norm` (`date`), puis OpenLegi pour le lien |
| Statistiques, cohortes, montants, voix énonciative en cassation | Themia |
| Droit étranger, comparé | LegalDataHunter ; `search_norms` (`jurisdiction`) pour les codes étrangers curés |
| Doctrine française | `scripts/doctrine_search.py`, HAL, recherche web |

## 7. Facettes et prudence statistique

Les effectifs de `facets` comptent des résultats sous une requête donnée ; ils dépendent de sa formulation, du plafond de rappel du moteur et de la composition, non exhaustive, de l'open data. Ils orientent la recherche ; ils ne sont **pas** des statistiques jurisprudentielles et ne peuvent être présentés ni en proportions ni en tendances. Toute affirmation quantitative relève de Themia ; à défaut, formulation qualitative et prudente.

## 8. Séquence de recherche recommandée

1. **Cadrer** — requête descriptive, sans filtre ou avec un `seat` de premier niveau (`CC`, `CE`…), `limit` 10.
2. **Raffiner** — lire les facettes ; réinjecter verbatim `seat`, `legal_instrument`, `legal_domain`, `publication`, `solution` ; resserrer les dates.
3. **Cibler le sens de la solution** — régime exact, phrase entre guillemets.
4. **Lire** — `get_decision` sur chaque candidate : texte intégral, `appellateFate`, `caseChronology`.
5. **Consolider** — repasse OpenLegi pour le lien Légifrance ; inscription au journal (`scripts/reference_journal.py add`) avec l'extrait réellement lu.

## 9. Limites

- Open data du fond partiel : l'absence de décision ne prouve rien ; ne jamais écrire « aucune décision n'a été rendue en ce sens ».
- Ni doctrine, ni JORF, ni conventions collectives.
- `aiSummary` non citable.
- Sort en appel limité aux liens connus du corpus. Pour un arrêt de cassation, `appellateFate` peut refléter la décision de la juridiction de renvoi (une « INFIRMATION » ne signifie pas alors que l'arrêt de cassation est remis en cause) : lire `caseChronology` avant d'en tirer une conséquence.
- Chronologie des versions (`get_norm`) : en cas de discordance avec les métadonnées Légifrance (état juridique, dates de vigueur lues par OpenLegi) — par exemple pour un texte à entrée en vigueur différée ou reportée —, les métadonnées Légifrance prévalent ; signaler la discordance.
- Décisions longues : la réponse de `get_decision` peut dépasser la taille de sortie ; l'enregistrer dans un fichier de l'espace de travail et y rechercher les motifs et le dispositif.
- 20 résultats au plus par appel : itérer par filtres successifs.
