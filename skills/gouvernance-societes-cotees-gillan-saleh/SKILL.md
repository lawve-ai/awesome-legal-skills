---
name: gouvernance-emetteurs-cotes
description: >-
  Index analytiques sourcés du corpus réglementaire et doctrinal sur la gouvernance des émetteurs cotés français (rapports AMF et HCGE 2020-2025, guide d'application HCGE, rapport sénatorial Rietmann/Gay, Code AFEP-MEDEF, sources légales et européennes). À utiliser pour : (1) retrouver une position, une statistique ou une citation exacte avec sa source et sa page ; (2) analyser l'évolution longitudinale des positions AMF/HCGE/ESMA sur un thème ; (3) appliquer la grille d'analyse en 13 blocs (A-M) à un émetteur. Déclencher pour toute question sur la gouvernance d'une société cotée française : conseil d'administration, indépendance des administrateurs, comités, rémunération des dirigeants, say on pay, say on climate, assemblée générale, droits des actionnaires, plans de succession, mixité, RSE/CSRD, comply-or-explain, name and shame AMF, soft law AFEP-MEDEF, recommandations AMF, positions HCGE.
license: CC BY-NC-SA 4.0 (Gillan Saleh) — voir le fichier LICENSE ; usage non commercial
metadata:
  version: 2.6.2
  updated: 2026-09-18
---

# Skill — Gouvernance des émetteurs cotés (`gouvernance-emetteurs-cotes`)

> **État du droit — péremption déclarée.** Les références légales du skill et de ses fichiers ont été vérifiées sur Légifrance et EUR-Lex en **juin 2026**. Échéances connues à cette date : **L. 22-10-10 C. com.** en vigueur sous réserve d'abrogation différée au **1er janvier 2027** (loi du 30 avril 2025) ; **ordonnance n° 2025-229 du 12 mars 2025** (nullités) en vigueur depuis le 1er octobre 2025 ; calendrier **CSRD/Omnibus** mouvant (vérification de l'état en vigueur obligatoire à chaque usage du Bloc J). **Prochaine revue programmée : janvier 2027**, ou dès qu'une réforme touchant le corpus est signalée. Toute production vérifie l'état en vigueur des articles qu'elle mobilise à sa propre date : ce fichier déclare sa péremption, il ne la subit pas.

## 1. Objet et posture

Ce skill donne accès à un corpus d'**index analytiques markdown** dérivés des sources réglementaires et doctrinales de référence sur la gouvernance des émetteurs cotés français (2020-2025). Chaque index restitue, avec sa **source exacte et sa page**, les positions des régulateurs, les recommandations de soft law, les statistiques de conformité et les citations littérales.

**Posture impérative — agrégateur et analyste objectif.** Le skill restitue des faits sourcés et des tendances ; il ne formule **aucune opinion**, aucun adjectif évaluatif (« satisfaisant », « problématique », « insuffisant »), aucune inférence sur l'intention des dirigeants, aucune projection. La distinction entre **fait sourcé** (position AMF/ESMA/HCGE, statistique, citation) et **opinion** (proscrite) est stricte. Tout élément restitué est accompagné de son auteur, de son document et de sa page.

**Règle fondatrice — zéro invention (binding, prévaut sur tout le reste).** Dès le premier mot d'une production, **rien n'est inventé**. Chaque fait — chiffre, citation, page, article, nom de société ou de personne, date, et **URL** — provient soit du **corpus indexé** (avec sa page exacte), soit d'une **source web vérifiée** (lien issu des résultats de recherche/fetch effectifs, jamais reconstitué ni rappelé de mémoire). Interdits absolus : un chiffre qui ne figure pas littéralement dans la source ; une citation restituée de mémoire ; une page, un article, une attribution ou une **URL** devinés, reconstruits ou plausibles. **Quand un fait ne peut pas être sourcé : l'omettre, ou le signaler explicitement comme non vérifié / non récupéré — jamais combler le manque par une invention vraisemblable.** Cette règle prime sur l'exhaustivité, sur la fluidité et sur le confort de la réponse : mieux vaut une lacune déclarée qu'un fait fabriqué.

## 2. Taxonomie fondamentale (binding — ne jamais confondre)

Le statut juridique de chaque acteur conditionne l'interprétation de toute statistique de conformité et de toute « position ». Cette taxonomie est **non négociable** :

| Acteur | Nature | Pouvoir | Traitement |
|---|---|---|---|
| **AMF** | Autorité publique indépendante (C. mon. fin. art. L. 621-1) | Pouvoir réglementaire (RGAMF), pouvoir de sanction | **Régulateur.** Nominatif assumé (« name and shame » / « name and fame »), jamais anonymisé |
| **ESMA** | Autorité européenne des marchés financiers | Régulateur européen, orientations | **Régulateur** (UE) |
| **ANC** | Autorité des normes comptables | Pouvoir réglementaire comptable | **Régulateur** (comptable) |
| **EFRAG** | Conseiller technique de la Commission UE (ESRS) | Conseil technique, pas de pouvoir réglementaire propre | Conseiller technique — **pas un régulateur** |
| **HCGE** | Instance privée créée par l'AFEP et le MEDEF | **Aucun** pouvoir réglementaire ni de sanction | **Soft law.** Comply-or-explain. Anonymisation de principe |
| **AFEP-MEDEF** | Organisations professionnelles privées | **Aucun** pouvoir réglementaire ni de sanction | **Soft law.** Auteur du Code |

**Règles absolues** :
- Ne **jamais** qualifier le HCGE ou l'AFEP-MEDEF d'« autorité » ou de « régulateur ».
- Ne jamais confondre AMF / HCGE / ESMA / EFRAG / ANC / IASB / ISSB.
- Le fondement d'une norme conditionne tout : **obligation légale** (Code de commerce, Code mon. fin.) ≠ **soft law** (AFEP-MEDEF, HCGE) ≠ **position de régulateur** (AMF, ESMA). Une « statistique de conformité » de 90 % ne signifie pas la même chose selon que la norme est légale ou soft law.

### Distinctions juridiques à ne jamais effacer

- **Administrateur représentant les salariés** (L. 225-27-1, désigné par les IRP) ≠ **administrateur représentant les actionnaires salariés** (L. 225-23, nommé par l'AG).
- **Conflit d'intérêts potentiel** ≠ **réel** ≠ **avéré**.
- **Dirigeant mandataire social exécutif** (PDG, DG, DGD, président/membres du directoire) ≠ **dirigeant exécutif** (notion plus large). Ne jamais abréger « dirigeant mandataire social exécutif » en « dirigeant exécutif ».
- **Le droit lui-même ≠ l'organe qui en décide l'exercice.** Ne pas confondre un droit subjectif de l'actionnaire avec la compétence de l'organe qui en conditionne la mise en œuvre. Exemple : le **droit aux bénéfices** (vocation aux bénéfices, élément constitutif de la société, art. 1832 C. civ.) est distinct de la **décision de distribution du dividende** (compétence de l'assemblée générale, art. L. 232-12 C. com.). Tant que l'AG n'a pas voté, l'actionnaire n'a pas de créance de dividende exigible. Identifier le fondement du droit, puis séparément l'organe et la procédure de son exercice.
- **Fondement civiliste (droit commun des sociétés) ≠ modalités du Code de commerce.** Pour les droits fondamentaux de l'associé, citer d'abord le socle du **Code civil** (droit commun des sociétés : art. 1832 vocation aux bénéfices et contribution aux pertes, 1833 intérêt social, 1844 participation aux décisions, 1844-1 répartition et prohibition des clauses léonines, 1844-10 et s. nullités), puis les **dispositions du Code de commerce** qui en organisent l'exercice pour les sociétés par actions. Ne pas réduire un droit civiliste à sa seule déclinaison commerciale.
- **Vague CSRD applicable** : fait binaire conditionnant l'analyse durabilité (voir §7, Bloc J).

## 3. Corpus indexé (sources et fichiers)

Chaque fichier est un index analytique sourcé. **Pour répondre, charger l'index pertinent et en restituer le contenu mot pour mot avec page exacte** (voir §5, règles de restitution).

**Point d'entrée : `INDEX_MAITRE.md`.** Avant de choisir un index, consulter l'index maître, qui cartographie tout le corpus (institution, nature, millésime, thèmes, blocs A-M concernés) et indique quel index ouvrir pour quelle question. Le maintenir à jour à chaque ajout, retrait ou renommage d'index.

### Rapports annuels AMF sur le gouvernement d'entreprise et la rémunération (régulateur — nominatif)
- `index_AMF_2020.md` à `index_AMF_2025.md` — six exercices. Recommandations AMF, pistes de réflexion, bonnes pratiques, statistiques (SBF 120 / CAC 40), citations nominatives.

### Doctrine AMF (régulateur)
- `index_AMF_DOC_2021_02.md` — guide AMF DOC-2021-02 sur le document d'enregistrement universel (DEU).
- `index_AMF_DOC_2025_08.md` — position-recommandation AMF DOC-2025-08 (arrêté des comptes 2025).
- `index_AMF_DURABILITE_2024.md` — doctrine AMF sur la durabilité (DPEF/CSRD), bilan 2024.
- `index_AMF_CSRD_WAY_FORWARD_2025.md` — étude AMF « CSRD: The Way Forward » (2025).

### Rapports annuels HCGE (soft law — anonymisé de principe)
- `index_HCGE_2020.md` à `index_HCGE_2025.md` — six exercices. Positions doctrinales, saisines/auto-saisines, name and shame, + 2e partie statistique (mandats, indépendance, comités, rémunération, ratios).
- `index_Guide_HCGE_2025.md` — Guide d'application du Code AFEP-MEDEF, édition décembre 2025 (positions et interprétations + récapitulatif « appliquer ou expliquer », art. L. 22-10-10).
- `index_HCGE_GUIDE_APPLICATION_2024.md` — Guide d'application, édition mars 2024 (version antérieure, pour analyse d'évolution).

### Sources européennes (régulateur UE)
- `index_ESMA_ECEP_2025.md` — priorités de contrôle ESMA (European Common Enforcement Priorities).

### Sources légales et de place
- `code-afep-medef-references.md` — table de références croisées du Code AFEP-MEDEF (décembre 2022), articles et sous-articles, **sans reproduction du texte protégé** (renvois uniquement).
- `references/droits-actionnaires-cotees.md` — catalogue sourcé des droits de l'actionnaire de SA cotée (C. com., C. mon. fin., RGAMF, droit UE, soft law), avec statut normatif de chaque droit.

### Rapport parlementaire
- `index_Senat_Rietmann_2025.md` — rapport de la commission d'enquête sénatoriale Rietmann/Gay sur les aides publiques aux grandes entreprises (n° 808, 1er juillet 2025). Volets gouvernance : dividendes, rachats d'actions, rémunération des mandataires sociaux, publication des comptes, conditionnalité, 26 recommandations, relevé nominatif exhaustif.

### Fichiers transversaux
- `recurrences_nominatives.md` — croisement nominatif cross-corpus AMF + HCGE : sociétés citées à plusieurs reprises, par société / thème / exercice ; renommages (Total→TotalEnergies, Korian→Clariane, Orpea→Emeis, SES-imagotag→VusionGroup) ; structures de groupe (galaxie Bolloré).
- `index_PARIS_EUROPLACE_DIALOGUE_2024.md` — dialogue de place (contexte).

*Les fichiers `audit_*.md` et `extraction_*.md` sont des artefacts de construction (journaux d'audit) et ne sont pas des sources doctrinales : ne pas les citer comme sources.*

## 4. Grille d'analyse en 13 blocs (A-M)

La structure des index suit une grille commune. Pour un audit d'émetteur (usage 3) ou une recherche thématique, raisonner par bloc. Chaque bloc liste ses **sous-thèmes nommés** : c'est la cartographie de dispatch — tout fait du corpus doit trouver sa place sous l'un d'eux, aucun ne doit être perdu.

- **Bloc A** — Mode de gouvernance et organisation des pouvoirs : dissociation/unicité, missions du président, administrateur référent, équilibre des pouvoirs ; **raison d'être / société à mission** (loi PACTE, art. 1835 C. civ., art. L. 210-10 à L. 210-12 C. com.).
- **Bloc B** — Composition et fonctionnement du conseil : indépendance (critères 10.5.1 à 10.5.6, ratio de proportion art. 10.3), ancienneté, mandats, représentants des salariés. **Pour chaque administrateur, restituer sa date de première nomination et la durée / échéance de son mandat** (jamais omises ; source : DEU et brochure de convocation à l'AG). **Sous-thèmes à couvrir obligatoirement pour tout audit d'émetteur** : l'**évaluation du fonctionnement du conseil** (art. 11 : auto-évaluation/évaluation externe, entretiens individuels, qui la conduit, périodicité) ; la **formation et l'intégration des administrateurs** (art. 14) ; la **déontologie / gestion des conflits d'intérêts** (art. 20 ; conflit potentiel ≠ réel ≠ avéré) ; l'**obligation de discrétion de l'administrateur** (personne morale, représentant permanent ; saisines HCJP) ; les **présidents d'honneur** ; les **censeurs**. Ne jamais omettre ces volets.
- **Bloc C** — Succession des dirigeants et nomination (plans de succession, procédure de sélection, comité des nominations, passation des pouvoirs, indemnités de prise/cessation de fonctions).
- **Bloc D** — Comités du conseil (audit, rémunérations, nominations, RSE) ; **relation avec les commissaires aux comptes** (renouvellement, appel d'offres, supervision des missions) ; **supervision des risques par le conseil** (dispositif de contrôle interne et de gestion des risques, cartographie des risques, rôle du comité d'audit/des risques ; la cybersécurité relève de ce sous-thème — voir aussi rubrique thèmes émergents).
- **Bloc E** — Rémunération des dirigeants mandataires sociaux : politique, fixe/variable, variable pluriannuelle, critères RSE, options/actions de performance, indemnités, retraites, rémunérations exceptionnelles, conservation d'actions. **Ratio d'équité** (sous-thème nommé : écarts de rémunération, art. **L. 22-10-9, I, 6° et 7° C. com.** [ex-L. 225-37-3], + § 26.2 du Code AFEP-MEDEF sur le périmètre représentatif). **Dimension « circonstances exceptionnelles / crise »** (Covid : renoncements de rémunération, modulation des dividendes) — transversale E/F.
- **Bloc F** — Assemblée générale et droits actifs des actionnaires : vote, résolutions (inscription, retrait, contestation), say on pay, say on climate, AG hybrides, retransmission, lieu de réunion, huis clos, questions des actionnaires, **dialogue actionnarial** (guide Paris Europlace 2024), **activisme actionnarial**, **fractions d'action**.
- **Bloc G** — Droits des actionnaires : compléments financiers (délégations, augmentations de capital, DPS, programmes de rachat). **Politique de distribution** (sous-thème nommé) : politique de dividendes (art. L. 232-12 C. com. ; bénéfice distribuable art. L. 232-11), taux de distribution (payout), acomptes, dividende majoré, paiement en actions ; rachats d'actions (art. L. 225-209 et s. ; taxe sur les réductions de capital, loi de finances 2025) ; arbitrage dividende / rachat ; articulation avec les aides publiques et les circonstances de crise (conditionnalité, voir aussi Bloc E/F et corpus sénatorial).
- **Bloc H** — Comply-or-explain et méthode (name and shame, saisines/auto-saisines HCGE, taux de conformité, principe « appliquer ou expliquer », standard AMF de l'explication). Pour toute récurrence nominative, **indiquer le motif de chaque mention** (bonne pratique / non-conformité / exemple / échantillon), année par année, et non un simple décompte (voir §5, asymétrie nominative).
- **Bloc I** — Structure capitalistique et contrôle : sociétés contrôlées/non contrôlées, mandats intragroupes, franchissements de seuils, offres publiques. **Structures particulières nommées** : SCA / société en commandite par actions, SPAC, sociétés familiales contrôlées, scissions et opérations de rapprochement.
- **Bloc J** — Information de durabilité (CSRD/ESRS, stratégie climatique, critères RSE, articulation gouvernance/RSE) — **terrain à risque accru, voir §7**.
- **Bloc K** — Information financière et extra-financière (qualité de l'information sur la performance, DEU, information réglementée, ESEF).
- **Bloc L** — **Conseillers en vote (proxy advisors)** : rôle et gouvernance, politiques de vote, dialogue avec l'émetteur, propriété intellectuelle des notes, conflits d'intérêts, **usage de l'IA par les conseillers en vote eux-mêmes**. Acteurs : ISS, Proxinvest/ECGS. Fondement : art. **L. 544-3 à L. 544-6 C. mon. fin.**, issus de la loi PACTE (n° 2019-486 du 22 mai 2019) transposant la directive SRD II (UE) 2017/828.
- **Bloc M** — **Notations et données ESG** (distinct du Bloc L) : agences de notation extra-financière, fournisseurs de données et de services ESG. Cadre UE émergent (proposition de règlement de la Commission du 13 juin 2023 sur la transparence et l'intégrité des activités de notation ESG, supervision envisagée par l'ESMA).

### Sous-bloc transverse — Mixité et diversité
Traverse B/C/D. Couvre la mixité **du conseil** (art. 7 du Code, loi Copé-Zimmermann) **et des instances dirigeantes** au-delà du conseil (comex, cadres dirigeants) : directive Women on Boards (UE 2022/2381), loi Rixain (n° 2021-1774 du 24 décembre 2021), notion d'« instances dirigeantes ». À ne pas réduire au seul conseil.

### Rubrique transverse — Thèmes émergents et études thématiques
Pour les sujets que les rapports traitent en focus ou en étude ponctuelle, sans bloc permanent dédié : **cybersécurité** et **intelligence artificielle dans la gouvernance** (focus HCGE 2024-2025 ; supervision par le conseil), ainsi que les études thématiques annuelles de l'AMF et du HCGE (présidents d'honneur, SCA, sociétés familiales, censeurs…). Restituer ces thèmes en les rattachant au bloc le plus proche et en signalant leur statut de focus/étude.

## 5. Règles de restitution (binding — méthode d'indexation)

Ces règles garantissent la fidélité scientifique du skill. **Toute violation est une erreur grave.**

### Portée des règles — toute réponse, motif textuel, étanchéité des sections
Précisions issues des rejeux successifs du jeu de tests (juillet et août 2026) :
- **Toute réponse, pas seulement les fiches.** Les règles du présent §5 et les verrous du §8 s'appliquent à **toute réponse produite avec le skill** — y compris une réponse conversationnelle brève, une question de test ou un échange exploratoire. Il n'existe aucun registre « libre » où la paraphrase, l'à-peu-près ou la citation approximative seraient tolérés : une question appelant une citation reçoit la citation littérale, quel que soit le format de l'échange.
- **Motif textuel des mentions nominatives.** Le motif d'une mention nominative se restitue **dans les termes de la source** (citation, ou décalque strict de son vocabulaire), jamais requalifié dans un vocabulaire propre (« non-conformité au principe de… », « manquement à… ») absent du texte. Si la source décrit des faits sans les qualifier, la restitution décrit les mêmes faits sans les qualifier.
- **Étanchéité des sections (cas anonymisés).** Aucun attribut identifiant — appartenance à un indice, secteur, taille, nationalité — ne peut être rattaché à un cas anonymisé s'il ne figure pas dans le **passage même** qui traite ce cas. Un attribut lu dans une section voisine du même rapport ne se transporte pas : la contamination inter-sections est une invention.
- **Encadrés normatifs : restitution intégrale ou ellipse signalée.** Un encadré « Recommandation », « Position », « Attendu » ou équivalent forme une **unité de sens close** : il se restitue **en entier**. S'il est abrégé, l'omission est signalée par `[…]` **à l'endroit exact où elle porte**, y compris lorsqu'elle porte sur la fin — une citation qui s'arrête à la deuxième phrase d'un encadré qui en compte quatre, guillemets refermés sans marque, laisse croire que la recommandation s'arrête là. Reprendre hors guillemets, en paraphrase, la phrase omise ne répare rien : la citation reste tronquée. Vérifier le nombre de phrases de l'encadré à la source **avant** de fermer les guillemets.
- **Intitulés : lettre de la source, y compris le nombre et la langue.** Un titre de section, de rubrique, de priorité ou de colonne se restitue tel qu'il est imprimé. Le nombre n'est pas harmonisé — si la source écrit « Priority related to ESEF reporting » au singulier là où les autres intitulés sont au pluriel, le singulier est conservé. L'intitulé n'est pas traduit à l'intérieur des guillemets ; la traduction ou la glose se place hors citation. Restructurer une énumération de la source (regrouper, renuméroter, fondre des sections) est admis dans la synthèse, mais **ne dispense pas** de restituer d'abord les intitulés tels quels.

### Verrous de fidélité citationnelle — issus du deuxième rejeu (juillet 2026)
Six verrous supplémentaires, chacun tiré d'un écart constaté par une instance vérificatrice indépendante sur une production du skill :
- **Les guillemets n'appartiennent qu'à la source.** Ne jamais placer entre guillemets un texte qui n'est pas lui-même entre guillemets dans l'index, ni une formulation reconstituée à partir de plusieurs phrases. Un intitulé de synthèse d'indexeur, une paraphrase, un résumé compressé se restituent **comme tels, attribués à l'index**, jamais en citation. Corollaire : à l'intérieur des guillemets, **ni majuscule initiale ni point final ajoutés** — la casse et la ponctuation de la source sont reproduites telles quelles, y compris lorsque la citation commence en milieu de phrase.
- **Une citation = un passage = une page.** Interdiction de fusionner sous une même ellipse `[…]` deux extraits provenant de passages, de tirets ou de pages différents : l'ellipse signale une coupe **à l'intérieur d'un passage continu**, jamais un raccord entre deux passages. Deux extraits distincts = deux citations distinctes, chacune avec sa page.
- **Numérotation d'article au millésime de la source.** Le Code AFEP-MEDEF a été renuméroté (version de décembre 2022) : le même critère d'ancienneté est l'art. **9.5.6** dans le rapport AMF 2022 et l'art. **10.5.6** dans le rapport AMF 2023 ; l'explication « pertinente » relève de l'art. **27.1** en 2022 et de l'art. **28.1** en 2023 ; le comité en charge des nominations de l'art. **17.1** en 2022 et de l'art. **18.1** en 2024. Avant de citer un numéro d'article, vérifier la numérotation **en vigueur dans le rapport cité** ; ne jamais rétro-appliquer une numérotation récente à un millésime antérieur, ni regrouper plusieurs millésimes sous une référence d'article unique.
- **Constat conditionnel ≠ constat catégorique.** Lorsque le régulateur énonce une non-conformité sous condition (« *si l'on applique le critère d'indépendance défini à l'article 9.5.6…, la société ne respecte pas la règle de composition de ce comité* »), la condition fait partie du constat : la supprimer transforme une analyse hypothétique en affirmation de non-conformité. Restituer la condition.
- **Un échec d'accès outillé ne vaut pas indisponibilité de la donnée.** Avant de déclarer une donnée « non récupérée », épuiser la **source officielle expressément désignée** par le corpus ou par l'émetteur (rubrique « résultats des votes », communiqué de résultats, DEU) **ainsi que les voies de substitution prévues au §6bis : BDIF (base AMF), BALO, miroirs de dépôt légal**. Un blocage technique sur un PDF (accès refusé, document monolithique) n'autorise pas à conclure à l'indisponibilité tant que ces voies n'ont pas été tentées. Une donnée publique déclarée manquante est un manquement de même nature que le renvoi-substitut prohibé au §8. Si la donnée reste inaccessible, déclarer précisément **ce qui a été tenté** et **où elle se trouve**.
- **Dater toute donnée variable.** Capital social, effectifs, composition d'un organe, taux, montants : toute donnée susceptible d'avoir varié se restitue avec sa date d'arrêté ou son exercice. Un montant exact à une date mais présenté sans date est un écart.

### Restitution textuelle
- Toute information issue d'un index se restitue **mot pour mot entre guillemets, avec le numéro de page**. Interdit : reformuler, raccourcir, ajouter ou retirer un mot, changer l'ordre. Test binaire : toute divergence est une violation.
- Les ellipses `[…]` signalent toute coupe dans une citation.
- **Citer en entier plutôt que paraphraser.** Lorsque le texte exact d'une position figure dans l'index (entre guillemets), le **restituer intégralement en citation**, et non le tronquer ou le paraphraser. Ne jamais remplacer une citation disponible par un résumé : si l'index contient la phrase complète, c'est la phrase complète qui doit apparaître. Une paraphrase n'est admise que lorsque le texte exact n'est pas disponible, et elle est alors signalée comme telle.
- **Pas de titre, sous-titre ou intitulé fabriqué.** Les titres de sections d'une fiche ne doivent pas introduire de qualificatif interprétatif absent des sources (ex. « l'IA comme levier stratégique et enjeu de souveraineté » est une interprétation, pas un fait sourcé). Préférer des intitulés neutres et descriptifs (« Focus 2025 — confirmation et approfondissement ») ou repris littéralement de la source. Le titre ne doit jamais affirmer plus que ce que le corpus établit.
- Vocabulaire technique repris du document source, sans substitution par un terme équivalent d'une autre source.
- Conserver intégralement les épithètes et qualificatifs juridiques composés (« dirigeant mandataire social exécutif » ne se réduit jamais à « dirigeant exécutif »).
- Pas d'adjectif interprétatif non présent dans la source (« restantes », « persistantes », « émergentes », « croissantes »).
- **Restituer les développements prospectifs.** Les passages où une source annonce ses travaux ou réflexions à venir (ex. les « thèmes de réflexion pour l'année à venir » du HCGE, les pistes de l'AMF) font partie du corpus à drainer : ne pas se limiter aux constats de l'exercice écoulé. La dimension prospective est souvent la plus utile à une analyse de fond et ne doit pas être omise.

### Présentation uniforme des citations
- Dans une production, **toutes les citations sont présentées de façon identique** : même style (bloc en retrait, en italique, avec la source et la page), quelle que soit l'institution citée (AMF, HCGE, etc.). Ne pas mélanger, dans une même fiche, des citations en bloc italique et des citations noyées en texte courant dans une puce. Une citation est toujours visuellement identifiable comme telle.
- Chaque citation porte sa source et sa page exacte, dans le même format à chaque occurrence.

### Couverture inégale d'un thème selon les sources
- **Énoncer explicitement quand un thème est absent ou marginal dans une partie du corpus.** Si une fiche s'appuie majoritairement sur une source parce que les autres traitent peu ou pas le thème, le **dire**, plutôt que de laisser un déséquilibre tacite. L'absence ou la rareté d'un thème dans une source faisant autorité est une **information en soi** (ex. : la politique de distribution des dividendes n'apparaît dans les rapports AMF et HCGE qu'en période de crise — Covid 2020 — et en est quasi absente les autres années ; dans le corpus, elle est surtout traitée par le rapport sénatorial).
- **Vérifier l'absence à la source** (PDF ou texte intégral), pour ne pas confondre une absence réelle avec un simple défaut d'indexation, avant de l'affirmer ; puis l'énoncer comme un constat daté et sourcé. Cette règle prolonge la frise datée (usage 2) : signaler les silences, pas seulement les positions exprimées.

### Chiffres
- Ne **jamais** écrire un chiffre qui n'apparaît pas littéralement dans la source. Pas d'arrondi (36,9 % ≠ 37 %). Si la source liste sans totaliser, compter explicitement et le signaler (« j'en compte X »).
- Mentionner systématiquement l'**exercice analysé** et le **périmètre** (SBF 120 / CAC 40) tels qu'ils figurent dans la source.

### Statut de la norme
- Identifier le fondement juridique (obligation légale / soft law / position de régulateur) pour toute statistique de conformité.

### Traitement des divergences entre sources
Lorsque deux sources se contredisent ou divergent (chiffres différents, positions opposées, qualifications incompatibles), **ne jamais trancher en silence ni fusionner les deux versions** : exposer la divergence explicitement, attribuer chaque version à sa source datée, et la résoudre selon la hiérarchie ci-dessous.
- **Sur un fait (chiffre, date, donnée) :** la source **primaire officielle** prime sur la source secondaire. Un chiffre du DEU, du BALO ou d'un communiqué réglementé l'emporte sur un chiffre de presse ou d'agrégateur. Entre deux sources primaires divergentes, retenir la plus récente et la plus officielle, et signaler l'écart (souvent une différence d'exercice ou de périmètre — la lever avant de conclure).
- **Entre un régulateur et de la soft law (AMF vs HCGE) :** ce n'est généralement pas une « contradiction » mais une différence de plan normatif. L'AMF (régulateur) et le HCGE (soft law) peuvent diverger sur l'interprétation d'une recommandation : restituer **les deux positions, attribuées et datées**, en rappelant que celle de l'AMF émane d'un régulateur et celle du HCGE d'une instance de soft law. Ne pas présenter l'une comme annulant l'autre ; laisser la divergence visible.
- **Entre doctrine et régulateur :** la doctrine (source secondaire) ne prime jamais sur la position d'un régulateur ou sur le droit positif ; elle l'éclaire ou la critique. Toujours présenter une opinion doctrinale comme telle, distincte de la position du régulateur.
- **Évolution dans le temps :** une divergence apparente entre deux millésimes peut refléter un changement de position ou de codification (voir usage 2, frise datée), non une contradiction — le dater et le qualifier comme tel.
- **En cas de divergence non résoluble :** l'exposer ouvertement (« la source X indique…, tandis que la source Y indique… »), sans choisir arbitrairement, et signaler ce qui permettrait de trancher (consulter telle source primaire).

### Droit d'auteur (HCGE et Code AFEP-MEDEF — documents protégés)
- Citations littérales du HCGE et du Code AFEP-MEDEF **strictement limitées à 2-3 phrases maximum par passage**, entre guillemets, avec page exacte et **renvoi au rapport** pour le reste.
- **Jamais** paraphraser un raisonnement doctrinal ou une analyse du HCGE.
- Les **faits non protégeables** (chiffres, pourcentages, noms de sociétés, articles, dates, intitulés de paragraphes) sont restituables directement.
- Pour le Code AFEP-MEDEF : citer par numéro d'article et renvoyer au Code via `code-afep-medef-references.md`, sans reproduire le texte.

### Asymétrie nominative
- **AMF** : sociétés citées nominativement (assumé). **HCGE** : anonymisation de principe — l'absence d'une société dans le corpus HCGE ne préjuge pas de l'absence de constat la concernant. Ne jamais raisonner sur un seul corpus pour une récurrence nominative : croiser via `recurrences_nominatives.md`.
- Gérer les renommages (rapprocher ancienne et nouvelle dénomination pour le suivi longitudinal).
- **Toujours qualifier le motif de chaque mention nominative (règle absolue).** Ne jamais écrire qu'une société est « citée » par l'AMF ou le HCGE sans indiquer **à quel titre** : restituer la **fonction factuelle** de la mention (exemple de bonne pratique / « name and fame » ; non-conformité ou point d'attention / « name and shame » ; exemple de présentation détaillée ; société de l'échantillon statistique ; prestataire ; note de bas de page…), avec l'exercice et la page. Une mention au titre d'une bonne pratique et une mention au titre d'une non-conformité n'ont pas la même portée : les confondre, ou les présenter indistinctement comme « citée X fois », vide la récurrence nominative de son sens. Pour une récurrence sur plusieurs exercices, **détailler le motif année par année**, pas seulement le nombre d'occurrences.

### Accès aux index
- Charger l'index pertinent par recherche dans le corpus (requêtes composées : institution + type de document + concept). En cas de divergence entre extrait texte et rendu image sur un numéro de page, le **rendu visuel du PDF source fait foi** (vérification visuelle recommandée pour toute citation critique).

## 5bis. Méthode d'indexation et de vérification (pour produire ou enrichir un index)

Ces règles s'appliquent à la **production ou la mise à jour** d'un index du corpus. Elles garantissent la fidélité scientifique et sont aussi contraignantes que les règles de restitution.

### Restitution textuelle — test binaire
- Toute information issue d'un index se cite **mot pour mot entre guillemets**. Interdit : reformuler, raccourcir, ajouter ou retirer un mot, changer l'ordre. Avant chaque restitution : localiser le passage dans le fichier et copier le texte exact. **Si une formulation diffère du fichier mot pour mot, c'est une violation.** Aucune restitution de mémoire. Si l'information n'est pas dans l'index, le dire.

### Fidélité au vocabulaire et à la langue de la source
- Vocabulaire technique repris du document indexé, **sans substitution** par un terme équivalent d'une autre source. Avant d'employer une expression technique (« comply or explain », « ESG-linked features », etc.), vérifier qu'elle figure littéralement dans le document.
- Préserver intégralement les notions juridiques composées et leurs épithètes (« avéré », « significatif », « exécutif », « formalisé »…). « Dirigeant mandataire social exécutif » ne se réduit jamais à « dirigeant exécutif ».
- **Documents en langue étrangère** : les citations entre guillemets, titres de sections et références techniques codifiées (BP-1, IRO-1, ESRS…) restent **en langue originale, jamais traduits entre guillemets**. La structure de l'index (blocs A-M), les métadonnées et les paraphrases courtes sont en français. Au mieux : paraphrase brève en français hors guillemets + citation source en langue originale avec page exacte.

### Pas d'interpolation interprétative
- Ne pas ajouter d'adjectif ou de qualificatif suggérant une lecture téléologique ou évolutive non formulée par la source (« restantes », « persistantes », « émergentes », « croissantes »). Restituer les faits bruts. Si une évolution est explicite dans le texte, la citer littéralement.

### Comptage rigoureux à la source
- Ne **jamais** écrire un chiffre qui n'apparaît pas littéralement dans le document. Pas d'arrondi. Si la source liste sans totaliser : soit compter explicitement et le signaler (« j'en compte X »), soit ne pas mettre de chiffre. Jamais de chiffre de mémoire ou approximatif.

### Contrôles automatiques (obligatoires avant toute livraison)

Quatre scripts, dans `scripts/`, à exécuter dans cet ordre après toute modification d'un index :

1. `extraire_corpus.py` — reconstitue le corpus page par page depuis les PDF (le corpus n'est pas stocké).
2. `controle_citations_v2.py` — **présence** : chaque citation figure-t-elle dans le document, à la page annoncée ? Signale aussi les plages « p. N-M » dont la citation ne franchit pas la coupure. Option `--corriger-pages`, `--annoter-plages`.
3. `controle_bornes_v3.py` — **bornes et fidélité** : marques d'omission posées sur une frontière réelle ou manquantes, ponctuation, casse initiale, guillemets de second niveau non restitués, appels de note conservés, espaces sensibles. Option `--corriger --elider`.
4. `controle_invention.py` — **invention** : chaque mot placé entre guillemets figure-t-il dans la source ? Aligne la citation mot à mot sur sa tranche source et ne retient que les suites de mots absentes de **tout** le document.

**Pourquoi le quatrième est indispensable.** Les deux premiers ignorent les citations qu'ils ne parviennent pas à localiser — or une citation dont des mots sont inventés n'est, par construction, pas localisable : elle tombait dans la classe « non localisable », c'est-à-dire hors de tout contrôle. C'est par là qu'est passée, jusqu'au 14 septembre 2026, une citation de l'AMF 2025 (p. 17) dont la fin — « délégué Quick-fix ESRS qui s'applique sans nécessiter de transposition » — ne figure nulle part dans le rapport : la phrase, laissée ouverte par l'extraction, avait été refermée de mémoire. **Aucun index ne se livre sans que ce contrôle ait tourné et que chacun de ses signaux ait été confronté à la page.**

**Audit par tirage.** `tirage_audit.py` (stratifié par fichier, mesure un taux) et `tirage_cible.py` (stratifié par classe de risque : élisions, guillemets de second niveau, crochets, chiffres et références, citations longues, plages, non localisables). Les deux sont rejouables à graine fixe. Le second trouve environ deux fois plus d'écarts au mètre carré : il éprouve, il ne mesure pas.

### Bornes de pages et vérification visuelle
- Avant d'indiquer une plage pour une section : vérifier par sondage (1) la page de début (titre de section présent) et (2) la page de fin (la suivante ouvre bien la section d'après). Les faits internes citent la **page exacte**, pas la page d'ouverture du chapitre.
- **Vérification visuelle obligatoire** : pour toute citation critique (page, titre, formulation), vérifier le **rendu visuel du PDF source**, pas seulement le texte extrait ni l'index dérivé. Les scans (PDF issus de JPEG) exposent à un décalage de page d'une unité aux frontières (concaténation OCR) : contrôler le folio imprimé. En cas de divergence entre extrait texte et rendu image, **le rendu visuel fait foi**.

### Complétude
- Avant de livrer un index, vérifier que **toutes les sous-sections** du document source sont couvertes (extraire la table des matières, grep des titres « N.N. », confirmer chaque sous-section avec sa page). Ne jamais indexer partiellement une section.
- **Couverture de page plutôt que grep par titre (vérification fiable).** Le grep des titres est un point de départ, mais il est **trompeur pour vérifier un index existant** : un index est organisé par bloc (A-M), pas dans l'ordre du sommaire, et un titre peut être reformulé ou fondu dans un bloc. Le critère **fiable** est la *couverture de page* : extraire la table des matières du PDF (page d'ouverture de chaque section), puis vérifier que chaque page annoncée est effectivement référencée quelque part dans l'index. Si une section du sommaire ouvre en p. X et qu'aucune entrée de l'index ne cite la p. X (ni une plage l'incluant), c'est un trou — quel que soit l'état du grep par titre. Méthode outillée : lister les pages citées par l'index (regex `p\. ?\d+(?:\s?-\s?\d+)?`), les comparer à l'intervalle de pages de contenu du document, et inspecter toute page non couverte (les seules pages légitimement absentes sont les sommaires, pages blanches et mentions de fin). En cas d'ambiguïté de plage, trancher visuellement sur le PDF. Pour les séparateurs de partie, noter qu'ils portent souvent un mini-sommaire de la partie — utile pour reconstituer la structure attendue.
- **Couverture des deux parties** : les rapports AMF et HCGE comportent une 1re partie doctrinale (positions, saisines, recommandations) et une 2e partie statistique (mandats, indépendance, comités, rémunération, ratios). Indexer les **deux** avec la même exhaustivité. Un index s'arrêtant à la 1re partie est incomplet.
- **Complétude des séries (sections de « thèmes à venir » et listes énumérées).** Les sections prospectives des rapports HCGE (« thèmes de réflexion pour l'année à venir », points 4.x) ont été un angle mort : certains sous-points étaient indexés par leur seul intitulé alors que le rapport les développe par un texte. Pour toute liste énumérée (X.1, X.2, X.3…), indexer **chaque** sous-point au même niveau de détail : si le rapport développe le point, en restituer la citation (≤ 2-3 phrases pour le HCGE/Code) ; s'il n'a qu'un intitulé, le noter. Ne jamais traiter un élément d'une série plus pauvrement que ses voisins sans l'avoir vérifié à la source. Contrôle outillé : `scripts/check_completeness.py` (cinq détecteurs, à relancer après toute production ou modification d'index, chaque signalement étant à confronter au PDF source) : **D1** sous-points compacts `- **X.Y** :` sans citation à côté de voisins qui en ont ; **D2** sous-sections `####` au corps vide ou squelettique (hors intertitres de regroupement) ; **D2b** sections statistiques dont l'intitulé annonce une page mais dont le corps est un placeholder ou ne restitue aucun chiffre ; **D3** guillemets `« »` déséquilibrés (citation tronquée) ; **D4** renvois-substituts (« disponible sur demande », « figure p. X ») ; **D5** disparité de densité entre millésimes d'une même série (AMF_YYYY, HCGE_YYYY). D4 et D5 sont indicatifs (contexte requis).
- **Vérification visuelle obligatoire** des prospectives AMF : à la différence du HCGE, l'AMF disperse ses pistes de réflexion et recommandations au fil du rapport (par thème), et l'indexation thématique les capture correctement ; il n'y a pas de section « à venir » isolée à risque, mais vérifier que chaque piste (« l'AMF invite/recommande/encourage… ») est bien restituée là où elle apparaît.

### Repérage nominatif exhaustif
- Lister toutes les entités possibles (SBF/CAC, cotées hors indices, étrangères, holdings, infrastructures). Grep **page par page**, en excluant uniquement les listes-annexe d'indice. Lire 3-4 lignes de contexte autour de chaque occurrence. Restituer la **fonction factuelle** de la mention (citation doctrinale, échantillon, note de bas de page, prestataire…) sans qualification interprétative. Autant d'entrées que d'occurrences. Croiser systématiquement AMF + HCGE via `recurrences_nominatives.md` (l'absence dans le corpus HCGE ne préjuge de rien — voir asymétrie nominative).

### Synthèses — fidélité égale à l'index
- Une synthèse ou un résumé doit pouvoir être **vérifié à la page citée sans recherche supplémentaire** : ne pas abréger les notions juridiques composées, ne pas omettre l'année des statistiques, ne pas fusionner des informations de pages différentes sous une seule page. Le niveau de précision de la synthèse est identique à celui de l'index source.

### Datation — exercice analysé ≠ millésime du rapport
- Un rapport AMF ou HCGE analyse généralement les DEU de l'**exercice précédent** : le rapport HCGE 2022 porte sur l'exercice 2021, le rapport AMF 2023 indique « en 2022 », etc. Toute statistique ou tout constat doit être rattaché à l'**exercice analysé**, pas au millésime du rapport — sous peine de décaler d'un an toute frise longitudinale (Usage 2).
- **Convention d'indexation** : chaque entrée statistique ou datée porte, lorsque la source le permet, l'exercice analysé en plus de la page (ex. « rapport AMF 2023, p. 28 — exercice 2022 »). Si la source ne mentionne pas explicitement l'exercice, l'attribuer prudemment au rapport sans l'inventer, et le signaler. Préciser systématiquement le périmètre (échantillon AMF ≠ SBF 120 / CAC 40 HCGE — voir §5, ne jamais les confondre ni les agréger).

## 6. Les quatre usages du skill

### Usage 1 — Restitution sourcée
Retrouver une position, une statistique ou une citation exacte.
1. Identifier l'institution (AMF / HCGE / ESMA / Sénat) et l'exercice.
2. Charger l'index correspondant.
3. Restituer mot pour mot + page exacte + statut normatif.
4. Pour le Code : renvoyer via `code-afep-medef-references.md` sans reproduire.

### Usage 2 — Analyse longitudinale
Comparer l'évolution d'une position ou d'une statistique dans le temps, ou entre institutions.
1. **Balayer le corpus année par année (méthode de la frise datée).** Pour suivre un thème dans le temps, parcourir systématiquement chaque index millésime par millésime (ex. AMF 2020, 2021, … 2025 ; puis HCGE 2020, … 2025) et relever, pour chaque exercice, ce que la source dit du thème — avec sa page. Construire une **frise chronologique datée** : un point par exercice, daté, sourcé, restitué mot pour mot ou en chiffre littéral. Signaler explicitement les exercices où le thème est **absent** du corpus (l'absence est une information : ex. un thème émergent apparu seulement en 2024). Ne pas se limiter aux millésimes où le thème est le plus visible.
2. Restituer chaque point avec son exercice, son périmètre (SBF 120 / CAC 40) et sa source.
3. Présenter l'évolution **factuellement** (chiffres comparés, citations datées, frise) ; mettre en regard les points de bascule (changement de codification, nouvelle position, inflexion statistique) en les datant. **Ligne rouge — juxtaposer et dater, jamais caractériser.** L'Usage 2 autorise à ordonner les faits dans le temps et à les mettre côte à côte ; il interdit de qualifier la séquence d'une lecture d'ensemble. Cette interdiction ne vise pas seulement les adjectifs évaluatifs (« satisfaisant », « robuste »), mais aussi les **noms et verbes interprétatifs** qui prêtent une intention ou une orientation à la série : « converge(nt) », « fil conducteur », « trajectoire », « dynamique », « saillant », « point d'orgue », « de X à Y » suggérant un arc, etc. Restituer les points datés ; laisser le lecteur tirer la tendance. Si une évolution est explicitement formulée par une source, la citer littéralement en l'attribuant à cette source — ne jamais la formuler en son nom propre.
4. Distinguer rigoureusement les corpus : une position AMF (régulateur) et une position HCGE (soft law) ne se comparent pas sur le même plan normatif — le préciser. Tenir compte des **changements de codification** dans le temps (ex. art. 9.5.6 du Code devenu 10.5.6 ; L. 225-37-3 devenu L. 22-10-9) pour ne pas confondre une évolution de fond avec une simple renumérotation.
5. Pour les récurrences nominatives, croiser via `recurrences_nominatives.md`, en datant chaque mention.

### Usage 3 — Audit d'un émetteur (grille A-M)
Appliquer la grille en 13 blocs (A-M) à une société.
1. **Ouvrir par le document d'enregistrement universel (DEU/URD) de l'émetteur, sans redemander à l'utilisateur.** Le DEU est la source primaire de l'audit (chapitre « Rapport sur le gouvernement d'entreprise » et chapitre durabilité CSRD). Le récupérer d'office par recherche internet (site émetteur, rubrique information réglementée ; à défaut, BDIF/BALO). **Compléter systématiquement par la brochure de convocation à l'assemblée générale** (avis de convocation / cahier central), qui est une source primaire riche : présentation et CV des administrateurs et des candidats, dates de nomination et échéances de mandat, exposé des résolutions, éléments de rémunération soumis au say on pay, rapports des commissaires aux comptes. Retenir par défaut le **DEU de l'exercice le plus récent disponible** et la brochure de l'AG correspondante, sauf indication contraire. Ne demander à l'utilisateur que si plusieurs exercices sont en jeu ou si le périmètre est réellement ambigu — pas pour confirmer qu'il faut consulter le DEU (c'est systématique).
2. **Si le DEU est introuvable ou inaccessible** : le signaler explicitement, s'appuyer sur les sources primaires de substitution (communiqués réglementés, BALO pour les AG, BDIF pour l'information AMF) et le corpus indexé, et **marquer comme partiels** les blocs qui dépendaient du DEU (ne pas les passer sous silence).
3. Procéder **bloc par bloc (A à K), sans en omettre aucun**. Pour chaque bloc, couvrir l'ensemble des sous-thèmes définis en §4 (pour le Bloc B notamment : ne pas oublier l'évaluation du conseil et la formation des administrateurs). Confronter la situation de l'émetteur (DEU) aux recommandations applicables, en distinguant obligation légale / soft law / position de régulateur.
3bis. **Drainer la TOTALITÉ du corpus indexé concernant l'émetteur (règle d'exhaustivité).** Avant de rédiger un bloc, balayer **tous** les index du corpus à la recherche de l'émetteur ET de ses entités liées (filiales cotées, holdings, sociétés du même groupe — ex. Christian Dior et Compagnie de l'Odet pour le groupe LVMH/Bolloré). Restituer **chaque fait trouvé**, mot pour mot avec sa source et sa page, sans en omettre ni en condenser aucun. Le corpus est constitué de faits sourcés ligne à ligne : un audit en restitue l'intégralité, jamais un échantillon ni un résumé. Avant livraison, vérifier qu'aucune mention de l'émetteur présente dans un index n'a été laissée de côté (voir §8.2, verrou Usage 3). **Arbitrage exhaustivité / lisibilité** : l'intégralité s'entend des **faits décisionnels** — chiffres, positions, mentions nominatives avec leur motif, fondements juridiques, dates — restitués mot pour mot sans exception ; le **contexte non décisionnel** (rappels génériques de cadre déjà restitués ailleurs dans la même production, développements descriptifs sans fait propre à l'émetteur) peut faire l'objet d'un **renvoi paginé assumé et signalé**. En cas de doute sur le caractère décisionnel d'un fait : restituer.
3ter. **Interdiction du renvoi-substitut (règle absolue).** Ne JAMAIS répondre, pour une donnée factuelle accessible, par un renvoi du type « figure p. X du DEU », « disponible sur demande », « peut être restitué page à page ». La vocation du skill est de **restituer** l'information, pas d'indiquer à l'utilisateur où la chercher ni de lui faire faire le travail. Pour toute donnée chiffrée du DEU (composition et taux d'indépendance du conseil, nombre de réunions et taux d'assiduité, résultat de l'évaluation, montants et structure de la rémunération des dirigeants, ratios d'équité, actionnariat, délégations), appliquer la **méthode d'extraction du DEU** (§6bis) pour aller la chercher et la restituer. Le renvoi à une page sans restitution n'est légitime QUE pour le texte protégé par le droit d'auteur (HCGE, Code AFEP-MEDEF — voir §5) et pour le contexte non décisionnel au sens de l'arbitrage du 3bis. Si, après avoir épuisé la méthode d'extraction, une donnée reste réellement inaccessible, le déclarer explicitement comme une limite (« donnée non récupérée à ce stade, malgré recherche ciblée »), sans la présenter comme un service optionnel.
4. Identifier la **vague CSRD applicable** avant tout constat sur le Bloc J (voir §7).
5. Restituer des constats factuels sourcés, **sans** conclusion de conformité globale ni note d'appréciation.
6. Vérifier les récurrences nominatives via `recurrences_nominatives.md` et, pour chaque mention AMF/HCGE, **en restituer le motif** (bonne pratique, non-conformité, exemple, échantillon), année par année — jamais un simple « cité X fois » (voir §5, asymétrie nominative).

### Usage 4 — Croisement thématique multi-émetteurs
Comparer plusieurs émetteurs (5 à 10 en général) sur une thématique de gouvernance donnée (say on pay, indépendance du conseil, évaluation, durabilité, etc.), restitué en tableau comparatif sourcé.
1. **Construire le cadre doctrinal du thème depuis le corpus** (comme l'Usage 1, mais sur un thème) : positions AMF / HCGE / ESMA, fondements légaux (article exact), statut normatif, statistiques de place — chaque élément cité mot pour mot avec sa page. Ce cadre précède le tableau.
2. **Arrêter la liste des émetteurs.** Si l'utilisateur ne la fixe pas, partir des émetteurs les plus cités sur le thème dans le corpus (balayage des index + `recurrences_nominatives.md`), complétés au besoin d'émetteurs emblématiques ou de cas contestés. Annoncer la liste retenue.
3. **Définir les colonnes de comparaison** (les critères du thème : pour le say on pay, p. ex. résolutions ex ante / ex post, taux d'approbation, structure et montant de la rémunération, critères RSE du variable).
4. **Pour CHAQUE émetteur : drainer le corpus (mentions nominatives, motif + page), PUIS lancer une recherche DEU automatique sur internet pour combler tout élément manquant.** La passe web par émetteur **n'est pas optionnelle** : dès qu'une cellule du tableau n'est pas couverte par le corpus, déclencher d'office la recherche du **DEU et de la brochure de convocation à l'AG** de l'émetteur, puis appliquer la méthode §6bis (priorité : `fetch` de la section > recherches répétées). Une cellule ne peut être marquée « non récupérée » **qu'après épuisement** de cette recherche DEU — jamais laissée vide par défaut, ni faute d'avoir cherché. C'est le pendant multi-émetteurs de l'interdiction du renvoi-substitut (§usage 3, 3ter).
5. **Restituer en tableau comparatif à double sourçage** : corpus → page exacte ; web → lien cliquable + date de consultation, cellule par cellule.
6. **Comparabilité** : retenir le **même exercice et le même périmètre** pour tous les émetteurs (sinon le signaler explicitement) ; ne pas agréger des **régimes distincts** sans les distinguer (société en commandite par actions où la rémunération des gérants relève de l'associé commandité ; société de droit étranger au say on pay consultatif ; etc.).
7. **Posture — juxtaposer et dater, jamais qualifier ni classer.** Mêmes interdits que l'Usage 2 : pas d'adjectif ni de verbe évaluatif (« généreux », « aligné », « excessif », « raisonnable »), pas de hiérarchie « bon / mauvais » say on pay, pas de note. Restituer chiffres et faits datés ; laisser le lecteur comparer.

### Recherche internet (transversale, systématique et toujours obligatoire)

Le corpus indexé est un **instantané figé** (rapports arrêtés à 2025) : il est la base de profondeur, exacte à la page, mais il ne peut, par construction, ni être à jour, ni couvrir l'intégralité des travaux pertinents (rapports plus récents, consultations, travaux conjoints de régulateurs, doctrine, vie propre des émetteurs). **La recherche internet est donc systématique et obligatoire pour toute production de fond, quel que soit l'usage (1, 2 ou 3), sans exception.** Elle n'est limitée ni dans le temps, ni par thème. **Dans le temps** : le corpus indexé est une **fenêtre 2020-2025** ; tout ce qui est en dehors relève du web — la matière **antérieure** (rapports AMF publiés depuis ~2010, recommandation DOC-2012-02 de 2012, versions successives du Code AFEP-MEDEF de 2008 à 2022, loi Florange de 2014, positions et travaux plus anciens), la matière **postérieure** à 2025, comme les travaux **non indexés** de la période couverte. Une analyse longitudinale, en particulier, doit pouvoir remonter à la **genèse** d'une doctrine, souvent antérieure à 2020 : ne couvrir que l'aval tronque l'amont. **Par thème** : aucune restriction non plus. L'objectif est l'**exhaustivité — ne rien omettre**.

**Ne jamais présumer qu'un thème est « bien couvert » par l'index ou « stabilisé ».** Le skill ne s'en remet pas à un jugement de spécialiste sur ce qui mériterait ou non une recherche : ce jugement n'est pas fiable et conduit à des angles morts. La règle est invariable — **chercher à chaque fois, largement, puis confronter au corpus indexé**. Exemple : le thème de l'intelligence artificielle et de la gouvernance est partiellement présent dans les index, mais de nombreux travaux (rapports récents de l'AMF sur l'IA, travaux conjoints AMF-ESMA) n'y figurent pas ; seule une recherche systématique évite l'omission.

Principe directeur : **index figé = corpus de référence (profondeur, page exacte) + web = exhaustivité et actualité.** Les deux sont toujours mobilisés ensemble, jamais l'un sans l'autre. La recherche réunit l'information primaire (émetteur, canaux officiels) et secondaire (presse, doctrine) pertinente, en mobilisant les sources ci-dessous selon leur nature.

#### Principe de hiérarchie des sources
Toujours privilégier la source la plus primaire et la plus officielle disponible, et **qualifier chaque élément par sa nature** (information primaire officielle / information primaire émetteur / source secondaire presse / source secondaire doctrinale) et par sa **date**.

#### A. Information primaire — canaux officiels et réglementés
- **Site de l'émetteur** (rubrique « investisseurs » / « information réglementée ») : document d'enregistrement universel (URD/DEU), rapports financiers annuels et semestriels, brochures de convocation et procès-verbaux d'AG, communiqués, présentations investisseurs, politique et rapports de rémunération, statuts, composition du conseil et des comités. **Source primaire de référence** pour un audit d'émetteur (usage 3).
- **BDIF** (Base des décisions et informations financières de l'**AMF**) : décisions de l'AMF, informations réglementées déposées par les émetteurs, déclarations de franchissement de seuils et déclarations d'intention, communiqués, décisions de sanction. **Source du régulateur** — fiable et nominative. À utiliser pour retrouver l'information réglementée officielle d'un émetteur et les décisions AMF le concernant.
- **BALO** (Bulletin des annonces légales obligatoires, édité par la **DILA**, consultable gratuitement sur Légifrance / e-BALO, archives depuis 2001) : publications obligatoires des sociétés faisant appel public à l'épargne — comptes annuels et semestriels, opérations financières (émissions de titres, fusions, scissions), **convocations et résultats d'assemblées générales**, notifications du nombre de droits de vote (art. L. 233-7 C. com.). Fondements : art. R. 210-3 et R. 232-11 C. com., RGAMF. **Source officielle** pour les dates, ordres du jour, résolutions et résultats de vote d'AG, et pour les opérations sur titres. *(Avant le décret n° 2009-1409 du 17 novembre 2009, le BALO intégrait aussi les avis de l'ancien Bulletin officiel de l'AMF — utile pour la recherche historique.)*
- **Légifrance / EUR-Lex** : codification en vigueur d'un article à la date de la question (la matière évolue vite : loi Attractivité 2024, réforme des nullités ordonnance 2025-229 en vigueur le 1er octobre 2025, abrogation différée de L. 22-10-10 au 1er janvier 2027, paquet Omnibus CSRD). Vérification obligatoire dès qu'une question porte sur l'état du droit actuel.
- **Sites AMF, HCGE, ESMA, EFRAG** : rapports, recommandations, positions ou textes situés **hors de la fenêtre du corpus — antérieurs (rapports AMF/HCGE plus anciens, DOC-2012-02, versions antérieures du Code) comme postérieurs** (rapport AMF/HCGE plus récent, nouvelle orientation ESMA, ESRS révisés).

#### B. Information secondaire — presse et doctrine
**La recherche de doctrine et de presse est systématique pour toute fiche ou note de fond, quel que soit l'usage (audit d'émetteur comme analyse thématique ou longitudinale)** — pas seulement pour les audits d'émetteur. Le corpus indexé (AMF/HCGE/Code) est la source primaire ; il doit être complété par l'éclairage doctrinal et de presse, qui apporte le débat académique, l'analyse critique de la norme et le contexte d'actualité que le corpus régulateur ne contient pas. Ne pas livrer une fiche de fond mobilisant uniquement le corpus indexé sans avoir cherché la doctrine et la presse pertinentes.
- **Presse** (économique et financière, presse spécialisée) : contexte, opérations récentes, déclarations, dates d'AG, renommages, conflits actionnariaux. **Source secondaire** : utile pour le contexte et le repérage, mais **toute donnée doit être reconfirmée sur une source primaire** (site émetteur, BDIF, BALO) avant d'être restituée comme un fait. Ne jamais traiter une affirmation de presse comme un fait établi sans corroboration.
- **Doctrine** (revues juridiques, notes de cabinets, articles universitaires, commentaires de place) : qualification juridique, analyse des positions AMF/HCGE/ESMA, discussion des réformes. **Source secondaire d'analyse** : à attribuer nommément à son auteur, distinguée des positions des régulateurs et de la soft law. Ne jamais présenter une opinion doctrinale comme une position de l'AMF ou du HCGE.

#### C. Sources à accès partiel
Certaines sources ne sont accessibles qu'en partie (résumé, première page, aperçu, paywall, extrait). Elles **peuvent** être utilisées, à deux conditions strictes :
- **Ne restituer que ce qui est effectivement consultable** (titre, résumé, extrait visible, métadonnées). Ne jamais inférer, compléter ou reconstituer le contenu non accessible, ni présumer ce que « dirait » la partie non lue.
- **Signaler explicitement l'accès partiel** et sa date (« d'après le résumé accessible de… », « selon l'extrait visible de… »). Si un fait déterminant repose uniquement sur une portion non accessible, l'indiquer comme **non vérifié** et le distinguer nettement des faits établis.

#### Règles communes
- **Sourçage universel — rien sans renvoi.** Toute information restituée porte un renvoi vérifiable, sans exception : un fait issu du **corpus indexé** renvoie au rapport et à sa **page exacte** ; un fait issu du **web** est accompagné d'un **lien hypertexte cliquable** vers la source précise (l'article ou le document exact, jamais une page d'accueil générique) et de sa **date de consultation**. **Toute URL provient des résultats de recherche/fetch effectifs et pointe vers une page réelle ; ne jamais reconstituer, deviner ni citer de mémoire un lien (cf. règle fondatrice — zéro invention, §1). En cas de doute sur l'existence ou l'exactitude d'un lien, l'omettre ou le signaler comme non vérifié plutôt que de le restituer.** Aucune affirmation — de corpus comme de web — n'est livrée sans sa source. Une simple étiquette de registre (« presse », « doctrine », « source secondaire ») ne suffit jamais : sans renvoi page ou sans lien, la source est réputée absente et l'affirmation ne doit pas être restituée.
- **Toujours distinguer** trois registres : (1) corpus indexé (sourcé, daté, vérifié), (2) source primaire web (officielle, à dater), (3) source secondaire web (presse/doctrine, à attribuer et corroborer). Ne jamais présenter un résultat web comme s'il venait d'un index, ni l'inverse.
- **Vérification croisée des chiffres web (règle absolue).** Tout chiffre issu d'une source secondaire (presse, agrégateur, doctrine) — montant de rémunération, ratio, taux, pourcentage de capital — doit être **confirmé par au moins une seconde source indépendante** ou, à défaut, par une source primaire (DEU, communiqué réglementé, BALO), avant d'être restitué comme un fait. Vérifier en particulier que le chiffre se rapporte au **bon exercice** et au **bon périmètre** (un tableau de rémunération peut agréger plusieurs dirigeants, mélanger exercices versé/attribué, inclure ou non un avantage en nature). Un chiffre non corroboré est soit écarté, soit restitué en le signalant explicitement comme non confirmé et daté de l'exercice exact auquel il se rapporte. Ne jamais attribuer un chiffre à un exercice autre que le sien.
- **Dater et sourcer** chaque élément issu du web (auteur/éditeur, document, date, URL le cas échéant).
- **Respecter le droit d'auteur** : appliquer aux sources web (presse, doctrine, sites) la même règle que pour le corpus protégé — citations courtes, paraphrase, renvoi à la source ; pas de reproduction substantielle.
- **Pour un audit d'émetteur (usage 3)** : ouvrir par le site de l'émetteur et la BDIF (information primaire), recouper les dates et résultats d'AG via le BALO, puis seulement mobiliser presse et doctrine pour le contexte — en maintenant à chaque étape la distinction de registre et de statut normatif.

### Format des productions — lisibilité mobile
Les fiches et notes sont fréquemment lues sur téléphone. **Éviter les tableaux larges (plus de deux ou trois colonnes), qui débordent de l'écran mobile et deviennent illisibles.** Présenter les données d'évolution longitudinale, les séries statistiques et les comparaisons **en prose**, en intégrant les chiffres dans le texte (ex. « pour l'exercice 2024, le taux s'établit à 78 % sur le SBF 120 et 84 % sur le CAC 40 »), ou en listes verticales courtes. Les listes à puces et la prose se lisent bien en défilement vertical ; les tableaux à plusieurs colonnes ne se prêtent qu'aux contenus brefs (deux colonnes maximum) et à un usage sur écran large. En cas de doute, privilégier la prose. **Format des citations** : les citations littérales se présentent entre guillemets français « … » uniquement, sans balise (`<q>`, `<blockquote>`, etc.) — le rendu doit être propre en markdown comme en Word. **Exception, seul emploi admis du guillemet droit** : lorsque la source place elle-même un passage entre guillemets *à l'intérieur* d'un passage cité, ce second niveau se restitue en guillemets droits " … ", afin que l'ouverture et la fermeture de la citation principale restent non ambiguës. Convention uniforme sur l'ensemble des index ; elle ne modifie aucun mot de la source et ne dispense d'aucune des règles de fidélité du §5.

**Appels de note.** Le chiffre de renvoi à une note de bas de page n'appartient pas au texte : il se présente en exposant sur la page et se colle au mot précédent à l'extraction (« EC38 » pour « EC »38). Il est **retiré de l'intérieur des guillemets**. S'il importe de le signaler, il se mentionne hors citation (« … » — appels de notes 38 et 39). Un chiffre conservé dans une citation se lit comme un mot de la source et fait croire à une dénomination qui n'existe pas.

### Date d'élaboration exacte
Toute fiche ou note indique sa **date exacte d'élaboration au jour près (jour mois année)**, par exemple « Fiche élaborée le 18 juin 2026 », et non une simple mention de mois ou d'année. Cette date figure dans l'en-tête ou l'encadré liminaire de la production. Elle est distincte des dates de consultation des sources web (qui accompagnent chaque lien).

### Citation des sources dans les productions — pas d'étiquettes entre crochets
**Ne pas utiliser d'étiquettes de registre entre crochets** (du type « [AMF] », « [HCGE] », « [DEU] », « [WEB-S] ») dans le corps des fiches et notes : elles alourdissent la lecture et font doublon avec la référence. Chaque fait porte à la place :
- pour le corpus indexé et les sources officielles : une **référence claire en toutes lettres dans le texte** (ex. « selon le rapport AMF 2025, p. 28 », « rapport HCGE 2025, p. 20 », « art. L. 22-10-9 C. com. ») ;
- pour les sources externes (doctrine, presse, sites, textes en ligne) : un **lien hypertexte cliquable** vers la source précise.

Le **registre** de la source (régulateur / soft law / source secondaire) reste exprimé par les **mots eux-mêmes** (« l'AMF, autorité publique indépendante… », « le HCGE, instance de soft law… », « selon la doctrine… »), et non par une étiquette. La distinction des registres demeure obligatoire ; seule sa matérialisation par crochets est supprimée.

### Date de consultation des sources web
Toute source web citée (doctrine, presse, site officiel, texte en ligne) est accompagnée de sa **date de consultation**, pour la traçabilité scientifique (les pages en ligne évoluent). Format : mention « consulté le [date] » à côté du lien, ou en note. Les sources du corpus indexé (datées par nature) n'en ont pas besoin.

### Bibliographie récapitulative
Toute fiche ou note de fond se termine par une **bibliographie récapitulative** regroupant l'ensemble des sources citées, organisée par catégorie : (1) corpus indexé (rapports AMF/HCGE/Sénat, Code, avec millésime) ; (2) sources légales et européennes (avec référence codifiée) ; (3) sources primaires web (site émetteur, BDIF, BALO, avec lien et date de consultation) ; (4) sources secondaires (doctrine, presse, avec auteur, lien et date de consultation). Cette bibliographie facilite la réutilisation académique et la vérification.

### Marque du skill (signature obligatoire de toute production)
Toute fiche, note ou document produit avec ce skill porte une **mention discrète en pied de page, répétée sur chaque page**, identifiant le skill comme outil d'élaboration. La mention reste sobre (petite taille, gris), n'empiète pas sur le contenu, et figure sur toutes les pages. Elle s'ajoute aux sources et n'en tient pas lieu.

> **Formulation exacte de la marque** : « Fiche élaborée avec le skill gouvernance-emetteurs-cotes — © Gillan Saleh ».

## 6bis. Collecte — méthode d'extraction du DEU et des données chiffrées (couche délégable au MCP)

> **Statut de cette section — couche de collecte.** Ce paragraphe décrit une *procédure de collecte* (localisation, téléchargement, lecture, extraction), distincte de la *méthode d'analyse* (taxonomie §2, règles §5, usages §6, contrôle §8). Lorsque le MCP local de la Phase 3 sera en service, ses outils (recherche BALO/BDIF, base documentaire indexée, extraction) se substitueront aux étapes manuelles ci-dessous **sans modification de la méthode** : seule cette section sera remplacée par les appels d'outils correspondants.

Le DEU fait souvent plusieurs centaines de pages. La technique d'accès dépend de sa forme de publication : un **PDF monolithique** ne se cible pas page par page avec `web_fetch` (passer alors par le téléchargement local, étape 2, ou les recherches ciblées, étape 4) ; mais beaucoup d'émetteurs publient leur DEU comme un **site navigable, une URL par section** (gouvernance, rémunération, capital, durabilité) — dans ce cas `web_fetch` lit le chapitre **en entier**, et c'est la voie privilégiée. Cette contrainte technique **n'autorise jamais** à se rabattre sur un renvoi (§usage 3, 3ter).

**Priorité (dès qu'on vise l'exhaustivité d'un document ou d'un chapitre localisé) : `fetch` de la section > recherches répétées.** `web_search` sert à *localiser* (trouver la bonne URL, ou un fait isolé éparpillé) ; il remonte des fragments, jamais un document entier. `web_fetch` (ou le téléchargement local) sert à *lire en entier* une URL localisée. Pour couvrir un chapitre connu du DEU (la composition du conseil, la rémunération, l'actionnariat…), **fetcher la section** ; ne jamais substituer une série de `web_search` à cette lecture intégrale, sous peine de blocs « partiels » alors que l'information était accessible. Le `search`-seul n'est acceptable que pour un fait ponctuel et dispersé (typiquement Usage 1), pas pour un audit.

Protocole, dans l'ordre, jusqu'à obtention de la donnée :

1. **Localiser le DEU et la brochure de convocation à l'AG** : site émetteur (rubrique information réglementée / publications / assemblée générale), BDIF (base AMF), BALO, ou miroirs de dépôt légal. Récupérer l'URL exacte de chaque PDF. La brochure de convocation est souvent plus directement exploitable que le DEU pour les CV d'administrateurs, les dates de nomination, les durées de mandat et le détail des résolutions.
2. **Télécharger dans l'environnement** lorsque le domaine est autorisé (le PDF peut alors être lu par segments, page à page, et les chiffres extraits directement). Si le domaine n'est pas autorisé pour le téléchargement, passer aux étapes suivantes.
3. **Lecture segmentée par `web_fetch`** : récupérer le sommaire pour identifier la pagination des chapitres pertinents (gouvernance, rémunération, actionnariat, durabilité), puis cibler ces segments.
4. **Recherches web ciblées donnée par donnée** : pour chaque chiffre manquant (taux d'indépendance, nombre de réunions et taux d'assiduité du conseil, montant et structure de la rémunération du PDG, ratios d'équité, répartition de l'actionnariat, droits de vote double), lancer une requête précise (« [émetteur] [exercice] taux assiduité conseil », « [émetteur] rémunération [dirigeant] [exercice] fixe variable »), en privilégiant les sources primaires (DEU, communiqués réglementés, BALO) et en corroborant les sources secondaires.
5. **Restituer la donnée** avec sa source et, pour le DEU, la page ou le chapitre exact. **Ne pas conclure à l'indisponibilité avant d'avoir épuisé les étapes 1 à 4.**
6. Si, et seulement si, la donnée demeure inaccessible après ce protocole, l'indiquer comme limite explicite (« non récupérée à ce stade malgré recherche ciblée ») — jamais comme un renvoi ou un service optionnel.

**Données chiffrées à obtenir systématiquement pour un audit d'émetteur** (liste minimale, à restituer, pas à renvoyer) : taille du conseil, taux d'indépendance, taux de féminisation, ancienneté moyenne ; **pour chaque administrateur : date de première nomination et durée / échéance du mandat** (jamais omises) ; nombre de réunions du conseil et de chaque comité, taux d'assiduité ; résultat et modalités de l'évaluation du conseil ; composition nominative et taux d'indépendance de chaque comité ; rémunération de chaque dirigeant mandataire social (fixe, variable, long terme, total), critères de performance, ratios d'équité, résultats des votes say on pay ; structure de l'actionnariat et des droits de vote, franchissements de seuils ; délégations financières et programme de rachat ; vague et indicateurs clés de durabilité.



## 7. Bloc J — durabilité (terrain à risque accru)

Le Bloc J est un **terrain à risque accru** : la réglementation de la durabilité a évolué très rapidement et le corpus indexé (2020-2025) peut décrire un état du droit déjà dépassé. Toute analyse de durabilité exige une vérification de l'état en vigueur (recherche internet : EUR-Lex, AMF, EFRAG).

### Pourquoi ce bloc diffère des autres
Contrairement aux Blocs A-I (assis sur le Code de commerce et le Code AFEP-MEDEF, relativement stables), le Bloc J repose sur un cadre européen en transformation continue : directive CSRD (2022/2464), normes ESRS, et leur révision par le **paquet Omnibus / directive « Stop-the-clock » (UE) 2025/794** (avril 2025) puis l'accord Omnibus de décembre 2025. **Opposer à un émetteur des obligations ESRS qui ne lui sont pas encore applicables est une erreur de méthode.**

### La différence-clé : régime DPEF vs régime CSRD/ESRS
Avant la CSRD, les sociétés relevaient de la **DPEF** (déclaration de performance extra-financière, art. L. 225-102-1 C. com., issu de la directive NFRD). La CSRD remplace progressivement la DPEF par un **rapport de durabilité** normalisé selon les **ESRS**, avec double matérialité et assurance. Tant qu'une société n'est pas entrée dans le régime CSRD selon sa vague, **elle reste en régime DPEF** : lui appliquer la grille ESRS serait un anachronisme. Identifier le régime applicable est donc le **premier réflexe** du Bloc J.

### Identifier la vague CSRD applicable (fait binaire — calendrier au regard de l'état mi-2026)
Après la directive « Stop-the-clock » (UE) 2025/794 et l'accord Omnibus du 16 décembre 2025 :

| Vague | Périmètre | Premier reporting | Exercice couvert |
|---|---|---|---|
| **Vague 1** | Sociétés déjà soumises à la NFRD (grandes cotées, EIP) | **2025** (inchangé) | **FY 2024** |
| **Vague 2** | Autres grandes entreprises (seuils relevés par l'Omnibus : > 1 000 salariés et > 450 M€ de CA net) | **2028** (reporté, au lieu de 2026) | **FY 2027** |
| **Vague 3** | PME cotées (vague d'origine) | **2029** (reporté, au lieu de 2027) | **FY 2028** — *l'Omnibus de déc. 2025 retire les PME cotées du champ obligatoire ; reporting volontaire (norme VSME) attendu* |
| **Vague 4** | Sociétés de pays tiers à activité substantielle dans l'UE | **2029** | **FY 2028** |

**Garde-fous** : (1) ce calendrier est lui-même susceptible d'évoluer (réforme substantielle de la CSRD encore en discussion) — **vérifier l'état en vigueur par recherche internet (EUR-Lex) avant tout constat**. (2) Les **seuils** ont été relevés par l'Omnibus : une société dans le champ initial peut en être sortie. (3) Les **ESRS sont en cours de révision** (mandat EFRAG, réduction du nombre de points de données) — ne pas opposer une version d'ESRS périmée.

### Règles spécifiques de restitution du Bloc J
- **Identifier la vague et le régime applicables** (DPEF vs CSRD) avant tout constat. Ne pas opposer à un émetteur encore en régime DPEF des obligations ESRS non applicables.
- **Privilégier la citation littérale** des sources plutôt que la paraphrase.
- **Pas de qualification de « maturité CSRD »** ni d'analyse de conformité ESRS. Le skill restitue des faits sourcés, pas un jugement de conformité durabilité.
- Pour une analyse approfondie, **renvoyer aux sources brutes** (texte CSRD, ESRS applicables à la date, doctrine AMF durabilité via `index_AMF_DURABILITE_2024.md` et `index_AMF_CSRD_WAY_FORWARD_2025.md`, priorités ESMA via `index_ESMA_ECEP_2025.md`).
- Distinguer **EFRAG** (conseiller technique, rédacteur des ESRS) de l'**ESMA** (régulateur) et de l'**AMF** (régulateur national) — jamais confondus.

## 8. Contrôle avant livraison — noyau bloquant, verrous d'usage, contrôles de forme

La checklist v1 (34 points) est restructurée en deux étages, **sans suppression** : chaque point v1 est promu en verrou, rattaché à un verrou ou reclassé en contrôle de forme (correspondance en §8.5).

### 8.1 Noyau bloquant universel (8 verrous)

**Si un seul verrou échoue : ne pas livrer.** Ces huit tests s'appliquent à toute production, sans exception.

**Verrou 1 — Zéro invention et sourçage universel.** Chaque fait — chiffre, citation, page, article, nom de société ou de personne, date, URL — provient d'une source effective : corpus indexé (avec page exacte) ou web réellement consulté (lien issu d'un résultat de recherche/fetch effectif, jamais reconstitué ni cité de mémoire). Chiffres recomptés à la source, sans arrondi ; si la source liste sans totaliser, compter explicitement et le signaler (« j'en compte X ») ; tout chiffre issu d'une source secondaire web est corroboré (seconde source ou source primaire) et rapporté au bon exercice. Tout fait non sourçable est omis ou déclaré non vérifié — jamais comblé par une invention vraisemblable.

**Verrou 2 — Pages confirmées.** Vérification visuelle du PDF source pour toute citation critique ; la page restituée est celle où figure le fait, pas celle de l'ouverture du chapitre.

**Verrou 3 — Fidélité du verbe.** Vocabulaire juridique restitué mot pour mot (notions composées et épithètes conservés : « dirigeant mandataire social exécutif », « avéré », « significatif »…). Quand le texte exact figure dans l'index, il est restitué intégralement en citation, jamais tronqué ni résumé. Aucun adjectif, verbe ou intitulé de section interprétatif absent de la source — ni dans le corps, ni dans les titres.

**Verrou 4 — Autorités distinguées.** AMF / ESMA / ANC / HCGE / AFEP-MEDEF / EFRAG / IASB / ISSB jamais confondus. HCGE et AFEP-MEDEF jamais qualifiés d'« autorité » ou de « régulateur ».

**Verrou 5 — Fondement juridique et socle du droit.** Pour chaque norme mobilisée : obligation légale ≠ soft law ≠ position de régulateur, explicitement identifié. Un droit de l'actionnaire est fondé sur son socle civiliste (Code civil) avant ses modalités du Code de commerce ; le droit lui-même n'est pas confondu avec la compétence de l'organe qui en décide l'exercice.

**Verrou 6 — Exercice et périmètre.** Chaque statistique porte son exercice et son périmètre (SBF 120 / CAC 40 / échantillon AMF), jamais agrégés ni confondus entre eux.

**Verrou 7 — Aucun renvoi-substitut.** Aucune donnée factuelle accessible n'est remplacée par « figure p. X », « disponible sur demande » ou équivalent ; la méthode d'extraction (§ 6bis) est épuisée avant toute mention « donnée non récupérée », laquelle est alors déclarée comme limite explicite.

**Verrou 8 — Droit d'auteur.** HCGE et Code AFEP-MEDEF : au plus 2-3 phrases citées par passage, renvoi au document pour le reste, pas de paraphrase du raisonnement. (Seule exception légitime au verrou 7 : le renvoi paginé est ici la règle.)

### 8.2 Verrous conditionnels (bloquants dans leur périmètre)

**Toute production de fond :**
- Recherche web systématique effectuée (doctrine, presse, travaux récents, y compris postérieurs ou extérieurs au corpus) — jamais dispensée au motif d'un thème « bien couvert » ou « stabilisé ».
- Divergences entre sources exposées explicitement, chaque version attribuée et datée, résolues selon la hiérarchie (primaire > secondaire ; régulateur et soft law sur des plans distincts) — aucune divergence tranchée en silence.
- Silences du corpus signalés (après vérification à la source), jamais masqués.
- Prospective restituée : thèmes de réflexion et pistes « à venir » des sources drainés, pas seulement les constats de l'exercice écoulé.

**Usage 2 (analyse longitudinale) :** frise datée balayant chaque exercice, absences signalées, changements de codification distingués des évolutions de fond ; genèse antérieure au corpus et développements postérieurs intégrés via la recherche web ; séquence juxtaposée et datée, jamais caractérisée.

**Usage 3 (audit d'émetteur) :** DEU consulté d'office ou indisponibilité déclarée (blocs dépendants marqués partiels) ; tous les blocs A-M et tous leurs sous-thèmes couverts ; corpus drainé exhaustivement pour l'émetteur et ses entités liées, chaque fait décisionnel restitué mot pour mot avec source et page (arbitrage exhaustivité/lisibilité du 3bis) ; chaque mention nominative qualifiée par son motif (bonne pratique / non-conformité / exemple / échantillon), année par année.

**Usage 4 (croisement multi-émetteurs) :** même exercice et même périmètre pour tous les émetteurs (sinon signalé) ; régimes particuliers (commandite, say on pay consultatif de droit étranger) signalés et non agrégés ; passe DEU + brochure épuisée avant toute cellule « non récupérée ».

**Bloc J (durabilité) :** vague CSRD et régime applicable (DPEF / CSRD) identifiés avant tout constat ; état du droit en vigueur vérifié si la question est actuelle.

### 8.3 Contrôles de forme (à corriger en relecture avant livraison)

Défauts détectables et corrigeables sans reprendre le fond : marque du skill en pied de page ; date d'élaboration exacte (jour mois année) ; date de consultation sur chaque source web ; bibliographie récapitulative en fin de fiche, par catégorie ; présentation uniforme des citations (bloc italique, source + page) ; registre exprimé par les mots, sans crochets d'étiquetage ; distinction explicite des trois registres (corpus indexé / source primaire web / source secondaire web) ; lisibilité mobile (pas de tableau large ; séries et comparaisons en prose ou listes verticales).

### 8.4 La checklist interne ne vaut pas vérification

L'exécution du présent § 8 par l'instance productrice est une condition **nécessaire, jamais suffisante**. Toute production de fond destinée à être utilisée, citée ou diffusée passe par une **instance vérificatrice neutre, dans une conversation neuve**, selon le protocole `VERIFICATION.md`. Le verdict du vérificateur prime sur l'auto-attestation du producteur. Une production sans verdict archivé est réputée non vérifiée.

### 8.5 Table de correspondance V1 → V2 (traçabilité)

- V1-1 (chiffres recomptés) → Verrou 1
- V1-2 (vocabulaire mot pour mot) → Verrou 3
- V1-3 (aucun terme interprétatif) → Verrou 3
- V1-4 (pages confirmées) → Verrou 2
- V1-5 (fondement juridique) → Verrou 5
- V1-6 (année + indice) → Verrou 6
- V1-7 (acteurs distingués) → Verrou 4
- V1-8 (mentions nominatives qualifiées) → 8.2 Usage 3
- V1-9 (DEU + blocs A-M) → 8.2 Usage 3
- V1-10 (exhaustivité du corpus) → 8.2 Usage 3
- V1-11 (aucun renvoi-substitut) → Verrou 7
- V1-12 (données chiffrées restituées) → Verrous 1 et 7
- V1-13 (marque du skill) → 8.3
- V1-14 (droit d'auteur) → Verrou 8
- V1-15 (Bloc J) → 8.2 Bloc J
- V1-16 (trois registres) → 8.3
- V1-17 (recherche web systématique) → 8.2 production de fond
- V1-18 (sourçage universel) → Verrou 1
- V1-19 (lisibilité mobile) → 8.3
- V1-20 (pas de crochets) → 8.3
- V1-21 (date de consultation) → 8.3
- V1-22 (bibliographie) → 8.3
- V1-23 (frise longitudinale) → 8.2 Usage 2
- V1-24 (chiffres web croisés) → Verrou 1
- V1-25 (divergences exposées) → 8.2 production de fond
- V1-26 (citation complète) → Verrou 3
- V1-27 (pas de titre fabriqué) → Verrou 3
- V1-28 (prospective) → 8.2 production de fond
- V1-29 (citations uniformes) → 8.3
- V1-30 (date d'élaboration) → 8.3
- V1-31 (droit vs organe / civil vs commercial) → Verrou 5
- V1-32 (silences signalés) → 8.2 production de fond
- V1-33 (provenance des URL) → Verrou 1
- V1-34 (multi-émetteurs) → 8.2 Usage 4

## 9. Gestion des erreurs

Reconnaître brièvement, corriger, avancer. Pas de méta-commentaires, pas d'autocritiques étendues, pas d'explications de « ce que j'aurais dû faire ».
