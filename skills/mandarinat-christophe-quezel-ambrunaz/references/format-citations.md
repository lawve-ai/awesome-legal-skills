# Normes de citation juridique

<!-- NOYAU-ANTIHALLUCINATION v4 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills (script sync-noyau.sh). -->

Référence normative : Guide de rédaction SNE RefLex 2022
https://reflex.sne.fr/sites/default/files/guide/Guide-de-redaction-SNE-RefLex-2022-03-18.pdf

## Lien officiel obligatoire pour toute référence

Toute référence jurisprudentielle ou normative française citée dans un livrable doit être accompagnée d'un lien hypertexte vers la source officielle Légifrance — sous la seule réserve des décisions non diffusées sur Légifrance (nombreuses décisions du fond, CNDA), pour lesquelles le lien `librejustice.fr` tient lieu de lien vérifiable (cf. « Régime d'emploi » ci-dessous et `references/principes-cardinaux.md`, point (d)). La règle est cardinale ; elle est rappelée ici dans sa dimension formelle.

Patterns d'URL Légifrance attendus, par type de référence :

| Type de référence | Pattern d'URL | Exemple |
|---|---|---|
| Jurisprudence judiciaire (Cour de cassation, CA, TJ) | `https://www.legifrance.gouv.fr/juri/id/JURITEXT…` | `https://www.legifrance.gouv.fr/juri/id/JURITEXT000007043704` (Cass. ass. plén., 25 févr. 2000, n° 97-17.378, *Costedoat*) |
| Jurisprudence administrative (CE, CAA, TA) | `https://www.legifrance.gouv.fr/ceta/id/CETATEXT…` | `https://www.legifrance.gouv.fr/ceta/id/CETATEXT000018259414` (CE, ass., 8 févr. 2007, n° 287110, *Gardedieu*) |
| Décisions du Conseil constitutionnel | `https://www.legifrance.gouv.fr/jorf/id/JORFTEXT…` ou page dédiée du site du Conseil | (URL à extraire de la réponse de l'outil de recherche) |
| Décisions de la CNIL | `https://www.legifrance.gouv.fr/cnil/id/CNILTEXT…` | (URL à extraire de la réponse de `OpenLegi:rechercher_decisions_cnil`) |
| Articles de codes | `https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI…` | lien de la version citée, lu dans la réponse de l'outil |
| Articles de lois et textes consolidés (LODA) | `https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI…` ou `…/loda/id/LEGITEXT…` | (URL à extraire de la réponse de `OpenLegi:rechercher_dans_texte_legal`) |
| Textes publiés au JO | `https://www.legifrance.gouv.fr/jorf/id/JORFTEXT…` | `https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051782996` (loi n° 2025-568 du 23 juin 2025) |
| Articles JO | `https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI…` | `https://www.legifrance.gouv.fr/jorf/article_jo/JORFARTI000051783004` (art. 3 de la loi n° 2025-568) |
| Conventions collectives (KALI) | `https://www.legifrance.gouv.fr/conv_coll/id/KALITEXT…` | (URL à extraire de la réponse de `OpenLegi:rechercher_conventions_collectives`) |

Pour les sources non françaises, les URLs officielles équivalentes s'imposent :

| Type de référence | Pattern d'URL |
|---|---|
| CEDH (HUDOC) | `https://hudoc.echr.coe.int/fre?i=…` ou `…/eng?i=…` |
| CJUE (Curia) | `https://curia.europa.eu/juris/document/document.jsf?docid=…` |
| Textes UE (EUR-Lex) | `https://eur-lex.europa.eu/eli/…` ou `…/legal-content/…` |

**Liens LibreJustice** — patterns : `https://librejustice.fr/decision/{identifiant}` (décision) et `https://librejustice.fr/norm/{juridiction}/{code}/{article}` (article, par exemple `…/norm/fr/code-civil/1240` ; ancien format `…/texte/code-civil/1240`).

Régime d'emploi :

| Situation | Lien porté dans le livrable |
|---|---|
| Référence française diffusée sur Légifrance | **Lien Légifrance obligatoire**, extrait d'une réponse OpenLegi. Le lien LibreJustice ne peut s'y substituer ; il peut être ajouté en second lien lorsqu'il apporte quelque chose (texte intégral commode, commentaires institutionnels). |
| Décision non diffusée sur Légifrance (décisions du fond, CNDA) | Lien LibreJustice, qui vaut alors lien vérifiable, avec mention de la source (« LibreJustice »). La recherche Légifrance par numéro d'affaire doit avoir été tentée au préalable. |
| CEDH, CJUE | Lien HUDOC / Curia (règle inchangée) ; lien LibreJustice en complément facultatif. |

**Origine du lien** — Le lien est **extrait de la réponse de l'outil de recherche** (OpenLegi, LibreJustice, LegalDataHunter, etc.) appelé pour cette référence dans la session courante. Il n'est jamais reconstruit de mémoire ni par analogie. Toute reconstruction est interdite (cf. `references/principes-cardinaux.md`, section « Ce qui est interdit »).

**Vérification** — Avant livraison, vérifier chaque lien selon les canaux de la checklist (OpenLegi pour les identifiants Légifrance, `scripts/verify_links.py --check-content` pour HUDOC, Curia, EUR-Lex ; cf. `references/checklist-pre-livraison.md`).

## Jurisprudence

### Cour de cassation
```
Cass. [chambre], [JJ] [mois abrégé] [AAAA], n° [XX-XX.XXX]
```
- Chambres : civ. 1re, civ. 2e, civ. 3e, com., soc., crim.
- Formations solennelles : Ass. plén., Ch. mixte
- Mois abrégés : janv., févr., mars, avr., mai, juin, juill., août, sept., oct., nov., déc.
- Lien Légifrance attendu : pattern `JURITEXT` (cf. tableau ci-dessus).
- Exemples :
  - `Cass. civ. 1re, 12 juill. 2023, n° 21-12.345`
  - `Cass. Ass. plén., 9 mai 1984, n° 79-16.612`

### Conseil d'État
```
CE, [formation], [JJ] [mois abrégé] [AAAA], n° [XXXXXX]
```
- Formations : Ass., Sect., ss-sect.
- Lien Légifrance attendu : pattern `CETATEXT`.
- Exemple : `CE, Ass., 8 févr. 2007, n° 287110, Gardedieu`

### Conseil constitutionnel
```
Cons. const., [JJ] [mois abrégé] [AAAA], n° [XXXX-XXX] [QPC/DC/LP/etc.]
```
- Lien attendu : page Légifrance (`JORFTEXT`) ou page dédiée du site du Conseil constitutionnel.
- Exemple : `Cons. const., 16 janv. 1982, n° 81-132 DC, Nationalisations`

### Cours d'appel
```
CA [ville], [chambre], [JJ] [mois abrégé] [AAAA], n° RG [XX/XXXXX]
```
- Lien Légifrance attendu : pattern `JURITEXT` (lorsque la décision est publiée).
- Exemple : `CA Paris, pôle 2, ch. 3, 15 mars 2024, n° RG 22/04567`

### Tribunaux judiciaires
```
TJ [ville], [JJ] [mois abrégé] [AAAA], n° RG [XX/XXXXX]
```

### CEDH
```
CEDH, [JJ] [mois abrégé] [AAAA], [Nom c/ État], n° [XXXXX/XX]
```
- Lien attendu : URL HUDOC.
- Exemple : `CEDH, 7 juill. 1989, Soering c/ Royaume-Uni, n° 14038/88`

### CJUE
```
CJUE, [JJ] [mois abrégé] [AAAA], [Nom], aff. [C-XXX/XX]
```
- Lien attendu : URL Curia.

## Textes normatifs

### Articles de codes
```
Art. [numéro] [code abrégé]
Art. L. [numéro] [code abrégé]
Art. R. [numéro] [code abrégé]
```
- Codes courants : C. civ., C. pén., C. com., C. trav., C. consom., CPC, CPP, CJA, CGCT, CSP, CSS.
- Lien Légifrance attendu : pattern `LEGIARTI` (codes/article_lc).
- **Mention de la version applicable** lorsque le texte a été modifié récemment : `Art. [numéro] [code abrégé], dans sa rédaction issue de [loi/ordonnance/décret] du [date]`.
- Exemples :
  - `Art. 1240 C. civ.`
  - `Art. L. 1234-5 C. trav.`
  - `Art. R. 421-1 CJA`
  - `Art. 1242 al. 4 C. civ., dans sa rédaction issue de la loi n° 2025-568 du 23 juin 2025`

### Lois
```
Loi n° [AAAA-NNN] du [JJ] [mois] [AAAA] [titre court]
```
- Lien attendu : pattern `JORFTEXT` (texte initial) ou `LEGITEXT` (version consolidée).
- Exemple : `Loi n° 2016-1547 du 18 nov. 2016 de modernisation de la justice du XXIe siècle`
- Exemple récent : `Loi n° 2025-568 du 23 juin 2025 visant à renforcer l'autorité de la justice à l'égard des mineurs délinquants et de leurs parents` (`https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051782996`)

### Ordonnances
```
Ord. n° [AAAA-NNN] du [JJ] [mois] [AAAA]
```
- Exemple : `Ord. n° 2016-131 du 10 févr. 2016 portant réforme du droit des contrats`

### Décrets
```
Décr. n° [AAAA-NNN] du [JJ] [mois] [AAAA]
```

## Doctrine

> **Identifiant vérifiable obligatoire.** Toute référence doctrinale doit être trouvée par recherche (`scripts/doctrine_search.py`, `scripts/hal_search.py`, web_search sur source identifiable) et porter un **identifiant vérifiable** : DOI (forme `https://doi.org/10.xxxx/...`), identifiant/URL HAL (`https://hal.science/hal-XXXXXXXX`), ou URL d'une base reconnue (Cairn, Persée, OpenEdition, Dalloz). En présence d'un DOI, l'indiquer en fin de référence ; à défaut, l'URL de la base. Une référence doctrinale sans identifiant vérifiable est signalée « (référence non vérifiée) » ou supprimée. La mise en forme bibliographique peut être assistée par `scripts/format_citation.py` (entrée JSON typée) et compilée par `scripts/generate_bibliography.py`.

### Articles de revue
```
[NOM] [Initiale(s) prénom(s)]., « [Titre exact de l'article] », [Revue abrégée] [AAAA], p. [X]
```
- Exemple : `BRUN Ph., « La responsabilité du fait des choses », RTD civ. 2023, p. 45`
- Revues courantes : RTD civ., RTD com., D., JCP G, JCP E, AJDA, RFDA, RDC, Gaz. Pal., Dr. soc., RJS, RLDC, RCA

### Ouvrages
```
[NOM] [Initiale(s) prénom(s)]., [Titre de l'ouvrage], [Éditeur], [Année], [édition si ≥ 2e]
```
- Exemple : `TERRÉ F., SIMLER Ph. et LEQUETTE Y., Droit civil. Les obligations, Dalloz, 2024, 13e éd.`

### Thèses
```
[NOM] [Initiale(s) prénom(s)]., [Titre], thèse [Université], [Année]
```

### Contributions à un ouvrage collectif
```
[NOM] [Initiale(s) prénom(s)]., « [Titre contribution] », in [Titre ouvrage], [Dir.], [Éditeur], [Année], p. [X]
```

### Notes d'arrêt et observations
```
[NOM] [Initiale(s) prénom(s)]., note sous [Juridiction], [date], [Revue] [AAAA], p. [X]
```

## Rapports et documents institutionnels
```
[Auteur/Institution], [Titre], [Date ou Année]
```
- Exemple : `Cour des comptes, Rapport annuel 2024, févr. 2024`

## Intégration des liens dans les notes de fin

Chaque référence en note de fin doit comporter le lien hypertexte vers la source officielle, conformément à la table ci-dessus. Forme attendue :

> Cass. ass. plén., 25 févr. 2000, n° 97-17.378, *Costedoat*, *https://www.legifrance.gouv.fr/juri/id/JURITEXT000007043704*.

> Art. 1242 al. 4 C. civ., dans sa rédaction issue de la loi n° 2025-568 du 23 juin 2025, *<lien Légifrance de la version citée, lu dans la réponse de l'outil>*.

L'absence de lien rend la note non conforme : la référence est alors traitée selon la procédure de la `references/checklist-pre-livraison.md` (suppression, reformulation impersonnelle ou mention « à vérifier »).

## Variantes admises par le guide RefLex

Le guide RefLex laisse certaines marges de liberté. Les variantes principales :

| Élément | Variante A | Variante B |
|---|---|---|
| Prénom auteur | `BRUN Ph.` | `Brun (Ph.)` |
| Plusieurs auteurs | `TERRÉ F., SIMLER Ph. et LEQUETTE Y.` | `F. Terré, Ph. Simler et Y. Lequette` |
| Titre revue | Abréviation (`RTD civ.`) | Nom complet (`Revue trimestrielle de droit civil`) |
| Guillemets titre | « … » | "…" |

L'essentiel est la **cohérence** au sein d'un même document. Le choix entre variantes appartient à l'auteur. Pour la tâche 10 (harmonisation), détecter quelle variante est majoritairement utilisée, puis demander confirmation avant d'appliquer systématiquement.

## Codes de certitude (pour les tâches 9 et 10)

| Code | Signification |
|---|---|
| 🟢 | Tous éléments identifiants présents (date + numéro + juridiction/série) + lien Légifrance valide |
| 🟡 | Un élément incertain ou à confirmer, ou lien Légifrance manquant |
| 🟠 | Deux éléments manquants ou approximatifs |
| 🔴 | Référence très partielle, normalisation conjecturale, lien Légifrance absent ou non vérifiable |
