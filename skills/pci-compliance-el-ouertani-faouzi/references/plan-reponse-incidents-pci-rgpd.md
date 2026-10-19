title: "Plan de réponse aux incidents — PCI DSS Req 12.10 et RGPD art. 32-33 (modèle)"
type: "text/markdown"
---

# Plan de réponse aux incidents (PCI DSS Req 12.10 · RGPD art. 32-33)

> Modèle de politique à adapter. Éléments juridiques vérifiés le 05/10/2026 via le connecteur EUR-Lex (EULEX Unified) sur la version consolidée en vigueur du règlement (UE) 2016/679 (CELEX 02016R0679-20160504).

## Bloc de contrôle de document

| Champ | Valeur |
|---|---|
| Titre | Plan de réponse aux incidents de sécurité |
| Version | 1.0 |
| Auteur | EL OUERTANI FAOUZI — faouzi.elouertani@gmail.com |
| Approuvé par | [Direction / RSSI] |
| Date | [JJ/MM/AAAA] |
| Prochaine revue | 12 mois après approbation (PCI DSS 12.10.2 ; RGPD art. 32 exige des mesures régulièrement évaluées) |

## 1. Objet

Définir la procédure de préparation, détection, qualification, réponse et retour d'expérience applicable à tout incident de sécurité susceptible d'affecter les données de compte (PAN, SAD, données de titulaires) ou des données à caractère personnel traitées par l'organisation.

Références de conformité :
- **PCI DSS v4.0.1** : exigences 12.10, 12.10.1 à 12.10.7 (plan, test annuel, astreinte 24/7, formation annuelle du personnel IR — 12.10.4.1, alertes des systèmes de supervision — 12.10.5, mises à jour selon les menaces — 12.10.6, procédure de découverte de PAN inattendus — 12.10.7) ; articulation avec 10.7.2/10.7.3 (détection des défaillances de contrôles critiques) et 12.8/12.9 (TPSP).
- **RGPD** : article 32 (sécurité du traitement — mesures techniques et organisationnelles appropriées, y compris la capacité de rétablir l'accès aux données en temps utile après un incident physique ou technique) et article 33 (notification à l'autorité de contrôle sous 72 heures), vérifiés sur la version consolidée en vigueur via EUR-Lex.

## 2. Périmètre

S'applique à l'ensemble des composants de l'environnement de données de titulaires (CDE), aux systèmes connectés pouvant en affecter la sécurité, au personnel interne et aux prestataires (TPSP) intervenant sur ces environnements, et à tout traitement de données à caractère personnel de l'organisation.

## 3. Rôles et responsabilités

| Rôle | Responsabilité | Référence |
|---|---|---|
| Direction générale | Approbation du plan, arbitrages, communication de crise | PCI 12.10.1 |
| RSSI / responsable du plan IR | Pilotage des incidents, qualification, coordination | PCI 12.10.3, 12.10.4 |
| Équipe IR (astreinte 24/7) | Intervention technique, confinement, investigation | PCI 12.10.3, 12.10.4.1 |
| DPO | Qualification RGPD, notification à la CNIL, information des personnes | RGPD art. 33, 34 |
| Correspondant PCI | Évaluation de l'impact compte/données de carte, notification aux marques/acquéreur | PCI 12.10 ; obligations contractuelles des marques |
| Responsable TPSP | Coordination avec les prestataires concernés | PCI 12.8, 12.9.2 |
| Juridique | Conservation des preuves, obligations contractuelles et déclaratives | — |

## 4. Préparation

1. **Plan documenté et prêt** (PCI 12.10.1) : le présent document, ses annexes et les procédures opérationnelles sont accessibles en permanence, y compris hors infrastructure compromise.
2. **Astreinte 24/7** (PCI 12.10.3) : registre des astreintes et coordonnées à jour, chaînes d'escalade nommées.
3. **Formation annuelle du personnel IR** (PCI 12.10.4.1) : programme et registre des formations.
4. **Test annuel du plan** (PCI 12.10.2) : exercice de type tabletop ou simulation, compte rendu et plans d'action.
5. **Intégration des alertes de supervision** (PCI 12.10.5) : les alertes SIEM, IDS/IPS, détection d'altération des pages de paiement (Req 11.6.1) et mécanismes de détection des défaillances de contrôles critiques (Req 10.7.2) déclenchent la procédure IR.
6. **Exercices avec les TPSP** : vérification périodique des clauses de notification d'incident des contrats (PCI 12.8.2 ; le sous-traitant notifie le responsable sans tarder — RGPD art. 33.2).
7. **Matériel de forensique** : images disque, chaîne de conservation, horodatage NTP (Req 10.6).

## 5. Détection et signalement

- Sources : SIEM (revue automatisée — Req 10.4.1.1), IDS/IPS (Req 11.5), détection d'altération des pages de paiement (Req 11.6.1), signalements du personnel, notifications TPSP, marques de paiement.
- Tout personnel signalant un événement suspecté le fait immédiatement au canal d'astreinte, sans filtrage préalable : la qualification relève de l'équipe IR (PCI 12.10 : réponse immédiate aux incidents suspectés et confirmés).

## 6. Qualification

Pour chaque événement, documenter a minima : date/heure de détection et de survenue (estimée), systèmes et données concernés, type d'incident (malveillance, e-skimming, compromission de comptes, perte de supports, défaillance), caractère confirmé ou suspecté.

**Double qualification systématique :**
- **Qualification PCI** : données de compte impliquées (PAN, SAD, CHD) ? Périmètre du CDE affecté ? Obligations contractuelles des marques de paiement susceptibles d'être déclenchées.
- **Qualification RGPD** : données à caractère personnel impliquées ? Risque pour les droits et libertés des personnes — critère de notification de l'article 33.1.

## 7. Réponse

1. **Confinement** : isolement des systèmes, blocage des comptes, révocation des clés et certificats, mise hors ligne des pages de paiement altérées.
2. **Éradication et remédiation** : correction des vulnérabilités, révision des accès (Req 7.2.4), restauration depuis des sauvegardes saines, remplacement des terminaux POI suspects (Req 9.5).
3. **Reprise** : rétablissement de la disponibilité et de l'accès aux données en temps utile après l'incident (RGPD art. 32.1 c) ; validation avant remise en production.
4. **Communication** :
   - **CNIL** : notification sans tarder et, si possible, au plus tard 72 heures après en avoir pris connaissance, lorsque la violation présente un risque pour les droits et libertés des personnes ; si la notification dépasse 72 heures, elle est accompagnée des motifs du retard (RGPD art. 33.1, vérifié via EUR-Lex). Contenu minimal de la notification : nature de la violation, catégories et nombre approximatif de personnes et d'enregistrements concernés, nom et coordonnées du DPO, conséquences probables, mesures prises ou envisagées (RGPD art. 33.3). Fourniture par phases possible (art. 33.4).
   - **Personnes concernées** : information en cas de risque élevé (RGPD art. 34).
   - **Acquéreur et marques de paiement** : selon les règles contractuelles applicables.
   - **Autorité NIS2 / DORA** le cas échéant pour les entités concernées — à vérifier selon le statut de l'organisation.

## 8. Procédure spécifique — découverte de PAN en un lieu inattendu (PCI 12.10.7)

1. Ne pas déplacer ni modifier les données ; documenter le lieu, le volume, le format.
2. Alerter immédiatement l'équipe IR et le correspondant PCI.
3. Déterminer l'origine (journaux, flux, applications) et évaluer l'exposition.
4. Supprimer ou sécuriser les données conformément à la politique de conservation (Req 3.2) après capture des preuves.
5. Mettre à jour les schémas de flux de données (Req 1.2.4) et le périmètre PCI (Req 12.5).

## 9. Documentation et registre des violations (RGPD art. 33.5)

Consigner pour chaque incident : les faits, les effets, les mesures correctives prises, les décisions de qualification (notification ou non et leurs motifs), les délais observés. Ce registre doit permettre à l'autorité de contrôle de vérifier le respect de l'article 33 et sert de preuve d'audit PCI (Req 12.10). Conservation : 12 mois minimum pour les journaux (Req 10.5) ; le registre des violations est conservé pendant la durée nécessaire à la démonstration de conformité.

## 10. Retour d'expérience

- Réunion post-mortem sous 10 jours ouvrés ; causes racines, écarts de procédure, plan d'action.
- **Mise à jour du plan** après l'incident, selon les nouvelles menaces et les leçons apprises (PCI 12.10.6).
- Revue annuelle du plan, alignée sur le test annuel (PCI 12.10.2) et sur l'évaluation régulière de l'efficacité des mesures (RGPD art. 32.1 d).

## 11. Annexes à établir

- A1. Chaîne d'escalade et astreinte (noms, coordonnées, suppléances)
- A2. Modèle de qualification d'incident (PCI / RGPD)
- A3. Modèle de notification CNIL (téléservice de notification de violation de données)
- A4. Contacts acquéreur et marques de paiement
- A5. Registre des violations (format tabulaire)
- A6. Trame d'exercice annuel (tabletop)
- A7. Clauses types de notification d'incident pour les contrats TPSP (PCI 12.8.2 / RGPD art. 33.2)

## Références vérifiées

- RGPD art. 33 (notification d'une violation de données à caractère personnel à l'autorité de contrôle ; délai de 72 heures ; contenu minimal ; fourniture par phases ; registre des violations) — vérifié via connecteur EUR-Lex, version consolidée CELEX 02016R0679-20160504 en vigueur.
- RGPD art. 32 (sécurité du traitement ; capacité de rétablissement après incident ; évaluation régulière de l'efficacité des mesures) — vérifié via connecteur EUR-Lex, même version consolidée.
- PCI DSS v4.0.1, Req 12.10 et sous-exigences — selon la norme PCI DSS v4.0.1 (PCI SSC, juin 2024) ; vérifier le libellé exact sur pcisecuritystandards.org avant citation en évaluation.