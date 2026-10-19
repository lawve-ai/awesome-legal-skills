# Tâche 3 — Sujets et corrigés d'exercices juridiques universitaires

> **Environnement** : aucun prérequis. Livrable Word par défaut (artefact Docs si l'utilisateur le demande) ; pour une question brève, réponse structurée dans la conversation. Tableau de vérification remis en document séparé (`references/environnement-et-livrables.md`).

## Objectif

Créer des sujets d'examen et/ou des corrigés pour les exercices juridiques universitaires : dissertation, fiche d'arrêt, commentaire d'arrêt, cas pratique, note de synthèse, mémoire (cadrage), thèse (cadrage).

## Processus

### 1. Qualification de la demande

Identifier :
- **Type d'exercice** demandé (dissertation, commentaire, cas pratique, etc.)
- **Niveau** : L1-L2 / L3 / M1 / M2 / CRFPA / Concours
- **Matière et sous-matière** : droit civil des obligations, droit administratif général, etc.
- **Nature de la production** : sujet seul / corrigé seul / sujet + corrigé
- **Durée d'épreuve** si applicable (3h, 5h, etc.)

Si la demande est ambiguë sur le type d'exercice : demander clarification.

### 2. Exécuter le playbook (tâche 0)

Cadrage juridique du thème. Le playbook identifie les questions de droit pertinentes.

### 3. Consulter le playbook de l'exercice concerné

**Playbooks intégrés** — Consulter le playbook correspondant au type d'exercice AVANT de rédiger :

| Exercice | Playbook |
|----------|----------|
| Dissertation | Section A ci-dessous |
| Fiche d'arrêt | Section B ci-dessous |
| Commentaire d'arrêt | Section C ci-dessous |
| Cas pratique | Section D ci-dessous |
| Mémoire de recherche | Section E ci-dessous |
| Thèse de doctorat | Section F ci-dessous |
| Note de synthèse | Section G ci-dessous |

### 4. Recherche documentaire

Pour le **sujet** : recherche ciblée sur le thème pour s'assurer de la pertinence et de l'actualité.

Pour le **corrigé** : recherche approfondie suivant la séquence du § 4 du SKILL.md (textes → jurisprudence suprême → jurisprudence du fond → doctrine → droit comparé si pertinent).

### 5. Rédaction

**Si sujet** :
- Rédiger un énoncé conforme aux standards du type d'exercice et du niveau
- Pour un commentaire d'arrêt : fournir le texte **intégral** de la décision (`LibreJustice:get_decision` ou `OpenLegi`, JAMAIS inventée ni reconstituée depuis un aperçu). Vérifier `appellateFate` avant de retenir l'arrêt : une décision du fond infirmée ne se commente qu'en connaissance de son sort. Les `commentaires` institutionnels (notice explicative, conclusions du rapporteur public) alimentent utilement le corrigé, sans dispenser de la lecture des motifs
- Pour un cas pratique : rédiger une hypothèse factuelle réaliste et juridiquement riche
- Pour une note de synthèse : constituer un dossier documentaire cohérent (documents réels uniquement)

**Si corrigé** :
- Suivre scrupuleusement la méthodologie du playbook de l'exercice
- Rédiger intégralement (pas de plan seul sauf demande explicite)
- Citer les sources avec les normes de `references/format-citations.md`
- Signaler les éléments de valorisation / pénalisation pour l'évaluation

**Si sujet + corrigé** :
- Produire les deux dans un seul document Word, clairement séparés

### 6. Livraison

Nommage : `[AAAA-MM-JJ]-[type-exercice]-[matiere]-[niveau].docx`

Proposer des tâches connexes : QCM ou exercices rapides sur le même thème (rediriger vers skill `qcm-exercices`), variantes du sujet, grille d'évaluation.

---

# PLAYBOOKS DES EXERCICES JURIDIQUES

## A. DISSERTATION JURIDIQUE

### Nature
Exercice de démonstration déductive : construire un raisonnement organisé, progressif et argumenté, fondé sur le droit positif. Ni catalogue, ni paraphrase, ni récitation.

### Analyse du sujet
- Identifier chaque terme, y compris les petits mots (« la » ≠ « une »)
- Distinguer : sujet notionnel, comparatif, relationnel, problématique
- Définir précisément chaque notion-clé
- Délimiter : bornes matérielles, temporelles, spatiales

### Problématique
- Vraie question (ni rhétorique, ni triviale)
- Spécifique au sujet posé
- Révèle une tension, ambiguïté, évolution ou paradoxe
- Formulée avec précision juridique
- ❌ « Qu'est-ce que la responsabilité contractuelle ? »
- ✅ « L'exigence de prévisibilité du dommage en matière contractuelle constitue-t-elle un obstacle à la réparation intégrale ? »

### Plan
- Structure binaire invariable : **2 parties (I/II)**, chacune en **2 sous-parties (A/B)**
- Titres apparents, **sans verbe conjugué**, sans ponctuation finale
- Titres analytiques (pas « Conditions », « Effets »)
- Équilibre entre parties, progressivité, non-répétition
- Plans courants : analytique (conditions/effets, principe/exceptions), thématique, dialectique

### Introduction (1/4 à 1/3 de la copie)
1. Accroche (directement liée au sujet)
2. Définition des termes et délimitation
3. Intérêt du sujet (théorique, pratique)
4. Historique/contexte (bref, 3-4 phrases max)
5. Problématique (tension révélée)
6. Annonce du plan (déguisée, uniquement I et II)

### Développement
- Chapeau de partie (2-3 phrases annonçant A et B)
- Structure interne : idée directrice → règle → application → nuance → conclusion partielle
- Raisonnement déductif
- Transition obligatoire entre I et II (3-5 phrases)
- Conclusion : absente ou très brève, ouvre sur une perspective

### Erreurs rédhibitoires
Hors-sujet, plan catalogue, tautologie, paraphrase, problématique absente, introduction trop courte.

---

## B. FICHE D'ARRÊT

### Nature
Résumé structuré et analytique d'une décision de justice. Pas de commentaire, pas de position doctrinale.

### Structure standard
1. **Faits** : uniquement les faits juridiquement pertinents, qualifiés juridiquement
2. **Procédure** : chronologie juridictionnelle, prétentions des parties
3. **Moyens/arguments** des parties (si disponibles)
4. **Problème de droit** : question abstraite, détachée des noms des parties
5. **Solution** : règle posée + application + sens du dispositif + portée

### Particularités par juridiction
- Cass. : identifier visa, chapeau, distinguer rejet/cassation
- CE : distinguer REP/plein contentieux
- Conseil constitutionnel : QPC vs. saisine a priori, conformité/réserves

### Erreurs rédhibitoires
Confusion faits/procédure, noms propres dans la question de droit, ignorer le visa, solution trop vague.

---

## C. COMMENTAIRE D'ARRÊT

### Nature
Analyse critique articulant explication, évaluation et contextualisation. Le piège majeur est la paraphrase.

### Préparation
1. Établir la fiche d'arrêt (obligatoire)
2. Mobiliser les connaissances contextuelles (droit antérieur, courant jurisprudentiel, doctrine, textes)

### Triptyque anti-paraphrase
Chaque développement répond à trois questions :
- **Quoi** : quelle est la solution sur ce point ?
- **Comment** : quel fondement, quel raisonnement ?
- **Pourquoi** : quels enjeux, quelle politique jurisprudentielle, quelles critiques ?

### Plan
- Binaire (I/II, A/B), titres analytiques sans verbes
- Plans acceptables : sens/portée (classique), thématique, dialectique
- Chapeau de partie obligatoire, transitions obligatoires

### Introduction
1. Accroche liée au thème
2. Fiche d'arrêt intégrée (rédigée)
3. Problématique (transcende la question de droit)
4. Annonce du plan (déguisée)

### Portée : normative, pratique, doctrinale, systémique, prospective.

### Erreurs rédhibitoires
Paraphrase, cours magistral, absence de problématique, ignorer la portée, sources absentes.

---

## D. CAS PRATIQUE

### Nature
Application du droit positif à une situation factuelle. Raisonnement syllogistique. Réponse opérationnelle.

### Lecture et qualification
- Identifier tous les problèmes juridiques (1 à N)
- Qualifier juridiquement les faits (traduction en catégories juridiques)
- Classer par ordre logique

### Syllogisme juridique (structure invariable par problème)
1. **Majeure** : règle de droit applicable (article, jurisprudence), citée avec précision, **dans sa rédaction en vigueur à la date des faits de l'énoncé** (et non à la date du jour, cf. § 6 du SKILL.md). Déterminer explicitement cette date pivot ; si l'énoncé est muet, la fixer par hypothèse signalée ou raisonner sur le droit positif actuel en le précisant.
2. **Mineure** : application aux faits spécifiques — vérifier chaque condition
3. **Conclusion** : solution opérationnelle (« X peut / ne peut pas… »)

### Gestion de l'incertitude
- Incertitude de droit : exposer les interprétations, indiquer la dominante
- Incertitude de fait : poser des hypothèses alternatives, résoudre les deux branches

### Questions procédurales
Prescription, compétence juridictionnelle, charge de la preuve, modes de preuve.

### Erreurs rédhibitoires
Exposé de cours, conclusion sans syllogisme, majeure vague, mineure absente, oublier un problème.

---

## E. MÉMOIRE DE RECHERCHE (M1/M2) — Cadrage

### Nature
Travail scientifique original. Exige : question de recherche originale, revue de littérature, plan de démonstration, contribution personnelle, rigueur formelle.

### Volume
M1 : 40-60 pages. M2 : 80-120 pages.

### Éléments structurels
- Introduction générale : accroche, définitions, délimitation, intérêt, état de l'art, problématique, annonce du plan
- Plan binaire (2 parties, 2 chapitres par partie, 2 sections par chapitre)
- Titres analytiques sans verbes conjugués
- Appareil de notes de bas de page systématique
- Bibliographie classée par catégories
- Conclusion : réponse à la problématique + limites + ouvertures

### Style
Impersonnel ou « nous », phrases précises, vocabulaire technique rigoureux.

### Erreurs rédhibitoires
Sujet sans problématique, plan catalogue, bibliographie incomplète, absence de notes, style non académique, plagiat.

---

## F. THÈSE DE DOCTORAT — Cadrage

### Nature
Contribution originale à la connaissance scientifique. 400-800 pages. Soutenance devant jury.

### Éléments clés
- Introduction générale (50-80 pages) : sujet, intérêt, état de l'art, concepts, délimitation, problématique, hypothèse, méthode, plan
- La thèse de l'auteur : prise de position scientifique argumentée, défendable et falsifiable
- Architecture : Parties / Titres / Chapitres (bipartie dominante)
- Bibliographie classée (normative, jurisprudence, doctrine subdivisée, rapports, sources étrangères)
- Index thématique recommandé

### Soutenance
Jury ≥ 4 membres (dont 2 rapporteurs extérieurs HDR). Exposé 30-45 min + questions 1h30-3h.

### Erreurs rédhibitoires
Sujet trop vaste, absence de thèse, état de l'art insuffisant, plan descriptif, notes lacunaires, plagiat.

---

## G. NOTE DE SYNTHÈSE (CRFPA / Concours)

### Nature
Restitution synthétisée et organisée du contenu d'un dossier documentaire. **Neutralité absolue** : aucune opinion personnelle, aucune source extérieure au dossier.

### Spécificité radicale
- Point de départ : dossier documentaire fourni (20-30 documents, 30-60 pages)
- Apport personnel : INTERDIT
- Sources utilisables : UNIQUEMENT les documents du dossier
- Volume : 4 pages maximum (~1500-2000 mots)

> **Constitution du dossier (sujet à créer).** Lorsque la skill doit *fabriquer* le dossier documentaire (et non traiter un dossier fourni), le borner à des **documents réels et reproductibles** : textes officiels (Légifrance via OpenLegi), décisions de justice intégralement accessibles, rapports publics. Proscrire l'insertion de doctrine sous paywall ou de pièces dont le texte intégral ne peut être ni vérifié ni reproduit — un dossier de note de synthèse suppose que chaque document soit lisible in extenso par le candidat. Chaque document inséré est tracé selon la règle anti-hallucination (existence et contenu vérifiés).

### Plan
- 2 parties (I/II), chacune en 2 sous-parties (A/B)
- Titres neutres et informatifs (pas de prise de position)
- Plan émergeant des documents, pas structure préconçue

### Rédaction
- Introduction brève (5-8 lignes) : sujet, question centrale, annonce du plan
- Corps rédigé (pas de listes), informations paraphrasées et articulées
- Chaque information rattachée à sa source : « (doc. X) »
- Tous les documents cités au moins une fois
- Tensions entre documents signalées
- Conclusion : non obligatoire, si présente très brève et factuelle

### Erreurs rédhibitoires
Opinions personnelles, connaissances extérieures, document ignoré, résumé document par document, dépassement de volume.
