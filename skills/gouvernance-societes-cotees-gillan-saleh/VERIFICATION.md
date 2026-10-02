# VERIFICATION.md — Protocole de l'instance vérificatrice

*Version 1 — intégrée au skill v2.0.0 le 2 juillet 2026. Complète le § 8.4 du SKILL.md : la checklist du producteur ne vaut pas vérification. Le prompt prêt à coller du README (« Protocole d'audit de fidélité ») en est la forme opératoire rapide.*

## 1. Objet et principe

Un producteur ne détecte pas de façon fiable ses propres écarts. Ce protocole organise la vérification par une **instance neutre**, dans une **conversation neuve**, sans accès au raisonnement du producteur. Le vérificateur **constate et rend un verdict** ; il ne réécrit pas, n'améliore pas, ne complète pas la production.

## 2. Conditions de neutralité

Le vérificateur reçoit exactement trois choses : (a) la production à vérifier ; (b) les sources citées — PDF du corpus et liens web ; (c) le présent protocole. Rien d'autre : ni le fil de la conversation productrice, ni les intentions, ni les justifications du producteur.

Règles de comportement, non négociables :
- **Zéro charité interprétative.** Toute divergence avec la source est un écart, y compris une divergence « améliorante » (une citation plus précise, plus élégante ou mieux ponctuée que la source reste un écart).
- **Rien n'est exact parce que plausible.** Un fait vraisemblable non retrouvé dans la source est classé NON VÉRIFIABLE, jamais conforme par défaut.
- **Aucune lacune comblée.** Le vérificateur constate les manques ; il ne les répare pas.
- **En cas de doute sur un contrôle : NON VÉRIFIABLE** — jamais conforme par défaut.

## 3. Périmètre de contrôle

**Contrôle intégral (100 %)** : toutes les citations entre guillemets ; tous les chiffres ; toutes les références d'articles de loi et de code ; toutes les URL ; toutes les attributions institutionnelles (AMF / HCGE / ESMA / EFRAG / ANC / IASB / ISSB).

**Sondage** (productions longues, plus d'une dizaine de pages) : les paraphrases — au moins une par section, confrontée à sa source, choisie de préférence là où l'enjeu juridique est le plus fort (statistiques commentées, positions doctrinales, mentions nominatives).

**Hors périmètre** : la pertinence de l'analyse, le style, les choix de structure. Le vérificateur juge la fidélité, pas la qualité.

## 4. Ordre des contrôles

1. **Citations — test binaire de copie.** Chaque citation confrontée caractère par caractère au PDF source, page vérifiée visuellement (rendu de la page, pas seulement la couche texte). Toute divergence — mot substitué, épithète perdu, ponctuation modifiant le sens, coupe non signalée — est un écart.
2. **Chiffres.** Chaque chiffre recompté à la source ; exercice et périmètre confrontés à ceux annoncés dans la production ; si la source liste sans totaliser, vérifier que la production porte la mention de comptage explicite.
3. **Références juridiques.** Chaque article vérifié en vigueur par consultation effective (Légifrance ou base équivalente) ; recodifications contrôlées (l'article cité est-il la numérotation applicable à la date de la production ?) ; abrogations différées signalées.
4. **URL.** Chaque lien testé par consultation effective ; un lien mort, redirigé ou pointant vers un autre contenu que celui annoncé est un écart.
5. **Attributions institutionnelles.** Balayage complet : chaque position attribuée à la bonne institution, avec le bon statut normatif (régulateur / soft law / conseiller technique) ; recherche spécifique des qualifications interdites (« autorité », « régulateur » appliqués au HCGE ou à l'AFEP-MEDEF).
6. **Vocabulaire interprétatif.** Balayage du corps ET des intitulés : adjectifs évaluatifs, verbes et noms de caractérisation (« converge », « trajectoire », « fil conducteur », « dynamique », « saillant », arcs « de X à Y »), qualificatifs non présents dans la source.
7. **Verrous conditionnels** selon le type de production (§ 8.2 du SKILL.md) : frise complète et non caractérisée (Usage 2) ; blocs et sous-thèmes complets, drainage exhaustif du corpus (Usage 3) ; homogénéité exercice/périmètre et passe DEU épuisée (Usage 4) ; vague CSRD identifiée (Bloc J).

## 5. Format du verdict

Pour chaque contrôle, un des trois états :
- **CONFORME**
- **ÉCART** — restitué en vis-à-vis : texte de la production / texte de la source / localisation exacte (document, page)
- **NON VÉRIFIABLE** — source inaccessible ou introuvable ; jamais assimilé à conforme ; le motif d'inaccessibilité est noté

Verdict global, un des trois :
- **LIVRABLE** — zéro écart sur les verrous (§ 8.1 et 8.2) ; les défauts de forme résiduels (§ 8.3) sont listés pour correction.
- **LIVRABLE APRÈS CORRECTIONS** — écarts limités et tous corrigeables sans reprendre le fond ; liste exhaustive jointe ; re-vérification **ciblée** sur les seuls points corrigés.
- **NON LIVRABLE** — au moins un écart de type invention, page fausse, chiffre erroné, attribution institutionnelle erronée ou citation infidèle ; retour au producteur ; la version corrigée repasse une vérification **complète**, pas ciblée.

Aucun écart n'est tranché en silence : tout ce qui a été constaté figure au verdict, même corrigé en cours de route.

## 6. Journal

Le verdict est archivé dans un fichier `audit_[production]_[AAAA-MM-JJ].md` joint à la production, comportant : la date, l'identification de la production vérifiée (titre, version), la liste des sources consultées, le détail des contrôles avec leur état, le verdict global. Une production sans verdict archivé est réputée non vérifiée.
