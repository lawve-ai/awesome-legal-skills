---
name: "note-de-synthese-crfpa"
description: "Génération de sujets d'entraînement complets pour l'épreuve de NOTE DE SYNTHÈSE (5 heures, coefficient 3) de l'examen d'accès au CRFPA : choix du sujet, dossier documentaire de 16 à 20 documents assemblé à partir de sources réelles vérifiées (textes, jurisprudence, travaux parlementaires, doctrine) avec contrôle du verbatim, puis grille de notation au modèle de la Commission nationale (résumé de chaque document, problématique, thèmes cotés sur 20, plan). Livraison en deux fichiers .docx distincts, le sujet et la grille. Si l'utilisateur n'impose pas de sujet, en chercher un dans l'actualité juridique. Mode aveugle pour l'étudiant qui compose sans rien voir du corrigé. Déclencher dès que l'utilisateur demande un sujet de note de synthèse, un dossier documentaire, une note de synthèse blanche, un entraînement à l'épreuve de 5 heures du CRFPA ou de l'IEJ, ou une grille de note de synthèse. NE PAS déclencher pour les épreuves de 3 heures (sujet-crfpa-toutes-matieres) ni pour la correction de copies.\n"
---

# Générateur de sujets de note de synthèse CRFPA

Cette skill fabrique un sujet d'entraînement complet pour l'épreuve d'admissibilité de note de synthèse (article 5-1° de l'arrêté du 17 octobre 2016), plus la grille de notation correspondante. Livraison en deux fichiers `.docx` distincts, le sujet et la grille de notation, pour que le sujet puisse être distribué à des candidats sans le corrigé. Un fichier unique, grille commençant sur la page suivant le sujet, est possible sur demande.

Elle sert deux publics : l'examinateur ou le directeur d'IEJ qui doit produire un sujet blanc et n'a pas le temps de dépouiller quinze bases, et l'étudiant qui veut s'entraîner sur un dossier inédit plutôt que de refaire les annales qu'il connaît déjà. Les deux publics n'appellent pas le même déroulement : voir « Mode examinateur et mode aveugle » ci-dessous.

**Hors champ** : la correction de copies, les épreuves de 3 heures (voir `sujet-crfpa-toutes-matieres`), la procédure et le grand oral.

## Étape 0 — Lire les références

Lire systématiquement, avant toute production :

- `references/format_officiel_nds.md` — cadre réglementaire, invariants du format relevés sur les sessions 2017 à 2026, tableau des sujets déjà tombés, maquettes de page de garde, gabarit complet de la grille de notation.
- `references/sources_documentaires.md` — protocole de collecte registre par registre, outils et requêtes, gisement de sources libres de droits, traitement de la doctrine payante et de la presse.

## La règle qui gouverne tout : le corrigé s'écrit avant le dossier

C'est la seule inversion à retenir. Un dossier collecté d'abord, puis organisé après coup, produit invariablement des thèmes déséquilibrés, des documents décoratifs et un plan bancal. La Commission procède dans l'autre sens : la matrice thématique existe d'abord, et chaque document est ensuite recruté pour remplir une cellule précise.

Concrètement : après le choix du sujet, écrire les quatre thèmes, leurs sous-thèmes et la pondération en points **avant** la première requête documentaire. La collecte devient alors une liste de commandes, ce qui la rend rapide et vérifiable.

## Mode examinateur et mode aveugle

Le mode se fixe au cadrage, avant toute recherche. **Mode examinateur par défaut.** Passer en **mode aveugle** dès que l'utilisateur dit vouloir composer lui-même, s'entraîner, ne pas voir le corrigé, ou se présente comme candidat. En cas de doute, poser la question en une phrase avant de lancer la veille.

**Mode examinateur.** Déroulement décrit dans la suite : propositions de sujet argumentées, matrice soumise avant la collecte, résumé du travail en fin de séance.

**Mode aveugle.** Le travail est exactement le même, la matrice s'écrit toujours avant la collecte, mais rien de ce qui prépare le corrigé n'apparaît dans la conversation. Un étudiant qui a lu la contradiction du sujet ou la liste des thèmes avant de composer ne s'entraîne plus à rien.

- **Propositions de sujet** : l'intitulé seul, avec les branches du droit concernées et la date de la veille. Ni question juridique d'actualité développée, ni pièces d'ancrage, ni esquisse de contradiction, ni note de faisabilité. Le tri sur les quatre critères de l'étape 1 se fait quand même, mais sans être montré.
- **Matrice** : jamais soumise, jamais affichée. Elle est écrite directement dans `dossier.json` (champ `matrice`).
- **Messages d'avancement** : des volumes, rien d'autre (« 11 pièces vérifiées sur 18 »). Aucun message ne résume un document, ne nomme un thème, ne commente la portée d'une pièce ni n'annonce une tension.
- **Contrôles** : `verifier_verbatim.py` est lancé avec `--sobre`, et la checklist de l'étape 9 est parcourue sans en recopier le détail ; seul le résultat global est donné.
- **Prévenir l'étudiant**, en une phrase au moment du cadrage : les appels d'outils et leurs résultats restent consultables dans l'interface ; s'il veut garder la surprise, qu'il ne les déplie pas.
- **Livraison** : produire les deux fichiers, ne présenter que le sujet. Le message final indique la durée (cinq heures), le nombre de documents et de pages, les emplacements à compléter s'il y en a, et précise que la grille est prête et sera remise sur demande. Rien sur les thèmes, la pondération, le plan ou les pièces maîtresses.
- **Remise de la grille** : quand l'étudiant la demande, présenter le fichier. S'il a disparu, le régénérer à partir de `dossier.json` avec `build_nds.js`.

## Invariants du format (détail dans `format_officiel_nds.md`)

1. **16 à 20 documents, 26 à 35 pages**, soit environ 1,5 page par document. Aucun document long : des extraits, et plusieurs documents d'un seul article de code.
2. **Cinq registres présents** : textes normatifs, jurisprudence, doctrine, documents institutionnels ou parlementaires, documents non juridiques (presse). Un dossier sans presse ni rapport ne ressemble pas à un sujet de la Commission.
3. **Désordre calibré** : les documents ne sont classés ni par date, ni par hiérarchie des normes, ni par thème. Le classement est précisément le travail demandé au candidat.
4. **Doublons assumés** : deux ou trois documents éclairent le même point sous des angles différents, ce qui récompense le regroupement et pénalise la paraphrase document par document.
5. **Couple décision plus commentaire** : au moins un arrêt accompagné de sa note explicative, de son résumé juridique officiel ou d'un commentaire, pour rendre une décision technique intelligible sans connaissance préalable.
6. **Document orphelin** : un document sert seul une sous-partie entière, généralement la branche faible du plan.
7. **Sujet en une formule nominale courte**, de un à six mots, transversale et actuelle : soit une notion (l'animal, la vulnérabilité, les restitutions, l'intelligence artificielle), soit une tension explicitée (l'imprescriptibilité à l'épreuve des droits fondamentaux).
8. **Le sujet doit être traitable en quatre pages manuscrites.** Un thème trop vaste produit une note de synthèse impossible.

## Processus de génération

### Étape 1 — Cadrage et choix du sujet

Recueillir ou inférer : sujet imposé ou libre, session fictive, mode (examinateur ou aveugle, voir plus haut), contraintes éventuelles de matière.

**Si l'utilisateur n'impose pas de sujet, en chercher un dans l'actualité juridique, à chaque fois, et ne jamais en proposer un de mémoire.** Le choix spontané retombe toujours sur les mêmes notions vedettes et sur des thèmes dont on croit connaître l'état du droit, ce qui produit des dossiers datés et parfois faux. Le sujet naît d'une recherche faite pendant la session, pas d'un souvenir.

#### Protocole de veille (obligatoire en l'absence de sujet imposé)

Balayer ces cinq gisements, avec les outils, avant toute proposition. Une recherche web pour dater l'actualité, puis les sources primaires pour la vérifier.

1. **Législation des douze derniers mois** : lois promulguées, ordonnances, décrets d'application attendus, via OpenLegi et `recherche_journal_officiel`. Une réforme récente ou en cours de décrets fournit toujours de la matière contradictoire.
2. **Textes européens en cours d'entrée en application** : règlements et directives dont l'échéance de transposition approche, souvent riches en tensions avec le droit interne.
3. **Jurisprudence marquante des dix-huit derniers mois** : arrêts publiés au bulletin, avis de la Cour de cassation, décisions du Conseil d'État publiées au Lebon, QPC, arrêts de grande chambre de la CEDH et de la CJUE.
4. **Travaux en cours** : propositions et projets de loi en navette, rapports d'information déposés, avis des autorités administratives indépendantes, rapports annuels. C'est là que se lisent les débats qui ne sont pas encore tranchés.
5. **Débats de société ayant une traduction juridique** : ce que l'arrêté appelle les aspects juridiques des problèmes sociaux, politiques, économiques ou culturels du monde actuel. La Commission a retenu l'influence commerciale, les violences conjugales, l'animal, l'intelligence artificielle : des sujets dont on parle hors des facultés.

Un sujet du dernier gisement adossé à des pièces des quatre premiers est le profil idéal.

#### Formulation et arbitrage

De ce balayage, tirer **trois propositions**, chacune formulée comme un sujet d'épreuve (formule nominale courte, ou tension explicitée) et accompagnée de quatre éléments : la question juridique d'actualité qui la porte, les deux ou trois pièces récentes qui l'ancrent avec leur date, l'esquisse de la contradiction qui fournira le plan, et une note de faisabilité sur les quatre critères ci-dessous. Laisser l'utilisateur trancher, et proposer aussi de tirer au sort si l'arbitrage l'indiffère. **En mode aveugle, ne montrer que les intitulés**, avec les branches concernées et la date de la veille.

- **Transversalité** : la notion doit traverser au moins trois branches (civil, pénal, public, européen, social). Un sujet cantonné à une branche donne un dossier de cas pratique déguisé.
- **Actualité normative** : au moins une évolution significative dans les vingt-quatre derniers mois, loi, règlement européen, revirement ou décision de principe. C'est le critère que la veille sert à documenter.
- **Tension interne** : le sujet doit porter en lui-même une contradiction, c'est elle qui fournira le plan en deux parties. Un sujet purement descriptif ne se laisse pas mettre en plan.
- **Disponibilité documentaire libre** : au moins douze documents reproductibles sans autorisation (voir `sources_documentaires.md`). Vérifier par quelques requêtes exploratoires avant de proposer le sujet, pas après.

Exclure les sujets déjà tombés, listés dans `format_officiel_nds.md`, ainsi que les notions trop voisines, et ceux que l'utilisateur signale comme déjà traités dans son IEJ. La skill n'a pas de mémoire entre conversations : poser la question lors du cadrage.

Un sujet d'actualité vieillit vite : indiquer à l'utilisateur la date de la veille et les pièces les plus récentes, pour qu'il sache quand le dossier devra être rafraîchi.

### Étape 2 — Matrice thématique

Écrire la matrice complète avant toute collecte, sur le modèle de la grille officielle :

- quatre thèmes (trois à cinq est acceptable), chacun pondéré, le total faisant exactement 20 points ;
- deux à trois sous-thèmes par thème ;
- pour chaque sous-thème, le type de document attendu et le nombre visé.

Dans la matrice puis pendant la collecte, désigner les documents par leur `id` (par exemple `cass_civ1_1962_lunus`), jamais par un numéro : les numéros ne sont attribués qu'au tirage de l'étape 5.

La pondération suit le volume documentaire, elle n'est pas uniforme : la session 2025 répartissait 5, 5, 6 et 4 points. La branche la plus faible du plan reçoit le moins de points et le moins de documents, souvent un seul.

Soumettre la matrice à l'utilisateur avant de lancer la collecte en mode examinateur : c'est le moment où son arbitrage coûte le moins cher. Jamais en mode aveugle.

### Étape 3 — Collecte réelle et vérifiée

**Règle cardinale : ne jamais inventer ni citer de mémoire une référence.** Chaque article, chaque décision, chaque article de doctrine est vérifié pendant la session sur sa source. Un dossier de note de synthèse repose entièrement sur l'exactitude des pièces : un arrêt au mauvais numéro de pourvoi ruine l'exercice et décrédibilise l'enseignant qui le distribue.

Protocole détaillé par registre dans `references/sources_documentaires.md`. En résumé :

| Registre | Outils | Ce qu'on récupère |
|---|---|---|
| Textes | OpenLegi (`rechercher_code`, `rechercher_dans_texte_legal`) | Article verbatim, version en vigueur, visa de modification |
| Jurisprudence judiciaire | Judilibre, OpenLegi, LibreJustice | Texte intégral, jamais un résumé |
| Jurisprudence administrative et constitutionnelle | OpenLegi (`rechercher_jurisprudence_administrative`, `rechercher_decisions_constitutionnelles`) | Décision et considérants utiles |
| Jurisprudence européenne | GoodLegal (`eu_caselaw_search`, `eu_retrieve`), Legal Data Hunter | Arrêt CJUE, résumé juridique CEDH |
| Travaux parlementaires | skill `travaux-preparatoires`, open data AN et Sénat | Exposé des motifs, amendement, rapport d'information |
| Doctrine | HAL, ISIDORE, CrossRef, OpenAlex, skill `recherche-doctrine` | Référence complète vérifiée, DOI, statut d'accès |
| Documents non juridiques sous Licence Ouverte | recherche web, puis téléchargement | Extrait verbatim, après vérification des mentions légales |
| Presse | recherche web | Référence et notice factuelle, jamais le texte intégral |

Pour chaque pièce retenue, créer son entrée dans `dossier.json` avec un `id`, un `registre`, une `nature` (`extrait` pour un texte reproduit, `notice` pour un résumé rédigé par la skill), et un objet `source` : outil, identifiant (numéro de pourvoi, requête, affaire, DOI), statut de reproduction (libre, ou soumis à droits). Ajouter, quand ils s'appliquent, `saga`, `couple_avec`, `cle_de_voute` et `date`, qui serviront au tirage. Schéma complet en tête de `scripts/build_nds.js`.

**Conserver la source brute** de chaque pièce reproduite dans `sources/<id>.txt` : téléchargée directement par le terminal quand c'est possible, sinon recopiée d'un bloc depuis le résultat de l'outil, juste après l'appel, sans coupe. Ce fichier sert au contrôle du verbatim de l'étape 6. Protocole dans `sources_documentaires.md`, section 0.

### Étape 4 — Traitement de la doctrine et de la presse

La Commission reproduit des extraits de Dalloz, du JCP ou du JurisClasseur. Un sujet fabriqué hors de ce cadre ne le peut pas reproduire, mais il doit en garder la trace, faute de quoi le dossier se reconnaît immédiatement comme un dossier de seconde main.

**Règle : tout dossier comporte au moins un article de doctrine sous droits, en emplacement à compléter.** Un ou deux au plus. Ce document est choisi comme les autres, pour la cellule de la matrice qu'il remplit, et non ajouté en décoration. Il est signalé en page de garde dans le décompte des emplacements à compléter, et sa notice analytique doit être assez précise pour que le dossier reste composable même si l'enseignant ne colle pas l'extrait.

Trois réponses, à combiner dans cet ordre :

1. **Privilégier le gisement libre qui joue le même rôle pédagogique que la doctrine** : notes explicatives et communiqués de la Cour de cassation, rapports annuels et groupes de travail, résumés juridiques du greffe de la CEDH, avis du Conseil d'État, rapports d'information parlementaires, avis de la CNCDH, du Défenseur des droits, du CNPEN, communiqués des autorités administratives indépendantes. Les sujets réels en font déjà un large usage. Ces pièces sont gratuites, reproductibles, et fournissent exactement le commentaire dont le candidat a besoin.
2. **Utiliser la doctrine réellement en accès ouvert** : dépôts HAL et TEL, OpenEdition, Persée, *Revue des droits et libertés fondamentaux*, *Revue des droits de l'homme*, thèses en ligne. Il y en a assez en droit pour deux à quatre documents par dossier.
3. **Pour la doctrine payante indispensable, produire une fiche de référence et non un extrait** : référence complète vérifiée, DOI ou lien éditeur, et un emplacement clairement signalé dans le dossier (« extrait à insérer ») accompagné d'une notice analytique de dix à quinze lignes rédigée par la skill, qui dit ce que l'article établit sans en reproduire le texte. L'utilisateur qui dispose d'un abonnement colle l'extrait dans l'emplacement ; le dossier reste jouable sans lui.

Pour le registre non juridique, la notice n'est pas la voie normale. Au moins un document non juridique est reproduit en verbatim depuis le gisement public sous Licence Ouverte (statistique publique, études, rapports de la Cour des comptes, vie-publique.fr : voir `sources_documentaires.md`, section 5), après vérification des mentions légales du site. La presse sous droits ne vient qu'en complément, en notice factuelle, jamais recopiée, et une seule par dossier sauf nécessité.

Le fichier `.docx` du sujet doit indiquer sur sa page de garde combien de documents comportent un emplacement à compléter, pour que l'enseignant sache en un coup d'œil ce qui lui reste à faire.

### Étape 5 — Calibrage et ordonnancement

Contraintes à respecter avant rédaction :

- 18 documents ± 2 ; 28 pages ± 3 ; longueur par document de 0,3 à 2,5 page ;
- quotas indicatifs : 3 à 6 textes, 3 à 8 décisions, 2 à 5 documents doctrinaux ou assimilés, 2 à 4 documents institutionnels ou parlementaires, 1 à 3 documents non juridiques, dont au moins un reproduit en verbatim depuis le gisement sous Licence Ouverte ;
- parmi les documents doctrinaux, un ou deux relèvent obligatoirement de la doctrine sous droits, traités en emplacement à compléter ;
- au moins un arrêt de principe ancien (la série comporte régulièrement une décision des années 1960 ou 1970) et au moins trois décisions de moins de dix-huit mois ;
- un à deux couples décision plus commentaire ; un document orphelin ;
- chaque document rattaché à au moins un thème, chaque thème alimenté par au moins deux documents, aucun document inutilisé.

**Ordonnancement** : tirer l'ordre au sort avec le script fourni, jamais à la main, ce qui reproduit toujours un ordre logique. Le tirage intervient avant la rédaction de la grille, qui renvoie aux numéros définitifs.

```bash
python3 scripts/tirer_ordre.py dossier.json            # tirage, renumérotation, graine consignée
python3 scripts/tirer_ordre.py dossier.json --graine 731402   # rejouer un tirage
```

Le script lit `id`, `registre`, `saga`, `couple_avec`, `cle_de_voute` et `date`, et applique ces contraintes : le document 1 n'est jamais la clé de voûte ; jamais deux textes normatifs consécutifs ; jamais trois documents consécutifs du même registre ; jamais deux pièces d'une même saga consécutives ; pas d'ordre proche de la chronologie quand au moins cinq pièces sont datées. Le commentaire d'un couple (`couple_avec`) est placé juste après sa décision, comme dans les annales (2017, documents 13 et 14), et ce couple échappe à la règle de la saga.

Le dossier 2025 enchaînait pourtant trois pièces de la même saga de l'abattage rituel (documents 2 à 4). Pour reproduire délibérément ce procédé du doublon assumé, lancer le tirage avec `--autoriser-saga`.

La graine et l'ordre retenu sont consignés dans le champ `tirage` du JSON. Si aucun ordre valide n'est trouvé, le script indique les contraintes le plus souvent violées : c'est la composition du dossier qu'il faut revoir (trop de textes, saga trop fournie), pas les contraintes.

### Étape 6 — Rédaction du dossier

Chaque document du dossier comporte un intitulé normalisé, sur le modèle des annales :

`DOCUMENT 7 : Article 515-14 du code civil créé par la loi du 16 février 2015`
`DOCUMENT 3 : Cour européenne des droits de l'homme, Executief van de Moslims van België et autres c. Belgique, 13 février 2024, n° 16760/22 et al. (résumé juridique)`
`DOCUMENT 20 : La Semaine Juridique Édition Générale n° 15, 14 avril 2025, act. 482, note par E. Vincent (extraits)`

Puis le contenu : texte verbatim pour les sources libres, coupé aux passages utiles et signalé par « (extraits) » ; notice analytique pour les pièces sous droits. Les coupes internes sont marquées par « (…) » comme dans les sujets réels, les insertions éditoriales entre crochets.

**Construire les extraits par copie, pas par réécriture** : prélever les passages dans `sources/<id>.txt` (Python ou `sed`) plutôt que de les retaper. C'est au moment de couper et de condenser que la paraphrase s'introduit sans qu'on la voie.

**Contrôle du verbatim**, une fois tous les contenus écrits :

```bash
python3 scripts/verifier_verbatim.py dossier.json --rapport verbatim.md   # --sobre en mode aveugle
```

Le script compare chaque segment d'extrait à sa source par séquences de quatre mots, en neutralisant la casse, les accents, les apostrophes et la ponctuation. Un segment non conforme se corrige en recopiant le passage depuis la source, jamais en abaissant le seuil ni en marquant le document comme notice pour l'exclure du contrôle. Les écarts mineurs se regardent un par un : coquille, mot ajouté, ou début de paraphrase. Les notices et les emplacements à compléter ne sont pas contrôlés, par construction.

**Écriture sans marqueurs d'IA**, dans le sujet comme dans la grille : aucun tiret cadratin ou demi-cadratin en incise, pas de gras dans le corps du texte, pas de formule méta, pas de rythmes ternaires systématiques. Si la skill `detecteur-tics-ia` est disponible, l'appliquer en relecture finale avant production des fichiers.

### Étape 7 — Rédaction de la grille de notation

Gabarit complet dans `format_officiel_nds.md`. Structure invariable :

1. **En-tête d'entraînement** avec mention de non-officialité : jamais la Commission nationale en émetteur, jamais le bloc réglementaire de l'article 51-1 du décret du 27 novembre 1991, qui est propre aux grilles officielles.
2. **Rappel des recommandations** applicables à l'épreuve (limite de quatre pages, plan apparent, synthèse objective, référence aux numéros de documents, qualité rédactionnelle sanctionnée).
3. **Résumé de chaque document**, de 150 à 250 mots, dans l'ordre du dossier. C'est le gros du corrigé : le résumé restitue l'apport juridique du document, pas son plan.
4. **Problématique générale** : un paragraphe qui pose la tension, enchaîne deux ou trois questions, et s'achève sur l'annonce des deux parties.
5. **Thèmes particuliers** : chaque thème coté en points, subdivisé en sous-thèmes, chaque sous-thème suivi de la liste des documents rattachés. Un même document peut et doit figurer sous plusieurs thèmes.
6. **Plan indicatif** en I / A / 1, explicitement raccordé aux thèmes.

Rappeler en fin de grille la règle de qualité rédactionnelle et le fait que la structuration du plan reste à la libre appréciation du candidat, de sorte qu'un plan différent bien construit ne doit pas être pénalisé.

### Étape 8 — Production des fichiers Word

Consulter `/mnt/skills/public/docx/SKILL.md`. Vérifier que l'ordre a été tiré (champ `tirage`) et que le contrôle du verbatim est passé, puis utiliser le script fourni :

```bash
node scripts/build_nds.js dossier.json /mnt/user-data/outputs/
```

Par défaut, **deux fichiers distincts** :

- `sujet_nds_<theme>_<session>.docx`
- `grille_nds_<theme>_<session>.docx`

C'est ce qu'il faut pour distribuer le sujet sans que la grille circule. Ajouter `--unique` pour n'obtenir qu'un fichier, la grille commençant alors sur la page suivant le dernier document, dans une section dont la pagination repart à 1.

Le décompte annoncé en page de garde ne compte que les pages du sujet. Le script le mesure lui-même par une conversion préalable, ce qui évite l'écart entre le nombre annoncé et le nombre réel.

Le script attend un fichier JSON dont le schéma est documenté en tête de `scripts/build_nds.js`. Il vérifie avant écriture le nombre de documents, le total des points, la présence d'un résumé par document, le rattachement de chaque document à un thème, la présence d'un registre et d'un fichier source pour chaque extrait, et la trace du tirage, et signale les manques.

L'intitulé du sujet apparaît encadré à quatre endroits : sur la page de garde, sur la page des recommandations après la formule « À partir des documents joints… », en tête de la liste des documents, et en tête de la grille. Un candidat qui ouvre le document au milieu doit savoir sur quoi il compose.

Après génération, convertir en PDF et regarder les pages, comme l'indique la skill docx. Vérifier la page de garde, la page du sujet, la première page de la grille.

En mode aveugle, ne présenter que le fichier du sujet (voir « Mode examinateur et mode aveugle »).

Si l'utilisateur veut la liste des références de doctrine payante à récupérer sur ses bases, produire en complément un court fichier `references_doctrine_<theme>.md` avec, pour chaque entrée, la référence complète, le DOI ou le lien, et le numéro du document où l'insérer.

### Étape 9 — Checklist de validation

**Sujet**
- [ ] Page de garde conforme, mention de non-officialité présente, décompte de pages exact
- [ ] Intitulé du sujet visible sur la page de garde, sur la page des recommandations, en tête de liste et en tête de grille
- [ ] Sujet formulé en une formule nominale courte, transversale, non déjà tombée
- [ ] Si le sujet était libre : veille d'actualité réellement effectuée, pièces d'ancrage datées et vérifiées
- [ ] 16 à 20 documents, 26 à 35 pages, cinq registres représentés
- [ ] Ordre tiré par `tirer_ordre.py`, graine consignée, couples décision plus commentaire adjacents
- [ ] Au moins un couple décision plus commentaire, au moins un document orphelin
- [ ] 100 % des références vérifiées en session sur leur source, aucune reproduction de texte sous droits
- [ ] Une source brute dans `sources/` pour chaque extrait, `verifier_verbatim.py` sans segment non conforme ni source manquante
- [ ] Au moins un document non juridique reproduit en verbatim, mentions légales du site vérifiées ; au plus une notice de presse sauf nécessité
- [ ] Au moins un article de doctrine sous droits, en emplacement à compléter, avec référence complète et notice analytique
- [ ] Emplacements à compléter clairement signalés et dénombrés

**Grille**
- [ ] Résumé présent pour chaque document, sans exception
- [ ] Problématique s'achevant sur l'annonce des deux parties
- [ ] Total des points exactement égal à 20, pondération cohérente avec le volume documentaire
- [ ] Chaque document rattaché à au moins un thème, aucun document orphelin de thème
- [ ] Plan indicatif raccordé aux thèmes, rappel de la liberté de structuration
- [ ] Prose continue, aucun tiret cadratin en incise ni autre marqueur d'IA

**Cohérence**
- [ ] Le sujet est traitable en quatre pages
- [ ] Deux fichiers produits, la grille n'est pas dans le fichier du sujet
- [ ] En mode aveugle : propositions réduites aux intitulés, matrice jamais affichée, aucun message n'a révélé un thème ou une tension, seul le sujet a été présenté
- [ ] Décompte de pages de la page de garde conforme au fichier du sujet seul

## Références

- `references/format_officiel_nds.md` : cadre réglementaire, annales 2017-2026 avec leur composition, maquettes, gabarit de la grille. **À lire à chaque utilisation.**
- `references/sources_documentaires.md` : protocole de collecte, outils, sources libres de droits, traitement des sources payantes.
- `scripts/build_nds.js` : assemblage des deux fichiers Word à partir d'un JSON, avec `--unique` pour n'en produire qu'un. Schéma du JSON en tête du fichier.
- `scripts/tirer_ordre.py` : tirage de l'ordre sous contraintes, renumérotation, graine consignée.
- `scripts/verifier_verbatim.py` : contrôle des extraits contre les sources brutes de `sources/`.

## Exemples d'utilisation

> « Fais-moi un sujet de note de synthèse sur le secret des affaires, avec le corrigé. »

1. Lire les deux références ; 2. vérifier que le sujet n'est pas déjà tombé et tester sa faisabilité documentaire par quelques requêtes ; 3. écrire la matrice à quatre thèmes et la soumettre ; 4. collecter texte par texte et arrêt par arrêt, en conservant chaque source brute ; 5. calibrer, tirer l'ordre avec `tirer_ordre.py` ; 6. rédiger le dossier par copie depuis les sources et passer `verifier_verbatim.py` ; 7. rédiger la grille ; 8. produire les deux docx et vérifier le rendu.

> « J'ai besoin d'un dossier documentaire pour un galop d'essai en novembre, sujet libre, pas trop pénal. »

Proposer trois sujets transversaux avec note de faisabilité, exclure ceux déjà tombés, puis dérouler le processus sur le sujet retenu.

> « Je veux m'entraîner sur un sujet inédit, ne me donne pas le corrigé tout de suite. »

Mode aveugle : intitulés seuls si le sujet est libre, matrice jamais affichée, avancement donné en volumes, seul le fichier du sujet est présenté, et la grille est remise quand l'étudiant la demande.

> « Un sujet de note de synthèse, ce que tu veux. »

Ne rien improviser : dérouler le protocole de veille, proposer trois sujets d'actualité datés et ancrés, puis construire celui que l'utilisateur retient.
