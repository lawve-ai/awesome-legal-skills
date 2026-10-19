# Skill de conformité PCI DSS — Édition Expertise (v1.7.0)

> Un skill pour les équipes sécurité, conformité, juridiques et ingénierie, couvrant PCI DSS v4.0.1 — de la délimitation du CDE et la sélection du SAQ jusqu'aux analyses d'écarts, la préparation d'audit QSA, la remédiation, et l'articulation avec le droit UE et français de la sécurité des paiements et des données.

## 1. Que fait le skill ?

Le skill fournit un conseil expert en conformité PCI DSS sur l'ensemble du cycle de vie : délimitation du CDE, analyses d'écarts sur les 12 exigences, sélection du SAQ (y compris la révision SAQ A de janvier 2025), guidance d'implémentation des contrôles avec conseils de preuve pour le QSA, génération de politiques et feuilles de route de remédiation. Il vérifie également les références juridiques UE et françaises (DSP2, RGPD, NIS2, DORA) via deux connecteurs MCP dédiés.

## 2. Couverture normative

- **PCI DSS v4.0.1** (juin 2024) — seule version active depuis le 31 décembre 2024
- Toutes les exigences future-dated de v4.0, obligatoires depuis le 31 mars 2025
- **Révisions SAQ r1**, dont le SAQ A r1 (janvier 2025, applicable au 1er avril 2025) avec le critère d'éligibilité « attaques par scripts » clarifié par la FAQ 1588 du PCI SSC
- Veille versionnelle : RFC sur v4.0.1 (juin–juillet 2026) ; v5.0 préliminaire attendue fin 2026 — sans impact sur les évaluations en cours

## 3. Publics visés

RSSI et responsables sécurité · Analystes conformité et équipes GRC · DPO et conseils juridiques · Développeurs et ingénieurs de systèmes de paiement · Architectes · Marchands niveaux 2–4 remplissant leur SAQ annuel · Prestataires gérant la due diligence TPSP

## 4. Vérification juridique via connecteurs MCP

| Connecteur | Périmètre | Sources vérifiées |
|-----------|-----------|------------------|
| **LibreJustice** (national, France) | Codes consolidés français, jurisprudence toutes juridictions, décisions CNIL et CJUE/CE | Légifrance |
| **EUR-Lex** (européen, UE) | Règlements, directives, textes consolidés UE | Journal officiel de l'UE |

Règle anti-hallucination : aucune référence juridique UE ou française n'est citée sans vérification préalable via le connecteur pertinent et un lien traçable ; les références non vérifiées sont marquées **[NON VÉRIFIÉ]**.

## 5. Cas d'usage courants

| Cas d'usage | Exemple de prompt |
|----------|---------------|
| Délimitation du CDE | « Aide-moi à délimiter notre CDE pour une plateforme e-commerce cloud utilisant Stripe. » |
| Sélection de SAQ | « Nous sommes un marchand niveau 3 ; les clients paient via un iframe intégré à notre page. SAQ A ou A-EP ? » (→ appliquer le critère SAQ A r1, FAQ 1588) |
| Analyse d'écarts | « Mène une analyse d'écarts PCI DSS v4.0.1. Nous sommes un marchand SAQ D… » |
| Changements v4.0 | « Qu'est-ce qui est devenu obligatoire en mars 2025 ? » |
| Guidance MFA | « Que signifie la Req 8.4.2 pour le personnel interne accédant aux systèmes du CDE ? » |
| Scripts de pages de paiement | « Comment nous conformer aux Req 6.4.3 et 11.6.1 ? » |
| Génération de politique | « Rédige un plan de réponse aux incidents aligné sur la Req 12.10 PCI DSS et l'art. 33 RGPD. » (→ vérifier l'art. 33 RGPD via EUR-Lex) |
| Articulation juridique | « Comment DSP2 (ASC) et la Req 8 PCI DSS s'articulent-elles ? » (→ vérifier DSP2 via EUR-Lex ; transposition française via LibreJustice) |
| Gestion des TPSP | « Que requiert PCI DSS pour la gestion des prestataires tiers ? » |

## 6. Détails d'implémentation

```
pci-compliance/
├── SKILL.md                           # Logique principale, flux de travail, règles MCP
├── README.md
└── references/
    ├── pci-dss-requirements.md        # 12 exigences : sous-exigences, preuves, écarts
    ├── pci-dss-saq-guide.md           # Arbre SAQ dont critère SAQ A r1, ROC/AOC/ASV
    └── pci-dss-v4-changes.md          # Journal v3.2.1 → v4.0/4.0.1, veille v5.0
```

**Phrases déclencheuses :** PCI DSS · conformité PCI · carte de paiement · données de titulaires · CDE · SAQ (A, A-EP, B, B-IP, C, C-VT, P2PE, D) · ROC · AOC · QSA · scan ASV · PAN · SAD · tokenisation · P2PE · Exigence 1–12 · niveau marchand · prestataire · segmentation · page de paiement · e-skimming · Magecart · TPSP · gestion des clés · DSP2 · PSD2 · RGPD · NIS2 · DORA

## 7. Auteur

**Skill conçu et maintenu par :** EL OUERTANI FAOUZI
**Contact :** faouzi.elouertani@gmail.com
**Version du skill :** 1.7.0 (Édition Expertise — corrigée, auditée, avec connecteurs MCP)
**Dernière vérification :** 5 octobre 2026
**Couverture normative :** PCI DSS v4.0.1 (juin 2024) ; révisions SAQ r1 ; DSP2/PSD2, RGPD, NIS2, DORA via les connecteurs MCP EUR-Lex et LibreJustice

## 8. Avertissement

Guidage d'information fondé sur des normes publiquement disponibles ; ne constitue pas un avis juridique, d'audit ou de conformité professionnelle. La validation formelle requiert un QSA ou un ISA. Vérifier auprès des sources officielles : pcisecuritystandards.org, eur-lex.europa.eu, legifrance.gouv.fr.
