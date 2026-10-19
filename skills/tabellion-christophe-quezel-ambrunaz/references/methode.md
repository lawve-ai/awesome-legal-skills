# Méthode de balisage

À lire avant de baliser un modèle. La syntaxe elle-même est exposée dans `syntaxe.md` ; les chemins disponibles sont dans `dictionnaire.md`.

## 1. Plan de balisage

Le plan est un fichier JSON appliqué par `tabellion.py baliser MODELE plan.json SORTIE`. Les paragraphes sont désignés par les codes du relevé (`D12`, `E1`…), qui renvoient toujours au document **d'origine**, quel que soit l'ordre des opérations.

```json
{"operations": [
  {"op": "remplacer", "paragraphe": "D4", "texte": "Monsieur Jean DUPONT", "occurrence": 1,
   "par": "{{procedure_civile.defendeur.designation_courte}}"},
  {"op": "remplacer_partout", "texte": "Monsieur Jean DUPONT", "par": "{{procedure_civile.defendeur.designation_courte}}"},
  {"op": "inserer_avant", "paragraphe": "D10", "texte": "[[SI bail.preneur EST PLURIEL]]"},
  {"op": "inserer_apres", "paragraphe": "D12", "texte": "[[FIN SI]]"},
  {"op": "entourer", "de": "D6", "a": "D7", "ouverture": "[[OPTION mediation \"Médiation préalable\"]]", "fermeture": "[[FIN OPTION]]"},
  {"op": "entourer_lignes", "paragraphe": "D30", "jusqua": "D31",
   "ouverture": "[[POUR CHAQUE x DANS procedure_civile.bordereau_pieces]]", "fermeture": "[[FIN POUR]]"}
]}
```

| Opération | Effet |
|---|---|
| `remplacer` | Remplace l'occurrence n° `occurrence` (1 par défaut) du `texte` dans le paragraphe, même répartie sur plusieurs *runs*. `par` vide : suppression. |
| `remplacer_partout` | Toutes les occurrences, dans toutes les parties. Le nombre d'occurrences est rapporté. |
| `inserer_avant` / `inserer_apres` | Nouveau paragraphe contenant une balise de structure. |
| `entourer` | Deux paragraphes de structure encadrant les paragraphes `de`…`a` (même emplacement). |
| `entourer_lignes` | Deux lignes de structure encadrant les lignes de tableau qui contiennent `paragraphe` et `jusqua`. |

Le `texte` à remplacer doit être recopié **exactement** depuis le relevé, apostrophes et espaces compris. Le signe `⇥` du relevé marque une tabulation ou un saut de ligne, qu'une balise ne peut pas franchir. Dans les cas atypiques (zones de texte, cellules fusionnées), on peut aussi baliser en modifiant directement le XML, puis vérifier par `compiler`.

## 2. Manifeste

```json
{
  "id": "bail-habitation-cabinet",
  "titre": "Bail d'habitation (logement nu)",
  "version": "1",
  "date_gel": "2026-10-05",
  "parametres": {"orthographe_nombres": "traditionnelle", "centimes": "si_non_nuls"},
  "locales": [
    {"id": "avocat", "libelle": "Avocat constitué", "type": "texte", "aide": "…", "exemple": "Maître Claire MODELE"}
  ],
  "calculs": [
    {"id": "date_fin", "libelle": "Date de fin du bail", "type": "date",
     "expression": "veille(ajouter_duree(bail.date_prise_effet, bail.duree))",
     "explication": "Veille du jour anniversaire, après ajout de la durée.",
     "source": "Choix confirmé par l'utilisateur le 5 octobre 2026"}
  ],
  "controles": [
    {"expression": "somme(societes.repartition.nombre_titres) = societes.titres.nombre",
     "message": "La répartition doit couvrir tous les titres", "bloquant": true}
  ],
  "tables": {
    "taux_legal": {"libelle": "Taux de l'intérêt légal", "source": "…", "date_gel": "2026-10-05",
                   "valeurs": {"2026-S2-particulier": 0.0}}
  },
  "aides": {"bail.destination": "Ex. : habitation principale."}
}
```

- `id` est stable, en minuscules et sans accent. Le dossier de l'utilisateur y rattache ses options, ses choix et ses variables locales.
- `centimes` vaut `si_non_nuls` (« 850 € », « 1 234,50 € ») ou `toujours` (« 850,00 € »).
- Les variables `locales` sont réservées aux **valeurs simples** propres au modèle et sans vocation à être réutilisées (une mention de cabinet, une observation). Elles admettent tous les types sauf `groupe`, `liste` et `reference` ; une variable de type `choix` porte ses `valeurs` (`[{"id", "libelle"}]`). Toute donnée réutilisable, structurée ou attachée à une personne relève d'une **extension** (§ 2 bis).
- Tout champ, local ou ajouté, porte un `exemple` manifestement fictif, repris dans les données d'essai.
- Les `calculs` exigent `explication` et `source`, qui sont affichées à l'utilisateur.
- Un `controle` non respecté est affiché ; s'il est `bloquant`, il empêche la génération.
- Une `table` contient des valeurs évolutives figées à `date_gel`. `table("taux_legal", "2026-S2-particulier")` refuse toute clé absente : le formulaire ne calcule jamais avec une valeur périmée. Les valeurs sont vérifiées avec l'utilisateur, sur une source qu'il confirme.

## 2 bis. Extensions du dictionnaire

Le dictionnaire commun est une **trame** : il évite de tout réécrire et assure qu'un même dossier `.json` serve à plusieurs formulaires. Il n'est **jamais bloquant**. Ce qui lui manque pour un modèle s'ajoute dans la rubrique `extensions` du manifeste ; la compilation produit alors le dictionnaire effectif du modèle, intégré au formulaire.

```json
"extensions": {
  "champs": {
    "personne.physique": [
      {"id": "situation_matrimoniale", "libelle": "Situation matrimoniale", "type": "texte", "exemple": "…"},
      {"id": "conjoint", "libelle": "Conjoint", "type": "reference", "cible": "personne", "natures": ["physique"]}],
    "societes.repartition": [{"id": "observations", "libelle": "Observations", "type": "texte", "exemple": "pleine propriété"}]
  },
  "modules": [{"id": "garantie_passif", "libelle": "Garantie de passif",
               "roles": [{"id": "garant", "libelles": {"ms": "garant", "fs": "garante", "mp": "garants", "fp": "garantes"},
                          "cardinalite": "1..n", "natures": ["physique", "morale"]}],
               "champs": [{"id": "plafond", "libelle": "Plafond", "type": "montant", "exemple": {"valeur": 50000, "devise": "EUR"}}]}],
  "roles": {"bail": [{"id": "sous_locataire", "libelles": {…}, "cardinalite": "0..n", "natures": ["physique"]}]},
  "attributs_roles": {"societes.cedant": [
      {"id": "parts_cedees", "libelle": "Nombre de parts cédées", "type": "entier", "exemple": 250},
      {"id": "origine_propriete", "libelle": "Origine de propriété", "type": "texte", "exemple": "…"}]},
  "libelles": {"societes.titres.nombre": {"libelle": "Nombre total de parts sociales"},
               "bail.preneur": {"libelles": {"ms": "locataire", "fs": "locataire", "mp": "locataires", "fp": "locataires"}}}
}
```

| Rubrique | Cible | Usage |
|---|---|---|
| `champs` | `personne`, `personne.physique`, `personne.morale`, une autre entité (`bien_immobilier`…), un module (`bail`), ou un groupe ou une liste existants (`societes.repartition`, `bail.loyer`) | Donnée qui manque à la trame |
| `modules` | — | Matière ou opération absente du dictionnaire, avec ses rôles et ses champs |
| `roles` | un module existant | Partie supplémentaire |
| `attributs_roles` | `module.role` | Donnée propre à une personne **en tant qu'elle tient ce rôle dans l'acte** |
| `libelles` | chemin d'un champ ou d'un rôle | Renommer une rubrique, préciser son aide, changer les libellés d'un rôle |

**Où ranger une donnée.** Une qualité de la personne elle-même (situation matrimoniale, conjoint) s'ajoute à `personne`. Un fait relatif à sa position dans l'acte (parts cédées, numéros, origine de propriété, intervention du conjoint) devient un **attribut de rôle**, s'écrit `{{c.parts_cedees}}` dans une boucle `[[POUR CHAQUE c DANS societes.cedant]]`, et se saisit dans le formulaire sous chaque personne désignée dans le rôle. Une donnée de l'opération s'ajoute au module.

**Règles.**

- Chercher d'abord dans `dictionnaire.md` une entrée qui convient : la transversalité dépend de la réutilisation des mêmes noms.
- Noms en minuscules, sans accent, explicites (`situation_matrimoniale`, non `sm`).
- Aucun ajout ne peut porter le nom d'une entrée existante. Un nom **voisin** d'une entrée existante produit un avertissement : s'il s'agit de la même notion, reprendre l'entrée existante.
- On ne supprime rien : le formulaire n'affiche que ce que le modèle emploie.
- Les ajouts sont énumérés dans le rapport de compilation et à l'utilisateur. Chaque dossier enregistre le type des extensions employées ; un formulaire qui ouvre un dossier où le même nom porte un autre type le signale.

### Fonctions de calcul

| Fonction | Effet |
|---|---|
| `ajouter_jours(d, n)`, `ajouter_mois(d, n)`, `ajouter_annees(d, n)`, `ajouter_duree(d, duree)` | Ajout ; un mois plus court ramène au dernier jour (31 janvier + 1 mois = 28 ou 29 février). |
| `veille(d)`, `lendemain(d)` | |
| `prorogation(d[, alsace_moselle])` | Report au premier jour qui n'est ni samedi, ni dimanche, ni férié. Les jours fériés sont calculés (Pâques comprise) ; le Vendredi saint et le 26 décembre s'ajoutent si le second argument est vrai. |
| `ecart_jours(d1, d2)`, `ecart_mois(d1, d2)`, `ecart_annees(d1, d2)` | Mois et années **révolus**. |
| `age(personne ou date, date_reference)` | En années révolues. |
| `somme(liste.champ)`, `nombre(x)`, `min(…)`, `max(…)` | Un chemin traversant une liste donne la suite de ses valeurs. |
| `arrondi(x, n)`, `arrondi_inferieur(x, n)`, `arrondi_superieur(x, n)`, `abs(x)` | `arrondi` : au plus proche, la demie s'éloignant de zéro. |
| `cumul(liste.champ, n)` | Somme des `n` premières valeurs (0 si `n` vaut 0) ; sert aux numérotations continues et aux échéanciers. |
| `si(condition, a, b)`, `renseigne(x)`, `table(nom, clé)` | |

**Calcul de ligne.** Un calcul qui porte `"element_de": "societes.repartition"` est évalué pour l'élément courant de cette liste (ou de ce rôle), désigné par `element`. Il ne s'emploie que dans `[[POUR CHAQUE … DANS societes.repartition]]`. Exemple, pour numéroter les parts de chaque associé :

```json
{"id": "debut", "libelle": "Premier numéro", "type": "entier", "element_de": "societes.repartition",
 "expression": "cumul(societes.repartition.nombre_titres, element#rang - 1) + 1", "explication": "…", "source": "…"}
```

Les opérateurs arithmétiques `+`, `-`, `*` et `/` sont disponibles. Un montant vaut sa valeur numérique. Une donnée manquante rend le calcul vide et la signale. Chaque règle de computation doit avoir été **confirmée par l'utilisateur** : le moteur ne présume d'aucune.

## 3. Décisions de balisage

**Chemins.** Préférer le dictionnaire, et lire `dictionnaire.md` pour trouver le bon chemin. Une partie se balise par un **rôle** (`bail.preneur`), jamais par une personne. Ce qui manque s'ajoute par une extension (§ 2 bis), jamais par un contournement du texte ; les ajouts sont présentés à l'utilisateur avec le balisage.

**Désignation des parties.** `designation_complete` suit un usage courant :

- personne physique : civilité, prénoms, NOM, né(e) le … à …, nationalité, profession, demeurant … ;
- personne morale : forme, capital, immatriculation, siège, représentant.

Si le modèle a sa propre formule, la composer à partir des champs, avec des conditions sur la nature de la personne.

Toute mention propre aux personnes physiques (naissance, nationalité) doit être placée sous `[[SI … EST PERSONNE PHYSIQUE]]` lorsque le rôle admet une personne morale. Les tests le révèlent : un « manquant » de date de naissance pour une société.

**Accords.** Chaque « (e) », « (s) », « né(e) » ou « le/la » rattaché à une partie devient un `|accord:…`. Dans un contrat, le rôle est souvent un terme défini invariable (« ci-après le Bailleur ») : ne pas l'accorder, mais accorder « dénommé(e) ». Vérifier l'accord des participes qui suivent une désignation (« représentée par »).

**Option, choix ou condition.**

- Une **option** est une clause que le rédacteur retient ou écarte.
- Un **choix** est une alternative entre des rédactions exclusives, décidée par le rédacteur.
- Une **condition** est un passage qui découle des données (pluralité, nature, montant).

Ne pas demander à l'utilisateur final une décision que les données emportent déjà.

**Paragraphes entiers.** Lorsqu'un passage entier est conditionnel, poser les balises de structure sur des paragraphes à part, ou envelopper le paragraphe entier. Une structure en ligne qui ne laisse rien dans le paragraphe laisserait un paragraphe vide.

**Numérotation.** La numérotation automatique de Word ou de LibreOffice se recalcule seule. Une numérotation manuelle (« Article 7 ») devient `{{compteur article}}` dès qu'un article est optionnel. Chaque renvoi manuel (« l'article 9 ») devient `{{renvoi ancre}}`. Les champs de renvoi Word (REF) ne sont pas mis à jour par le formulaire : le signaler (une mise à jour par F9 dans Word suffit).

**Listes.** Tableau de pièces, échéancier : utiliser des lignes de répétition. Liste d'alinéas : envelopper un paragraphe par `[[POUR CHAQUE]]`. Énumération dans une phrase : utiliser directement le chemin, qui produit « A, B et C ».

**En-têtes et pieds de page.** Ils sont balisables. Les structures n'y franchissent pas les limites d'un paragraphe ou d'un tableau.

**Valeurs évolutives et règles de droit.** Ne jamais en intégrer sans validation. En cas de doute, faire saisir la valeur par l'utilisateur final plutôt que de la calculer.

## 4. Liste de contrôle avant remise

- [ ] Le relevé a été lu en entier ; tous les emplacements « … », « XXX » et « (e) » sont traités ou volontairement laissés.
- [ ] `compiler` : zéro erreur ; avertissements expliqués.
- [ ] `tester` : aucune anomalie. Chaque « manquant » est expliqué (absent du dossier fictif) ou corrigé (balisage incomplet).
- [ ] Les aperçus des variantes ont été lus : accords, ponctuation des énumérations, numérotation, renvois.
- [ ] La première page du PDF de base a été regardée.
- [ ] Chaque calcul a une explication et une source confirmées ; chaque table a sa date de gel.
- [ ] Chaque extension est justifiée (aucune entrée existante ne convenait) ; les avertissements de noms voisins sont tranchés.
- [ ] Les variantes `pluriel-…` ont été lues : chaque partie plurielle reçoit bien ses propres mentions.
- [ ] Le texte hors balises est inchangé.
- [ ] L'utilisateur a validé le document balisé, sauf instruction contraire.
