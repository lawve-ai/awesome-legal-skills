# Tâche 7 — Veille juridique

> **Environnement** : aucun prérequis. Livrable Word par défaut (artefact Docs si l'utilisateur le demande) ; pour une question brève, réponse structurée dans la conversation. Tableau de vérification remis en document séparé (`references/environnement-et-livrables.md`).

## Objectif

Produire une synthèse regroupant et analysant les changements du droit positif sur une matière ou un point de droit, pour une période donnée.

## Processus

### 1. Exécuter le playbook (tâche 0)

Identifier le périmètre de la veille : matière, période, type de sources pertinentes.

### 2. Recherche des évolutions — Séquence descendante

**EXÉCUTER :**

**2a. Évolutions législatives et réglementaires** via OpenLegi :
- `recherche_journal_officiel` → textes publiés sur la période, filtrés par matière
- `rechercher_dans_texte_legal` → lois, ordonnances, décrets récents
- `rechercher_code` → articles modifiés ou créés sur la période
- Identifier : lois promulguées, ordonnances, décrets d'application, projets/propositions en cours

**2b. Évolutions jurisprudentielles** via LibreJustice puis OpenLegi :
- `LibreJustice:search_decisions` avec `date_from` (borne de la période veillée), `sort: "date_desc"` et `seat` successivement `["CC"]`, `["CE"]`, `["CONSTIT"]` — puis les juridictions du fond si la veille les couvre
- `procedure: ["QPC"]` pour isoler les questions prioritaires de constitutionnalité, `publication: ["PUBLIE_RAPPORT","PUBLIE_BULLETIN","LETTRE_CHAMBRE","PUBLIE_LEBON"]` pour hiérarchiser
- `LibreJustice:get_decision` sur chaque décision signalée dans la veille : motifs réels, `appellateFate`, `commentaires` institutionnels
- `OpenLegi:rechercher_jurisprudence_judiciaire` / `rechercher_jurisprudence_administrative` (tri `DATE_DESC`) et `rechercher_decisions_constitutionnelles` — complément et lien Légifrance de chaque décision citée
- Identifier : revirements, précisions, confirmations de jurisprudence constante

**2c. Évolutions doctrinales** via HAL + web_search :
- `scripts/doctrine_search.py` → publications récentes (multi-sources, identifiant vérifiable) ; `scripts/hal_search.py` en complément ciblé
- web_search → Dalloz Actualité, JCP Actualité, AJDA, recensions récentes
- Identifier : analyses critiques des réformes, propositions doctrinales, débats en cours

**2d. Évolutions européennes et internationales** via web_search si pertinent :
- CEDH (hudoc.echr.coe.int), CJUE (curia.europa.eu)
- Directives et règlements de l'UE en cours de transposition

### 3. Classification et qualification des sources JORF

Pour chaque document issu du Journal officiel : qualifier sa nature (normatif / travaux parlementaires / document administratif) conformément aux principes cardinaux. Ne pas présenter un rapport parlementaire comme du droit positif.

### 4. Rédaction du document Word

**Structure :**

1. **Synthèse** : principales évolutions, tendances, impact pratique
2. **Évolutions législatives et réglementaires** (chronologie, analyse de chaque texte)
3. **Évolutions jurisprudentielles** (arrêts marquants, analyse de leur portée)
4. **Évolutions doctrinales** (débats en cours, analyses critiques)
5. **Perspectives** : textes en préparation, projets de loi, transpositions attendues
6. **Notes et références**

Pour chaque évolution : date, référence exacte, résumé du contenu, analyse de l'impact, lien hypertexte.

### 5. Livraison

Nommage : `[AAAA-MM-JJ]-veille-[matiere]-[periode].docx`
