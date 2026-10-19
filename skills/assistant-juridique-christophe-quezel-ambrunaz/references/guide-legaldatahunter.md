# Guide LegalDataHunter — Droit de l'UE, CEDH et droit étranger/comparé

<!-- NOYAU v4 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills (script sync-noyau.sh). -->

## ⚠️ Vérification de disponibilité obligatoire

**Avant tout usage**, vérifier que le connecteur est présent. Son nom de serveur varie selon les comptes (par exemple « Droit_compar ») : l'identifier par ses outils (`search`, `resolve_reference`, `discover_countries`, `discover_sources`, `get_filters`, `get_document`, `report_source_issue`), après une recherche d'outils différés. Dans ce guide, `LegalDataHunter:` désigne ce serveur, quel que soit son nom affiché.
- S'il est absent : il s'ajoute depuis les connecteurs de Claude (paramètres) ; à défaut, contacter Christophe Quézel-Ambrunaz.
- En cas d'indisponibilité : informer l'utilisateur, basculer sur web_search avec les sites officiels (curia.europa.eu, hudoc.echr.coe.int, sites officiels des juridictions étrangères). Signaler la limitation dans le livrable.

**Ne jamais bloquer l'exécution** pour indisponibilité du MCP — utiliser le fallback web_search.

## Périmètre d'utilisation

LegalDataHunter est le MCP **prioritaire** pour toute question portant sur :
- **Droit de l'Union européenne** : jurisprudence CJUE, Tribunal UE, textes normatifs UE récents — code `EU`
- **Droit de la Convention européenne des droits de l'homme** : jurisprudence CEDH — code `CoE`
- **Droit étranger** (système juridique d'un autre pays) — code ISO du pays
- **Droit comparé** (confrontation de systèmes juridiques)
- **Résolution d'une citation étrangère**

**⚠️ Ne PAS utiliser pour le droit français.** OpenLegi est prioritaire pour toute source française. LegalDataHunter couvre aussi la France (code `FR`, ~2,3M documents) mais OpenLegi est plus complet, plus fiable et mieux intégré pour ce périmètre. Exception : si OpenLegi est indisponible.

## Codes pays principaux

| Périmètre | Code | Couverture | Notes |
|---|---|---|---|
| Droit de l'UE | `EU` | CJUE, Tribunal UE, EUR-Lex récent, DGComp, EPO… | Voir limites temporelles ci-dessous |
| CEDH / Conseil de l'Europe | `CoE` | HUDOC (97K décisions, 1960-2026), Charte sociale européenne | Source principale pour la CEDH |
| Allemagne | `DE` | Important | case_law, legislation |
| Royaume-Uni | `UK` | Important | case_law, legislation |
| États-Unis | `US` | Important | case_law, legislation |
| Italie | `IT` | Important | case_law, legislation |
| Belgique | `BE` | Important | case_law, legislation |
| Suisse | `CH` | Important | case_law, legislation |
| Espagne | `ES` | Important | case_law, legislation |
| International | `INTL` | 30 sources, tribunaux internationaux | CIJ, CPI, etc. |

Pour la liste complète : `LegalDataHunter:discover_countries`

## ⚠️ Limites temporelles connues — à mentionner dans tout livrable concerné

| Source | Couverture temporelle | Impact |
|---|---|---|
| `EU/CURIA` (jurisprudence CJUE) | **2015–2026** seulement (9 383 décisions) | Pour les arrêts CJUE antérieurs à 2015 : fallback web_search sur curia.europa.eu |
| `EU/EUR-Lex` (législation UE consolidée) | **2024–2026** seulement (5 001 documents) | Pour les textes UE antérieurs à 2024 : web_search sur eur-lex.europa.eu |
| `CoE/HUDOC` (CEDH) | **1960–2026** (97K décisions) | Couverture complète — aucune limite pratique |

**Règle de priorité pour le droit UE :**
1. **Jurisprudence CJUE récente (2015+)** → `LegalDataHunter:search` (`country: "EU"`, `namespace: "case_law"`)
2. **Jurisprudence CJUE antérieure à 2015** → web_search sur curia.europa.eu
3. **Textes normatifs UE (règlements, directives)** → web_search EUR-Lex en première intention (couverture plus large) ; LegalDataHunter en complément pour les actes très récents (2024+)

## Outils disponibles (7)

### 1. `LegalDataHunter:search`
**Usage principal** : Recherche hybride sémantique + mots-clés.

**Paramètres** :
- `query` (obligatoire) : termes de recherche (fonctionne en anglais et dans les langues nationales)
- `namespace` : `case_law` | `legislation` | `doctrine`
- `country` : code pays (ex. `EU`, `CoE`, `DE`, `GB`)
- `court_tier` : niveau de juridiction (`supreme`, `appellate`, `first_instance`)
- `date_from`, `date_to` : bornes temporelles (format ISO)
- `language` : langue des résultats
- `limit` : nombre de résultats (défaut : 10)

### 2. `LegalDataHunter:get_document`
**Usage** : Obtenir le texte intégral d'un document identifié par son ID.

### 3. `LegalDataHunter:resolve_reference`
**Usage** : Résoudre une citation juridique étrangère (ex. « BVerfG, 1 BvR 1585/13 »).
**Paramètres** : `reference` (texte de la citation), `country` (optionnel).

### 4. `LegalDataHunter:discover_countries`
**Usage** : Lister les pays disponibles avec le nombre de documents.

### 5. `LegalDataHunter:discover_sources`
**Usage** : Lister les sources disponibles pour un pays donné.
**Paramètres** : `country_code` (obligatoire).

### 6. `LegalDataHunter:get_filters`
**Usage** : Obtenir les filtres disponibles pour un pays et un namespace.

### 7. `LegalDataHunter:report_source_issue`
**Usage** : Signaler un problème avec une source.

## Stratégies de recherche

### Jurisprudence CEDH (CoE)

```
LegalDataHunter:search
  query: "[question de droit en anglais ou français]"
  country: "CoE"
  namespace: "case_law"
```
Si résultats insuffisants : essayer sans filtre `namespace`, ou reformuler en anglais.

### Jurisprudence CJUE (EU)

```
LegalDataHunter:search
  query: "[question de droit]"
  country: "EU"
  namespace: "case_law"
```
⚠️ Couverture 2015-2026 seulement. Pour les arrêts antérieurs : web_search sur curia.europa.eu.

### Législation UE (règlements, directives)

Privilégier web_search EUR-Lex (eur-lex.europa.eu) — `EU/EUR-Lex` ne couvre que 2024-2026.
En complément pour les actes très récents (2024+) :
```
LegalDataHunter:search
  query: "[intitulé ou objet du texte]"
  country: "EU"
  namespace: "legislation"
```

### Recherche comparative bilatérale (France vs. pays X)

1. Identifier la question en termes généraux (anglais recommandé)
2. `search` avec `country` = pays cible, `namespace` = `case_law` ou `legislation`
3. Comparer avec le droit français (OpenLegi) sur la même question
4. Synthétiser convergences et divergences

### Recherche multi-pays (panorama comparatif)

1. `discover_countries` pour identifier les pays disposant de sources pertinentes
2. Pour chaque pays sélectionné : `search` avec les mêmes termes
3. Organiser par famille juridique (romano-germanique, common law, mixte)

### Résolution d'une citation étrangère

1. `resolve_reference` avec le texte exact de la citation
2. Si échec : `search` avec les éléments identifiables
3. Si toujours négatif : web_search, puis signaler que la référence n'a pu être résolue

## Intégration avec la séquence de recherche (§ 4 du SKILL.md)

- **Étape 2 (jurisprudence suprême)** : LegalDataHunter pour CJUE (`EU`) et CEDH (`CoE`)
- **Étape 5 (droit étranger/comparé)** : LegalDataHunter pour les pays tiers

**Schéma de déclenchement :**
- Question sur la CJUE → `search` (country: `EU`) + fallback web_search curia.europa.eu si antérieur à 2015
- Question sur la CEDH → `search` (country: `CoE`)
- Question sur un texte normatif UE → web_search EUR-Lex en première intention, LegalDataHunter en complément (2024+)
- Question sur le droit d'un autre pays → `search` (country: code ISO)
- Analyse comparative → séquence multi-pays

## Format de citation

**CEDH :**
```
CEDH, [chambre], [date], req. n° [numéro], [Nom de l'affaire]
Ex. : CEDH, Gr. Ch., 29 avr. 2002, req. n° 2346/02, Pretty c. Royaume-Uni
```

**CJUE :**
```
CJUE, [chambre], [date], aff. [C-XX/XX], [Nom de l'affaire]
Ex. : CJUE, Gr. Ch., 5 juin 2018, aff. C-210/16, Wirtschaftsakademie Schleswig-Holstein
```

**Droit étranger (règle générale)** :
```
[Juridiction], [date], [référence nationale]
```
Pour la common law : `[Nom de l'affaire] [année] [recueil] [page]`

Toujours indiquer le pays d'origine et, si pertinent, la traduction du titre ou du principe dégagé.

## Gestion des erreurs

| Situation | Action |
|---|---|
| MCP indisponible | Informer l'utilisateur ; basculer sur web_search avec sites officiels |
| Arrêt CJUE antérieur à 2015 | web_search curia.europa.eu — mentionner dans le livrable |
| Texte UE antérieur à 2024 | web_search eur-lex.europa.eu — mentionner dans le livrable |
| Pays non disponible | `discover_countries`, proposer un pays voisin de même tradition |
| 0 résultat | Reformuler en anglais, élargir les filtres, autre namespace |
| Document incomplet | `get_document` pour le texte intégral, sinon signaler la limite |
| Citation non résolue | `search` avec éléments partiels, puis web_search |
