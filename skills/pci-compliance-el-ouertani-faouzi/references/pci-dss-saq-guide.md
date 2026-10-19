# PCI DSS v4.0.1 — Guide de sélection des SAQ

> Les effectifs de contrôles sont des ordres de grandeur indicatifs ; la référence faisant autorité est le SAQ en vigueur sur pcisecuritystandards.org. Les marchands niveau 1 et les prestataires niveau 1 ne sont pas éligibles aux SAQ — ROC requis.

## Arbre de décision

**Étape 1 — Marchand niveau 1 ou prestataire niveau 1 ?** Oui → ROC. Non → Étape 2.
**Étape 2 — Prestataire (non marchand) ?** Oui → SAQ D pour prestataires. Non → Étape 3.
**Étape 3 — Carte présente uniquement ?**
- Machines à empreintes ou terminaux numérotation isolés uniquement → **SAQ B**
- Terminaux PTS POI autonomes connectés en IP uniquement → **SAQ B-IP**
- Solution P2PE validée PCI uniquement → **SAQ P2PE**
- Terminal virtuel web sur appareil isolé (pas de carte présente par ce canal) → **SAQ C-VT**
- Application de paiement connectée à Internet, segmentée → **SAQ C**
- Tout autre scénario carte présente → **SAQ D marchands**

**Étape 4 — Carte absente (e-commerce/MOTO) uniquement ?**
- **Redirection complète** (côté serveur ou lien statique, aucun script de paiement côté marchand ; toutes les fonctions CHD externalisées à des tiers conformes PCI ; aucune CHD électronique conservée) → **SAQ A**
- **Formulaire de paiement intégré (iframe) hébergé sur la page du marchand** → **SAQ A**, sous réserve du **critère d'éligibilité r1** (voir ci-dessous) ; si le critère ne peut être satisfait → **SAQ A-EP**
- Le marchand contrôle la page hébergeant le widget/les scripts de paiement ou influence la redirection → **SAQ A-EP**
- MOTO uniquement avec terminal virtuel web sur appareil isolé → **SAQ C-VT**
- Tout autre scénario CNP → **SAQ D marchands**

## Critère d'éligibilité SAQ A r1 (révision janvier 2025, applicable au 1er avril 2025)

Le SAQ A révisé ne contient plus les exigences 6.4.3, 11.6.1 ni la TRA 12.3.1 qui soutenait 11.6.1. À leur place, les marchands dont la page héberge une page ou un formulaire de paiement intégré du prestataire (par ex. iframe) doivent confirmer que leur site n'est pas susceptible d'attaques par scripts affectant leurs systèmes e-commerce. Conformément à la **FAQ 1588 du PCI SSC**, la confirmation s'apporte soit :
1. en mettant en œuvre des techniques équivalentes aux Req 6.4.3 et 11.6.1 sur la page hébergeant l'iframe ; ou
2. en obtenant du processeur de paiement conforme PCI DSS la confirmation que son formulaire intégré inclut ces protections lorsqu'il est implémenté selon ses instructions.

Les avis des QSA divergent sur la portée (page de l'iframe seulement, ou site entier) — documenter l'analyse et confirmer avec l'évaluateur/l'acquéreur. Les marchands en redirection complète sont hors de ce critère.

## Types de SAQ — Référence

### SAQ A (~22 contrôles, indicatif)
CNP entièrement externalisé (e-commerce et/ou MOTO) ; pas de carte présente ; aucune CHD électronique stockée, traitée ou transmise par le marchand. Marchands en iframe : critère r1 applicable.

### SAQ A-EP (~191 contrôles, indicatif)
Marchands e-commerce contrôlant la page hébergeant la capture tierce (widgets, iframes avec scripts contrôlés par le marchand, maîtrise de la redirection). 6.4.3 (inventaire des scripts, autorisation, intégrité — CSP/SRI ou équivalent) et 11.6.1 (détection d'altération des en-têtes HTTP et du contenu) s'appliquent intégralement.

### SAQ B (~41) — machines à empreintes ou terminaux numérotation isolés ; pas d'e-commerce.
### SAQ B-IP (~83) — terminaux PTS POI listés PCI, autonomes, connectés en IP, isolés ; pas d'e-commerce.
### SAQ C (~160) — applications de paiement connectées à Internet, segmentées des autres systèmes ; pas d'e-commerce.
### SAQ C-VT (~90) — terminal virtuel web sur appareil isolé et dédié ; pas d'e-commerce.
### SAQ P2PE (~33) — solution P2PE validée et listée PCI uniquement ; pas d'e-commerce ; aucun accès aux CHD en clair. Réduction majeure du périmètre.
### SAQ D marchands (~340) / SAQ D prestataires (~340) — tous les autres cas ; les 12 exigences. Les prestataires font face à des attentes supplémentaires autour des Req 12.8/12.9 (TPSP) et 3.3.2 (SAD pré-autorisation).

## ROC, AOC, ASV, QSA/ISA

**ROC** — marchands niveau 1 (>6 M transactions Visa/MC par an, ou tout marchand victime d'une compromission) et prestataires niveau 1 (>300 000 transactions/an ou désignés par une marque). Procédure : engager un QSA listé PCI SSC → évaluation sur site → gabarit ROC v4.0.1 → AOC signé par le QSA et un dirigeant → transmission à l'acquéreur/à la marque.

**AOC** — déclaration d'état de conformité, établie avec le ROC (niveau 1) ou le SAQ (niveaux 2–4), signée annuellement par le responsable (et le QSA le cas échéant) ; versions marchand et prestataire distinctes.

**Scans ASV** — scans externes de vulnérabilités trimestriels par un ASV approuvé PCI SSC, pour tous les marchands et prestataires ; scan concluant requis (aucune vulnérabilité grave/critique non résolue conformément au ASV Program Guide) ; conserver les rapports. Les scans internes (11.3.1) peuvent être réalisés par le personnel interne.

**QSA vs ISA** — QSA : société externe approuvée PCI SSC, requise pour le ROC ; ISA : salarié interne certifié PCI SSC, pouvant réaliser des évaluations internes et appuyer la validation SAQ pour les niveaux 2–4 ; un ISA ne remplace pas un QSA pour un ROC de niveau 1.
