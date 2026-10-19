# Tâche 0 — Playbook juridique

> **Environnement** : aucun prérequis.

## Nature

Document de cadrage interne à la session. Le playbook oriente toutes les tâches 1-6 en aval. Il n'est pas livré comme fichier Word sauf demande explicite de l'utilisateur ou complexité justifiant un livrable autonome.

## Déclenchement

**Systématique** avant toute tâche 1-6, SAUF si les deux conditions cumulatives suivantes sont réunies :
1. La qualification juridique est univoque (un seul régime applicable, aucune hésitation possible)
2. Une seule branche du droit est impliquée

Si ces deux conditions sont réunies, le playbook est exécuté silencieusement (intégré au raisonnement sans production séparée). Sinon, il est produit explicitement en contexte de session.

## Processus

### Étape 1 — Identification des questions juridiques

À partir de la demande de l'utilisateur et des documents présents dans le dossier de travail (cf. `references/environnement-et-livrables.md` § 2), identifier **1 à 6 questions juridiques principales**.

Chaque question est formulée comme une interrogation juridique précise :
- ❌ Vague : « le problème du contrat »
- ✅ Précis : « La clause de non-concurrence insérée à l'article 8 du contrat de travail est-elle valide au regard des conditions posées par la jurisprudence de la Chambre sociale (Cass. soc., 10 juill. 2002) ? »

Si le nombre de questions identifiées dépasse 6, regrouper les questions connexes ou hiérarchiser. Au-delà de 6, la demande est probablement trop large et devrait être décomposée en sous-tâches.

### Étape 2 — Recherche du droit applicable (séquence descendante)

Pour chaque question identifiée, appliquer la séquence de recherche du § 4 du SKILL.md :

**2a. Textes normatifs** :
- Rechercher les articles de code, lois, décrets applicables via OpenLegi
- Vérifier le statut temporel de chaque texte
- Identifier les régimes spéciaux éventuels (hiérarchie spécial > général)

**2b. Jurisprudence des cours suprêmes** :
- Rechercher les arrêts de principe de la Cour de cassation ou du Conseil d'État
- Identifier les éventuels revirements récents
- Ne pas approfondir la jurisprudence du fond ni la doctrine à ce stade — le playbook est un cadrage, pas une recherche exhaustive

### Étape 3 — Production du playbook

Structurer le playbook comme suit (en contexte de session, pas dans un fichier) :

```
PLAYBOOK JURIDIQUE — [Objet de la demande]

QUESTION 1 : [Formulation précise]
  Textes : [Articles de code / loi / décret applicables — avec statut temporel]
  Jurisprudence directrice : [Arrêts de principe identifiés]
  Points d'attention : [Zones d'incertitude, pièges, conditions à vérifier]
  Orientation : [Ce que cette question implique pour la tâche en aval]

QUESTION 2 : [...]
[...]

ARTICULATION : [Comment les questions s'articulent entre elles, ordre logique de traitement]
```

### Étape 4 — Transition vers la tâche demandée

Le playbook une fois produit :
1. Oriente la recherche approfondie (tâche 1) vers les axes identifiés
2. Fournit les points d'attention pour la relecture (tâche 2) et la mise à jour (tâche 4)
3. Cadre les questions juridiques pour les sujets et corrigés (tâche 3)
4. Structure les contenus de cours (tâche 5)
5. Identifie les axes des exercices pour les fiches de TD (tâche 6). Pour la Variante A (thème de fiches non précisé), le playbook s'exécute après la validation du découpage thématique, non avant.

Passer directement à l'exécution de la tâche demandée sans interruption.

## Exemples

### Exemple 1 — Demande de recherche sur la responsabilité du fait des produits défectueux
```
PLAYBOOK JURIDIQUE — Responsabilité du fait des produits défectueux

QUESTION 1 : Quel est le régime applicable (articulation directive 85/374/CEE, art. 1245 s. C. civ., droit commun) ?
  Textes : Art. 1245 à 1245-17 C. civ. (en vigueur), directive 85/374/CEE
  Jurisprudence : Cass. civ. 1re, 20 sept. 2017, n° 16-19.109 (articulation régimes)
  Points d'attention : Le droit commun reste invocable (CJUE, 21 juin 2023, C-128/22)
  Orientation : Structurer la recherche autour des deux régimes et de leur articulation

QUESTION 2 : Quelles sont les conditions de mise en jeu (défectuosité, mise en circulation, lien de causalité) ?
  [...]

ARTICULATION : Traiter Q1 en premier (détermination du régime) car Q2-Q3 en dépendent.
```

## Limites

Le playbook est un cadrage rapide, pas une recherche exhaustive. Il ne vise pas à couvrir l'intégralité du droit applicable mais à identifier les axes structurants et les points d'attention. La recherche approfondie relève des tâches 1-6 en aval.
