# Tâche 10 — Harmonisation des références

> **Environnement** : espace de travail requis (document miroir annoté par édition XML du .docx). Lorsqu'un dossier connecté existe, y écrire le miroir au fur et à mesure (reprise). Sans espace de travail (cas résiduel) : indiquer que l'activation de « Exécution de code et création de fichiers » permettrait la tâche, et proposer une liste d'harmonisation dans la conversation.

## Objectif

Assurer la cohérence formelle de toutes les citations dans un document juridique, conformément au guide RefLex SNE 2022. Détecter les incohérences, proposer un choix de forme à l'utilisateur, puis appliquer systématiquement.

## Principe

Le guide RefLex laisse une certaine liberté sur plusieurs points de forme (voir `references/format-citations.md`, section « Variantes admises »). Le choix entre variantes appartient à l'auteur. L'harmonisation ne consiste pas à imposer une norme unique mais à assurer la **cohérence interne** du document.

## Processus

### Étape 1 — Extraction et inventaire

**EXÉCUTER :**
1. Parcourir l'intégralité du document (corps, notes, bibliographie, annexes)
2. Extraire toutes les références (utiliser `scripts/extract_references.py` si disponible)
3. Pour chaque référence : relever la forme exacte telle qu'elle apparaît dans le document

### Étape 2 — Détection des incohérences

Regrouper les références par catégorie et identifier les variantes de forme au sein de chaque catégorie :

**Catégories à examiner :**

| Catégorie | Variantes courantes |
|---|---|
| Nom d'auteur | `BRUN Ph.` vs `Brun (Ph.)` vs `Ph. Brun` vs `Philippe Brun` |
| Chambre Cour de cassation | `Cass. civ. 1re` vs `Cass. 1re civ.` vs `Cass. civ. 1ère` vs `Civ. 1re` |
| Conseil d'État | `CE` vs `Cons. d'Ét.` vs `Conseil d'État` |
| Date | `12 juillet 2023` vs `12 juill. 2023` vs `12/07/2023` |
| Numéro de pourvoi | `n° 21-12.345` vs `n° 21-12345` vs `pourvoi n° 21-12.345` |
| Titre de revue | `RTD civ.` vs `Rev. trim. dr. civ.` vs `Revue trimestrielle de droit civil` |
| Guillemets | `« … »` vs `"…"` vs `"…"` |
| Article de code | `art.` vs `Art.` vs `article` |
| Référence croisée | `V.` vs `v.` vs `Voir` vs `Cf.` |
| Séparation auteurs multiples | `et` vs `&` vs `,` |
| Numéro de page | `p.` vs `pp.` vs `page` vs `pages` |

### Étape 3 — Présentation et choix (UNIQUE INTERRUPTION)

**INTERROMPRE UNE SEULE FOIS** pour présenter à l'utilisateur un tableau des variantes détectées et demander ses choix :

```
HARMONISATION DES RÉFÉRENCES — Variantes détectées

J'ai identifié les incohérences suivantes dans le document. Pour chaque catégorie,
indiquez la forme que vous souhaitez adopter (ou validez ma recommandation RefLex).

| Catégorie | Forme A (N occurrences) | Forme B (N occurrences) | Recommandation RefLex |
|---|---|---|---|
| Nom d'auteur | BRUN Ph. (12 occ.) | Brun (Ph.) (3 occ.) | BRUN Ph. |
| Chambre Cass. | Cass. civ. 1re (8 occ.) | Civ. 1re (2 occ.) | Cass. civ. 1re |
| Date | 12 juill. 2023 (15 occ.) | 12 juillet 2023 (5 occ.) | 12 juill. 2023 |
| … | … | … | … |

Souhaitez-vous adopter les recommandations RefLex ou modifier certains choix ?
```

Attendre la réponse de l'utilisateur. Enregistrer les choix.

### Étape 4 — Application systématique

**EXÉCUTER sans interruption :**

Pour chaque référence du document, appliquer les choix de forme validés par l'utilisateur. Produire le document corrigé.

### Étape 5 — Annotation du document miroir

Si exécutée seule (sans tâche 9), produire un document miroir annoté. Si couplée avec la tâche 9, ajouter les commentaires d'harmonisation au document miroir commun.

**Format du commentaire d'harmonisation :**
```
📐 HARMONISATION
Avant : [forme originale dans le document]
Après : [forme corrigée]
Règle : [référence à la règle RefLex ou au choix de l'utilisateur]
```

**⚠️ Règle impérative — Références situées dans des notes de bas de page :**
Si la référence à harmoniser se trouve dans une note de bas de page (stockée dans `footnotes.xml`), le commentaire **doit impérativement être ancré dans `document.xml`** au niveau de l'appel de note — c'est-à-dire le `<w:r>` contenant le `<w:footnoteReference w:id="N"/>` correspondant — et **non** dans `footnotes.xml`. Le texte du commentaire doit mentionner le numéro de la note concernée (ex. : « Note n° 12 — »).

**Exemples :**

```
📐 HARMONISATION
Avant : Cass. civ. 1ère, 12 juillet 2023
Après : Cass. civ. 1re, 12 juill. 2023
Règle : Abréviation ordinale « 1re » (pas « 1ère ») + mois abrégés (RefLex §3.2)
```

```
📐 HARMONISATION
Avant : Brun (Ph.), « La responsabilité... »
Après : BRUN Ph., « La responsabilité... »
Règle : Choix utilisateur — forme PATRONYME Initiale(s).
```

### Interaction avec la vérification (tâche 9)

Lorsque les tâches 9 et 10 sont combinées :

1. **Si la vérification révèle une ERREUR_CITATION** : l'harmonisation propose la forme corrigée (pas seulement harmonisée, mais factuellement exacte). Le commentaire cumule les deux informations :
```
⚠️ ERREUR_CITATION + 📐 HARMONISATION
Réf. normalisée : Cass. civ. 1re, 20 sept. 2017, n° 16-19.109
Erreur détectée : numéro de pourvoi erroné (16-19.019 → 16-19.109)
Harmonisation : date abrégée (septembre → sept.), forme Cass. civ. 1re
Lien : [URL]
```

2. **Si la vérification retourne NON_TROUVEE** : la référence est signalée comme non vérifiée mais sa forme est quand même harmonisée. Ne pas la tenir pour illégitime.
```
❌ NON_TROUVEE + 📐 HARMONISATION
Réf. normalisée : CA Lyon, 3e ch., 12 mars 2019, n° RG 17/05432
Non trouvée sur Legifrance ni par web_search.
Harmonisation appliquée : forme de date et juridiction standardisées.
La référence n'est pas tenue pour illégitime — l'absence de résultat peut avoir des causes techniques.
```

## Livraison

**Si exécutée seule :**
- Document corrigé : `[AAAA-MM-JJ]-harmonise-[nom-doc].docx`
- Document miroir (annotations) : `[AAAA-MM-JJ]-miroir-harmo-[nom-doc].docx`

**Si couplée avec tâche 9 :**
- Document miroir unique : `[AAAA-MM-JJ]-miroir-verif-harmo-[nom-doc].docx`
- Document corrigé (harmonisation appliquée) : `[AAAA-MM-JJ]-harmonise-[nom-doc].docx`
