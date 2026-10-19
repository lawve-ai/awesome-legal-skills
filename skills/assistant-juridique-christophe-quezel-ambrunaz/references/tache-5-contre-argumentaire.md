# Tâche 5 — Analyse des références et contre-argumentaire

> **Environnement** : le document adverse est lu intégralement (pièce jointe ou dossier connecté). Un document long se traite par sections dans l'espace de travail ; lorsqu'un dossier connecté existe, y écrire l'analyse au fur et à mesure (reprise). Livrable Word par défaut.

## Objectif

Vérifier les références juridiques d'un document adverse, évaluer la solidité de l'argumentation, et développer un contre-argumentaire structuré.

## Processus

### 1. Exécuter le playbook (tâche 0)

### 2. Scanner le dossier de travail (approfondi)

**Le document adverse est la matière première de cette tâche.** Si des pièces complémentaires sont présentes (propres pièces du client, jurisprudence favorable déjà identifiée), les intégrer à l'analyse.

EXÉCUTER :
1. Lire intégralement le document adverse
2. Extraire la structure argumentative : moyens principaux, moyens subsidiaires, fondements invoqués
3. Lister toutes les références citées (textes, jurisprudence, doctrine)

### 2bis. Construction de la chronologie des faits de l'espèce

**EXÉCUTER systématiquement** dès que des faits sont exposés dans le document adverse ou dans les pièces :

Construire un tableau chronologique des événements :

| Date | Fait | Source (pièce ou document adverse) |
|---|---|---|
| [date] | [événement] | [source] |

- Ordonner tous les faits par date (ordre chronologique strict)
- Identifier les parties et leurs qualités respectives
- Repérer les faits contestés ou contestables (divergences entre la version adverse et les propres pièces)
- **Intégrer la chronologie dans le livrable** (section « Faits de l'espèce »)

### 2ter. Vérification des délais juridiques

**EXÉCUTER après la chronologie**, si des délais légaux sont susceptibles d'avoir un impact :

1. **Identifier les délais potentiellement applicables** :
   - Délai de prescription de droit commun (art. 2224 C. civ. : 5 ans à compter de la connaissance des faits)
   - Délais spéciaux selon la matière (prescription biennale consommateur, décennale construction, etc.)
   - Délais de recours contentieux
   - Délais contractuels

2. **Vérifier chaque délai via OpenLegi** (`rechercher_code`) — ne jamais affirmer un délai de mémoire.

3. **Calculer la consistance des délais** à partir de la chronologie :
   - L'adversaire invoque-t-il une prescription ? Vérifier son point de départ et son calcul.
   - L'action est-elle susceptible d'être prescrite ou forclose au regard des dates ?
   - Des faits interruptifs ou suspensifs (mise en demeure, demande en justice, etc.) modifient-ils le calcul ?

4. **Signaler explicitement** :
   - ⚠️ **Prescription soulevée par l'adversaire** : vérifier sa consistance et préparer la réponse
   - ⚠️ **Prescription non soulevée mais potentiellement applicable** : alerter l'utilisateur
   - ⚠️ **Délai de réponse ou de voies de recours** : signaler tout délai procédural imminent

**⚠️ Précaution** : si les dates nécessaires sont absentes du document adverse ou des pièces, l'indiquer et exposer les hypothèses.

### 3. Vérification des références adverses

Pour chaque référence citée par l'adversaire :

**EXÉCUTER via LibreJustice et OpenLegi (jurisprudence et textes) et web_search (doctrine) :**
1. Vérifier l'existence de la référence (`OpenLegi` par numéro exact ; `LibreJustice:search_decisions` en régime lexical, la citation entre guillemets, lorsque le numéro est absent ou erroné)
2. Vérifier l'exactitude de la citation (date, numéro, juridiction, contenu) — lecture du texte intégral par `LibreJustice:get_decision`, jamais d'un aperçu
3. Vérifier le statut temporel (texte en vigueur ? décision infirmée ou cassée ? — lire `appellateFate` et `caseChronology`, et signaler le cas échéant que l'adversaire invoque une décision réformée)
4. Évaluer la pertinence : la référence soutient-elle réellement l'argument avancé ?
5. Identifier les citations tronquées, sorties de contexte, ou détournées

**Classifier chaque référence :**
- ✅ Référence exacte et pertinente pour l'argument
- ⚠️ Référence exacte mais pertinence discutable (hors sujet, distinguable, obiter dictum)
- ❌ Référence inexacte (erreur de citation) ou introuvable
- 🔄 Référence exacte mais texte abrogé / jurisprudence renversée

### 4. Analyse de l'argumentation

Pour chaque moyen adverse :
1. Identifier le fondement juridique invoqué
2. Évaluer la solidité du raisonnement (cohérence logique, adéquation texte-faits)
3. Identifier les faiblesses : sophismes, lacunes, présupposés non démontrés, confusions de qualification
4. Chercher la jurisprudence contraire ou les distinctions possibles

### 5. Élaboration du contre-argumentaire

**Séquence de recherche descendante (§ 4 du SKILL.md)** pour chaque moyen de réponse :
1. Textes normatifs soutenant la position opposée
2. Jurisprudence suprême contraire ou permettant de distinguer
3. Jurisprudence du fond favorable
4. Doctrine appuyant la position défendue

**Structure du contre-argumentaire :**
- Pour chaque moyen adverse : exposé du moyen → critique → réponse fondée en droit
- Moyens de réponse classés par force décroissante
- Arguments subsidiaires développés

### 6. Livraison

Document Word comprenant :
1. Chronologie des faits de l'espèce (tableau)
2. Analyse des délais juridiques (si pertinent)
3. Tableau de vérification des références adverses (synthèse)
4. Analyse critique de l'argumentation adverse
5. Contre-argumentaire structuré avec références vérifiées
6. Notes et références

Nommage : `[AAAA-MM-JJ]-contre-argumentaire-[affaire].docx`
