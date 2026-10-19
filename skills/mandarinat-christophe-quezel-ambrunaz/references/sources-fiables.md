# Sources juridiques fiables

## Accès direct aux bases officielles via OpenLegi

**OpenLegi** est un serveur MCP (Model Context Protocol) qui donne à Claude un accès direct et structuré aux bases de données juridiques officielles. **Toute source accédée via OpenLegi est considérée comme fiable** : les données proviennent directement des bases Legifrance.

### Connecteurs disponibles
- **Legifrance** (`mcp.openlegi.fr/legifrance/mcp`) : codes, textes légaux, jurisprudence judiciaire et administrative, décisions du Conseil constitutionnel, décisions CNIL, Journal officiel, conventions collectives

### Priorité d'utilisation
OpenLegi doit être utilisé **en priorité** avant web_search pour toute recherche portant sur des textes officiels, de la jurisprudence ou des publications au Journal officiel. web_search reste indispensable en **complément** pour la doctrine, les analyses, et les sources non couvertes par OpenLegi.

---

## Recherche jurisprudentielle via LibreJustice

**LibreJustice** (`librejustice.fr`) est un serveur MCP offrant un moteur de recherche **sémantique et lexical** sur l'ensemble des juridictions françaises (Cour de cassation, Conseil d'État, Conseil constitutionnel, Tribunal des conflits, cours d'appel, tribunaux judiciaires, tribunaux des activités économiques, CAA, TA), la CNDA, les sanctions CNIL, la CEDH et la CJUE, ainsi qu'un référentiel de textes normatifs versionnés (codes français, codes étrangers curés, droit de l'UE, traités).

### Utilisation
- Jurisprudence : `search_decisions` (filtres structurés et facettes) puis `get_decision` (texte intégral, `appellateFate`, `caseChronology`, `commentaires`)
- Textes : `search_norms` (article recherché par son objet), `get_norm` (rédaction à une date donnée, chronologie des versions)
- Guide d'utilisation : `references/guide-librejustice.md`

### Fiabilité et réserves
Le corpus provient des bases publiques de diffusion (Judilibre, ArianeWeb, opendata de la justice administrative, HUDOC, CURIA). Deux réserves gouvernent son emploi :

1. **Les aperçus ne fondent rien** — `aiSummary` est une paraphrase produite par un modèle, `snippet` le passage d'appariement des mots-clés (possiblement issu des moyens des parties). Toute citation suppose la lecture du texte intégral par `get_decision`.
2. **LibreJustice ne fournit pas de lien Légifrance** — toute référence française diffusée sur Légifrance est repassée par OpenLegi pour en extraire le lien officiel ; à défaut de diffusion (décisions du fond, CNDA), le lien `librejustice.fr` tient lieu de lien vérifiable, source mentionnée.

---

## Accès au droit étranger et comparé via LegalDataHunter

**LegalDataHunter** est un serveur MCP donnant accès à plus de 6 millions de documents juridiques couvrant plus de 90 pays. Il offre une recherche hybride (sémantique + mots-clés) dans trois espaces de noms : `case_law`, `legislation`, `doctrine`.

### Utilisation
- **Recherche comparative** : `LegalDataHunter:search` avec filtres pays, juridiction, date
- **Résolution de citations étrangères** : `LegalDataHunter:resolve_reference`
- **Découverte de sources** : `LegalDataHunter:discover_sources`, `LegalDataHunter:discover_countries`
- Guide d'utilisation : `references/guide-legaldatahunter.md`

### Fiabilité
Les sources LegalDataHunter proviennent de bases officielles nationales et internationales. Qualifier systématiquement le niveau de fiabilité selon la source (officielle vs. secondaire).

---

## LISTE NOIRE - Sites à ne JAMAIS consulter ou citer

**INTERDICTION ABSOLUE** de consulter, référencer ou citer les sites suivants car ils diffusent de fausses informations juridiques :

- https://www.droitjustice.fr/
- https://www.conseil-juridique-online.fr/
- https://www.fde-avocat.com/

**Si ces sites apparaissent dans les résultats de recherche** : Les ignorer totalement et ne jamais les mentionner à l'utilisateur.

**Si l'utilisateur cite ces sources** : L'avertir que ces sites sont connus pour diffuser des informations juridiques erronées et proposer de rechercher sur des sources fiables.

---

## Sites prioritaires pour textes officiels et règles

### Sources françaises officielles
- https://www.legifrance.gouv.fr/ - Textes législatifs et réglementaires
- Tous les sites du domaine gouv.fr
- https://www.service-public.gouv.fr/ - Information administrative
- https://librejustice.fr/ - LibreJustice (moteur de recherche jurisprudentielle, toutes juridictions)
- https://www.courdecassation.fr/ - Cour de cassation (site principal et Judilibre)
- https://www.courdecassation.fr/acces-rapide-judilibre - Base de données Judilibre
- https://www.conseil-etat.fr/ - Conseil d'État (jurisprudence et documentation)
- https://opendata.justice-administrative.fr/ - Données ouvertes de la justice administrative
- https://opendata.justice-administrative.fr/recherche - Recherche dans les décisions
- https://www.conseil-constitutionnel.fr/ - Conseil constitutionnel (décisions et commentaires)
- https://www.assemblee-nationale.fr/ - Assemblée nationale (travaux parlementaires, projets et propositions de loi)
- https://www.senat.fr/ - Sénat (travaux parlementaires, rapports)

### Sources européennes et internationales
- https://www.echr.coe.int/ - Cour européenne des droits de l'homme
- https://hudoc.echr.coe.int - Base HUDOC de la CEDH
- https://curia.europa.eu/jcms/jcms/j_6/fr/ - Cour de justice de l'Union européenne
- https://european-union.europa.eu/index_fr - Union européenne
- https://european-union.europa.eu/institutions-law-budget/law/find-legislation_fr - Législation européenne
- https://european-union.europa.eu/institutions-law-budget/law/find-case-law_fr - Jurisprudence européenne
- https://basedoc.diplomatie.gouv.fr/exl-php/recherche/mae_internet___traites - Traités internationaux

### Autorités administratives indépendantes
Toutes les AAI listées sur : https://www.legifrance.gouv.fr/contenu/menu/autour-de-la-loi/autorites-independantes/autorites-administratives-independantes-et-autorites-publiques-independantes-relevant-du-statut-general-defini-par-la-loi-n-2017-55-du-20-janvier

## Sources doctrinales fiables

### `doctrine_search.py` — Recherche multi-sources (outil principal)
Le script `scripts/doctrine_search.py` interroge en un appel plusieurs bases ouvertes et retourne, pour chaque référence, un **identifiant vérifiable** (DOI, identifiant HAL, URL) :
- **HAL** (`api.archives-ouvertes.fr`) — archive ouverte FR, domaine droit.
- **OpenAlex** (`api.openalex.org`) — graphe bibliographique mondial, riche en DOI.
- **Isidore** (`api.isidore.science`) — moteur SHS francophone (CNRS / Huma-Num).
- **Crossref** (`api.crossref.org`) — registre DOI, utilisé pour résoudre et dédoublonner par DOI.

Le script dédoublonne par DOI puis par titre normalisé, et signale les sources injoignables (`sources_failed`) sans bloquer. Il constitue l'outil de première intention pour la doctrine ; HAL ciblé (`hal_search.py`) et web_search le complètent.

### HAL — Accès structuré via API
**HAL** (Hyper Articles en Ligne) est l'archive ouverte nationale française gérée par le CCSD (CNRS). L'API permet un accès structuré aux métadonnées et, lorsque disponible, au texte intégral des publications en droit.

- **Point d'entrée API** : `https://api.archives-ouvertes.fr/search/`
- **Accès** : Via `scripts/doctrine_search.py` (multi-sources) ou `scripts/hal_search.py` (HAL ciblé, notes d'arrêt par pourvoi)
- **Guide d'utilisation** : `references/guide-hal.md`
- **Couverture en droit** : ~227 000 documents (articles, ouvrages, chapitres, thèses, communications)
- **Fiabilité** : Les métadonnées HAL sont fiables (dépôts vérifiés par les auteurs et les laboratoires). Les citations formatées (`citationFull_s`) peuvent être utilisées directement.
- **Limites** : Couverture non exhaustive (dépend des dépôts par les auteurs). Les revues commerciales n'y figurent souvent qu'en notice sans texte intégral. HAL ne se substitue pas à web_search pour la doctrine.

### Portails web
- https://shs.hal.science/ - Archive ouverte HAL Sciences humaines et sociales
- https://droit.cairn.info/ - Revues juridiques sur Cairn
- https://www.persee.fr/ - Portail Persée (revues scientifiques)
- https://journals.openedition.org/ - Revues en sciences humaines et sociales
- https://books.openedition.org/ - Ouvrages en sciences humaines et sociales

## Utilisation des sources

Toujours privilégier ces sources lors des recherches juridiques. Ordre de priorité pour l'accès :
1. **LibreJustice** (recherche jurisprudentielle sémantique — toutes juridictions françaises, CNDA, CNIL, CEDH, CJUE ; textes versionnés) — voir `references/guide-librejustice.md`
2. **OpenLegi** (accès direct aux bases officielles — fiable par défaut, source du lien Légifrance)
3. **`doctrine_search.py`** (recherche doctrinale multi-sources — HAL + OpenAlex + Isidore, identifiant vérifiable) — voir `references/guide-hal.md`
4. **HAL API ciblé** (`hal_search.py` — notes d'arrêt par pourvoi, recherche par auteur)
5. **LegalDataHunter** (droit étranger et comparé — 90+ pays) — voir `references/guide-legaldatahunter.md`
6. **Sites officiels listés ci-dessus** (via web_search/web_fetch)
7. **Sources doctrinales web** (via web_search : Cairn, Persée, OpenEdition)

En cas de conflit entre sources, respecter la hiérarchie des normes :
1. Textes législatifs et réglementaires en vigueur
2. Jurisprudence (en fonction de l'autorité de la juridiction)
3. Doctrine (commentaires d'auteurs)
