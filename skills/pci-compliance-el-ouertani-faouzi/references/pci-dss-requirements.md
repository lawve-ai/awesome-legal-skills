# PCI DSS v4.0.1 — Les 12 exigences (synthèse pédagogique)

> **Avertissement :** ce fichier est une synthèse pédagogique. Avant de citer une exigence en évaluation, vérifier le libellé exact dans la norme officielle PCI DSS v4.0.1 (pcisecuritystandards.org). La numérotation suit la structure officielle v4.0.1, notamment pour les Req 8 et 12.

## OBJECTIF 1 : Construire et maintenir un réseau et des systèmes sécurisés

### Exigence 1 — Contrôles de sécurité réseau (NSC)
Les NSC (pare-feux, routeurs, groupes de sécurité cloud) préviennent tout accès non autorisé vers/depuis le CDE.

Sous-exigences clés : 1.1 (politiques) · 1.2.x (standards de configuration, contrôle des changements, schémas réseau et de flux de données, ports/services documentés, revue des configurations NSC tous les 6 mois) · 1.3.x (restriction du trafic entrant/sortant, séparation sans fil) · 1.4.x (inspection réseaux de confiance/non confiance, anti-usurpation, pas de route directe vers le CDE, non-divulgation des IP internes) · 1.5.x (gestion du risque de connectivité des appareils).

**Écarts fréquents :** règles de pare-feu périmées ; absence de filtrage en sortie ; réseau à plat ; sans fil non séparé du CDE.

### Exigence 2 — Configurations sécurisées
Éliminer les paramètres constructeur et services inutiles : 2.1 (processus) · 2.2.x (standards de durcissement, comptes par défaut, fonctions minimales, justification des protocoles non sécurisés, chiffrement des accès administratifs non console) · 2.3.x (sans fil : WPA2-Entreprise/WPA3, rotation des clés au départ du personnel).

**Écarts fréquents :** mots de passe constructeur ; Telnet/FTP encore actifs ; absence de standards de durcissement documentés.

## OBJECTIF 2 : Protéger les données de compte

### Exigence 3 — Protéger les données de compte stockées
Minimiser le stockage ; ne jamais stocker de SAD après autorisation. 3.1–3.2 (processus, minimisation, conservation) · 3.3/3.3.1 (pas de SAD post-autorisation) · 3.3.2/3.3.3 (chiffrement des SAD pré-autorisation et gestion des clés associées — émetteurs et services d'émission) · 3.4–3.5 (PAN illisible partout où il est stocké : chiffrement, troncature, hachage, tokenisation) · 3.6–3.7 (cycle de vie complet des clés : 3.7.1 politiques, 3.7.2 stockage sécurisé, 3.7.3 moins de dépositaires possible, 3.7.4 retrait, 3.7.5 compromission, 3.7.6 connaissance scindée/double contrôle, 3.7.7 pas de substitution informelle, 3.7.8 reconnaissance des dépositaires, 3.7.9 KMS du fournisseur cloud).

**Écarts fréquents :** CVV stocké ; PAN dans les journaux ; absence de rotation des clés ; clés stockées à côté des données chiffrées.

### Exigence 4 — Protéger les CHD pendant la transmission
4.1 (processus) · 4.2.1 (cryptographie forte sur les réseaux publics ouverts — TLS 1.2+ ; pas de SSL, TLS 1.0/1.1) · 4.2.1.1 (inventaire des clés et certificats de confiance) · 4.2.1.2 (sans fil : cryptographie forte pour le PAN) · 4.2.2 (pas de PAN par messagerie non protégée).

**Écarts fréquents :** TLS ancien ; certificats expirés ; PAN par courriel en clair.

## OBJECTIF 3 : Maintenir un programme de gestion des vulnérabilités

### Exigence 5 — Protéger contre les logiciels malveillants
5.1–5.2.x (déploiement sur tous les composants applicables) · 5.3.x (définitions à jour, analyses périodiques et en temps réel, analyse des supports amovibles — 5.3.3, journaux, non désactivable par les utilisateurs) · 5.4/5.4.1 (**solution technique automatisée anti-hameçonnage** : passerelle de messagerie, filtrage DNS, SPF/DKIM/DMARC).

**Écarts fréquents :** Linux/Unix non couverts ; antivirus désactivable ; pas de protection anti-hameçonnage.

### Exigence 6 — Développer et maintenir des systèmes et logiciels sécurisés
6.1–6.3.x (gestion des vulnérabilités avec priorisation, inventaire logiciel / SBOM — 6.3.2) · 6.4.x (applications web publiques : WAF — 6.4.1/6.4.2, **gestion des scripts de pages de paiement — 6.4.3**) · 6.5.x (gestion des changements, séparation des environnements, pas de PAN réels en test).

**Écarts fréquents :** pas de SDLC ; PAN réels en test ; WAF en mode détection seule ; scripts non inventoriés.

## OBJECTIF 4 : Mettre en œuvre de fortes mesures de contrôle d'accès

### Exigence 7 — Restreindre l'accès selon le besoin d'en connaître
7.1 (processus) · 7.2.x (moindre privilège, attribution par rôle, approbation des accès privilégiés, **revues d'accès tous les 6 mois — 7.2.4**, gestion des comptes applicatifs/système — 7.2.5, accès restreint aux bases CHD) · 7.3.x (système de contrôle d'accès : application de la moindre privilège, tenu à jour).

**Écarts fréquents :** comptes partagés ; pas de recertification ; comptes de service sur-privilégiés.

### Exigence 8 — Identifier les utilisateurs et authentifier les accès
8.1 (processus) · 8.2.x (identifiants uniques, exceptions encadrées pour comptes partagés, MFA pour comptes tiers — 8.2.3, cycle de vie des identités, révocation immédiate au départ, désactivation à 90 jours d'inactivité, gestion des comptes de service, expiration de session à 15 minutes) · 8.3.x (politique de mots de passe : **minimum 12 caractères — 8.3.5** ; **rotation tous les 90 jours uniquement pour les comptes NON protégés par MFA — 8.3.6** ; historique, verrouillage, information des utilisateurs) · 8.4 (**MFA pour tout accès au CDE — 8.4.2, y compris les utilisateurs du réseau interne** ; 8.4.1 admin non console) · 8.5 (prévention de la fraude à la MFA) · 8.6 (comptes applicatifs/système : pas de mots de passe en dur — 8.6.2).

**Écarts fréquents :** comptes admin partagés ; pas de MFA pour l'accès interne au CDE ; identifiants codés en dur.

### Exigence 9 — Restreindre l'accès physique
9.1–9.3.x (contrôles d'accès aux locaux, accès individuel, gestion des visiteurs, protection des points d'accès sans fil et des prises publiques) · 9.4.x (supports : stockage sécurisé, classification, distribution tracée, destruction) · 9.5.x (inspection des terminaux POI contre l'altération).

**Écarts fréquents :** pas de registre des visiteurs ; terminaux POI non inspectés ; destruction non documentée.

## OBJECTIF 5 : Surveiller et tester régulièrement les réseaux

### Exigence 10 — Journaliser et surveiller les accès
10.1–10.3.x (journalisation des accès utilisateurs, actions admin, audit de l'audit, échecs d'authentification, protection et centralisation des journaux) · 10.4 (**revue automatisée des journaux — 10.4.1.1** ; revue quotidienne ; traitement des exceptions) · 10.5 (conservation 12 mois, dont 3 mois immédiatement disponibles) · 10.6 (synchronisation horaire) · 10.7.x (**détection, signalement et réponse aux défaillances des contrôles critiques — 10.7.2/10.7.3**).

**Écarts fréquents :** pas de SIEM ; conservation <12 mois ; revue manuelle seule.

### Exigence 11 — Tester régulièrement la sécurité
11.2.x (gestion des points d'accès sans fil, réconciliation trimestrielle) · 11.3.x (scans internes trimestriels ; **scans externes ASV trimestriels — 11.3.2** ; remédiation et nouveau scan) · 11.4.x (tests d'intrusion internes et externes annuels ; **test de segmentation tous les 6 mois — 11.4.5** ; support des prestataires multi-clients — 11.4.7) · 11.5.x (IDS/IPS, détection de changements) · 11.6 (**détection de modification/altération des pages de paiement — 11.6.1**, en-têtes HTTP et contenu).

**Écarts fréquents :** scans ASV non concluants ; segmentation non testée ; pas de surveillance des pages de paiement.

## OBJECTIF 6 : Maintenir une politique de sécurité de l'information

### Exigence 12 — Politiques et programmes organisationnels
12.1 (politique globale) · 12.2 (applicabilité aux tiers) · 12.3.1 (**TRA pour chaque exigence en approche personnalisée**) · 12.3.2 (**TRA pour les éléments à fréquence flexible de l'approche définie**) · 12.3.3 (**revue annuelle des suites cryptographiques**) · 12.3.4 (**revue annuelle des technologies**) · 12.4/12.4.2 (conformité suivie ; revues trimestrielles) · 12.5.x (documentation du périmètre, inventaire des composants, vérification annuelle et après changement majeur) · 12.6.x (sensibilisation, revue annuelle, attestations annuelles) · 12.7 (filtrage du personnel) · 12.8.x (registre TPSP, accords écrits, due diligence, suivi annuel de conformité, matrice de responsabilités) · 12.9.x (support des TPSP aux clients, confirmation de responsabilités) · 12.10.x (réponse aux incidents : plan, test annuel, astreinte 24/7, formation annuelle du personnel IR — 12.10.4.1, alertes de supervision, mises à jour selon les menaces, procédure de découverte de PAN inattendus — 12.10.7).

**Écarts fréquents :** politique non revue annuellement ; pas de registre TPSP ; plan IR jamais testé ; pas de processus TRA.

**Renvois réglementaires (vérifier via les connecteurs MCP avant citation) :** RGPD art. 32 (mesures de sécurité) — EUR-Lex ; RGPD art. 33 (notification sous 72 h) en cohérence avec la Req 12.10 ; NIS2 notification d'incidents pour les entités concernées — EUR-Lex ; DSP2 art. 97 (authentification forte) — EUR-Lex ; transposition française et loi n° 78-17 — LibreJustice/Légifrance.
