# note-de-synthese-crfpa

Générateur de sujets d'entraînement pour l'épreuve de note de synthèse de
l'examen d'accès au CRFPA (cinq heures, coefficient 3), avec la grille de
notation correspondante.

## Ce que fait le skill

- **Choix du sujet** : à défaut de sujet imposé, le skill mène une veille
  d'actualité juridique (législation récente, textes européens, jurisprudence
  marquante, travaux parlementaires en cours, débats de société) et propose
  trois sujets datés et ancrés dans des pièces vérifiées. Il ne propose
  jamais un sujet de mémoire et écarte ceux qui sont déjà tombés depuis 2017.
- **Dossier documentaire** : 16 à 20 documents, 26 à 35 pages, couvrant les
  cinq registres des sujets réels (textes, jurisprudence, doctrine, documents
  institutionnels ou parlementaires, documents non juridiques). L'ordre des
  documents est tiré au sort sous contraintes, comme dans les annales.
- **Vérification** : chaque référence est contrôlée pendant la session sur sa
  source, et chaque extrait est comparé mécaniquement à la source brute pour
  écarter toute paraphrase.
- **Grille de notation** au modèle de la Commission nationale : résumé de
  chaque document, problématique, thèmes cotés sur 20 points, plan indicatif.
- **Livraison** : deux fichiers Word distincts, le sujet et la grille, pour
  distribuer le dossier sans le corrigé. Un fichier unique est possible sur
  demande.

## Deux modes

- **Mode examinateur** (par défaut) : pour l'enseignant ou le directeur d'IEJ.
  Le skill soumet ses propositions de sujet argumentées, puis la matrice des
  thèmes avant de lancer la collecte.
- **Mode aveugle** : pour l'étudiant qui veut composer lui-même. Le travail
  est identique, mais rien de ce qui prépare le corrigé n'apparaît dans la
  conversation. Seul le sujet est remis ; la grille l'est à la demande.

## Contenu du paquet

    note-de-synthese-crfpa/
    ├── SKILL.md                         instructions et processus
    ├── README.md                        ce fichier
    ├── references/
    │   ├── format_officiel_nds.md       cadre réglementaire, annales 2017-2026,
    │   │                                maquettes, gabarit de la grille
    │   └── sources_documentaires.md     protocole de collecte par registre
    └── scripts/
        ├── build_nds.js                 production des deux fichiers Word
        ├── tirer_ordre.py               tirage de l'ordre des documents
        └── verifier_verbatim.py         contrôle des extraits contre les sources

## Installation

1. Importer le dossier `note-de-synthese-crfpa/` comme compétence dans Claude
   (Personnaliser > Compétences > Ajouter).
2. Activer la **recherche web**, nécessaire à la veille d'actualité et à la
   collecte des documents non juridiques.
3. Connecter les connecteurs juridiques (voir ci-dessous).
4. Autoriser les domaines réseau utiles (Paramètres > Capacités > Domaines
   autorisés, voir ci-dessous).

### Connecteurs

| Connecteur | Statut | Usage |
|---|---|---|
| OpenLegi | **Indispensable** | Textes, Journal officiel, jurisprudence judiciaire, administrative et constitutionnelle |
| GoodLegal | Fortement recommandé | Droit de l'Union (textes et CJUE), résumés juridiques de la CEDH |
| LibreJustice | Facultatif | Jurisprudence judiciaire, source de secours |
| Legal Data Hunter | Facultatif | Droit de l'Union, CEDH, doctrine étrangère |

### Domaines réseau

Les scripts du skill n'interrogent aucun site : le tirage, le contrôle du
verbatim et la production des fichiers Word fonctionnent hors ligne. Les
domaines servent à télécharger la source brute de chaque pièce, ce qui
renforce le contrôle du verbatim. Sans eux, le skill recopie le résultat de
l'outil qui a servi à la recherche et le contrôle fonctionne quand même.

**Recommandés**

- `data.assemblee-nationale.fr`, `www.assemblee-nationale.fr`
- `data.senat.fr`, `www.senat.fr`
- `api.archives-ouvertes.fr`, `hal.science`
- `www.courdecassation.fr`
- `www.vie-publique.fr`

**Si les skills compagnons sont installés**

- `gallica.bnf.fr`, `api.bnf.fr` (archeologue-gallica)
- `api.piste.gouv.fr` (judilibre)
- `api.isidore.science`, `api.openalex.org`, `api.crossref.org`,
  `sudoc.abes.fr`, `theses.fr` (recherche-doctrine)

**Facultatifs, pour les documents non juridiques et européens**

- `www.insee.fr`, `dares.travail-emploi.gouv.fr`,
  `drees.solidarites-sante.gouv.fr`
- `www.ccomptes.fr`, `www.conseil-etat.fr`
- `hudoc.echr.coe.int`, `eur-lex.europa.eu`, `curia.europa.eu`

### Skills compagnons (facultatifs)

Le skill fonctionne seul, mais tire parti des skills suivants lorsqu'ils sont
installés :

- **docx** (natif dans Claude) : rendu des fichiers Word ;
- **judilibre** : jurisprudence judiciaire par l'API de la Cour de cassation
  (clé gratuite à demander sur le portail PISTE) ;
- **travaux-preparatoires** : exposés des motifs, amendements, rapports ;
- **recherche-doctrine** : identification et vérification de la doctrine ;
- **archeologue-gallica** : arrêts de principe anciens et leur note d'origine ;
- **legal-hallucination-checker** : contrôle final des références ;
- **detecteur-tics-ia** : relecture finale du sujet et de la grille.

### Utilisation hors de Claude.ai

Dans Claude.ai, l'environnement fournit déjà tout le nécessaire. Ailleurs
(Claude Code en local, par exemple), il faut installer :

- Node.js et le paquet npm `docx` ;
- LibreOffice et `pdfinfo` (paquet poppler), qui servent à mesurer le nombre
  de pages annoncé sur la page de garde. Sans eux, les fichiers sont produits
  mais ce décompte reste à compléter à la main.

Les deux scripts Python n'utilisent que la bibliothèque standard de Python 3.

## Limites à connaître

- **Sujet d'entraînement, non officiel.** Les fichiers le mentionnent
  expressément ; la Commission nationale n'y figure jamais comme émetteur.
- **Doctrine sous droits.** Les extraits de revues payantes (Dalloz,
  LexisNexis, Lextenso…) ne sont pas reproduits. Chaque dossier comporte un
  ou deux emplacements « extrait à insérer », avec la référence complète, le
  DOI ou le lien, et une notice analytique qui rend le dossier composable
  même si l'enseignant ne colle pas l'extrait. La page de garde indique le
  nombre d'emplacements à compléter.
- **Presse.** Les articles de presse ne sont jamais recopiés : ils font
  l'objet d'une notice factuelle, une seule par dossier sauf nécessité.
- **Un sujet d'actualité vieillit vite.** Le skill indique la date de la
  veille et les pièces les plus récentes, pour savoir quand rafraîchir le
  dossier.
- **Pas de mémoire entre conversations.** Le skill demande au cadrage quels
  sujets ont déjà été traités dans l'IEJ ; il ne peut pas le savoir seul.
- **Mode aveugle.** Les appels d'outils et leurs résultats restent
  consultables dans l'interface : l'étudiant qui veut garder la surprise ne
  doit pas les déplier.
- **Relecture humaine.** Le contrôle automatique repère la paraphrase et les
  références introuvables, mais il ne remplace pas la lecture du dossier par
  l'enseignant avant distribution.

## Exemples de demandes

- « Fais-moi un sujet de note de synthèse sur le secret des affaires, avec le
  corrigé. »
- « J'ai besoin d'un dossier pour un galop d'essai en novembre, sujet libre,
  pas trop pénal. »
- « Je veux m'entraîner sur un sujet inédit, ne me donne pas le corrigé tout
  de suite. »

## Sources

Le skill s'appuie sur des sources publiques : Légifrance, open data de
l'Assemblée nationale et du Sénat, publications de la Cour de cassation, du
Conseil d'État et des autorités administratives indépendantes, archives
ouvertes (HAL, OpenEdition, Persée), statistique publique et rapports publiés
sous la Licence Ouverte d'Etalab. Avant toute reproduction d'un document non
juridique, il vérifie les mentions légales du site et écarte les contenus de
tiers (tribunes signées, infographies, photographies).
