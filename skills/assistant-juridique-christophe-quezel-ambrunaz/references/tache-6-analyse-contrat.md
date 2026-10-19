# Tâche 6 — Analyse de contrat

> **Environnement** : contrat en pièce jointe ou dans le dossier connecté. Livrable Word par défaut (artefact Docs sur demande).

## Objectif

Analyser exhaustivement un contrat pour identifier sa conformité, ses clauses problématiques, ses risques juridiques, et proposer des améliorations.

## Processus

### 1. Exécuter le playbook (tâche 0)

Le playbook est particulièrement structurant ici : il identifie le régime applicable au contrat et les points d'attention prioritaires (clauses à vérifier en premier, mentions obligatoires, régimes spéciaux).

### 2. Scanner le dossier de travail (approfondi)

**Le contrat est la matière première de cette tâche.** Si des documents connexes sont présents (courriers de négociation, avenants, contrats précédents, cahier des charges), les intégrer à l'analyse.

EXÉCUTER :
1. Lire intégralement le contrat
2. Identifier les parties, l'objet, le prix, la durée
3. Relever la structure du contrat (articles, annexes)
4. Identifier le régime applicable à partir de la qualification (cf. playbook)

### 3. Recherche du cadre juridique applicable

**EXÉCUTER via OpenLegi :**
- Régime général des contrats (art. 1101 s. C. civ.)
- Régime spécial applicable (bail, vente, travail, consommation, etc.)
- Mentions obligatoires pour ce type de contrat
- Clauses réputées non écrites ou interdites
- Jurisprudence récente sur les clauses litigieuses de ce type de contrat — `LibreJustice:search_decisions` (requête descriptive sur la clause, `date_from` sur les cinq dernières années, `legal_instrument` sur le code applicable), lecture par `get_decision`, puis repasse OpenLegi pour le lien Légifrance

### 4. Analyse clause par clause

Pour chaque clause significative :

| Clause | Conformité | Risque | Recommandation |
|---|---|---|---|
| Art. X — [Objet] | Conforme / Non conforme / Ambigu | Nul / Modéré / Élevé | Maintenir / Modifier / Supprimer |

**Points d'attention systématiques :**
- Clauses abusives (C. consom. si B2C, jurisprudence si B2B)
- Clauses de responsabilité et de limitation de responsabilité
- Clauses pénales (pouvoir de révision judiciaire, art. 1231-5 C. civ.)
- Clauses de résiliation (conditions, préavis, effets)
- Clauses de non-concurrence (conditions de validité)
- Force majeure (définition contractuelle vs légale)
- Loi applicable et juridiction compétente
- Protection des données personnelles (RGPD si applicable)

### 5. Analyse des risques globaux

Au-delà de l'analyse clause par clause :
- Équilibre global du contrat (déséquilibre significatif ?)
- Cohérence interne (contradictions entre clauses ?)
- Lacunes (clauses manquantes indispensables pour ce type de contrat ?)
- Conformité aux évolutions récentes du droit

### 6. Livraison

Document Word comprenant :
1. **Synthèse** : qualification du contrat, conformité globale, risques principaux
2. **Tableau d'analyse clause par clause**
3. **Analyse des risques globaux**
4. **Recommandations** : modifications proposées, clauses à ajouter
5. **Notes et références**

Nommage : `[AAAA-MM-JJ]-analyse-contrat-[type-ou-parties].docx`
