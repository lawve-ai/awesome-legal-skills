# Skill — Gouvernance des émetteurs cotés (`gouvernance-emetteurs-cotes`)

Outil d'analyse documentaire à vocation scientifique sur la **gouvernance des
émetteurs cotés français**. Le skill agrège, sous forme d'**index analytiques
sourcés**, un corpus réglementaire et doctrinal daté (rapports annuels AMF et
HCGE 2020-2025, doctrine AMF, guides d'application HCGE 2024-2025, Code
AFEP-MEDEF 2022, priorités ESMA 2025, guide Paris Europlace 2024, rapport
sénatorial 2025, textes légaux et européens — détail en « Corpus indexé »
ci-dessous) et permet de le restituer, de l'analyser dans le temps et de
l'appliquer à un émetteur.

> **Auteure : Gillan Saleh.**
> Licence : **CC BY-NC-SA 4.0** (voir le fichier `LICENSE`). Usage non commercial.

---

## Ce que fait le skill

Trois usages, servis par une grille d'analyse commune en **13 blocs (A-M)** :

1. **Restitution sourcée** — retrouver une position, une statistique ou une
   citation exacte, avec sa source et sa page.
2. **Analyse longitudinale** — comparer l'évolution d'une position ou d'une
   statistique dans le temps et entre institutions (AMF / HCGE / ESMA).
3. **Audit d'un émetteur** — appliquer la grille A-M à une société, à partir de
   son document d'enregistrement universel (DEU), complété par le corpus indexé
   et la recherche internet (doctrine, presse, sources officielles).

## Exemples (quickstart)

**Usage 1 — restitution sourcée.**
*Question* : « Quelle proportion de sociétés a évalué son conseil en 2022, selon l'AMF ? »
*Réponse type* : selon le rapport AMF 2023 (p. 28), « 92 % des sociétés de l'échantillon » et « 100 % du CAC 40 de l'échantillon » ont procédé à une évaluation du conseil en 2022 (exercice 2022 ; périmètre : échantillon AMF, à ne pas confondre avec le SBF 120). Complété, le cas échéant, par une recherche web pour tout développement postérieur.

**Usage 2 — analyse longitudinale** (extrait de frise, thème « évaluation du conseil ») :
- Rapport HCGE 2022, p. 36 : « Toutes les sociétés ont mis en place une évaluation du conseil. »
- Rapport AMF 2024, p. 36 : recommandations adressées à 21 sociétés, dont 5 du CAC 40 ; 18 mises en conformité.

Séquence datée et juxtaposée, jamais caractérisée. La frise remonte à la genèse antérieure au corpus et intègre les développements postérieurs, via recherche web.

**Usage 3 — audit d'un émetteur** (extrait illustratif ; la fiche complète couvre les 13 blocs A-M, à partir du DEU de l'émetteur + corpus + web) :
- *Bloc B — Composition et indépendance* : taux d'administrateurs indépendants, motifs de qualification, cas de dépassement de douze ans — chaque constat sourcé (rapport + page) et confronté au DEU.
- *Bloc E — Rémunération / say on pay* : structure de la rémunération, critères RSE, ratio d'équité (art. L. 22-10-9) — chiffres confirmés au DEU et au rapport de rémunération.

Chaque bloc renvoie au corpus indexé (page exacte) et à la source primaire de l'émetteur (lien).

## Principes directeurs

- **Posture d'agrégateur objectif** : faits sourcés et tendances, aucune opinion,
  aucun adjectif évaluatif.
- **Taxonomie stricte** : l'AMF (régulateur, nominatif assumé), l'ESMA et l'ANC
  (régulateurs), le HCGE et l'AFEP-MEDEF (soft law, anonymisation de principe)
  ne sont jamais confondus.
- **Restitution textuelle** : citations mot pour mot, avec page exacte ; chiffres
  littéraux uniquement ; chaque mention nominative qualifiée par son motif.
- **Droit d'auteur** : citations limitées et renvoi à la source pour les
  documents protégés (HCGE, Code AFEP-MEDEF) ; restitution directe des seuls
  faits non protégeables.
- **Bloc J (durabilité CSRD/ESRS)** : terrain à risque accru, encadré par un
  disclaimer méthodologique (vague applicable, régime DPEF/CSRD).

## Corpus indexé

Liste exacte des documents indexés (liens officiels pour les obtenir dans
`references/sources.md`) :

- **AMF — rapports annuels** sur le gouvernement d'entreprise et la rémunération des dirigeants des sociétés cotées, **exercices 2020 à 2025** (6 rapports).
- **AMF — doctrine** : guide d'élaboration du document d'enregistrement universel (position-recommandation **DOC-2021-02**) ; recommandation sur l'arrêté des comptes 2025 (**DOC-2025-08**) ; doctrine sur la durabilité DPEF/CSRD (**bilan 2024**) ; étude CSRD « The Way Forward » (**2025**).
- **HCGE — rapports annuels 2020 à 2025** (6 rapports) ; **Guide d'application du Code AFEP-MEDEF**, éditions **mars 2024** et **décembre 2025**.
- **ESMA** — priorités communes de contrôle (European Common Enforcement Priorities), **2025**.
- **Code AFEP-MEDEF**, édition **décembre 2022** (table de références croisées, sans reproduction du texte protégé).
- **Paris Europlace** — Guide du dialogue actionnarial (**juin 2024**).
- **Sénat** — rapport **n° 808 (2024-2025)**, commission d'enquête sur l'utilisation des aides publiques aux grandes entreprises et à leurs sous-traitants (Rietmann / Gay, **1er juillet 2025**) — volets gouvernance.
- **Textes légaux et européens** (via Légifrance / EUR-Lex, non figés) : Code de commerce, Code monétaire et financier, RGAMF, droit de l'Union (MAR, Prospectus, CSRD/ESRS, SRD II).

Le corpus indexé est une **fenêtre 2020-2025** ; il est systématiquement complété
par une recherche internet (actualité, travaux antérieurs ou postérieurs,
doctrine, sources officielles).

## Contenu du skill

```
SKILL.md                              Fichier d'orchestration (instructions, grille, méthode)
LICENSE                               Licence CC BY-NC-SA 4.0
NOTICES.md                            Attribution des sources tierces
README.md                             Ce fichier

index_AMF_2020.md … index_AMF_2025.md     Rapports AMF + doctrine AMF (durabilité, DEU…)
index_HCGE_2020.md … index_HCGE_2025.md   Rapports HCGE + guides d'application
index_ESMA_ECEP_2025.md                   Priorités de contrôle ESMA
index_Senat_Rietmann_2025.md              Rapport sénatorial (aides publiques)
index_Guide_HCGE_2025.md                  Guide d'application HCGE (déc. 2025)

code-afep-medef-references.md             Table de références croisées du Code (sans repro)
recurrences_nominatives.md                Croisement nominatif AMF + HCGE
references/droits-actionnaires-cotees.md  Catalogue sourcé des droits de l'actionnaire
references/sources.md                     Liens officiels pour obtenir les documents du corpus
scripts/check_completeness.py             Détecteur de complétude et de cohérence des index
```

## Grille d'analyse (13 blocs A-M)

A. Mode de gouvernance · B. Composition et fonctionnement du conseil ·
C. Succession et nomination · D. Comités (dont supervision des risques) ·
E. Rémunération (dont ratio d'équité) · F. Assemblée générale et droits des
actionnaires · G. Compléments financiers · H. Comply-or-explain ·
I. Structure capitalistique et contrôle · J. Durabilité (CSRD/ESRS) ·
K. Information financière et extra-financière · L. Conseillers en vote
(proxy advisors) · M. Notations et données ESG.

Sous-bloc transverse « Mixité et diversité » ; rubrique « Thèmes émergents »
(cybersécurité, IA dans la gouvernance, études thématiques).

## Productions

Le skill produit des **fiches émetteurs** et des **fiches thématiques** (Word),
chacune sourcée, avec distinction des registres (corpus indexé / source primaire
web / source secondaire), liens vers les sources secondaires, et une présentation
adaptée à la lecture mobile. Chaque production porte en pied de page la mention :
*« Fiche élaborée avec le skill gouvernance-emetteurs-cotes — © Gillan Saleh ».*

## Vérifier le corpus vous-même

Les citations de ce skill portent chacune leur document et leur page. Vous n'avez pas
à me croire sur parole : les programmes qui les vérifient sont livrés avec le corpus,
et vous pouvez les lancer.

**Ce qu'il vous faut.** Les documents sources au format PDF. Ils sont tous publics et
téléchargeables gratuitement (liens dans `references/sources.md`). Ils ne sont pas
inclus dans le skill — poids, et politique de rediffusion du HCGE.

**Comment faire.** Déposez les PDF dans la conversation, puis demandez simplement :

> « Lance les contrôles du corpus. »

Claude reconstruit le texte des rapports page par page, puis rapproche chaque citation
de l'index de la page dont elle se réclame. Il rend un rapport : nombre de citations
vérifiées, écarts éventuels, avec la page de chacun.

**Les cinq contrôles, et ce que chacun cherche :**

| Script | Question posée |
|---|---|
| `extraire_corpus.py` | reconstruit le texte des PDF, page par page |
| `controle_citations_v2.py` | la citation figure-t-elle dans le document, à la page annoncée ? |
| `controle_bornes_v3.py` | est-elle complète — rien coupé sans marque, casse et ponctuation de la source ? |
| `controle_invention.py` | chaque mot entre guillemets figure-t-il dans la source ? |
| `controle_recurrences.py` | chaque société citée figure-t-elle bien à la page indiquée ? |

**Documents attendus, et nom de fichier.** Le script les reconnaît à leur nom ; s'il
manque un document, il le signale et poursuit avec les autres.

| Document | Nom de fichier attendu |
|---|---|
| Rapports AMF sur le gouvernement d'entreprise 2020-2025 | `AMF_2020.pdf`, `AMF_2021_compressed.pdf`, `AMF_2022.pdf`, `AMF_2023.pdf`, `AMF_2024.pdf`, `AMF_2025.pdf` |
| Rapports annuels HCGE 2020-2025 | `Rapport_HCGE_2020_compressed.pdf`, `Rapport_HCGE_2021_compressed.pdf`, `Rapport_HCGE_2022_compressed.pdf`, `15661-hcge-2024-rapport-hcge-2023-fr-0212.pdf`, `16213hcgerapport2024frhd_compressed.pdf`, `17165hcgerapport2025frvfinale_compressed.pdf` |
| Guides d'application HCGE | `2024_Guide_Mars.pdf` (mars 2024), `17072-2025-guide-decembre-2025.pdf` (décembre 2025) |
| Code AFEP-MEDEF (décembre 2022) | `Code_AFEP_MEDEF_decembre_2022.pdf` |
| AMF — DOC-2021-02, DOC-2025-08, durabilité 2024, CSRD way forward | `2021-02-decembre-2024.pdf`, `amfrecommandationdoc202508arretedescomptes2025.pdf`, `AMF_DURABILITE__2024.pdf`, `amf_study_csrd_reporting_the_way_forward_2025_2.pdf` |
| ESMA — priorités de supervision 2025 | `ESMA_PRIORITE__2025.pdf` |
| Sénat — rapport n° 808 (Rietmann/Gay) | `r24-808-11.pdf` |
| Paris Europlace — dialogue actionnarial 2024 | `link_php.pdf` |

Attention à ne pas confondre les deux guides HCGE : celui de **mars 2024** et celui de
**décembre 2025** sont deux documents distincts, et cinq entrées de l'index portent sur
le premier.

**Ce que ces contrôles ne font pas.** Ils vérifient qu'un texte est là, à sa page, en
entier. Ils ne jugent pas le *sens* : qu'un passage soit correctement attribué — l'AMF
citant le Code, ou un émetteur — se vérifie en lisant la page. C'est l'objet du
protocole d'audit décrit plus bas.

## Outils — vérifier ou enrichir le corpus

Le skill inclut un détecteur de complétude et de cohérence des index,
`scripts/check_completeness.py`. Il ne corrige ni ne juge rien : il **signale**
des zones à confronter au PDF source. Après tout ajout ou édition d'un index,
le lancer depuis le dossier du skill :

```
python3 scripts/check_completeness.py .
```

Cinq détecteurs :
- **D1** — séries inline incomplètes (un sous-point sans citation à côté d'un voisin de même série qui en a une).
- **D2 / D2b** — sous-sections squelettiques ou statistiques maigres (titre posé sans contenu).
- **D3** — guillemets « » déséquilibrés (citation tronquée ou mal fermée).
- **D4** — renvois-substituts (« figure p. X », « disponible sur demande ») [indicatif].
- **D5** — disparité de série (millésime atypiquement maigre ou dense) [indicatif].

Un signalement n'est pas une erreur automatique : c'est un point à vérifier à la
source. **Pour enrichir le corpus** : indexer le PDF localement (ne jamais le
redistribuer — voir `NOTICES.md`), ajouter son lien officiel dans
`references/sources.md`, puis lancer le détecteur.

## Vérification par une seconde instance — l'agent vérificateur

Le skill embarque une auto-vérification du producteur (la checklist du `SKILL.md`,
§8). Mais une auto-relecture a une faiblesse de principe : c'est le **même**
agent qui se relit, et un agent peut se convaincre d'avoir vérifié ce qu'il n'a
pas rouvert. La garantie de fidélité ne vient donc pas d'une consigne ajoutée au
producteur — elle vient d'une **seconde instance, neutre et fraîche**, qui ne
sait pas ce que le producteur croyait avoir vérifié.

D'où un protocole simple, que l'on orchestre soi-même en **deux requêtes
successives** :

1. **Producteur** — une première instance produit la fiche avec le skill.
2. **Vérificateur** — dans une **conversation neuve**, une seconde instance reçoit
   la fiche et les sources, et n'a qu'une tâche : auditer la fidélité, affirmation
   par affirmation. Elle ne réécrit pas, ne complète pas, n'améliore pas — elle
   vérifie et produit une **table de preuve**.

L'indépendance ne se décrète pas : elle tient au fait que le vérificateur est une
instance distincte. Un skill ne peut pas, seul, invoquer un vérificateur vraiment
indépendant ; c'est l'utilisateur qui crée la séparation en lançant la seconde
requête. Le critère de validation tient en une phrase : **« montre-moi la page ».**

Depuis la **v2.0.0**, ce protocole est formalisé dans **`VERIFICATION.md`** (conditions de neutralité, périmètre intégral/sondage, ordre des contrôles, format du verdict, journal d'audit) ; le prompt ci-dessous en reste la forme opératoire rapide. La règle est inscrite au §8.4 du `SKILL.md` : **la checklist interne ne vaut pas vérification**, et une production sans verdict archivé est réputée non vérifiée. À chaque modification du skill, du corpus ou du modèle sous-jacent, rejouer en outre le **jeu de tests de non-régression** (19 tests à réponse-étalon). **Ce jeu est volontairement conservé hors de l'archive du skill** : tant qu'il y figurait, l'instance testée avait accès aux réponses attendues, et le rejeu du 28 août 2026 a effectivement été contaminé de cette façon. Il est distribué séparément (`jeu-de-tests/`, plus une version Word imprimable) et ne doit jamais être replacé dans l'archive ni chargé dans la conversation de rejeu.

### Protocole d'audit de fidélité (à coller dans une nouvelle conversation)

```
Tu es un agent de vérification, distinct de l'agent qui a produit le document
ci-dessous. Ta seule tâche est d'auditer sa fidélité aux sources. Tu ne réécris
pas, tu ne complètes pas, tu n'améliores pas : tu vérifies.

Document à auditer : [coller la fiche]
Sources de référence : [skill / index / PDF accessibles]

Méthode, sans exception :
1. Extraire CHAQUE affirmation factuelle : chaque chiffre, chaque citation entre
   guillemets, chaque page citée, chaque nom de société ou de personne, chaque
   date, chaque article de loi, chaque numéro de section.
2. Pour chacune, rouvrir la source (index ou PDF) et retrouver le passage exact.
   Ne pas se fier au document audité ni à la mémoire.
3. Restituer, pour chaque affirmation, une ligne de preuve : l'affirmation telle
   qu'écrite | la source (rapport + page) | le texte source exact | le statut.
4. Statuts : CONFORME (le texte source confirme mot pour mot / chiffre pour
   chiffre) ; ÉCART (toute divergence, même mineure : reformulation entre
   guillemets, page différente, chiffre approché, épithète ajoutée ou retirée,
   numéro de section non confirmé) ; INTROUVABLE (l'affirmation ne figure pas
   dans la source).
5. Pour les faits issus du web : vérifier que le lien provient d'une source
   réelle, que le chiffre est corroboré par une seconde source indépendante ou
   une source primaire, et que l'exercice et le périmètre sont les bons.

Règle bloquante : toute divergence est une violation. Une seule affirmation au
statut ÉCART ou INTROUVABLE suffit à refuser le document. Ne pas conclure
« conforme » tant qu'une seule ligne ne l'est pas. Si une affirmation n'est pas
dans la source, le dire explicitement — ne pas la justifier, ne pas la réparer.

Livrable : la table de preuve complète, puis une seule ligne de verdict —
VALIDÉ (toutes lignes conformes) ou À CORRIGER (liste des affirmations en écart
ou introuvables).
```

### Format de la table de preuve

| Affirmation (telle qu'écrite) | Source (rapport + page) | Texte source exact | Statut |
|---|---|---|---|
| « 13 résolutions rejetées au CAC 40 en 2021 » | AMF 2021, p. 26 | « 13 résolutions rejetées en 2021 (contre 4 en 2020) » | CONFORME |
| « mis fin à cette présentation consultative » | AMF 2023, p. 56 | « la société a mis fin à sa pratique de cumul » | ÉCART |

Le détecteur `check_completeness.py` (ci-dessus) et l'agent vérificateur sont
complémentaires : le premier **signale** mécaniquement des zones à confronter au
PDF ; le second **audite** la fidélité d'une production finie, affirmation par
affirmation, depuis une instance indépendante.

## Limites

- Les index sont arrêtés à 2025 ; pour l'état du droit en vigueur et l'actualité,
  le skill complète par une recherche internet (Légifrance, EUR-Lex, sites
  officiels).
- Le skill produit des analyses documentaires à vocation scientifique. **Il ne
  constitue ni un conseil juridique, ni un conseil en investissement.**

## Licence

Œuvre sous **Creative Commons Attribution - Pas d'Utilisation Commerciale -
Partage dans les Mêmes Conditions 4.0 International (CC BY-NC-SA 4.0)**.

Vous pouvez partager et adapter le skill, à condition de **créditer Gillan
Saleh**, de **ne pas en faire un usage commercial**, et de **repartager à
l'identique**. Les documents sources tiers restent la propriété de leurs éditeurs
(voir `NOTICES.md`). Le texte intégral de la licence figure dans le fichier
`LICENSE`.
