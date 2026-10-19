# Guide Themia — données jurimétriques

<!-- NOYAU-JURIMETRIE v2 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills (script sync-noyau.sh). Noms d'outils vérifiés le 27 septembre 2026. -->

## Sommaire

1. Déclenchement et modules
2. Outils : schéma commun
3. Règle de bascule à quatre niveaux
4. Cour de cassation : voix énonciative
5. Séquences-types
6. Interprétation et seuils
7. Restitution

## 1. Déclenchement et modules

Recourir à Themia dès qu'une question appelle des données statistiques, des montants pratiqués, une comparaison entre juridictions, une tendance, ou — pour la Cour de cassation et les juridictions suprêmes — une recherche ciblant **qui parle** dans la décision.

Modules exposés au 27 septembre 2026 (suffixe des outils) : `cassation`, `conseil_etat`, `cedh`, `dommage_corporel`, `travail`, `baux_commerciaux`, `construction`, `concurrence_deloyale`, `rupture_brutale`, `entreprises_difficulte`. La liste n'est pas figée : un module nouveau s'utilise selon le même schéma d'outils. Si le module pertinent est ambigu, le demander à l'utilisateur.

Themia fournit des **statistiques descriptives** : ce qui a été accordé ou jugé, non ce qui doit l'être. Il ne fournit ni texte officiel ni lien Légifrance.

## 2. Outils : schéma commun

Pour un module `<m>` :

| Outil | Fonction |
|---|---|
| `obtenir_guide_<m>` | **référentiel du module servi par le serveur** : champs, erreurs fréquentes, filtres, règles de validation. L'appeler avant la première analyse d'un module, lorsqu'il existe (cassation, conseil_etat, cedh, dommage_corporel, travail, baux_commerciaux au 27/09/2026). |
| `recherche_options_<m>` | appelé **sans `field`** : liste exacte des champs du module ; avec `field` (et `parent` pour les hiérarchies de postes) : valeurs admises et **clés composites** d'indemnités. Ne jamais deviner une clé. |
| `compter_decisions_<m>` | effectif N sous des filtres — orientation avant analyse |
| `statistiques_jurimetriques_<m>` | **outil d'analyse** (remplace l'ancien `analyser_insights_<m>`) : types `metric`, `distribution`, `comparison`, `trend`, `correlation`, `geo` |
| `echantillon_decisions_<m>` | décisions d'exemple (`decision_id`, `themia_url`), 1 à 10, tri optionnel |

Règles de validation communes (le guide du module les précise) : `distribution` / `comparison` / `correlation` / `geo` exigent `breakdown_field` ; `trend` exige `date_histogram_field` et `date_histogram_interval` ; `correlation` exige `secondary_breakdown_field` ; `metric` interdit `breakdown_field`. Agrégation `stats` pour obtenir N, moyenne, quartiles et écart-type ; `series_field: "decision_count"` pour compter.

Filtres : les champs listés par `recherche_options_<m>` (sans `field`), plus les filtres textuels `text` (plein texte) et `passage_text` (par zone de la décision) ; la date se filtre sous la forme décrite par `obtenir_guide_<m>` (par exemple `{"date": {"from": "2023-01-01"}}`), les clés `date_from` / `date_to` étant refusées. `echantillon_decisions_<m>` renvoie au plus 10 décisions par appel, sans pagination : varier le tri (`sort`) ou resserrer les filtres pour couvrir une cohorte plus large.

Les clés d'indemnités varient d'un module à l'autre et évoluent avec le corpus (en dommage corporel, par exemple, `direct_victim_indemnity_events-extra_patrimoniaux_temporaires-SOUFFRANCES_ENDUREES` au 27/09/2026 ; le suffixe `-coefficient` est réservé aux postes d'assistance par tierce personne) : les obtenir par `recherche_options_<m>` (champ d'indemnité, puis `parent`) et les copier telles quelles. Le corpus est annoté en français : un nom de champ anglais échoue.

## 3. Règle de bascule à quatre niveaux

Pour le volet **quantitatif** d'une demande et, en cassation, pour la **recherche par voix** :

1. **Themia disponible → prioritaire.**
2. **Themia indisponible → le signaler une fois**, puis LibreJustice : « Les résultats seraient plus précis avec Themia (app.themia.pro), qui fournit des statistiques agrégées et, pour la Cour de cassation, la segmentation par voix énonciative. Je poursuis avec LibreJustice. » Cohorte par filtres (`seat`, `solution`, `publication`, dates), lecture par `get_decision`. Les effectifs de facettes ne sont pas des statistiques : aucune proportion présentée comme représentative.
3. **Themia et LibreJustice indisponibles → OpenLegi**, même réserve, quantification approximative signalée.
4. **Aucun des trois → le signaler**, répondre avec la recherche web sur sources officielles en explicitant fortement les limites.

Réserve d'articulation : la bascule vaut pour la dimension statistique. **Toute décision citée** dans un livrable reste soumise au noyau anti-hallucination : lecture du texte, content-matching, lien Légifrance extrait d'OpenLegi. Un `themia_url` peut être mentionné en complément, jamais en substitut du lien officiel.

## 4. Cour de cassation : voix énonciative

Le module `cassation` rattache chaque passage à la voix qui l'énonce. Filtres (combinables en ET) : `passage_voix_cour` (motifs propres, dispositif), `passage_visas`, `passage_chapeau` (énoncés de principe), `passage_motifs_ca` (motifs de la cour d'appel), `passage_moyens`, `passage_moyens_annexes` (arguments des parties) ; filtres textuels `text` et `passage_text` (zones : introduction, exposé, moyens, motivations, dispositif). Détail : `obtenir_guide_cassation`.

**Attribution énonciative.** Un extrait n'exprime la position de la Cour que s'il provient de `passage_voix_cour`, `passage_visas` ou `passage_chapeau`. Présenter un extrait de `passage_motifs_ca` ou `passage_moyens` comme la position de la Cour est une hallucination par mauvaise attribution. Indiquer la voix en citant : « la Cour retient… », « la cour d'appel avait jugé… », « le demandeur soutenait… ». En cas de doute, relire la décision intégrale (OpenLegi ou `LibreJustice:get_decision`) avant de citer.

## 5. Séquences-types

- **Orientation** : `recherche_options_<m>` (sans field) → `compter_decisions_<m>` → vérifier N (§ 6).
- **Montant pratiqué** : `metric` avec `series_aggregation: "stats"` sur la clé du poste → `comparison` par juridiction ou ville → `trend` si l'évolution importe.
- **[Ville] contre national** : `metric` sans filtre géographique, puis avec ; tableau P25 / P50 / P75 / N / σ ; écart relatif.
- **Cassation** : `compter_decisions_cassation` → `statistiques_jurimetriques_cassation` (distribution par `chamber`, `solution`, `publication` ; `trend` par `date`) → `echantillon_decisions_cassation` → lecture et lien OpenLegi pour toute décision citée.
- **Questions préalables** (dommage corporel, travail) : regrouper en une seule interaction le périmètre géographique, le fait générateur, la période et les caractéristiques pertinentes de la victime ou du salarié ; ne pas sur-filtrer.

## 6. Interprétation et seuils

| N | Conduite |
|---|---|
| < 5 | ne pas exploiter |
| 5 – 20 | exploitable avec mise en garde ; proposer d'élargir |
| 20 – 50 | exploitable avec prudence |
| > 50 | résultats robustes |

Médiane (P50) : indicateur central le plus robuste ; intervalle P25–P75 : zone de convergence ; écart-type élevé : hétérogénéité à signaler. Données `redacted` : ne pas exploiter ; valeurs `__missing__` : exclure et signaler le taux de complétude s'il est significatif ; valeur `-1` (cotations) : non renseignée.

## 7. Restitution

Périmètre et corpus (N, filtres, précautions) → résultats commentés et tableaux → observations et limites. Mentionner une fois, en tête, le caractère descriptif et non normatif des données. Pour un rapport de jurimétrie complet (cohorte, insights, publication), rediriger vers la skill `rapport-jurimetrie`. Une IA générative seule n'est pas l'outil d'un travail statistique : sans Themia, recommander un outil spécialisé.
