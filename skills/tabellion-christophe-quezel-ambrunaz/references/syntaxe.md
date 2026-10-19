# Les balises tabellion

Ce document peut être remis tel quel à l'utilisateur qui souhaite corriger ou compléter lui-même un modèle balisé.

Une balise s'écrit directement dans le document, dans Word ou LibreOffice, sans mise en forme particulière. Deux familles existent :

- `{{ … }}` désigne une **valeur** à insérer ;
- `[[ … ]]` désigne une **structure** : passage conditionnel, optionnel, alternatif ou répété.

La mise en forme de la balise (gras, italique, police) est reprise par la valeur insérée. Le surlignage posé lors du balisage disparaît dans le document produit.

## Valeurs

Une valeur se désigne par un **chemin** : module, puis rubrique, puis sous-rubrique, séparés par des points, en minuscules et sans accent.

| Balise | Produit |
|---|---|
| `{{bail.loyer.montant}}` | 850 € |
| `{{acte.date_acte}}` | 5 octobre 2026 |
| `{{bail.bailleur.designation_complete}}` | la société ALPHA, société par actions simplifiée au capital de…, représentée par… |
| `{{bail.preneur.designation_courte}}` | Madame Jeanne ESSAI et Monsieur Paul FICTIF |
| `{{local.observations}}` | une rubrique propre à ce modèle |
| `{{calcul.date_fin}}` | un résultat de calcul défini lors de la préparation |

Lorsqu'un rôle compte plusieurs personnes, les valeurs sont énumérées automatiquement : « A, B et C ».

### Rendus

Un rendu se place après une barre verticale. Plusieurs rendus peuvent s'enchaîner : `{{acte.date_acte|lettres|majuscules}}`.

| Type | Rendus | Exemples |
|---|---|---|
| montant | `chiffres` (par défaut), `lettres`, `lettres_puis_chiffres`, `chiffres_puis_lettres` | huit cent cinquante euros (850 €) |
| date | `longue` (par défaut), `courte`, `lettres`, `iso` | 1er octobre 2026 ; 01/10/2026 ; premier octobre deux mille vingt-six |
| nombre entier | `chiffres`, `lettres`, `ordinal`, `ordinal_abrege`, `romain` | trois ; troisième ; 3e ; III |
| durée | `lettres` (par défaut), `chiffres` | trois ans ; 3 ans |
| pourcentage | `chiffres`, `lettres` | 3,5 % ; trois virgule cinq pour cent |
| heure | `courte`, `lettres` | 9 h 30 ; neuf heures trente |
| adresse | `ligne`, `bloc` | sur une ligne, ou ligne à ligne |
| liste fermée | `libelle`, `long` | SAS ; société par actions simplifiée |
| identifiant | `tel_quel`, `groupe` | 000 000 000 |
| toute valeur | `majuscules`, `minuscules`, `initiale_majuscule` | |

Les nombres s'écrivent en lettres selon l'orthographe traditionnelle : quatre-vingts, deux cents, deux cent mille.

### Rôles et accords

Un rôle est une qualité tenue par une ou plusieurs personnes du dossier : `bail.bailleur`, `procedure_civile.defendeur`.

- `{{bail.preneur|qualite}}` : preneur, preneuse, preneurs ou preneuses ;
- `{{bail.preneur|qualite:locataire}}` : locataire ou locataires (variante de libellé) ;
- `{{bail.preneur|accord:né/née/nés/nées}}` : la forme accordée, dans l'ordre masculin singulier / féminin singulier / masculin pluriel / féminin pluriel ;
- `{{bail.preneur|accord:s'engage/s'engagent}}` : deux formes, singulier / pluriel ;
- `{{bail.preneur|nombre|lettres}}` : le nombre de personnes, en lettres.

Une personne morale s'accorde selon son nom générique : « la société X, demanderesse ». Au pluriel, le masculin l'emporte dès qu'une personne de genre masculin figure parmi les personnes.

## Structures

Une structure s'ouvre et se ferme **au même niveau** :

- soit **dans un même paragraphe** : `… payable [[SI bail.loyer.terme = a_echoir]]d'avance[[SINON]]à terme échu[[FIN SI]].` ;
- soit **sur des paragraphes entiers**, la balise occupant seule son paragraphe, au même emplacement (corps du texte, ou même cellule de tableau) ;
- soit **sur des lignes entières d'un tableau**, la balise occupant seule sa ligne.

Un paragraphe entièrement enveloppé, comme `[[OPTION x]]Texte de la clause.[[FIN OPTION]]`, disparaît en entier lorsque l'option est écartée.

### Option : passage à retenir ou à écarter

```
[[OPTION clause_penale "Clause pénale"]]
Article 7 — Clause pénale …
[[FIN OPTION]]
```

L'identifiant `clause_penale` s'écrit sans accent ni espace. Le libellé entre guillemets est celui que voit l'utilisateur du formulaire. La même option peut réapparaître ailleurs, sans libellé : `[[OPTION clause_penale]]…[[FIN OPTION]]`.

### Choix : rédactions alternatives exclusives

```
[[CHOIX duree "Durée du bail"]]
[[CAS trois "Trois ans"]]
Le bail est conclu pour trois ans…
[[CAS six "Six ans"]]
Le bail est conclu pour six ans…
[[FIN CHOIX]]
```

### Condition : passage dépendant des données

```
[[SI bail.preneur EST PLURIEL]]Les preneurs sont tenus solidairement.[[FIN SI]]
[[SI procedure_civile.defendeur EST PERSONNE MORALE]]…[[SINON SI choix.duree = six]]…[[SINON]]…[[FIN SI]]
```

Les conditions s'écrivent avec :

- les comparaisons `=`, `!=`, `<`, `>`, `<=`, `>=` ;
- les opérateurs `ET`, `OU`, `NON` et les parenthèses ;
- les prédicats `EST PLURIEL`, `EST SINGULIER`, `EST FEMININ`, `EST MASCULIN`, `EST PERSONNE MORALE`, `EST PERSONNE PHYSIQUE`, `EST RENSEIGNE`, `EST VIDE`, `EST VRAI`, `EST FAUX` (chacun peut être nié : `EST NON …`) ;
- les références `option.x` et `choix.x`.

`[[SI chemin]]` est vrai lorsque la valeur est renseignée, et qu'elle est différente de « non » et de zéro.

### Répétition

```
[[POUR CHAQUE piece DANS procedure_civile.bordereau_pieces]]
{{piece#rang}}. {{piece.intitule}}, du {{piece.date|courte}}
[[FIN POUR]]
```

La répétition porte sur une liste ou sur un rôle (`[[POUR CHAQUE p DANS bail.preneur]]`). Dans la boucle, quatre indications sont disponibles :

- `piece#rang` : le rang de l'élément, à partir de 1 ;
- `piece#premier` et `piece#dernier` : vrai pour le premier ou le dernier élément ;
- `piece#avant_dernier` : vrai pour l'avant-dernier élément ;
- `piece#nombre` : le nombre total d'éléments.

Elles servent notamment à la ponctuation : `[[SI p#dernier]].[[SINON]] ;[[FIN SI]]`.

Dans une boucle sur un rôle, chaque personne peut porter des mentions qui lui sont propres dans l'acte (attributs de rôle, définis lors de la préparation du modèle) :

```
[[POUR CHAQUE c DANS societes.cedant]]
{{c.designation_complete}}, titulaire de {{c.parts_cedees|lettres}} parts, numéros {{c.numeros}} ;
[[FIN POUR]]
```

Un calcul défini pour chaque élément d'une liste (calcul de ligne) s'emploie de même dans la boucle : `{{calcul.debut}} à {{calcul.fin}}`.

Pour répéter des lignes de tableau, placer `[[POUR CHAQUE …]]` seul dans une ligne, puis les lignes à répéter, puis `[[FIN POUR]]` seul dans une ligne.

## Numérotation et renvois

| Balise | Effet |
|---|---|
| `{{compteur article}}` | numéro suivant de la série « article », dans l'ordre du document produit |
| `{{compteur article ancre=penale}}` | idem, et mémorise ce numéro sous le nom « penale » |
| `{{renvoi penale}}` | reprend le numéro mémorisé, où qu'il se trouve dans le document |

Rendus possibles : `romain`, `romain_minuscule`, `lettre`, `lettre_majuscule`, `lettres`, `ordinal`, `ordinal_abrege`. Lorsqu'un article optionnel est écarté, la numérotation et les renvois se recalculent. Un renvoi vers un article écarté est signalé.

Si le modèle utilise la numérotation automatique de Word ou de LibreOffice, elle se recalcule d'elle-même ; seuls les renvois saisis à la main doivent être balisés.

## Notes

`[[NOTE texte libre]]` laisse une indication dans le modèle balisé. Elle disparaît du document produit.

## Erreurs courantes

- **Balise coupée** par une tabulation, un saut de ligne ou un appel de note : la réécrire d'un seul tenant.
- **Accents dans un chemin** (`{{bail.preneur.prénoms}}`) : les chemins n'en comportent pas.
- **Structure fermée à un autre niveau**, par exemple ouverte dans une phrase et fermée sur un paragraphe seul : elle est refusée.
- **Balise placée dans un champ Word, un contrôle de contenu ou une zone en révision** : la déplacer hors de cet élément.
