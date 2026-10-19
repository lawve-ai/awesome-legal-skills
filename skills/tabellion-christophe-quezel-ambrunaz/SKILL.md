---
name: "tabellion"
description: "Transforme un modèle juridique (.docx ou .odt : contrat, conclusions, assignation, courrier type, procès-verbal…) en formulaire HTML autonome, exécuté hors ligne, qui produit sans IA le document complété, fidèle au modèle, dans son format d'origine : parties optionnelles et alternatives, listes répétées, accords, montants et dates en lettres, calculs, numérotation et renvois. Déclencher dès que l'utilisateur veut « transformer ce modèle en formulaire », « automatiser un modèle », un « modèle à remplir » ou un « générateur d'actes », réutiliser régulièrement un contrat ou une trame, ou demande « fais-moi un modèle de … à remplir » ; aussi pour faire évoluer un formulaire tabellion existant. Pas pour compléter une seule fois un document. Compétence créée par Christophe Quézel-Ambrunaz, Université Savoie Mont Blanc (V.1.1)."
---

# Tabellion

Compétence créée par **Christophe Quézel-Ambrunaz**, professeur de droit privé à l'Université Savoie Mont Blanc (Centre de recherche en droit Antoine Favre). Version 1.1.

**Modèle conseillé : Claude Opus.** Le balisage mêle analyse juridique du modèle, questions sur les règles de calcul, rédaction de plans JSON et cycles de correction après compilation et tests. Un modèle plus léger risque de baliser incomplètement ou de laisser passer une règle erronée. Sonnet peut convenir à un modèle simple ; Haiku est déconseillé. Si la conversation ne s'exécute pas avec Opus, le signaler à l'utilisateur dès le message d'accueil, en une phrase, sans refuser le travail.

Le tabellion dressait les actes à partir des formules. Cette skill fait de même : elle **balise** un modèle (Claude propose, l'utilisateur valide), puis le **compile** en un fichier HTML unique. L'utilisateur remplit ce formulaire dans son navigateur, sans connexion et sans IA, et obtient un document Word ou OpenDocument complété, identique au modèle hors des zones balisées.

Toute l'intelligence est dépensée au balisage. Le formulaire n'exécute ensuite qu'une logique entièrement explicite. Il s'ensuit une règle cardinale : **tout ce qui n'a pas été anticipé et validé au balisage sera mal traité**. Il vaut donc mieux poser une question de trop que laisser passer une règle ou un calcul faux.

## Fichiers de la skill

| Fichier | Rôle |
|---|---|
| `references/accueil.md` | Message d'accueil, à présenter au premier déclenchement |
| `references/methode.md` | Méthode de balisage : plan JSON, manifeste, cas difficiles, liste de contrôle. **À lire avant tout balisage.** |
| `references/syntaxe.md` | Langage des balises, rédigé pour le juriste ; peut lui être remis tel quel |
| `references/ameliorations.md` | Catalogue des améliorations du formulaire à proposer |
| `references/dictionnaire.json` / `.md` | Dictionnaire commun, trame extensible par chaque modèle (le JSON fait foi) |
| `scripts/tabellion.py` | Commandes `analyser`, `baliser`, `compiler`, `tester`, `formulaire`, `tout` |
| `assets/moteur.js`, `assets/formulaire.html` | Moteur et gabarit du formulaire (ne pas modifier pour un modèle donné) |

## Contrôle de l'environnement

Avant toute chose, vérifier en une commande : `python3 -c "import lxml" && node --version && soffice --version`. Le balisage et la compilation exigent Python et lxml, les tests exigent Node, et le contrôle d'ouverture exige LibreOffice.

Si Python ou lxml manque, l'installer (`pip install lxml --break-system-packages`). Si l'exécution de code n'est pas disponible du tout, le dire et s'arrêter : aucun mode dégradé n'est sûr.

Les commandes s'exécutent dans le répertoire de travail. Les scripts s'appellent par leur chemin absolu `<dossier de la skill>/scripts/tabellion.py`.

## Déroulé

### 0. Accueil

Au premier déclenchement dans une conversation, présenter le message de `references/accueil.md`. Il peut être adapté au contexte, mais doit garder la recommandation de déposer un modèle anonymisé et la discipline de sauvegarde. La skill **ne contrôle pas** l'anonymat du modèle.

### 1. Obtenir le modèle

- **Formats acceptés : .docx et .odt.** Chaque modèle reste dans son format : un .docx produit un .docx, un .odt produit un .odt.
- **Fichier .doc, .rtf ou .pdf.** Proposer une conversion par LibreOffice (`soffice --headless --convert-to docx`), en prévenant qu'elle peut altérer la mise en page. Le PDF ne permet aucune fidélité de mise en forme : demander l'original.
- **Modèle à rédiger** (« fais-moi un modèle de bail à remplir »). Chercher, parmi les skills disponibles, une skill de rédaction juridique française avec vérification des sources : `assistant-juridique-fr`, ou toute skill de l'utilisateur dont la description couvre cet usage. Se fonder sur la description, non sur le nom.
  - Si une telle skill existe, la charger, rédiger le modèle selon ses règles, le soumettre à l'utilisateur, puis le traiter comme un modèle déposé.
  - Si aucune n'existe, **s'arrêter** et expliquer qu'une skill de rédaction juridique est nécessaire pour un travail de qualité. Ne pas rédiger en mode dégradé.
  - **Aucune mention de cette délégation** ne figure dans les documents produits.
- **Vérification des références** (option, à proposer en une ligne, avant le balisage). Faire contrôler par la même skill de rédaction l'actualité des textes cités et des montants. Les corrections ne sont appliquées qu'après validation de l'utilisateur.

### 2. Relevé

`python3 tabellion.py analyser MODELE` produit la liste numérotée des paragraphes (`D12` pour le corps, `E1…` pour les en-têtes, `P1…` pour les pieds de page, `N…` pour les notes, `S…` pour les styles de l'ODT). Elle signale aussi les indices : emplacements à remplir, « (e) », numérotation manuelle, renvois internes, dates, montants. Lire **tout** le relevé.

Les alertes bloquent le balisage :

- **Modifications suivies** : demander à l'utilisateur de les accepter ou de les refuser.
- **Commentaires** : ils seraient reproduits dans chaque document généré ; proposer de les supprimer.

### 3. Questions

Identifier puis lister, sans encore baliser :

- les **variables** ;
- les **rôles**, c'est-à-dire les parties et leur pluralité possible ;
- les **options**, des passages à retenir ou à écarter ;
- les **choix**, des rédactions alternatives exclusives ;
- les **conditions**, des passages qui dépendent des données (personne morale, pluralité, montant…) ;
- les **répétitions** (pièces, parties) ;
- les **accords** ;
- les **calculs** ;
- la **numérotation** et les **renvois**.

Poser ensuite les questions nécessaires, par lots de quatre au plus (outil de questions s'il est disponible). Sont **toujours** soumis à l'utilisateur :

- **Toute règle de droit ou tout calcul** que le formulaire appliquera : point de départ, mode de computation, arrondis, valeur légale. Aucune règle n'est tirée de la mémoire de Claude ; la source est donnée par l'utilisateur ou vérifiée avec lui.
- **Toute valeur évolutive** (taux, indice, barème). Si elle est intégrée, elle est figée dans une table datée, et le formulaire refuse de calculer au-delà.
- **La frontière entre option et choix**, et le libellé présenté à l'utilisateur final.
- **Les variantes de désignation des parties** : désignation complète tirée du dictionnaire, ou composition propre au modèle.

### 4. Balisage

Lire `references/methode.md`, puis rédiger :

1. un **plan de balisage** JSON, appliqué par `python3 tabellion.py baliser MODELE plan.json modele-balise.docx`. Les balises apparaissent surlignées : en jaune pour les valeurs, en bleu clair pour les structures ;
2. un **manifeste** JSON : titre, identifiant, extensions du dictionnaire, variables locales, calculs, contrôles, tables figées, aides.

Le dictionnaire commun est une **trame, jamais un obstacle**. Utiliser ses chemins chaque fois qu'ils conviennent ; ce qui lui manque (champ d'une personne, colonne d'une liste, module, rôle, donnée attachée à une partie dans l'acte) s'ajoute dans la rubrique `extensions` du manifeste (`methode.md`, § 2 bis). Ne jamais renoncer à une mention du modèle, ni la déformer, faute d'entrée dans le dictionnaire. Présenter les ajouts à l'utilisateur avec le balisage.

### 5. Compilation

`python3 tabellion.py compiler modele-balise.docx manifeste.json travail/` contrôle chaque balise contre la syntaxe et le dictionnaire. Corriger chaque erreur, puis recompiler jusqu'à zéro erreur.

### 6. Validation par l'utilisateur

Remettre le document balisé (SendUserFile) avec, dans la conversation, un tableau récapitulatif :

- les variables, avec leur libellé ;
- les options et les choix ;
- les conditions, en langage clair ;
- les répétitions ;
- les calculs, avec leur règle et leur source ;
- les variables locales.

Indiquer que l'utilisateur peut corriger le balisage directement dans Word ou LibreOffice, en suivant `references/syntaxe.md`, puis renvoyer le fichier. **Attendre sa confirmation** avant de construire le formulaire, sauf s'il a demandé d'enchaîner.

Si un document balisé modifié revient, le recompiler tel quel, sans passer par `baliser`, et signaler les différences constatées.

### 7. Construction et tests

`python3 tabellion.py tout modele-balise.docx manifeste.json travail/ formulaire.html` compile, construit le formulaire et l'éprouve sur des dossiers fictifs : base, options écartées, chaque cas de chaque choix, singulier, listes vides. Pour chaque variante, l'outil vérifie que le XML est bien formé et qu'aucune balise ne subsiste. Il contrôle aussi l'ouverture du document par LibreOffice.

Ensuite :

- lire `travail/rapport-tests.md` et **les aperçus** `travail/tests/*.apercu.txt`. Un « manquant » signale souvent un balisage incomplet, par exemple une date de naissance demandée pour une personne morale : il faut alors une condition `EST PERSONNE PHYSIQUE` ;
- vérifier les accords, la ponctuation des énumérations et les renvois ;
- rendre la première page du PDF de base (`pdftoppm -r 60 -png -f 1 -l 1`) et la regarder ;
- corriger, puis recommencer.

Les tests s'exécutent sous LibreOffice ; aucune ouverture dans Microsoft Word n'est possible ici. Le dire à l'utilisateur et lui demander de vérifier le premier document produit dans Word.

### 8. Livraison

Remettre par SendUserFile :

- le **formulaire** `.html` ;
- le **document balisé** et le **manifeste**, qui constituent le paquet de maintenance permettant de reconstruire ou de faire évoluer le formulaire.

Le formulaire est un fichier local : **ne jamais le publier comme artifact**. Une page hébergée contredirait l'engagement de confidentialité. Si l'ordinateur de l'utilisateur est relié et qu'il en exprime le souhait, écrire aussi les fichiers dans son dossier.

Expliquer brièvement l'usage du formulaire :

- au premier lancement, des données d'essai sont chargées ; le bouton « Commencer un dossier réel » les efface ;
- le dossier s'enregistre en `.json` à la fin de chaque séance ; ce fichier peut être rouvert dans tout autre formulaire tabellion pour réutiliser les mêmes personnes ;
- la page fonctionne hors ligne.

Proposer enfin deux à quatre améliorations pertinentes tirées de `references/ameliorations.md`.

### 9. Évolutions

Pour toute modification, reprendre le document balisé et le manifeste, corriger, puis relancer `tout`. Incrémenter `version` dans le manifeste.

Les dossiers `.json` existants restent compatibles tant que les chemins utilisés ne changent pas. Signaler à l'utilisateur tout chemin supprimé ou renommé.

## Règles impératives

- **Fidélité.** Hors des balises, le texte et la mise en forme du modèle ne sont pas modifiés. Toute amélioration rédactionnelle est proposée à part, et n'est appliquée qu'avec l'accord de l'utilisateur.
- **Aucune règle de droit non validée.** Chaque calcul porte dans le manifeste une `explication` (affichée comme note de calcul) et une `source` confirmée par l'utilisateur. Le dictionnaire ne contient aucune règle de droit, et cela doit le rester.
- **Hors ligne absolu.** Le formulaire ne charge rien et n'envoie rien ; sa politique de sécurité interdit toute connexion. Ne jamais ajouter de ressource distante au gabarit.
- **Valeurs fictives.** Elles restent manifestement fictives (ESSAI, Exempleville, 00000) ; ne jamais y placer de données réelles.
- **Honnêteté sur les limites.** Signaler ce que le formulaire ne fait pas pour le modèle donné : champs Word non mis à jour, renvois non balisés, mise en forme propre à Word non vérifiable ici.
- **Dictionnaire.** Ne pas modifier `references/dictionnaire.json` pour un modèle donné : les besoins propres au modèle passent par les extensions du manifeste, qui ne sont jamais refusées si elles sont bien formées. Préférer toujours une entrée existante à un ajout de même sens, afin qu'un même dossier `.json` serve à plusieurs formulaires.
