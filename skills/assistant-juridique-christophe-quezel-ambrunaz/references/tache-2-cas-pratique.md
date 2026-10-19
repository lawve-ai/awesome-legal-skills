# Tâche 2 — Cas pratique / Consultation

> **Environnement** : aucun prérequis. Livrable Word par défaut (artefact Docs si l'utilisateur le demande) ; pour une question brève, réponse structurée dans la conversation. Tableau de vérification remis en document séparé (`references/environnement-et-livrables.md`).

## Objectif

Analyser une situation factuelle et produire une réponse juridique structurée, selon un raisonnement syllogistique. La consultation peut être neutre ou orientée pour une partie.

## Processus

### 1. Exécuter le playbook (tâche 0)

### 2. Analyse des documents du dossier

Scanner le dossier de travail (`references/environnement-et-livrables.md` § 2). Si des pièces sont présentes : les lire, extraire les éléments factuels pertinents (dates, sommes, relations contractuelles, preuves disponibles).

### 2bis. Construction de la chronologie des faits

**EXÉCUTER systématiquement** dès que des documents sont présents ou que des faits sont exposés :

Construire un tableau chronologique des événements :

| Date | Fait | Source (pièce ou déclaration) |
|---|---|---|
| [date] | [événement] | [source] |

- Ordonner tous les faits par date (ordre chronologique strict)
- Identifier les parties impliquées à chaque étape
- Repérer les lacunes factuelles (faits évoqués sans date, contradictions entre pièces)
- **Intégrer la chronologie dans le document Word** (section « Rappel des faits »)

### 2ter. Vérification des délais juridiques

**EXÉCUTER après la chronologie**, si des délais légaux sont susceptibles d'avoir un impact :

1. **Identifier les délais potentiellement applicables** à partir des faits :
   - Délai de prescription de droit commun (art. 2224 C. civ. : 5 ans à compter de la connaissance des faits)
   - Délais spéciaux (prescription biennale consommateur, décennale construction, quinquennale contrats d'assurance, etc.)
   - Délais de recours contentieux (2 mois en matière administrative, 30 ans pour les actions réelles immobilières, etc.)
   - Délais de procédure (appel, cassation, opposition)
   - Délais contractuels stipulés dans les pièces

2. **Vérifier chaque délai via OpenLegi** (`rechercher_code`) — ne jamais affirmer un délai de mémoire.

3. **Calculer le délai résiduel** à partir des dates de la chronologie :
   - Date de point de départ du délai (fait générateur, connaissance du dommage, etc.)
   - Date d'échéance théorique
   - Date du jour → délai restant ou dépassement éventuel

4. **Signaler explicitement** tout risque :
   - ⚠️ **Délai expiré** : la prescription ou forclusion semble acquise — le signaler en début de consultation
   - ⚠️ **Délai imminent** (moins de 3 mois) : avertir l'utilisateur de l'urgence
   - ✅ **Délai non couru ou largement ouvert** : le préciser pour rassurer

5. Si des faits interruptifs ou suspensifs sont identifiables (mise en demeure, demande en justice, minorité, etc.) : les mentionner et recalculer.

**⚠️ Précaution** : si les faits sont insuffisants pour calculer le délai avec certitude, l'indiquer et exposer les hypothèses.

### 3. Qualification juridique

**EXÉCUTER systématiquement :**
- Qualifier les personnes : consommateur/professionnel, salarié/fonctionnaire, type de société, mineur/majeur protégé
- Qualifier les choses : VTM, produit défectueux, immeuble/meuble
- Qualifier les situations : type de contrat, délit/quasi-délit, régime matrimonial
- Vérifier les définitions légales incertaines via OpenLegi (`rechercher_code`)

**INTERROMPRE SI** les faits sont insuffisants pour qualifier : poser des questions précises sur les éléments manquants indispensables.

### 4. Identification de la question juridique

Reformuler la question centrale. Cette question reçoit une réponse directe placée en début de document (réponse nuancée admise : « Oui, mais… », « En principe oui, sauf si… »).

Décomposer en sous-questions si nécessaire (arborescence logique).

### 5. Recherche — Séquence descendante

Pour chaque question/sous-question :
1. Textes normatifs applicables (OpenLegi ; `LibreJustice:get_norm` avec `date` pour la rédaction en vigueur à la date des faits)
2. Jurisprudence suprême (LibreJustice `search_decisions` puis `get_decision` ; OpenLegi pour le lien Légifrance) — arrêts de principe
3. Jurisprudence du fond (LibreJustice, filtre `seat`) — décisions illustratives proches des faits, sort en appel vérifié (`appellateFate`)
4. Doctrine (HAL + web_search) — analyses pertinentes

### 6. Raisonnement syllogistique

Pour chaque question :
```
MAJEURE  : Règle de droit applicable (texte + jurisprudence)
MINEURE  : Application aux faits de l'espèce
CONCLUSION : Solution juridique
```

**Date pivot** : la majeure mobilise le texte **dans sa rédaction en vigueur à la date des faits** soumis (et non à la date du jour), conformément au § 6 du SKILL.md. Déterminer explicitement cette date pivot ; si la consultation est prospective, retenir la date de l'effet projeté. Signaler toute évolution postérieure du texte si elle éclaire la réponse.

Identifier les forces et faiblesses de chaque argument. Si consultation orientée : développer les arguments favorables à la partie tout en signalant les risques.

### 7. Rédaction du document Word

**Structure :**
1. **Synthèse** : réponse directe à la question posée
2. **Rappel des faits** : chronologie (tableau), parties, enjeux
3. **Délais juridiques** : synthèse des délais applicables, risques identifiés (si pertinent)
4. **Qualification juridique** : régime applicable, justification
5. **Analyse détaillée** : syllogisme pour chaque question, discussion des arguments
6. **Conclusion** : recommandations générales, points de vigilance
7. **Notes et références**

Nommage : `[AAAA-MM-JJ]-consultation-[sujet].docx`
