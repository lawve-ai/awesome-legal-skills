# Environnement d'exécution, persistance et livrables

<!-- NOYAU-ANTIHALLUCINATION v4 — synchronisé mandarinat 2.0.0 / assistant-juridique-fr 8.0.0. Fichier commun aux deux skills : toute modification doit être répercutée à l'identique dans l'autre (script sync-noyau.sh). -->

## Sommaire

1. Capacités à constater en début de tâche
2. Où lire les pièces, où écrire les livrables
3. Choix du format du livrable
4. Tableau de vérification : document séparé systématique
5. Vérificateur indépendant (sous-agent)
6. Sources doctrinales et réseau

## 1. Capacités à constater en début de tâche

Depuis septembre 2026, Claude ne distingue plus de « modes » (chat, Cowork, computer use) que l'utilisateur choisirait. Chaque conversation dispose normalement d'un **espace de travail** (système de fichiers, interpréteur Python, scripts de la skill), et peut en outre être **liée à l'ordinateur de l'utilisateur** par l'application de bureau, avec des dossiers connectés. L'ancienne grille COWORK / CHAT_CU / CHAT est abandonnée : on constate les capacités effectivement présentes, sans demander à l'utilisateur de « basculer ».

Constater, sans le commenter à l'utilisateur :

| Capacité | Comment la constater | Conséquence |
|---|---|---|
| Espace de travail (fichiers, Python) | un outil shell ou d'écriture de fichiers est disponible | scripts de la skill exécutables, livrables en fichiers, journal de références |
| Dossier connecté sur l'ordinateur de l'utilisateur | des outils d'accès à l'appareil (liste de dossiers, shell distant) répondent | lecture des pièces sur place, écriture des livrables et du journal dans ce dossier, reprise d'un travail antérieur |
| Sous-agents | un outil de délégation à un agent est disponible | vérification indépendante des références (§ 5), parallélisation des tâches longues |
| Connecteurs juridiques | outils de recherche présents dans la session | voir `guide-librejustice.md`, `guide-openlegi.md`, `guide-themia.md`, `guide-legaldatahunter.md` |

Les connecteurs portent des noms variables selon les comptes (par exemple, le connecteur LegalDataHunter peut apparaître sous un autre intitulé, tel « Droit_compar »). Les identifier **par leur fonction** (outils `search`, `resolve_reference`, `discover_countries`…) plutôt que par le nom du serveur, et charger les outils différés par une recherche d'outils avant de conclure à leur absence.

**Cas résiduel — aucun espace de travail** (exécution de code désactivée dans les paramètres, ou surface sans système de fichiers) : exécuter la tâche en réponse structurée, avec la même rigueur de fond, et produire le tableau de vérification à la main. Pour les tâches qui exigent l'édition d'un fichier Word (commentaires, document miroir, suivi des modifications), indiquer en une phrase que l'activation de « Exécution de code et création de fichiers » dans les paramètres de Claude le permettrait, et proposer ce qui peut être fait sans.

Un document long ou un dossier volumineux ne justifie plus un refus : l'espace de travail permet de le traiter par sections (extraction du texte, travail par lots, écriture progressive du livrable).

## 2. Où lire les pièces, où écrire les livrables

Dans les fichiers de tâches, le **« dossier de travail »** désigne le dossier connecté lorsqu'il existe, à défaut l'espace de travail de la conversation (pièces jointes comprises).

**Pièces.** Les fichiers joints à la conversation sont lisibles directement (leur emplacement varie : ne pas présumer d'un chemin, les retrouver par leur nom). Les fichiers d'un dossier connecté se lisent par les outils d'accès à l'appareil. Ne jamais coder un chemin en dur (`/mnt/user-data/…`, etc.).

**Livrables.**
- **Dossier connecté disponible** : écrire le livrable, le tableau de vérification et le journal de références (`verification/journal-references.ndjson`) **dans ce dossier**, à côté des pièces. C'est ce qui assure la persistance et la reprise d'une conversation à l'autre (documents miroirs partiels des tâches de vérification, productions antérieures).
- **Pas de dossier connecté** : travailler dans l'espace de travail, puis **remettre les fichiers** à l'utilisateur (outil d'envoi de fichiers). L'espace de travail est éphémère : tout ce qui n'est pas remis est perdu à la fin de la conversation — y compris le journal, qui doit donc être remis avec le tableau lorsque sa conservation importe.

**Productions antérieures.** Au début d'une tâche portant sur un dossier connecté, inventorier les productions antérieures de la skill (livrables datés, `verification/`, documents miroirs) et poursuivre le travail plutôt que le refaire.

**Convention de nommage** : `[AAAA-MM-JJ]-[type]-[sujet].[ext]`, et `[AAAA-MM-JJ]-verification-[sujet].[ext]` pour le tableau de vérification.

## 3. Choix du format du livrable

Règle par défaut, posée par l'auteur de la skill et valant instruction permanente :

| Livrable | Défaut | Alternative, sur demande |
|---|---|---|
| Document rédigé (consultation, recherche, acte, corrigé, cours, fiche de TD, note…) | **Word (.docx)**, via la skill `docx` | **artefact Docs** si l'utilisateur demande « un doc », un document à partager ou à éditer en ligne |
| Support de présentation | **PowerPoint (.pptx)**, via la skill `pptx` | **artefact Slides** si l'utilisateur demande des « slides » ou une présentation à éditer en ligne |
| Relecture commentée, document miroir, suivi des modifications, harmonisation | **Word obligatoirement** (commentaires et révisions Word) | — |
| Réponse brève à une question (sans livrable demandé) | réponse dans la conversation | — |

Motif du défaut Word : notes de fin à numérotation continue, commentaires en marge, suivi des modifications, conformité aux usages de l'édition juridique et du contentieux. Si l'utilisateur choisit Docs ou Slides, signaler en une ligne ce qui ne sera pas reproduit à l'identique lorsque la différence importe (en particulier les notes de fin : à défaut de prise en charge, section « Notes et références » numérotée en fin de document).

Structure documentaire type (sauf trame fournie par l'utilisateur, qui prévaut) : synthèse — plan — développement — « Notes et références » (notes de fin, numérotation continue, lien officiel pour chaque référence). Citations entre guillemets français « … ».

**Notes de fin en Word.** Après génération du .docx (pandoc depuis Markdown, ou docx-js), exécuter `python3 scripts/notes_de_fin.py livrable.docx` : conversion des notes de bas de page en notes de fin, numérotation en chiffres arabes (Word numérote par défaut les notes de fin en chiffres romains), détection des appels multiples à une même note (à remplacer par « préc. note n »), report des relations (liens hypertextes) des notes et contrôle d'intégrité. Si le script sort en erreur (`ERREUR_integrite`), le fichier serait déclaré corrompu par Word : ne pas le livrer. Contrôler ensuite le rendu (conversion PDF et lecture) ; LibreOffice tolère des défauts que Word refuse, d'où le contrôle d'intégrité préalable.

## 4. Tableau de vérification : document séparé systématique

Le tableau de vérification (cf. `checklist-pre-livraison.md`) est **systématiquement remis dans un document distinct du livrable**, dès lors que la réponse contient au moins une référence (jurisprudence, texte, doctrine) — y compris lorsque la réponse elle-même reste dans la conversation. Ce document séparé est l'instrument de contrôle de l'utilisateur : il lui permet de vérifier chaque référence sans relire le livrable, et il rend visible toute ligne non confrontée.

Format : Markdown (`[AAAA-MM-JJ]-verification-[sujet].md`, généré par `scripts/reference_journal.py table --out …`), converti en Word si le livrable est en Word et que l'utilisateur le souhaite (`pandoc` ou skill `docx`). Dans le cas résiduel sans espace de travail, le tableau figure en fin de réponse, sous un intertitre distinct.

## 5. Vérificateur indépendant (sous-agent)

Le rédacteur qui a choisi une référence est mal placé pour juger qu'elle soutient l'assertion : il relit ce qu'il croit y avoir lu. Lorsqu'un outil de sous-agent est disponible, confier le contrôle de concordance (étape 3 de la checklist) à un **vérificateur indépendant** :

- **Transmettre** : le livrable (ou ses passages citants), le journal de références, la liste des assertions à contrôler, et le chemin des scripts de la skill. **Ne pas transmettre** le raisonnement du rédacteur ni ses conclusions sur la concordance.
- **Consigne** : pour chaque ligne, rouvrir la source par l'outil (OpenLegi, `LibreJustice:get_decision`, `LibreJustice:get_norm`, fiche HAL/DOI), lire les motifs, le dispositif ou l'alinéa, et répondre **oui / non** à la question « le texte lu fonde-t-il l'assertion telle qu'elle est rédigée ? », avec l'extrait décisif ; signaler toute voix énonciative erronée (cassation), toute décision infirmée (`appellateFate`), toute rédaction non applicable à la date pertinente.
- **Report** : `reference_journal.py mark --index N --independent oui|non --note "…"`. Une ligne « non » du vérificateur bloque la clôture exactement comme une ligne « non » du rédacteur.
- **Volume** : pour un livrable long, répartir les lignes entre plusieurs vérificateurs en parallèle (par lots de 10 à 15 références), en priorité les lignes P1.

Sans outil de sous-agent : procéder soi-même au contrôle, en rouvrant chaque source au lieu de s'en remettre au souvenir de la lecture, et le mentionner dans l'en-tête du tableau (« contrôle non indépendant »).

## 6. Sources doctrinales et réseau

`scripts/doctrine_search.py` interroge HAL, OpenAlex et Isidore, avec résolution Crossref. Selon l'environnement, certaines sources peuvent être injoignables (constaté en septembre 2026 depuis l'espace de travail : HAL et Crossref accessibles ; OpenAlex en limitation de débit ; Isidore injoignable). Le script le signale (`sources_failed`) sans bloquer : compléter alors par la recherche web sur Cairn, Persée, OpenEdition, Dalloz Actualité, et le mentionner dans la section des limites.

Légifrance refuse les requêtes automatisées (challenge anti-bot Cloudflare) : la vérification des références françaises passe **normalement** par OpenLegi et LibreJustice (cf. checklist), non par requête HTTP.
