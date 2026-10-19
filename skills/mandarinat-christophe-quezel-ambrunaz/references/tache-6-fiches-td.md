# Tâche 6 — Préparation de fiches de travaux dirigés (TD)

> **Environnement** : livrable Word par défaut (artefact Docs sur demande) ; une fiche unique peut être rendue dans la conversation si l'utilisateur le souhaite.

## Objectif

Préparer des fiches de TD pour un enseignement de droit, fondées sur des recherches réelles préalables. Chaque fiche comporte trois exercices complémentaires : connaissance, approfondissement, mise en pratique.

**Règle anti-hallucination absolue** : les arrêts, textes, articles de doctrine utilisés dans les exercices doivent avoir été trouvés par une recherche réelle via LibreJustice, OpenLegi, `doctrine_search.py`/HAL ou web_search, et **lus dans leur texte intégral**. Aucun arrêt, article ou texte inventé ou reconstitué de mémoire.

---

## VARIANTE A — Thème de cours (sans thème de fiche précisé)

**Déclencheur** : l'utilisateur fournit uniquement la matière ou le cours (ex. « droit des contrats », « droit de la famille »), sans indiquer les thèmes des fiches.

### Étape 1 — Clarification préalable

Demander à l'utilisateur :
1. Le niveau des étudiants (L1, L2, L3, M1, M2, doctorat, préparation concours)
2. Le volume horaire de la matière (nombre de séances de TD)
3. Les thèmes déjà couverts ou à exclure (si connu)
4. La profondeur souhaitée (survol ou approfondissement)

### Étape 2 — Structuration du plan de TD

À partir des éléments fournis et des connaissances sur la matière :
1. Proposer un découpage thématique en N fiches (N = nombre de séances disponibles ou demandées)
2. Présenter le plan sous forme de liste numérotée avec un titre et une ligne de description pour chaque fiche
3. Demander validation avant de produire les fiches

### Étape 3 — Production des fiches

Pour chaque thème validé, exécuter d'abord le **playbook (tâche 0)** sur ce thème (le playbook s'exécute thème par thème, après la validation du découpage à l'étape 2, et non en amont), puis appliquer la **Variante B** ci-dessous.

---

## VARIANTE B — Thème de fiche connu (ou issu de la Variante A)

**Déclencheur** : l'utilisateur fournit le thème précis de la fiche, ou ce thème a été identifié à l'étape 2 de la Variante A.

### Étape 1 — Recherche préalable sur le fond du droit

**EXÉCUTER avant toute production** — la fiche doit reposer sur des sources trouvées, pas sur la mémoire.

Séquence de recherche (§ 4 du SKILL.md) adaptée aux besoins pédagogiques :

1. **Textes normatifs** (`OpenLegi:rechercher_code`) :
   - Identifier les articles de code centraux sur le thème
   - Vérifier leur état de vigueur (métadonnées temporelles)
   - Repérer les définitions légales, les conditions, les effets, les sanctions

2. **Jurisprudence suprême** (`LibreJustice:search_decisions` puis `get_decision` ; `OpenLegi:rechercher_jurisprudence_judiciaire` / `rechercher_jurisprudence_administrative` pour le lien Légifrance) :
   - Trouver les arrêts de principe (au moins 3, idéalement 5-6) — `publication: ["PUBLIE_RAPPORT","PUBLIE_BULLETIN","LETTRE_CHAMBRE","PUBLIE_LEBON"]` remonte en priorité les décisions publiées
   - Lire les motifs par `get_decision` : un arrêt de TD est choisi pour ce qu'il juge, jamais sur la foi d'un `aiSummary` ou d'un `snippet`
   - Identifier les revirements ou évolutions notables
   - Pour chaque arrêt : noter la juridiction, la date, le numéro de pourvoi, le principe dégagé

3. **Doctrine** (`scripts/doctrine_search.py` multi-sources + web_search) :
   - Trouver au moins 2-3 articles doctrinaux pertinents sur le thème
   - Identifier les controverses doctrinales si elles existent

4. **Texte de loi ou arrêt principal** pour l'exercice de connaissance :
   - Sélectionner un texte (article de code, extrait de loi) ou un arrêt lisible et pédagogiquement riche
   - S'assurer qu'il est accessible (Legifrance via OpenLegi, ou `librejustice.fr` pour une décision non diffusée sur Légifrance) et citable — porter le lien dans la fiche

### Étape 2 — Construction de la fiche

La fiche de TD comporte **trois exercices distincts et séquentiels** :

---

#### EXERCICE 1 — Connaissance

**Objectif** : vérifier et consolider la maîtrise des fondamentaux (définitions, textes, lecture de sources primaires).

**Format** — choisir parmi (ou combiner) :

**Option 1 : Définitions**
- Lister 4 à 8 notions à définir, choisies parmi les notions centrales du thème
- Les notions doivent être trouvées dans les textes ou la jurisprudence identifiés à l'étape 1
- Indiquer les sources attendues dans le corrigé (article de code, définition jurisprudentielle)

**Option 2 : Identification d'articles de code**
- Demander aux étudiants de trouver et citer les articles du code applicables à des situations données
- Les situations doivent être simples et directement illustratives

**Option 3 : Lecture et questions sur un texte de loi, un arrêt ou un article de doctrine**
- Reproduire un extrait (arrêt, article de code, extrait de loi)
- Poser 4 à 8 questions graduées : compréhension → analyse → évaluation
- Questions de compréhension (Q1-Q2) : « Quels sont les faits ? La solution ? »
- Questions d'analyse (Q3-Q5) : « Quel est le fondement juridique ? Quelle règle cela illustre-t-il ? »
- Questions d'évaluation (Q6-Q8) : « Cette solution est-elle critiquable ? En quoi s'inscrit-elle dans l'évolution du droit ? »

**Corrigé de l'exercice 1** :
- Réponses attendues pour chaque question/définition, avec références exactes (articles, arrêts)
- Signaler les nuances et pièges éventuels

---

#### EXERCICE 2 — Approfondissement

**Objectif** : travailler en profondeur un ou plusieurs arrêts ou textes fondamentaux.

**Format** — choisir l'un :

**Option A : Fiche d'arrêt (3 à 6 arrêts)**
- Sélectionner 3 à 6 arrêts trouvés à l'étape 1, formant une progression thématique ou chronologique
- Pour chaque arrêt : fournir les références complètes (juridiction, date, numéro de pourvoi, source Legifrance)
- Demander une fiche d'arrêt structurée : faits → procédure → problème de droit → solution → portée
- Proposer une mise en perspective : comment ces arrêts s'articulent-ils ? Y a-t-il un revirement ?

**Option B : Étude approfondie et guidée d'un texte**
- Sélectionner un texte législatif ou réglementaire complexe (plusieurs articles articulés)
- Guider l'étude par des questions précises sur la structure du texte, ses conditions d'application, ses exceptions
- Demander une analyse de l'articulation entre les différentes dispositions

**Corrigé de l'exercice 2** :
- Pour les fiches d'arrêts : corrigé type de chaque fiche, avec le principe dégagé et sa portée
- Pour l'étude de texte : réponses aux questions guidées, avec références aux articles et à la jurisprudence

---

#### EXERCICE 3 — Mise en pratique

**Objectif** : mobiliser les connaissances dans une situation concrète ou une démonstration argumentée.

**Format** — choisir l'un, selon le niveau et les objectifs :

**Option A : Cas pratique**
- Construire une situation factuelle fictive mais juridiquement vraisemblable, articulant plusieurs questions du thème
- La situation doit être suffisamment complexe pour mobiliser règle + exceptions + jurisprudence
- Ne pas indiquer les qualifications juridiques dans l'énoncé (c'est le travail de l'étudiant)
- **Structure du corrigé** : liste des problèmes identifiés → règle applicable → application aux faits → solution pour chacun
- Corrigé fondé exclusivement sur les sources trouvées à l'étape 1

**Option B : Commentaire d'arrêt**
- Sélectionner l'un des arrêts les plus riches identifiés à l'étape 1
- Fournir le texte intégral de l'arrêt (ou l'extrait pertinent avec référence Legifrance)
- Donner les consignes de commentaire : introduction (faits, procédure, problème, annonce de plan), développement en deux parties, conclusion
- **Structure du corrigé** : problématique proposée, plan détaillé (I. → A./B., II. → A./B.), développement argumenté avec références

**Option C : Dissertation**
- Proposer un sujet en rapport direct avec le thème, formulé comme une question ou une affirmation à discuter
- Éviter les sujets trop larges (toujours délimiter le champ)
- Donner les consignes : introduction (contextualisation, définition des termes, enjeux, plan annoncé), développement en deux parties équilibrées, conclusion
- **Structure du corrigé** : problématique, plan détaillé argumenté, références aux textes et jurisprudence

---

### Étape 3 — Mise en forme du document

**Structure du document Word** :
1. **En-tête** : Matière — Niveau — Thème de la séance
2. **Exercice 1 — Connaissance** : énoncé
3. **Exercice 2 — Approfondissement** : énoncé (avec arrêts ou texte reproduit ou référencé)
4. **Exercice 3 — Mise en pratique** : énoncé
5. **Corrigés** : corrigé détaillé de chaque exercice (en deuxième partie du document, ou dans un document séparé si demandé)
6. **Références** : liste des sources utilisées (textes, jurisprudence, doctrine)

**Nommage** :
- Fiche : `[AAAA-MM-JJ]-fiche-td-[matiere]-[theme].docx`
- Corrigé séparé (si demandé) : `[AAAA-MM-JJ]-corrige-td-[matiere]-[theme].docx`

---

## Propositions post-tâche

Après livraison, proposer :
- Préparation des autres fiches de la série (si Variante A)
- Conversion en QCM ou en exercices rapides (textes à trous, appariements, flashcards) des exercices de connaissance (rediriger vers skill `qcm-exercices`)
- Création d'un support de cours sur le même thème (tâche 5)
- Mise à jour si la jurisprudence ou la législation a évolué (tâche 4)
