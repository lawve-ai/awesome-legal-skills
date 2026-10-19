# Guide d'utilisation de l'API HAL pour la recherche doctrinale

<!-- NOYAU v4 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills (script sync-noyau.sh). -->

## Vue d'ensemble

HAL (Hyper Articles en Ligne) est l'archive ouverte nationale française, gérée par le CCSD (CNRS). L'API permet d'interroger la base sans authentification.

- **Point d'entrée** : `https://api.archives-ouvertes.fr/search/`
- **Syntaxe** : Apache Solr
- **Domaine droit** : `1.shs.droit` (~227 000 documents)
- **Accès recommandé** : `scripts/doctrine_search.py` (multi-sources HAL + OpenAlex + Isidore, dédoublonnage DOI via Crossref, identifiant vérifiable par référence) — **outil de première intention pour la doctrine**. `scripts/hal_search.py` pour les requêtes HAL ciblées (notes d'arrêt par numéro de pourvoi via `--pourvoi`, recherche par auteur via `--author`). En dernier recours, `bash_tool` + `curl` directement sur l'API (patrons ci-dessous).

## Caractéristiques et limites

### Forces
- Métadonnées structurées (auteurs, revue, année, mots-clés)
- Citations pré-formatées (`citationFull_s`)
- Liens permanents (`uri_s`)
- Texte intégral en accès ouvert quand disponible (`fileMain_s`)
- Couverture significative : ~148 000 articles, ~30 000 chapitres, ~8 700 ouvrages en droit

### Limites à garder en mémoire
- **Couverture non exhaustive** : HAL ne contient que les publications déposées par leurs auteurs. Les revues commerciales (Dalloz, LexisNexis, LGDJ) n'y figurent souvent qu'en notice sans texte intégral
- **Pas de recherche plein texte** : La recherche porte sur les métadonnées (titre, résumé, mots-clés), pas dans le contenu des articles
- **Biais de dépôt** : La couverture est hétérogène selon les laboratoires et les auteurs
- **Conséquence** : HAL est un excellent **complément** à web_search, jamais un substitut

## Patron de requête standard (doctrine juridique)

```bash
curl -s "https://api.archives-ouvertes.fr/search/?q=(title_t:(TERMES) OR abstract_t:(TERMES) OR keyword_t:(TERMES))&fq=domain_s:1.shs.droit&fq=docType_s:(ART OR OUV OR COUV OR COMM OR DOUV OR THESE OR HDR)&sort=producedDate_tdate desc&rows=10&wt=json&fl=halId_s,title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,docType_s,citationFull_s,abstract_s,keyword_s,fileMain_s,submitType_s"
```

### Paramètres obligatoires

| Paramètre | Valeur | Rôle |
|---|---|---|
| `q` | Requête multi-champs | Termes de recherche |
| `fq=domain_s` | `1.shs.droit` | Filtrer sur le domaine juridique |
| `fq=docType_s` | `(ART OR OUV OR COUV OR COMM...)` | Types de documents académiques |
| `sort` | `producedDate_tdate desc` | Plus récent d'abord |
| `rows` | `10` (défaut recommandé) | Nombre de résultats |
| `wt` | `json` | Format de réponse |
| `fl` | Liste des champs | Champs à retourner |

### Encodage des caractères spéciaux

Les caractères accentués doivent être encodés en URL :
- `é` → `%C3%A9`
- `è` → `%C3%A8`
- `ê` → `%C3%AA`
- `à` → `%C3%A0`
- espace → `%20`

Les caractères Solr doivent être échappés avec `\` : `+ - && || ! ( ) { } [ ] ^ " ~ * ? : \`

## Stratégies de recherche

### 1. Recherche thématique (usage principal)

Combiner titre + abstract + mots-clés :

```bash
q=(title_t:(responsabilité civile) OR abstract_t:(responsabilité civile) OR keyword_t:(responsabilité civile))
```

**Conseil** : Limiter à 2-4 termes significatifs. Le moteur Solr applique AND par défaut — trop de termes = 0 résultat.

### 2. Recherche par auteur

```bash
q=authLastName_t:Bénabent
# ou pour un auteur avec nom composé :
q=authLastName_t:Quézel-Ambrunaz
```

### 3. Recherche de notes d'arrêt (par numéro de pourvoi)

```bash
q=title_t:"21-12345"
```

Fonctionne car de nombreux auteurs incluent le numéro de pourvoi dans le titre de leur note.

### 4. Recherche par revue juridique

```bash
fq=journalTitle_t:"Recueil Dalloz"
fq=journalTitle_t:"Gazette du Palais"
fq=journalTitle_t:"Revue trimestrielle de droit civil"
```

### 5. Recherche temporelle

Doctrine des N dernières années :
```bash
fq=producedDateY_i:[2023 TO 2026]
```

Doctrine récente (6 derniers mois) :
```bash
fq=producedDate_tdate:[NOW-6MONTHS/DAY TO NOW/DAY]
```

### 6. Recherche de texte intégral en accès ouvert uniquement

```bash
fq=submitType_s:file
```

Le champ `fileMain_s` contiendra alors l'URL du PDF.

### 7. Recherche d'expression exacte

Utiliser les guillemets :
```bash
q=title_t:"préjudice d'anxiété"
```

### 8. Recherche interdisciplinaire (élargissement du domaine)

Pour les sujets à la frontière du droit et d'autres disciplines (droit et économie, droit et philosophie, etc.) :
```bash
fq=domain_s:(1.shs.droit OR 0.shs)
```

Retirer le filtre domaine en dernier recours si les résultats sont insuffisants.

## Champs de retour (fl)

### Champs essentiels (toujours demander)

| Champ | Type | Description |
|---|---|---|
| `halId_s` | string | Identifiant HAL unique |
| `title_s` | string[] | Titre(s) du document |
| `authFullName_s` | string[] | Nom(s) complet(s) des auteurs |
| `producedDateY_i` | int | Année de publication |
| `journalTitle_s` | string | Titre de la revue |
| `uri_s` | string | URL permanente HAL |
| `docType_s` | string | Type de document (ART, OUV, COUV, COMM, THESE, HDR) |
| `citationFull_s` | string | **Citation formatée complète** (très utile) |

### Champs complémentaires (demander si pertinent)

| Champ | Type | Description |
|---|---|---|
| `abstract_s` | string[] | Résumé (quand disponible) |
| `keyword_s` | string[] | Mots-clés |
| `fileMain_s` | string | URL du document principal (PDF) |
| `submitType_s` | string | `file` (texte intégral) ou `notice` (métadonnées seules) |
| `files_s` | string[] | Liste de tous les fichiers associés |

## Types de documents (docType_s)

Types pertinents pour la doctrine juridique :

| Code | Description | Usage |
|---|---|---|
| `ART` | Article de revue | ⭐ Source principale |
| `COUV` | Chapitre d'ouvrage | Contributions à des mélanges, traités |
| `OUV` | Ouvrage / monographie | Manuels, thèses publiées, traités |
| `COMM` | Communication dans un congrès | Actes de colloque |
| `DOUV` | Direction d'ouvrage | Ouvrages collectifs dirigés |
| `THESE` | Thèse de doctorat | Recherche approfondie |
| `HDR` | Habilitation à diriger des recherches | Synthèse de travaux |

## Format de citation recommandé

Utiliser `citationFull_s` comme base, puis ajouter le lien HAL :

```
[Citation formatée HAL]
Disponible sur HAL : [uri_s]
```

Si texte intégral disponible (`submitType_s == "file"`) :
```
[Citation formatée HAL]
Disponible en accès ouvert : [fileMain_s]
```

## Stratégies d'élargissement si 0 résultat

1. **Réduire le nombre de termes** : Passer de 4 à 2 termes
2. **Passer en OR** : `q=title_t:(terme1 OR terme2)` au lieu du AND implicite
3. **Supprimer le filtre domaine** : Retirer `fq=domain_s:1.shs.droit` (certains articles juridiques sont classés en économie, philosophie, etc.)
4. **Élargir les types** : Ajouter `OTHER`, `REPORT`, `BLOG`
5. **Chercher dans le titre seul** : Parfois `title_t` seul est plus efficace que la combinaison multi-champs
6. **Utiliser la troncature** : `responsab*` pour capturer responsabilité/responsable/responsabilisation

## Stratégies d'affinement si trop de résultats

1. **Filtrer par année** : `fq=producedDateY_i:[2020 TO 2026]`
2. **Filtrer par type** : Se limiter aux `ART` pour les articles de revue
3. **Recherche d'expression exacte** : Guillemets autour de la phrase
4. **Combiner avec un auteur** : Ajouter `fq=authLastName_t:NOM`

## Requêtes types par cas d'usage

### Recherche juridique approfondie (tâche de recherche)
Recherche thématique large + filtre temporel pour la doctrine récente :
```bash
curl -s "https://api.archives-ouvertes.fr/search/?q=(title_t:(clause%20abusive) OR abstract_t:(clause%20abusive) OR keyword_t:(clause%20abusive))&fq=domain_s:1.shs.droit&fq=docType_s:(ART OR OUV OR COUV OR COMM OR THESE)&sort=producedDate_tdate desc&rows=15&wt=json&fl=halId_s,title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,docType_s,citationFull_s,abstract_s,fileMain_s,submitType_s"
```

### Veille doctrinale (tâche de veille juridique)
Doctrine des 2 dernières années sur un thème :
```bash
curl -s "https://api.archives-ouvertes.fr/search/?q=(title_t:(RGPD%20données%20personnelles) OR abstract_t:(RGPD%20données%20personnelles) OR keyword_t:(RGPD))&fq=domain_s:1.shs.droit&fq=producedDateY_i:[2024 TO 2026]&fq=docType_s:(ART OR OUV OR COUV OR COMM)&sort=producedDate_tdate desc&rows=10&wt=json&fl=halId_s,title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,docType_s,citationFull_s,fileMain_s,submitType_s"
```

### Bibliographie d'un article de loi (tâche d'analyse d'article)
Combinaison du numéro d'article + thème :
```bash
curl -s "https://api.archives-ouvertes.fr/search/?q=(title_t:(1240%20code%20civil) OR title_t:(responsabilité%20civile%20extracontractuelle))&fq=domain_s:1.shs.droit&fq=docType_s:(ART OR OUV OR COUV OR THESE)&sort=producedDate_tdate desc&rows=10&wt=json&fl=halId_s,title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,docType_s,citationFull_s,fileMain_s,submitType_s"
```

### Notes d'arrêt (par numéro de pourvoi)
```bash
curl -s "https://api.archives-ouvertes.fr/search/?q=title_t:\"21-19.900\"&fq=domain_s:1.shs.droit&rows=10&wt=json&fl=halId_s,title_s,authFullName_s,producedDateY_i,journalTitle_s,uri_s,docType_s,citationFull_s,fileMain_s,submitType_s"
```

## Gestion des erreurs

| Situation | Action |
|---|---|
| Timeout curl (>10s) | Basculer sur web_search seul |
| Erreur HTTP 5xx | Réessayer une fois, puis basculer sur web_search |
| 0 résultat | Appliquer stratégie d'élargissement, puis web_search |
| Résultats non pertinents | Affiner la requête, vérifier les termes |

## Complémentarité HAL / web_search

| Aspect | HAL | web_search |
|---|---|---|
| Métadonnées structurées | ✅ Excellentes | ❌ Variables |
| Citations formatées | ✅ `citationFull_s` | ❌ Non disponible |
| Texte intégral gratuit | ✅ Quand disponible | ❌ Souvent paywall |
| Exhaustivité revues commerciales | ❌ Partielle (notices) | ✅ Meilleure |
| Doctrine sur Cairn/Persée | ❌ Non couvert | ✅ Oui |
| Billets de blog juridique | ❌ Rare | ✅ Oui |
| Fiabilité des liens | ✅ Permanents | ⚠️ Variable |
| Recherche par numéro de pourvoi | ✅ Dans les titres | ✅ Plus large |

**Règle d'or** : Toujours utiliser les deux sources en parallèle pour une couverture optimale de la doctrine.
