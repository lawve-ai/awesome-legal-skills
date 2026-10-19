# Checklist pré-livraison — anti-hallucination

<!-- NOYAU-ANTIHALLUCINATION v4 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills : toute modification doit être répercutée à l'identique dans l'autre (script sync-noyau.sh). -->

## Sommaire

1. Objet et moment
2. Canaux de vérification
3. Journal de références et tableau (document séparé)
4. Les cinq étapes
5. Vérificateur indépendant
6. Priorisation des livrables volumineux
7. Formule de clôture
8. Conduite à tenir en cas d'échec
9. Exemples

## 1. Objet et moment

La checklist est le dernier filtre avant la remise de tout livrable contenant une référence jurisprudentielle, normative ou doctrinale — corrigé de cas pratique comme ouvrage, consultation brève comme mémoire. Elle vise deux risques :

1. la référence **inventée** (numéro de pourvoi, d'article, pagination doctrinale fictifs) ;
2. la référence **mal attribuée** : réellement trouvée par un outil dans la session, mais dont le contenu ne soutient pas l'assertion qu'on lui fait porter. C'est le risque le plus insidieux, parce que la traçabilité formelle donne une fausse assurance.

Elle s'exécute **après** la rédaction et **avant** la remise, et prend la forme d'un **tableau** remis dans un **document séparé** (cf. § 3). Elle n'est jamais déclarée accomplie si elle ne l'a pas été.

## 2. Canaux de vérification

Légifrance oppose un challenge anti-bot Cloudflare à toute requête HTTP automatisée : la vérification des références françaises passe donc **normalement** par les connecteurs, qui ne sont pas concernés par ce blocage et qui renvoient en outre l'état juridique et les dates de vigueur.

| Référence | Canal nominal | Complément |
|---|---|---|
| Identifiant Légifrance (LEGIARTI, JURITEXT, CETATEXT, CONSTEXT, JUFITEXT, JORFTEXT, JORFARTI, LEGITEXT, CNILTEXT, KALITEXT) | **OpenLegi** — outil indiqué par `python3 scripts/verify_links.py --extract-ids --from-file urls.json` | `LibreJustice:get_decision` / `LibreJustice:get_norm` pour lire le texte intégral, le sort en voie de recours et la rédaction à une date donnée |
| Décision non diffusée sur Légifrance (fond, CNDA) | `LibreJustice:get_decision` sur l'URL `librejustice.fr/decision/…` | — |
| HUDOC, Curia, EUR-Lex, conseil-constitutionnel.fr | `python3 scripts/verify_links.py --from-file urls.json --check-content` (requête HTTP, opérationnelle pour ces domaines) | LibreJustice (`CEDH`, `CJUE`), LegalDataHunter |
| Doctrine | identifiant DOI / HAL / URL de base reconnue, résolu (`scripts/doctrine_search.py --doi …`, fiche HAL, page de la base) | — |

`python3 scripts/verify_links.py --preflight` reste disponible comme diagnostic : exit 4 (anti-bot Légifrance) est le cas attendu ; exit 0 permettrait en sus une vérification HTTP du contenu Légifrance ; exit 2 (domaines non autorisés dans l'espace de travail) ou 3 (erreur réseau) n'affectent que le complément HTTP, jamais le canal nominal. Inutile d'afficher un message à l'utilisateur pour exit 4 ; pour exit 2, une phrase suffit si HUDOC, Curia ou EUR-Lex sont concernés.

Sans espace de travail (cas résiduel) : appeler directement OpenLegi et LibreJustice pour chaque référence, sans les scripts.

## 3. Journal de références et tableau (document séparé)

**Journal.** Alimenté **au moment de chaque appel d'outil** qui produit une référence destinée à la citation, pendant que la réponse est sous les yeux :

```bash
python3 scripts/reference_journal.py add --journal verification/journal-references.ndjson \
  --ref "art. 1242 al. 1er C. civ." --tool "OpenLegi:rechercher_code" --id "LEGIARTI<identifiant lu dans la réponse>" \
  --url "<lien Légifrance lu dans la réponse>" \
  --excerpt "On est responsable [...] des choses que l'on a sous sa garde." \
  --assertion "fonde le principe de la responsabilité du fait des choses" --kind texte
```

Le tableau est ensuite **généré depuis le journal**, jamais reconstitué de mémoire. À défaut de journal (oubli), le reconstituer en rouvrant les sources — jamais de mémoire. Emplacement du journal : cf. `environnement-et-livrables.md` § 2.

**Verdicts.** `python3 scripts/reference_journal.py mark --journal … --index N --supports oui|non|reformulation|retiree [--independent oui|non] [--note "…"]`. `retiree` marque une référence supprimée ou remplacée dans le livrable (la substitution fait l'objet d'une nouvelle entrée). `--independent` ne se renseigne que pour une ligne effectivement contrôlée par un vérificateur indépendant (`--independent aucun` efface un verdict porté par erreur).

**Complétude.** `python3 scripts/reference_journal.py check --journal …` : exit 0 seulement si aucune entrée n'est incomplète, non confrontée ou en échec.

**Document séparé.** `python3 scripts/reference_journal.py table --journal … --livrable "[titre]" --mode "[canal]" --out [AAAA-MM-JJ]-verification-[sujet].md`, remis à l'utilisateur **avec** le livrable, systématiquement (cf. `environnement-et-livrables.md` § 4).

**Colonnes** : # ; citation telle qu'écrite ; outil + identifiant (+ URL) ; extrait textuel pertinent retourné par l'outil ; voix énonciative (cassation) ; soutient l'assertion ? ; contrôle indépendant ; observations.

**Une ligne par citation effective** : une référence citée à trois endroits pour fonder trois propositions distinctes appelle trois confrontations (sous réserve de la priorisation du § 6).

## 4. Les cinq étapes

### Étape 1 — Inventorier toutes les références

Jurisprudence (juridiction, date, numéro, lien) ; textes normatifs (texte, article, version applicable, lien) ; doctrine (auteur, titre, support, année, identifiant vérifiable). L'inventaire est exhaustif, arrêts de principe et articles « ultra-classiques » compris : la familiarité est précisément l'endroit où l'hallucination se loge. Il comprend aussi les **mentions accessoires** porteuses d'un numéro ou d'un lien (arrêts « jumeaux » du même jour, décisions citées « dans le même sens ») : chacune figure au journal, avec son propre identifiant lu dans une réponse d'outil — jamais déduit par analogie avec un identifiant voisin. Pour un document existant, `python3 scripts/extract_references.py --file [livrable]` pré-remplit l'inventaire et la localisation.

### Étape 2 — Traçabilité

Rattacher chaque référence à l'appel d'outil qui l'a produite dans la session (colonne « outil + identifiant »). Une référence non rattachable est **présumée hallucinée** : exécuter la recherche manquante, ou supprimer, ou convertir en formulation impersonnelle.

### Étape 3 — Concordance du contenu (content-matching)

1. **Lire le contenu réel** : motifs et dispositif (`LibreJustice:get_decision`, fiche OpenLegi), alinéa exact de l'article (`LibreJustice:get_norm`, `OpenLegi:rechercher_code`), propos effectif de l'auteur. Un aperçu LibreJustice (`aiSummary`, `snippet`) **ne vaut pas lecture** : une colonne « extrait » renseignée depuis un aperçu vaut « non ».
2. **Reporter l'extrait** décisif.
3. **Confronter** l'extrait à l'assertion : oui / non / reformulation.
4. **Cassation** : l'extrait présenté comme position de la Cour doit provenir de la voix de la Cour (`passage_voix_cour`, `passage_visas`, `passage_chapeau`), non des motifs de la cour d'appel ni des moyens.
5. **Sort en voie de recours** : une décision infirmée (`appellateFate: INFIRMATION`) ne peut être invoquée comme état du droit ; l'absence de mention ne prouve pas l'absence de recours.
6. **Doctrine** : l'identifiant résout vers la référence annoncée, et la thèse attribuée correspond au propos réel de l'auteur.

Toute ligne « non » reçoit l'une des trois issues : (i) changer de référence ; (ii) reformuler la proposition pour qu'elle corresponde au contenu réel ; (iii) formulation impersonnelle, sans numéro.

### Étape 4 — Lien officiel ou identifiant vérifiable

Lien Légifrance pour toute référence française, **extrait de la réponse d'un outil** (jamais reconstruit), selon les patterns JURITEXT, CETATEXT, CONSTEXT, JUFITEXT, JORFTEXT, JORFARTI, LEGIARTI, LEGITEXT, CNILTEXT, KALITEXT. Pour une décision non diffusée sur Légifrance, lien `librejustice.fr/decision/…` après tentative effective de recherche OpenLegi par numéro. HUDOC, Curia, EUR-Lex pour les sources européennes. DOI, HAL ou URL de base reconnue pour la doctrine. Vérification selon le § 2.

### Étape 5 — Rédaction applicable

Pour chaque texte normatif : rédaction en vigueur **à la date pertinente** — date des faits (cas pratique, consultation rétrospective, commentaire d'arrêt), date du jour (droit positif, consultation prospective). `LibreJustice:get_norm` avec `date` donne la version applicable et la chronologie des versions ; les métadonnées OpenLegi donnent l'état juridique. Mentionner la version citée lorsque le texte a été récemment modifié.

## 5. Vérificateur indépendant

Lorsqu'un outil de sous-agent est disponible, l'étape 3 est doublée par un vérificateur qui n'a pas rédigé le livrable (protocole : `environnement-et-livrables.md` § 5). Son verdict figure dans la colonne « contrôle indépendant » ; un « non » bloque la clôture. À défaut de sous-agent, l'en-tête du tableau porte « contrôle non indépendant ».

## 6. Priorisation des livrables volumineux

Pour un livrable court (corrigé, fiche de TD, consultation brève) : une ligne par occurrence. Pour un livrable comportant des dizaines de citations (cours, ouvrage, mémoire, contre-argumentaire dense) :

- **P1** — référence fondant une majeure, citée en introduction ou en conclusion, ou répétée plus de trois fois : contrôle à chaque occurrence ;
- **P2** — référence illustrative citée une à trois fois : contrôle unique à la référence ;
- **P3** — référence en bibliographie seule : contrôle d'existence et d'identifiant.

## 7. Formule de clôture

Lorsque `reference_journal.py check` renvoie 0 (ou, sans espace de travail, lorsque toutes les lignes sont à « oui », « reformulation » ou « retirée »), prononcer :

> « Tableau de vérification produit ; X lignes contrôlées ; Y reformulations effectuées ; aucune référence non tracée ne subsiste. La livraison est autorisée. »

La formule atteste l'existence du tableau ; elle ne le remplace pas. Formule sans tableau, ou tableau comportant une ligne ouverte ou en échec : la livraison n'est pas déclarée conforme.

## 8. Conduite à tenir en cas d'échec

Trois issues, et trois seulement : **vérification tardive réussie** (la recherche confirme la référence et sa concordance : conserver) ; **suppression** (avec, le cas échéant, formulation impersonnelle) ; **mention « à vérifier »** dans le livrable et le tableau — cette dernière voie seulement si l'utilisateur accepte de recevoir des références non vérifiées. Livrer malgré une ligne en échec est exclu.

Terminologie : une référence est « non trouvée », « non vérifiée » ou « à vérifier » — jamais « fausse » ni « inexistante » sur la seule foi d'une recherche infructueuse.

## 9. Exemples

**A — Passée.** Corrigé de responsabilité du fait des choses : art. 1242 al. 1er C. civ. (`OpenLegi:rechercher_code`, identifiant LEGIARTI… de la version applicable, extrait « On est responsable […] des choses que l'on a sous sa garde », oui) ; Cass. ch. réunies, 13 févr. 1930, *Jand'heur* (`OpenLegi:rechercher_jurisprudence_judiciaire`, JURITEXT…, extrait sur la présomption qui ne cède que devant la cause étrangère, oui). Formule prononcée : 2 lignes, 0 reformulation.

**B — Défaut de traçabilité.** « Cass. civ. 2e, 8 juill. 2004, n° 03-12.244 » n'est rattaché à aucun appel d'outil. Recherche OpenLegi par numéro (`champ: "NUM_AFFAIRE"`, `type_recherche: "EXACTE"`) : l'arrêt porte sur un administrateur judiciaire, sans rapport avec la garde. Issue (iii) : « la jurisprudence constante de la deuxième chambre civile retient que la garde implique une maîtrise effective de la chose ». Ligne initiale marquée `retiree`.

**C — Mauvaise attribution.** « conduite d'un engin sciemment débridé en violation de l'article R. 412-43-3 du Code de la route » : l'appel d'outil existe, mais l'article fixe l'âge minimum de quatorze ans et le port d'un équipement rétro-réfléchissant la nuit ; il ne traite pas du débridage. Issue (i) : l'art. R. 311-1, 6.15, C. route fixe la vitesse maximale par construction des EDPM à 25 km/h. Nouvelle ligne à « oui », ancienne à `retiree`. Seule l'étape 3 prévient ce type d'erreur.
