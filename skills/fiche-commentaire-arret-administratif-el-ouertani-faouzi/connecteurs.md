# Connecteurs de vérification — MCP LibreJustice (https://librejustice.fr/mcp/)

Source principale : le connecteur `librejustice` (MCP LibreJustice, moteur sémantique sur la jurisprudence française et européenne — CE, CAA, TA, TC, Conseil constitutionnel, CNDA, CNIL, CEDH, CJUE — et les textes à toute date). Appuis : `open_legi_carthagolex` (Légifrance) et `tools.web_search.open_url` pour la confirmation finale du texte exact sur Légifrance.

## 1. Rechercher une décision — `librejustice.search_decisions`

- Requête en français, en langage naturel ou mots-clés descriptifs ; le moteur gère synonymes et reformulations. Exemples : « "SA HLM Antin Résidences" », « "Commune d'Aragnouet" », ou un problème juridique (« clause exorbitante contrat domaine privé »).
- Mode : `mode: "reference"` pour retrouver une décision par son identité (numéro de pourvoi, nom d'affaire, juridiction et date) ; `mode: "auto"` pour un problème juridique ; phrases entre guillemets pour une formule consacrée ou une entité nommée (recherche lexicale stricte, sans synonymes ; attention, la recherche sémantique ignore les négations).
- Filtres structurés (les valeurs se réutilisent verbatim depuis le bloc `facets` de la réponse) :
  - `seat` : type de juridiction et chambre (« CE », « CE.ASSEMBLEE », « TA.PARIS », « CAA.BORDEAUX », « TC », « CONSTIT »...) ;
  - `publication` : côté administratif — `PUBLIE_LEBON`, `MENTIONNE_LEBON`, `INEDIT_LEBON` ;
  - `legal_instrument` / `legal_article` : décisions citant un code ou un article précis (ex. `"code-de-justice-administrative|L761-1"`) ;
  - `date_from` / `date_to`, `procedure` (QPC, référés...), `solution` (ANNULATION, REJET, CONFIRMATION...).
- La réponse donne une liste courte (`title`, `url`, `aiSummary` ou `snippet`, métadonnées). ATTENTION : les aperçus (aiSummary, snippet) sont indicatifs ; ne jamais qualifier ou citer une décision sur leur seule base.

## 2. Lire la décision en texte intégral — `librejustice.get_decision`

- Entrée : l'`url` du résultat (lien librejustice.fr en `/decision/`).
- Renvoie le texte intégral, les métadonnées (formation, publication, numéro), `officialUrl` (éditeur officiel, preuve d'authenticité — utile pour la confirmation Légifrance), `caseChronology` (décisions antérieures et postérieures de la même affaire : appel, pourvoi — précieux pour la rubrique « procédure » et l'« apport ») et `commentaires` (conclusions du rapporteur public, notes).
- Le texte comporte des liens inline vers les articles cités (`/norm/`, à ouvrir avec `get_norm`) et les décisions citées (`/decision/`, à ouvrir avec `get_decision`) — à suivre pour vérifier la jurisprudence de contexte citée dans les visas et motifs.

## 3. Vérifier un texte cité — `librejustice.search_norms` puis `librejustice.get_norm`

- `search_norms({ query: "délai de recours refus implicite", code: "code-de-justice-administrative" })` : liste courte d'articles avec extraits.
- `get_norm({ url })` : texte de l'article en vigueur à la date donnée (`date: "YYYY-MM-DD"` pour la version à la date du litige ; omettre pour la version actuelle) ; signaler la version citée, les dates de validité et l'état (abrogé, en vigueur...).
- URL composable : `/norm/fr/code-de-justice-administrative/r222-13` (clé d'article en minuscules : « l761-1 », « r222-13 »).

## 4. Appuis complémentaires

- `open_legi_carthagolex.rechercher_jurisprudence_administrative({ search, champ: "ALL", date_debut, date_fin })` : fond CETAT (CE, CAA, TA), texte intégral et lien Légifrance ; le numéro de décision se met directement dans `search`.
- Confirmation finale d'un texte exact : ouvrir le lien Légifrance renvoyé via `tools.web_search.open_url` avant de citer mot pour mot.
- `tools.web_search.web_search` : uniquement pour l'actualité non encore indexée, en le signalant.

## 5. Règles de citation dans les livrables

- **Règle absolue : aucune ressource non vérifiée dans un livrable.** Si une référence ne peut pas être confirmée par connecteur (texte intégral ou extrait lu, lien à l'appui), elle est omise ou ramenée strictement à ce qui est vérifiable. Les marqueurs [NON VÉRIFIÉ] appartiennent uniquement aux notes de travail internes.
- Décisions anciennes : les chercher par numéro de dossier, non par nom (anonymisation fréquente : ex. CE, 31 juillet 1992, n° 102487, identifié par numéro).
- Si une référence importante reste introuvable après recherches croisées (LibreJustice, CETAT, web Légifrance), formuler le propos sans elle — jamais citer de mémoire un numéro, une date ou un apport.

Retours du test initial (7 juin 2019, SA HLM Antin Résidences) : `search_decisions` mode reference, `get_decision` (texte intégral + chronologie + officialUrl), `search_norms` et `get_norm` (CRPA R. 343-1, L. 300-2) fonctionnent. Point de vigilance : la clé d'article `r222-13` du CJA a renvoyé une version obsolète — toujours confirmer un article sensible sur Légifrance avant citation. La jurisprudence CE 1992 Mme Vatin n'a pas été retrouvée par requête testée : si elle est citée, la vérifier par une recherche dédiée ou la marquer [NON VÉRIFIÉ].

- Chaque décision citée comporte : juridiction, date, nom de l'affaire, numéro éventuel, et lien (url librejustice.fr ou lien Légifrance vérifié).
- Mentionner le connecteur utilisé pour la vérification. Toute référence non vérifiée est marquée [NON VÉRIFIÉ].
- En cas de doute sur la version d'un texte applicable au litige, utiliser `get_norm` avec la date pertinente et signaler la version retenue.
