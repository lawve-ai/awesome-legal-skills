# Tâche 4 — Mise à jour de documents juridiques

> **Environnement** : espace de travail requis (lecture intégrale du document source, fichier de modifications numéroté, intégration éventuelle). Un document long se traite par sections ; lorsqu'un dossier connecté existe, y écrire le fichier de modifications au fur et à mesure (reprise dans une autre conversation). Livrable Word par défaut.

## Objectif

Mettre à jour un document juridique existant (cours, ouvrage, article, support de TD, fiches) en identifiant les évolutions législatives, jurisprudentielles et doctrinales intervenues depuis la dernière version.

## Règle fondamentale : ne jamais modifier directement le document

**INTERDIT** de modifier le document source directement. Le processus est toujours en deux temps :
1. **Produire un fichier de modifications numéroté** (Markdown) présentant chaque modification proposée avec son contenu prêt au copier-coller
2. **Proposer l'intégration** après validation par l'utilisateur

## Processus

### 1. Analyse préalable du document

**EXÉCUTER :**
1. Lire intégralement le document source
2. Identifier :
   - Nature du document (cours, ouvrage, article, fiches, support TD)
   - Matière et sous-matière
   - Date estimée de dernière mise à jour (mentions de dates, références les plus récentes)
   - Structure et plan du document
   - Style et registre de langue
   - Format des citations utilisé dans le document
3. Inventorier les points de droit traités
4. Lister toutes les références présentes (textes, jurisprudence, doctrine)

### 2. Exécuter le playbook (tâche 0)

Cadrage juridique rapide des thèmes couverts par le document, pour identifier les axes de recherche d'actualisation.

### 3. Recherche d'actualité

Pour chaque point de droit identifié dans le document :

**3a. Vérification des textes normatifs** via OpenLegi :
- `rechercher_code` pour chaque article cité → vérifier la version en vigueur, les modifications récentes
- `rechercher_dans_texte_legal` → nouvelles lois, ordonnances, décrets sur le thème
- `recherche_journal_officiel` → textes récents non encore codifiés
- **Signaler** toute modification législative postérieure à la date estimée de dernière mise à jour

**3b. Recherche jurisprudentielle** via LibreJustice puis OpenLegi :
- `LibreJustice:search_decisions` avec `date_from` fixée à la date estimée de dernière mise à jour, `sort: "date_desc"`, `publication: ["PUBLIE_RAPPORT","PUBLIE_BULLETIN","LETTRE_CHAMBRE","PUBLIE_LEBON"]` pour hiérarchiser, et `legal_article` pour cibler les décisions visant les articles traités par le document
- `LibreJustice:get_decision` sur chaque décision retenue (motifs réels, `appellateFate`) ; `OpenLegi` pour le lien Légifrance
- `OpenLegi:rechercher_jurisprudence_judiciaire` / `_administrative` avec mots-clés + filtre date postérieure à la dernière mise à jour
- Identifier : nouveaux arrêts de principe, revirements, évolutions significatives
- Distinguer : arrêts fondateurs (à conserver) vs. arrêts illustratifs (remplaçables si plus récent et plus pertinent)

**3c. Recherche doctrinale** via HAL + web_search :
- `scripts/doctrine_search.py` → doctrine récente sur les thèmes du document (multi-sources, identifiant vérifiable) ; `scripts/hal_search.py` en complément ciblé
- web_search → Cairn, Dalloz Actualité, Persée
- Identifier les évolutions doctrinales majeures, les nouveaux débats

**3d. Droit comparé** (si le document contient des éléments comparatistes) :
- `LegalDataHunter:search` pour vérifier l'actualité des éléments de droit étranger

### 4. Vérification des références existantes

Pour chaque référence présente dans le document :
1. Vérifier l'existence et l'exactitude via OpenLegi ou web_search
2. Vérifier le statut temporel (texte toujours en vigueur ? — `LibreJustice:get_norm` avec `date` ; jurisprudence non renversée ? — `appellateFate` et `caseChronology`)
3. Si erreur : corriger dans le fichier de modifications
4. Si référence obsolète : proposer un remplacement

### 5. Production du fichier de modifications

**Un seul fichier** `[AAAA-MM-JJ]-modifications-[nom-doc].md` structuré comme suit :

```
# Modifications proposées — [Nom du document]

**Date** : [AAAA-MM-JJ]
**Document source** : [nom du fichier]
**Dernière mise à jour estimée** : [date]

**Synthèse** :
- Nombre total de modifications : X
- Principales actualisations : [liste brève]
- Vérifications OpenLegi : [effectuées / indisponible]

---

## MODIFICATION 1 — SECTION : [Nom exact de la section]

### [AJOUTER / REMPLACER / SUPPRIMER] [précision sur le point d'insertion]

**Ancien texte** (si REMPLACER) :
[Texte actuellement dans le document]

**Nouveau texte** :
[Contenu formaté prêt au copier-coller, dans le style du document]

**Justification** : [Explication brève, 1-3 phrases]

**Source vérifiée** : [URL ou outil OpenLegi utilisé]

---

## MODIFICATION 2 — SECTION : [...]
[...]
```

### Principes du fichier de modifications

**Ordre** : suivre strictement l'ordre du document (du haut vers le bas).

**Types d'opérations** :
- **AJOUTER** : insertion de nouveau contenu (préciser le point d'insertion)
- **REMPLACER** : substitution (toujours indiquer ancien ET nouveau texte)
- **SUPPRIMER** : retrait (justification solide obligatoire)

**Format du contenu** :
- Texte directement formaté dans le style du document source
- Prêt au copier-coller (aucune manipulation nécessaire)
- Respecter le registre de langue, le système de citation et la structure du document

**Traitement différencié des arrêts** :
- Arrêts fondateurs (Teffaine, Jand'heur, Franck, etc.) : **NE PAS REMPLACER**
- Arrêts illustratifs : remplacer si arrêt plus récent (< 3 ans) ET plus pertinent
- En cas de doute : proposer plusieurs options à l'utilisateur

### 6. Livraison et proposition d'intégration

1. Livrer le fichier de modifications dans le dossier de travail
2. Proposer à l'utilisateur :
   - Intégration des modifications dans le document (si Word : édition directe après validation)
   - Modifications à discuter ou rejeter
   - Recherches complémentaires sur des points spécifiques

Proposer des tâches connexes : mise à jour d'un support PPTX associé, création de QCM ou d'exercices rapides actualisés (rediriger vers `qcm-exercices`), création d'un nouveau sujet d'examen sur le thème actualisé.
