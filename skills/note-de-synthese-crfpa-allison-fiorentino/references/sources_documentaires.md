# Sources documentaires et protocole de collecte

## 0. Règle cardinale

Aucune référence n'entre dans le dossier ou dans la grille sans avoir été vérifiée pendant la session sur sa source. Pas de citation de mémoire, pas de numéro de pourvoi reconstitué, pas de page de revue approximative. Si une pièce ne se vérifie pas, elle est abandonnée et remplacée : mieux vaut un dossier de 16 documents exacts qu'un dossier de 20 dont trois sont douteux.

Lire chaque décision retenue en texte intégral avant de la résumer. Un résumé de résumé introduit des erreurs de solution.

**Conserver la source brute.** Pour chaque pièce reproduite en verbatim, enregistrer le texte intégral récupéré dans `sources/<id>.txt`, à côté de `dossier.json`, avec en première ligne la référence et l'URL ou l'identifiant. Deux cas :

- quand la source est téléchargeable depuis le terminal (open data de l'Assemblée nationale et du Sénat, HAL, Gallica, API Judilibre par la skill `judilibre`, sites publics accessibles), la télécharger directement dans le fichier : c'est la garantie la plus forte ;
- quand elle vient d'un outil MCP (OpenLegi, GoodLegal, LibreJustice, Legal Data Hunter), recopier le résultat brut d'un seul bloc dans le fichier, juste après l'appel, sans coupe ni mise en forme.

Ce fichier est la référence du contrôle de verbatim (`scripts/verifier_verbatim.py`). Le contrôle ne garantit rien si le fichier source a lui-même été retouché : il repère l'écart le plus fréquent, la reformulation qui s'introduit au moment de couper et de condenser.

## 1. Textes normatifs

**OpenLegi** (Légifrance) est la source primaire.

- `rechercher_code` pour un article de code : récupérer le numéro exact, le texte verbatim, la version en vigueur et le visa de modification (« modifié par la loi n° … du … »), que les sujets réels reproduisent dans l'intitulé.
- `rechercher_dans_texte_legal` pour les lois et ordonnances non codifiées.
- `recherche_journal_officiel` pour un texte très récent non encore consolidé.
- `lister_codes_juridiques` si l'on cherche la bonne branche.

Droit de l'Union : le texte des règlements et directives se récupère via GoodLegal (`eu_retrieve` par référence CELEX) ou Legal Data Hunter. Citer le numéro complet et l'intitulé officiel abrégé.

Conventions internationales et Conseil de l'Europe : recherche web sur le site de l'organisation, jamais de citation de mémoire.

**Reproduction** : les textes officiels français relèvent de la licence ouverte et sont librement reproductibles. Les textes de l'Union le sont également. Couper aux alinéas utiles et signaler la coupe.

## 2. Jurisprudence

| Ordre | Outil | Remarques |
|---|---|---|
| Judiciaire | skill `judilibre`, OpenLegi `rechercher_jurisprudence_judiciaire`, LibreJustice | Judilibre est le recours quand Légifrance est en panne |
| Administratif | OpenLegi `rechercher_jurisprudence_administrative`, `get_decision_administrative` | Conseil d'État, CAA |
| Constitutionnel | OpenLegi `rechercher_decisions_constitutionnelles` | DC, QPC |
| CEDH | GoodLegal `web_search` ciblé HUDOC, Legal Data Hunter | Le **résumé juridique** publié par le greffe est libre et parfait pour un dossier |
| CJUE | GoodLegal `eu_caselaw_search` puis `eu_retrieve` | Reprendre les points utiles de l'arrêt, pas les conclusions |
| Ancienne jurisprudence | skill `archeologue-gallica` | Pour un arrêt de principe antérieur aux bases modernes, et sa note d'origine |

Pour chaque décision, noter juridiction, formation, date, numéro de pourvoi, requête ou affaire, mention de publication (publié au bulletin, inédit, publié au recueil Lebon), et la solution exacte.

**Reproduction** : les décisions de justice françaises et européennes sont librement reproductibles. Pour une décision longue, ne garder que l'exposé du litige et les motifs décisifs, en signalant les coupes par « (…) ».

## 3. Travaux parlementaires et documents institutionnels

Gisement essentiel, libre de droits, et sous-exploité par les générateurs. Il fournit le registre « politique et social » que la Commission introduit systématiquement.

- **skill `travaux-preparatoires`** : exposé des motifs, amendements adoptés et rejetés, rapports de commission, comptes rendus de débats, via l'open data de l'Assemblée nationale et du Sénat. Un amendement adopté au projet de loi de finances figurait au dossier 2025, une proposition de loi et une proposition de résolution au dossier 2024.
- **Rapports d'information** des commissions permanentes et des délégations : excellent matériau de synthèse, déjà rédigé pour un lecteur non spécialiste.
- **Avis du Conseil d'État** sur les projets de loi, publiés depuis 2015.
- **Autorités administratives indépendantes** : Défenseur des droits, CNIL, CNCDH, Autorité de la concurrence, ARCOM, CNPEN. Leurs avis, décisions et communiqués sont libres et se prêtent aux extraits.
- **Cour de cassation** : notes explicatives d'arrêts, communiqués, rapports annuels, rapports de groupes de travail. Ce sont les meilleures pièces pour le procédé « décision plus commentaire » puisqu'elles sont gratuites.

## 4. Doctrine

Deux objectifs distincts : identifier les articles qui comptent sur le sujet, et déterminer lesquels sont reproductibles.

**Recherche et vérification** : skill `recherche-doctrine`, qui interroge ISIDORE (agrège Cairn, Persée, OpenEdition), HAL, OpenAlex, CrossRef, Sudoc, theses.fr, et produit un statut de vérification par référence. Compléter par Legal Data Hunter pour la doctrine étrangère si le sujet a une dimension comparée.

**Statut d'accès, à renseigner pour chaque référence :**

- *Accès ouvert reproductible* : dépôt HAL ou TEL, OpenEdition, Persée, revues en libre accès (RDLF, *Revue des droits de l'homme*, *Jus Politicum*, certains numéros de la *Revue internationale de droit économique*), thèses en ligne. Ces textes peuvent être extraits dans le dossier, en citant la source et en respectant la brièveté de l'extrait.
- *Accès payant* : Dalloz, LexisNexis, Lextenso, Éditions Législatives, Lefebvre. Le texte n'est pas reproduit. Produire à la place :
  - l'intitulé normalisé complet du document, exactement comme dans un sujet réel ;
  - une notice analytique de dix à quinze lignes rédigée par la skill, qui expose ce que l'auteur établit et pourquoi cela compte pour le sujet, sans reprendre ses formulations ;
  - la mention explicite « Extrait à insérer par l'enseignant. Référence : … DOI ou lien : … ».

Viser deux à quatre pièces de ce registre par dossier, dont au moins la moitié en accès ouvert ou dans le gisement institutionnel de la section 3, pour que le dossier reste jouable tel quel.

**Ouvrages** : les manuels et traités figurent régulièrement dans les sujets réels (Malaurie, Aynès et Stoffel-Munck en 2021, Garrigue et Deschamps en 2024). Ils ne sont pas reproductibles davantage : même traitement que la doctrine payante. Les vérifier au Sudoc pour l'édition et la pagination.

## 5. Documents non juridiques : le gisement sous Licence Ouverte d'abord, la presse ensuite

Ils remplissent deux fonctions : fournir l'accroche concrète de l'introduction et documenter la branche « insuffisances pratiques » du plan. Les sujets réels en comportent un à trois.

Une notice rédigée par la skill n'est pas un document non juridique : c'est un résumé, qui perd le ton, le point de vue et les chiffres bruts que le candidat doit apprendre à manier. D'où la règle : **au moins un document non juridique du dossier est reproduit en verbatim**, tiré du gisement public décrit ci-dessous. La presse sous droits ne vient qu'en complément, en notice factuelle.

### 5.1. Gisement reproductible

L'information publique produite par les administrations de l'État est en principe réutilisable sous la Licence Ouverte d'Etalab, à charge de mentionner la source et la date de mise à jour. Sources qui jouent naturellement le rôle de document « du monde actuel » :

- **Statistique publique** : INSEE (*Insee Première*, *Insee Focus*), DARES, DREES, SDSE du ministère de la Justice, SSMSI du ministère de l'Intérieur, INJEP. Chiffres, enquêtes, évolutions : le matériau idéal pour la branche des insuffisances pratiques.
- **Études et prospective** : France Stratégie, Haut Conseil pour le climat, Conseil d'orientation des retraites, Haut Conseil de la famille, de l'enfance et de l'âge.
- **Contrôle et évaluation** : rapports publics de la Cour des comptes et des chambres régionales, rapports des inspections générales (IGAS, IGF, IGJ) lorsqu'ils sont publiés.
- **Information institutionnelle** : vie-publique.fr (DILA), dossiers et synthèses ; communiqués de presse des ministères et des autorités administratives indépendantes.
- **Débats publics** : comptes rendus intégraux des séances parlementaires (déjà libres, voir section 3), auditions en commission.

### 5.2. Précautions avant de reproduire

1. **Vérifier en session les mentions légales du site**, ou la mention de licence figurant sur la publication. La Licence Ouverte est la règle pour l'État, pas une garantie universelle : certains organismes ou certaines publications ont leurs propres conditions. Noter dans `source.statut` le résultat de cette vérification.
2. **Écarter les contenus tiers intégrés** : tribunes et contributions signées par des auteurs extérieurs (fréquentes sur vie-publique.fr), photographies, infographies et graphiques d'agences, extraits de presse repris dans un rapport. Ils restent soumis aux droits de leur auteur.
3. **Reproduire à l'identique et dater** : le texte est extrait verbatim, coupé aux passages utiles avec « (…) », et l'intitulé indique l'organisme, le titre, le numéro de la publication et la date, comme pour toute autre pièce. Ne pas réécrire un chiffre ni actualiser une donnée : le document vaut à sa date.
4. **Discours publics** : un discours ministériel ou présidentiel peut servir de document non juridique, mais s'en tenir à un extrait bref, cité avec sa source, sauf si le site qui le publie le place expressément sous licence ouverte.

### 5.3. La presse sous droits

Les articles de presse sont protégés. Ne jamais recopier l'article. Produire un intitulé normalisé (titre, organe, date, auteur), marquer le document `"nature": "notice"`, et rédiger une **notice factuelle** à partir de l'information, qui restitue les faits, les chiffres et les positions en présence. Les faits bruts ne sont pas appropriables, la rédaction de l'article l'est.

Une notice de presse au plus par dossier, deux si le sujet l'exige vraiment : au-delà, le registre non juridique devient un registre de résumés.

## 6. Contrôle final des références

Avant production des fichiers :

1. Passer l'ensemble du dossier et de la grille au vérificateur d'hallucinations si la skill `legal-hallucination-checker` est disponible.
2. Recompter : chaque document a un intitulé complet, une source identifiée, un statut de reproduction.
3. Lancer `scripts/verifier_verbatim.py` : aucun segment non conforme, aucune source manquante.
4. Vérifier que les versions d'articles citées sont bien celles en vigueur, et signaler dans l'intitulé les modifications récentes comme le font les sujets réels.
5. Vérifier qu'aucun extrait sous droits n'a été reproduit par inadvertance.
