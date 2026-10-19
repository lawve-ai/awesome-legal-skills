# PCI DSS v3.2.1 → v4.0 / v4.0.1 — Journal des changements et veille versionnelle

## Chronologie des versions

| Version | Publication | Statut |
|---------|----------|--------|
| v3.2.1 | Mai 2018 | **Retirée le 31 mars 2024** |
| v4.0 | Mars 2022 | **Retirée le 31 décembre 2024** |
| v4.0.1 | Juin 2024 | **Version courante — seule version active** |

**Jalons :** 31/03/2024 — v3.2.1 retirée · 31/12/2024 — v4.0 retirée, v4.0.1 seule version active · 31/03/2025 — les 51 exigences future-dated de v4.0 devenues obligatoires (sur 64 nouvelles exigences : 13 immédiates + 51 différées) · 01/04/2025 — critère d'éligibilité SAQ A r1 applicable · 03/06–20/07/2026 — RFC du PCI SSC sur v4.0.1 préparant l'itération suivante (technologies futures et IA) ; v5.0 préliminaire attendue fin 2026, sans changement imminent des obligations d'évaluation.

La v4.0.1 n'ajoute aucune exigence : corrections de forme et typographiques, clarifications d'intention, déplacement des gabarits de l'approche personnalisée de l'annexe E vers le site PCI SSC, ajouts de définitions en annexe G.

## Nouvelles exigences (obligatoires depuis le 31 mars 2025)

**Req 3 :** 3.3.2 (chiffrement des SAD pré-autorisation — émetteurs/services d'émission), 3.3.3 (gestion des clés associée).
**Req 4 :** 4.2.1.1 (inventaire des clés et certificats de confiance).
**Req 5 :** 5.3.3 (analyse des supports amovibles), 5.4.1 (anti-hameçonnage automatisé).
**Req 6 :** 6.3.2 (inventaire logiciel sur mesure / SBOM), 6.4.3 (inventaire, autorisation et intégrité des scripts de pages de paiement).
**Req 7 :** 7.2.4 (revues d'accès semestrielles), 7.2.5/7.2.5.1 (comptes applicatifs/système), 7.3.2 (application de la moindre privilège).
**Req 8 :** 8.3.6 (rotation à 90 jours pour les comptes sans MFA), 8.4.2 (MFA pour TOUT accès au CDE), 8.6.1/8.6.2 (comptes système ; pas de mots de passe en dur).
**Req 10 :** 10.4.1.1 (revue automatisée des journaux), 10.7.2/10.7.3 (détection et réponse aux défaillances des contrôles critiques).
**Req 11 :** 11.4.7 (support aux tests d'intrusion par les prestataires multi-clients), 11.6.1 (détection de modification/altération des pages de paiement).
**Req 12 :** 12.3.1 (TRA — approche personnalisée), 12.3.2 (TRA — fréquences flexibles), 12.3.3/12.3.4 (revues annuelles crypto et technologies), 12.5.2.1 (vérification du périmètre par les prestataires multi-clients, semestrielle), 12.8.4 (suivi annuel de conformité des TPSP), 12.9.2 (confirmation des responsabilités par les TPSP), 12.10.4.1 (formation annuelle du personnel IR), 12.10.7 (procédure de découverte de PAN inattendus).

## Changements conceptuels majeurs

1. **Approche personnalisée** — contrôles alternatifs atteignant l'Objectif énoncé d'une exigence ; TRA par contrôle, approbation de la direction, évaluation par QSA via CATP, revalidation annuelle.
2. **Extension de la MFA (8.4.2)** — tout accès au CDE, y compris depuis le LAN interne ; la segmentation seule ne suffit plus.
3. **Scripts de pages de paiement (6.4.3/11.6.1)** — lutte contre l'e-skimming (Magecart) ; dans le SAQ A, remplacés depuis avril 2025 par le critère d'éligibilité r1 (FAQ 1588) ; pleinement applicables en SAQ A-EP et en ROC.
4. **Anti-hameçonnage (5.4.1)** — passerelle de messagerie sécurisée, filtrage DNS, DMARC/DKIM/SPF ou équivalent.
5. **TRA (12.3.1/12.3.2)** — analyse de risque formalisée : description du risque, exigence applicable, motif, atteinte de l'objectif, preuve d'efficacité, validation, revue annuelle.
6. **Revue automatisée des journaux (10.4.1.1)** — la revue manuelle seule ne suffit plus ; SIEM ou équivalent avec alerting.

## Supprimés ou restructurés

6.3 → 6.3.1–6.5.6 · 10.6 → 10.4 (automatisé) · 11.2 restructurée (cadrance ASV inchangée) · 12.10 étendue · BAU → exigences de conformité continue spécifiques · annexe A2 (migration TLS) supprimée · annexe A3 actualisée · gabarits de l'annexe E déplacés vers le site PCI SSC (v4.0.1).

## Liste de contrôle de migration (v3.2.1 → v4.0.1)

**Gouvernance (Req 12) :** processus et gabarit TRA (12.3.1/12.3.2) · revue annuelle crypto (12.3.3) · revue annuelle technologies (12.3.4) · registre TPSP et suivi annuel (12.8.4) · formation annuelle IR (12.10.4.1) · procédure de découverte de PAN (12.10.7) · vérification du périmètre (12.5.2) et revues trimestrielles (12.4.2).
**Authentification (Req 8) :** MFA pour tout accès au CDE, interne compris (8.4.2) · minimum 12 caractères (8.3.5) · rotation uniquement pour les comptes sans MFA (8.3.6) · pas de mots de passe en dur (8.6.2).
**E-commerce (Req 6, 11) :** inventaire, autorisation et intégrité des scripts (6.4.3) · détection d'altération des en-têtes et du contenu (11.6.1) · CSP/SRI — et, pour les marchands SAQ A en iframe, le critère d'éligibilité r1 ou la confirmation du prestataire.
**Anti-malveillance/hameçonnage (Req 5) :** solution anti-hameçonnage automatisée (5.4.1) · analyse des supports amovibles (5.3.3).
**Journalisation (Req 10) :** revue automatisée (10.4.1.1) · surveillance des défaillances de contrôles (10.7.2/10.7.3).
**Accès (Req 7, 8) :** revues d'accès semestrielles (7.2.4) · gestion des comptes applicatifs/système (7.2.5).
**Logiciel (Req 6) :** SBOM pour le logiciel sur mesure (6.3.2).

## Veille versionnelle — v5.0

Le PCI SSC a conduit une RFC sur v4.0.1 du 3 juin au 20 juillet 2026, orientée vers les technologies futures et l'innovation en IA, à mesure que débute le travail sur l'itération suivante. Une version préliminaire de PCI DSS v5.0 est attendue pour commentaires vers fin 2026. Au vu des transitions passées (v4.0 : publiée en 2022, obligatoire en 2024–2025), aucun changement imminent des obligations d'évaluation n'est attendu : toutes les évaluations 2026 se font sur v4.0.1, chaque exigence dans le périmètre. Ne pas anticiper d'exigences v5.0.
