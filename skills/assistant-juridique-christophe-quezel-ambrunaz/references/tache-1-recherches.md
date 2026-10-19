# Tâche 1 — Recherches juridiques

> **Environnement** : aucun prérequis. Livrable Word par défaut (artefact Docs si l'utilisateur le demande) ; pour une question brève, réponse structurée dans la conversation. Tableau de vérification remis en document séparé (`references/environnement-et-livrables.md`).

## Objectif

Produire une synthèse approfondie avec références vérifiées sur un point de droit, priorisant l'état actuel du droit tout en traitant les évolutions et dynamiques.

## Processus

### 1. Exécuter le playbook (tâche 0)

Identifier les questions juridiques et le droit applicable. Le playbook oriente les axes de recherche.

### 2. Recherche documentaire — Séquence descendante

Suivre la séquence du § 4 du SKILL.md dans cet ordre strict :

**EXÉCUTER :**

**2a. Textes normatifs** via OpenLegi :
- `rechercher_code` → articles des codes applicables
- `rechercher_dans_texte_legal` → lois, ordonnances, décrets
- `recherche_journal_officiel` → textes récents
- Vérifier les métadonnées temporelles de chaque texte (état juridique, dates de vigueur)
- Qualifier le statut temporel dans chaque citation

**2b. Jurisprudence suprême** via LibreJustice (première intention), OpenLegi (référence exacte et lien Légifrance) :
- `LibreJustice:search_decisions` — requête descriptive ; `seat` `["CC"]`, `["CE"]`, `["CONSTIT"]` (ou une chambre : `CC.C1_CIVILE`…) ; `publication` `["PUBLIE_RAPPORT","PUBLIE_BULLETIN","LETTRE_CHAMBRE","PUBLIE_LEBON"]` pour remonter d'abord les décisions publiées ; `legal_article` (`code-civil|1240`) pour cibler les décisions visant un article déterminé
- `LibreJustice:get_decision` sur chaque décision retenue — motifs, dispositif, `appellateFate`, `caseChronology`, `commentaires`. Jamais de sélection ni de citation sur la foi d'un `aiSummary` ou d'un `snippet`
- `OpenLegi:rechercher_jurisprudence_judiciaire` / `rechercher_jurisprudence_administrative` / `rechercher_decisions_constitutionnelles` — recherche par numéro exact et extraction du lien Légifrance de chaque décision citée
- Identifier les arrêts de principe, les revirements, la jurisprudence constante

**2c. Jurisprudence du fond** via LibreJustice :
- `LibreJustice:search_decisions` — `seat` (`CA`, `TJ`, `TCOM`, `CAA`, `TA`, ou une juridiction déterminée : `CA.PARIS`, `TA.LYON`…) ; `CNDA` pour l'asile
- Lire `appellateFate` avant de retenir une décision : une décision infirmée n'illustre pas l'état du droit sans que son infirmation soit signalée
- `OpenLegi:rechercher_jurisprudence_judiciaire` / `rechercher_jurisprudence_administrative` en complément et pour le lien Légifrance ; à défaut de diffusion sur Légifrance, porter le lien `librejustice.fr` en le qualifiant
- Sélectionner les décisions illustrant concrètement l'application de la règle, sans jamais présenter l'absence de décision trouvée comme une absence de jurisprudence

**2d. Doctrine** via HAL + web_search :
- `scripts/doctrine_search.py` → recherche doctrinale multi-sources (HAL + OpenAlex + Isidore), identifiant vérifiable par référence ; `scripts/hal_search.py` pour les notes d'arrêt par pourvoi
- web_search → Cairn, Dalloz Actualité, Persée, OpenEdition
- Rechercher les notes d'arrêt par numéro de pourvoi (HAL : `q=title_t:"NUMÉRO_POURVOI"`)
- Dédoublonner HAL / web_search
- **Minimum 10 sources doctrinales**, variées en supports (articles, ouvrages, thèses, notes) et en auteurs, chacune avec un **identifiant vérifiable** (DOI / HAL / URL d'une base reconnue) ; à défaut, mention « référence non vérifiée » ou suppression.

**INTERROMPRE UNIQUEMENT SI :**
- Aucun résultat pertinent sur l'ensemble des sources → signaler et proposer des axes alternatifs
- Contradiction majeure entre textes normatifs → exposer le conflit et la résolution proposée

### 3. Vérification

Pour chaque référence citée :
1. Confirmer l'existence et **lire le contenu** via LibreJustice (`get_decision`, `get_norm`), OpenLegi ou web_search (cf. `references/principes-cardinaux.md`)
2. Vérifier le statut temporel (en vigueur / abrogé / futur)
3. Qualifier la nature de la source (normatif / travaux parlementaires / informatif)
4. Créer un lien hypertexte vers la source

### 4. Rédaction du document Word

**Structure :**

1. **Synthèse** (réponse directe aux questions posées, en début de document)
2. **Introduction** : définitions, contexte historique, enjeux contemporains
3. **Développement** en plan structuré :
   - Titres descriptifs en sentence case
   - Citations exactes entre guillemets français « … » avec notes de fin
   - Confrontation des points de vue doctrinaux dans le corps du texte (dialectique, pas énumération)
   - Faits clés et éléments importants en gras
4. **Notes et références** en fin de document

**Traitement de la doctrine dans le corps du texte :**
- Intégrer les citations exactes des auteurs directement dans le développement
- Confronter les points de vue divergents : présenter la thèse, l'antithèse, expliquer les raisons du désaccord
- Indiquer les zones de consensus et de controverse

**Format des citations** : voir `references/format-citations.md`

### 5. Livraison

Écrire le livrable selon le § 3 du SKILL.md (Word par défaut, Docs sur demande). Nommage : `[AAAA-MM-JJ]-recherche-[sujet].docx`.
