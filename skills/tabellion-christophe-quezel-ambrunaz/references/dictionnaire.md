# Dictionnaire de données tabellion

Version 0.2.0 du 2026-10-05, projet soumis à critique. Document généré depuis `dictionnaire.json`, qui fait foi ; ne pas modifier ce fichier à la main.

## Conventions

- **Identifiants** : Identifiants en français, en minuscules, sans diacritiques, mots séparés par « _ » (date_naissance). Les libellés affichés sont en français accentué. Raison : une balise saisie dans Word ne doit pas dépendre de la normalisation Unicode des accents (NFC/NFD) ni de la correction automatique.
- **Chemins** : Une balise désigne une valeur par un chemin : rôle ou module, puis champ. Exemples : {{bail.loyer.montant}}, {{bail.bailleur.designation_complete}}, {{acte.date_acte}}.
- **Personnes et rôles** : Les personnes, biens, véhicules et comptes sont saisis une seule fois dans le dossier et désignés par identifiant (P1, B1…). Les modèles déclarent des rôles (module.role) que l'utilisateur rattache aux personnes. La même personne peut tenir des rôles dans plusieurs modèles.
- **Accords** : Le genre et le nombre d'un rôle se déduisent des personnes qui y sont rattachées : singulier ou pluriel selon leur nombre ; au pluriel, féminin seulement si toutes sont de genre féminin (règle traditionnelle ; paramétrable). Une personne morale prend le genre de son nom générique (« la société X, demanderesse »).
- **Termes définis** : Dans les contrats, le rôle est souvent un terme défini invariable (« ci-après le Bailleur »). Le modèle choisit, au balisage, entre terme défini invariable et qualité accordée ; seuls les participes et adjectifs (« dénommé(e) », « né(e) ») s'accordent alors.
- **Absence de règles de droit** : Le dictionnaire ne contient aucune règle de droit ni valeur légale (taux, montants, délais). Les règles qu'un modèle met en œuvre sont arrêtées au balisage avec l'utilisateur, avec leur source ; les valeurs évolutives (indices, taux) sont figées dans le formulaire avec leur date de gel, au-delà de laquelle le calcul est refusé.
- **Champs sensibles** : Les champs marqués sensibles (santé, protection juridique, NIR, IBAN) sont signalés à la saisie ; le formulaire rappelle que le fichier .json n'est pas chiffré.
- **Valeurs fictives** : Les exemples du dictionnaire sont manifestement fictifs (ESSAI, Exempleville, code postal 00000, SIREN 000000000, banque 99999). Préchargés pour le test, ils sont marqués dans le dossier ; le formulaire refuse la génération finale tant qu'une valeur fictive subsiste, sauf confirmation expresse.
- **Un dictionnaire-trame** : Le dictionnaire commun est une trame, jamais bloquante. Le manifeste d'un modèle peut lui ajouter des champs (à une entité, un module, un groupe ou une liste), des modules, des rôles, des attributs de rôle, et modifier des libellés. Rien n'est supprimé : le formulaire n'affiche que ce que le modèle utilise. Les données des extensions sont rangées dans le dossier au même endroit que celles du dictionnaire, ce qui préserve leur réutilisation.
- **Attributs de rôle** : Un attribut de rôle porte une donnée propre à une personne en tant qu'elle tient un rôle dans l'acte (parts cédées, origine de propriété), distincte des données de la personne elle-même.
- **Variables locales** : Une valeur simple propre au modèle, sans vocation à être réutilisée, peut aller dans local.<champ>. Une donnée réutilisable ou structurée relève plutôt d'une extension.
- **Compatibilité** : Le dossier déclare la version du dictionnaire. Les champs inconnus d'un formulaire sont conservés intacts à l'export, pour ne pas détruire les données destinées à un autre modèle.
- **Une instance par module** : Un dossier contient au plus une instance de chaque module (un bail, une instance). Plusieurs instances supposent plusieurs dossiers, en v0.1.

## Format du dossier (.json de l'utilisateur)

- `format` : toujours « tabellion-dossier »
- `version_dictionnaire` : version du dictionnaire utilisée
- `cree_le / modifie_le` : horodatage ISO 8601
- `personnes` : objet { P1: {...}, P2: {...} }
- `biens` : objet { B1: {...} }
- `vehicules` : objet { V1: {...} }
- `comptes` : objet { C1: {...} }
- `roles` : objet { 'module.role': [identifiants] }
- `attributs_roles` : objet { 'module.role': { identifiant: { attribut: valeur } } }
- `types_extensions` : objet { chemin: type } des extensions employées ; permet de déceler un même nom employé avec deux types
- `modules` : objet { module: { champ: valeur } }
- `local` : objet { identifiant_modele: { champ: valeur } }
- `decisions` : objet { identifiant_modele: { options: { id: true|false }, choix: { id: id_cas } } }
- `valeurs_fictives` : liste des chemins encore fictifs
- `extensions` : réservé ; conservé tel quel

## Types

| Type | Description | Rendus |
|---|---|---|
| `texte` | Texte court, sur une ligne. | tel_quel |
| `texte_long` | Texte sur plusieurs lignes ou paragraphes ; les sauts de paragraphe sont reproduits dans le document. |  |
| `entier` | Nombre entier. | chiffres, lettres, ordinal, ordinal_abrege, romain |
| `decimal` | Nombre décimal, virgule décimale à l'affichage. | chiffres, lettres |
| `montant` | Valeur et devise. | chiffres, lettres, lettres_puis_chiffres, chiffres_puis_lettres |
| `pourcentage` | Taux exprimé en pour cent (3,5 et non 0,035). | chiffres, lettres |
| `date` | Date du calendrier grégorien. | longue, courte, lettres, iso |
| `heure` | Heure. | courte, lettres |
| `texte_transformations` | Transformations applicables à toute valeur rendue, après le rendu propre au type. | majuscules, minuscules, initiale_majuscule |
| `duree` | Durée exprimée dans une unité. | chiffres, lettres |
| `booleen` | Oui ou non ; sert de condition aux blocs optionnels. | oui_non |
| `choix` | Une valeur parmi une liste fermée ; chaque valeur porte un libellé, éventuellement un genre. | libelle, long |
| `adresse` | Adresse postale structurée (voir entité adresse). | ligne, bloc |
| `telephone` | Numéro de téléphone, conservé tel que saisi. |  |
| `courriel` | Adresse électronique. |  |
| `identifiant` | Numéro normalisé, contrôlé par une règle de format ou une clé (voir validation du champ). | tel_quel, groupe |
| `reference` | Renvoi vers une entité du dossier (personne, bien, compte) par son identifiant ; jamais de recopie. |  |
| `groupe` | Ensemble de champs formant une unité. |  |
| `liste` | Suite répétable d'éléments ; rendue par énumération, puces, numérotation ou tableau. | nombre, enumeration_ou |

Contrôles des identifiants :

- `siren` : 9 chiffres, clé de Luhn
- `siret` : 14 chiffres, clé de Luhn
- `tva_fr` : FR + clé de 2 chiffres + SIREN ; clé = (12 + 3 × (SIREN mod 97)) mod 97
- `rna` : W + 9 caractères
- `iban` : clé ISO 13616 (modulo 97)
- `nir` : 13 chiffres + clé de 2 chiffres = 97 − (NIR mod 97) ; Corse : 2A → 19, 2B → 18 avant calcul
- `code_postal_fr` : 5 chiffres

## Entités

### Adresse (`adresse`)

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `numero` | Numéro | texte |  |
| `indice` | Indice de répétition | choix : bis / ter / quater |  |
| `voie` | Type et libellé de la voie | texte |  |
| `complement` | Complément (bâtiment, escalier, étage) | texte |  |
| `lieu_dit` | Lieu-dit | texte |  |
| `code_postal` | Code postal | texte |  |
| `commune` | Commune | texte |  |
| `cedex` | Cedex | texte |  |
| `pays` | Pays | texte | Laisser vide pour la France. |


### Personne (`personne`), identifiants P1, P2…

**Champs communs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `nature` | Nature | choix : Personne physique / Personne morale |  |
| `telephone` | Téléphone | telephone |  |
| `courriel` | Courriel | courriel |  |
| `adresse_correspondance` | Adresse de correspondance, si elle diffère | adresse |  |

**Personne physique**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `civilite` | Civilité | choix : Monsieur / Madame |  |
| `nom` | Nom de famille | texte | Rendu en capitales dans les désignations. |
| `nom_naissance` | Nom de naissance, s'il diffère | texte |  |
| `nom_usage` | Nom d'usage | texte |  |
| `prenoms` | Prénoms | texte | Tous les prénoms, dans l'ordre de l'état civil. |
| `prenom_usuel` | Prénom usuel | texte |  |
| `date_naissance` | Date de naissance | date |  |
| `lieu_naissance` | Lieu de naissance | groupe |  |
| `lieu_naissance.commune` | Commune | texte |  |
| `lieu_naissance.departement` | Département (numéro ou nom) | texte |  |
| `lieu_naissance.pays` | Pays, si hors de France | texte |  |
| `nationalite` | Nationalité | texte | Au féminin : « de nationalité française ». |
| `profession` | Profession | texte |  |
| `domicile` | Domicile | adresse |  |
| `capacite` | Capacité | choix : Majeur capable / Mineur / Majeur en tutelle / Majeur en curatelle / Majeur en curatelle renforcée / Majeur sous sauvegarde de justice / Majeur sous habilitation familiale / Majeur bénéficiant d'un mandat de protection future | **sensible** |
| `representants` | Représentants (tuteur, curateur, administrateur légal…) | liste |  |
| `representants[].personne` | Personne | renvoi → personne |  |
| `representants[].qualite` | Qualité | texte |  |
| `representants[].decision` | Décision de désignation (juridiction, date) | texte |  |
| `date_deces` | Date du décès | date |  |
| `lieu_deces` | Lieu du décès | texte |  |
| `nir` | Numéro de sécurité sociale | identifiant (nir) | **sensible** |
| `qualite_professionnelle` | Exercice d'une profession réglementée | groupe |  |
| `qualite_professionnelle.profession_reglementee` | Profession | choix : Avocat / Commissaire de justice / Notaire / Expert judiciaire / Médiateur / Administrateur judiciaire / Mandataire judiciaire / Expert-comptable / … |  |
| `qualite_professionnelle.ressort` | Barreau, compagnie ou ressort | texte |  |
| `qualite_professionnelle.toque` | Toque ou case | texte |  |
| `qualite_professionnelle.structure_exercice` | Structure d'exercice | renvoi → personne (morale) |  |
| `qualite_professionnelle.adresse_professionnelle` | Adresse professionnelle | adresse |  |

**Personne morale**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `forme_juridique` | Forme juridique | choix : SA / SAS / SASU / SARL / EURL / SNC / SCA / SCS / … |  |
| `forme_precisee` | Forme juridique (si « Autre ») | texte |  |
| `genre_grammatical` | Genre grammatical | choix : Masculin / Féminin | Déduit de la forme ; à renseigner seulement pour « Autre » ou pour corriger. |
| `denomination` | Dénomination sociale | texte |  |
| `sigle` | Sigle | texte |  |
| `nom_commercial` | Nom commercial | texte |  |
| `enseigne` | Enseigne | texte |  |
| `capital` | Capital social | montant |  |
| `capital_variable` | Capital variable | booleen |  |
| `immatriculation` | Immatriculation | groupe |  |
| `immatriculation.registre` | Registre | choix : Registre du commerce et des sociétés / Registre national des entreprises / Répertoire des métiers / Répertoire national des associations / Registre étranger / Autre |  |
| `immatriculation.greffe` | Greffe ou ville d'immatriculation | texte |  |
| `immatriculation.numero` | Numéro | texte | Pour le RCS, en principe le SIREN. |
| `siren` | SIREN | identifiant (siren) |  |
| `siret` | SIRET de l'établissement | identifiant (siret) |  |
| `tva_intracommunautaire` | Numéro de TVA intracommunautaire | identifiant (tva_fr) |  |
| `rna` | Numéro RNA | identifiant (rna) |  |
| `siege` | Siège | adresse |  |
| `etablissement` | Établissement concerné, s'il diffère du siège | adresse |  |
| `representants_legaux` | Représentants légaux | liste |  |
| `representants_legaux[].personne` | Personne | renvoi → personne |  |
| `representants_legaux[].qualite` | Qualité | texte |  |
| `representants_legaux[].pouvoirs` | Origine des pouvoirs (statuts, délibération du…) | texte |  |

**Valeurs dérivées** (calculées par le formulaire, jamais saisies)

- `genre` : Personne physique : genre de la civilité. Personne morale : genre_grammatical, à défaut celui de la forme.
- `designation_courte` : « Madame Jeanne ESSAI » ; « la société ALPHA ESSAI » (article + nom générique de la forme + dénomination).
- `designation_complete` : Physique : civilité, prénoms, NOM, « né(e) le … à … », nationalité, profession, « demeurant … ». Morale : nom générique, dénomination, forme longue, capital, immatriculation, siège, « prise en la personne de son représentant légal » ou désignation du représentant. Les éléments vides sont omis avec leur ponctuation. L'ordre et les mentions retenus par un modèle sont fixés au balisage, non par le dictionnaire.
- `nom_complet` : « Jeanne ESSAI » (prénom usuel, à défaut premier prénom, et NOM) ; dénomination pour une personne morale.
- `age` : En années révolues à une date de référence ; la date de référence est TOUJOURS déclarée par le modèle.
- `majeur` : Âge ≥ 18 à la date de référence déclarée par le modèle.


### Bien immobilier (`bien_immobilier`), identifiants B1, B2…

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `nature` | Nature | choix : Appartement / Maison / Local commercial / Local professionnel / Bureaux / Terrain / Immeuble entier / Emplacement de stationnement / … |  |
| `designation` | Désignation | texte_long |  |
| `adresse` | Adresse | adresse |  |
| `batiment` | Bâtiment | texte |  |
| `etage` | Étage | texte |  |
| `cadastre` | Références cadastrales | liste |  |
| `cadastre[].prefixe` | Préfixe | texte |  |
| `cadastre[].section` | Section | texte |  |
| `cadastre[].numero` | Numéro | texte |  |
| `cadastre[].lieu_dit` | Lieu-dit ou adresse cadastrale | texte |  |
| `cadastre[].contenance` | Contenance | texte |  |
| `copropriete` | Bien en copropriété | booleen |  |
| `lots` | Lots de copropriété | liste |  |
| `lots[].numero` | Numéro de lot | texte |  |
| `lots[].description` | Description | texte |  |
| `lots[].tantiemes` | Quote-part des parties communes | texte |  |
| `surface_habitable` | Surface habitable (m²) | decimal |  |
| `surface_privative` | Superficie de la partie privative (m²) | decimal |  |
| `nombre_pieces` | Nombre de pièces principales | entier |  |
| `annexes` | Annexes et dépendances | liste de texte |  |
| `epoque_construction` | Époque ou année de construction | texte |  |
| `classe_energie` | Classe énergétique | choix : A / B / C / D / E / F / G |  |
| `classe_climat` | Classe climat (GES) | choix : A / B / C / D / E / F / G |  |


### Véhicule (`vehicule`), identifiants V1, V2…

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `categorie` | Catégorie | texte |  |
| `marque` | Marque | texte |  |
| `modele` | Modèle | texte |  |
| `immatriculation` | Immatriculation | texte |  |
| `numero_identification` | Numéro d'identification (VIN) | texte |  |
| `date_premiere_immatriculation` | Date de première immatriculation | date |  |
| `proprietaire` | Propriétaire | renvoi → personne |  |


### Compte bancaire (`compte_bancaire`), identifiants C1, C2…

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `titulaire` | Titulaire | renvoi → personne |  |
| `etablissement` | Établissement teneur du compte | texte |  |
| `iban` | IBAN | identifiant (iban) | **sensible** |
| `bic` | BIC | texte |  |

## Modules

### Acte et dossier (`acte`)

Données communes à tout document : références, date et lieu, signataires, annexes. Toujours présent.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `acte.redacteur` | rédacteur | rédactrice | rédacteurs | rédactrices | 0..1 | physique, morale |
| `acte.signataire` | signataire | signataire | signataires | signataires | 0..n | physique, morale |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `acte.reference_interne` | Référence interne du dossier | texte |  |
| `acte.intitule` | Intitulé du document | texte |  |
| `acte.date_acte` | Date de l'acte | date |  |
| `acte.lieu_acte` | Lieu de l'acte | texte |  |
| `acte.nombre_exemplaires` | Nombre d'exemplaires originaux | entier |  |
| `acte.date_reference` | Date de référence des calculs | date | Date à laquelle sont calculés âges, anciennetés et durées écoulées, lorsque le modèle n'en fixe pas d'autre. |
| `acte.annexes` | Annexes | liste |  |
| `acte.annexes[].numero` | Numéro | texte |  |
| `acte.annexes[].intitule` | Intitulé | texte |  |
| `acte.evenements` | Chronologie des faits | liste |  |
| `acte.evenements[].date` | Date | date |  |
| `acte.evenements[].lieu` | Lieu | texte |  |
| `acte.evenements[].description` | Description | texte_long |  |

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Le document est-il daté de sa signature, de son établissement ou laissé en blanc pour la signature manuscrite ?


### Procédure civile et contentieux (`procedure_civile`)

Juridiction, parties à l'instance, conseils, numéros, audiences, décision attaquée, demandes, pièces.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `procedure_civile.demandeur` | demandeur | demanderesse | demandeurs | demanderesses | 1..n | physique, morale |
| `procedure_civile.defendeur` | défendeur | défenderesse | défendeurs | défenderesses | 1..n | physique, morale |
| `procedure_civile.requerant` | requérant | requérante | requérants | requérantes | 1..n | physique, morale |
| `procedure_civile.appelant` | appelant | appelante | appelants | appelantes | 1..n | physique, morale |
| `procedure_civile.intime` | intimé | intimée | intimés | intimées | 1..n | physique, morale |
| `procedure_civile.intervenant_volontaire` | intervenant volontaire | intervenante volontaire | intervenants volontaires | intervenantes volontaires | 0..n | physique, morale |
| `procedure_civile.appele_en_cause` | appelé en cause | appelée en cause | appelés en cause | appelées en cause | 0..n | physique, morale |
| `procedure_civile.creancier_poursuivant` | créancier poursuivant | créancière poursuivante | créanciers poursuivants | créancières poursuivantes | 0..n | physique, morale |
| `procedure_civile.debiteur_saisi` | débiteur saisi | débitrice saisie | débiteurs saisis | débitrices saisies | 0..n | physique, morale |
| `procedure_civile.tiers_saisi` | tiers saisi | tiers saisi | tiers saisis | tiers saisis | 0..n | physique, morale |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `procedure_civile.juridiction` | Juridiction saisie | groupe |  |
| `procedure_civile.juridiction.type` | Juridiction | choix : Tribunal judiciaire / Tribunal de commerce / Tribunal des activités économiques / Conseil de prud'hommes / Tribunal paritaire des baux ruraux / Cour d'appel / Cour de cassation / Tribunal administratif / … |  |
| `procedure_civile.juridiction.ville` | Siège | texte |  |
| `procedure_civile.juridiction.formation` | Formation ou fonction | texte | Ex. : juge aux affaires familiales, juge de l'exécution, juge des contentieux de la protection, président statuant en référé, chambre sociale. |
| `procedure_civile.juridiction.chambre` | Chambre, pôle ou section | texte |  |
| `procedure_civile.juridiction.adresse` | Adresse de la juridiction | adresse |  |
| `procedure_civile.nature_instance` | Nature de l'instance | choix : Instance au fond / Référé / Requête / Procédure accélérée au fond / Injonction de payer / Appel / Pourvoi en cassation / Exécution / … |  |
| `procedure_civile.representation_obligatoire` | Représentation par avocat obligatoire | booleen | Renseigné par l'utilisateur ; le dictionnaire ne le déduit pas. |
| `procedure_civile.numero_rg` | Numéro de répertoire général | texte |  |
| `procedure_civile.numero_portalis` | Numéro Portalis | texte |  |
| `procedure_civile.date_introduction` | Date de l'acte introductif | date |  |
| `procedure_civile.date_signification` | Date de signification | date |  |
| `procedure_civile.audience` | Audience | groupe |  |
| `procedure_civile.audience.date` | Date | date |  |
| `procedure_civile.audience.heure` | Heure | heure |  |
| `procedure_civile.audience.salle` | Salle | texte |  |
| `procedure_civile.audience.nature` | Nature de l'audience | texte | Ex. : orientation, mise en état, plaidoiries. |
| `procedure_civile.decision_attaquee` | Décision attaquée ou exécutée | groupe |  |
| `procedure_civile.decision_attaquee.juridiction` | Juridiction | texte |  |
| `procedure_civile.decision_attaquee.date` | Date | date |  |
| `procedure_civile.decision_attaquee.numero_rg` | Numéro RG | texte |  |
| `procedure_civile.decision_attaquee.nature` | Nature | choix : Jugement / Ordonnance / Arrêt / Sentence arbitrale |  |
| `procedure_civile.decision_attaquee.date_signification` | Date de signification | date |  |
| `procedure_civile.decision_attaquee.chefs_critiques` | Chefs de décision critiqués | texte_long |  |
| `procedure_civile.conseils` | Conseils des parties | liste |  |
| `procedure_civile.conseils[].partie` | Partie | renvoi → personne |  |
| `procedure_civile.conseils[].avocat_postulant` | Avocat postulant | renvoi → personne (physique) |  |
| `procedure_civile.conseils[].avocat_plaidant` | Avocat plaidant | renvoi → personne (physique) |  |
| `procedure_civile.commissaire_de_justice` | Commissaire de justice instrumentaire | renvoi → personne |  |
| `procedure_civile.demandes` | Demandes chiffrées | liste |  |
| `procedure_civile.demandes[].intitule` | Intitulé | texte |  |
| `procedure_civile.demandes[].montant` | Montant | montant |  |
| `procedure_civile.demandes[].fondement` | Fondement invoqué (saisi par l'utilisateur) | texte |  |
| `procedure_civile.frais_irrepetibles` | Frais irrépétibles demandés | montant | Somme demandée au titre de l'article 700 du code de procédure civile. |
| `procedure_civile.distraction_depens` | Distraction des dépens demandée | booleen |  |
| `procedure_civile.bordereau_pieces` | Bordereau de pièces | liste |  |
| `procedure_civile.bordereau_pieces[].numero` | Numéro | texte |  |
| `procedure_civile.bordereau_pieces[].intitule` | Intitulé | texte |  |
| `procedure_civile.bordereau_pieces[].date` | Date | date |  |

**Contrôles de cohérence**

- Chaque partie de la liste « conseils » est rattachée à un rôle du dossier.
- Date d'audience postérieure à la date de l'acte introductif.

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Le modèle calcule-t-il un délai (comparution, appel, prescription) ? Si oui : point de départ, computation (jours francs ou non), report des samedis, dimanches et jours fériés : à arrêter avec l'utilisateur, avec la source.
- Mentions de désignation des parties exigées par l'acte : ordre et contenu à confirmer au balisage.


### Baux (`bail`)

Baux d'habitation, commerciaux, professionnels et dérogatoires : parties, bien, durée, loyer, charges, indexation, garanties.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `bail.bailleur` | bailleur | bailleresse | bailleurs | bailleresses | 1..n | physique, morale |
| `bail.preneur` | preneur | preneuse | preneurs | preneuses | 1..n | physique, morale ; variantes : locataire |
| `bail.caution` | caution | caution | cautions | cautions | 0..n | physique, morale |
| `bail.mandataire_gestion` | mandataire | mandataire | mandataires | mandataires | 0..1 | physique, morale |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `bail.type_bail` | Type de bail | choix : Habitation, logement nu / Habitation, logement meublé / Bail mobilité / Bail commercial / Bail dérogatoire / Bail professionnel / Bail mixte / Autre |  |
| `bail.bien` | Bien loué | renvoi → bien_immobilier |  |
| `bail.destination` | Destination des lieux | texte |  |
| `bail.date_prise_effet` | Date de prise d'effet | date |  |
| `bail.duree` | Durée | duree |  |
| `bail.loyer` | Loyer | groupe |  |
| `bail.loyer.montant` | Montant | montant |  |
| `bail.loyer.periodicite` | Périodicité | choix : mensuel / trimestriel / annuel |  |
| `bail.loyer.terme` | Terme | choix : à échoir / échu |  |
| `bail.loyer.jour_exigibilite` | Jour d'exigibilité | entier |  |
| `bail.loyer.assujetti_tva` | Assujetti à la TVA | booleen |  |
| `bail.charges` | Charges | groupe |  |
| `bail.charges.mode` | Mode | choix : provision avec régularisation / forfait / refacturation au réel |  |
| `bail.charges.montant` | Montant par période | montant |  |
| `bail.depot_garantie` | Dépôt de garantie | montant |  |
| `bail.indexation` | Révision ou indexation | groupe |  |
| `bail.indexation.stipulee` | Clause stipulée | booleen |  |
| `bail.indexation.indice` | Indice | texte | Ex. : IRL, ILC, ILAT, ICC. |
| `bail.indexation.trimestre_reference` | Trimestre de référence | texte |  |
| `bail.indexation.valeur_reference` | Valeur de l'indice de référence | decimal | Donnée évolutive : saisie par l'utilisateur, jamais préremplie. |
| `bail.indexation.date_revision` | Date de révision | texte |  |
| `bail.encadrement` | Encadrement des loyers | groupe |  |
| `bail.encadrement.applicable` | Encadrement applicable | booleen |  |
| `bail.encadrement.loyer_reference` | Loyer de référence (€/m²) | decimal |  |
| `bail.encadrement.loyer_reference_majore` | Loyer de référence majoré (€/m²) | decimal |  |
| `bail.encadrement.complement_loyer` | Complément de loyer | montant |  |
| `bail.encadrement.justification_complement` | Justification du complément | texte_long |  |
| `bail.franchise` | Franchise de loyer | duree |  |
| `bail.droit_entree` | Droit d'entrée ou pas-de-porte | montant |  |
| `bail.clause_resolutoire` | Clause résolutoire | booleen |  |
| `bail.solidarite_preneurs` | Solidarité entre preneurs | booleen |  |
| `bail.garantie` | Garantie | groupe |  |
| `bail.garantie.nature` | Nature | choix : cautionnement simple / cautionnement solidaire / garantie autonome / dispositif public ou paritaire / autre |  |
| `bail.garantie.montant_maximal` | Montant maximal garanti | montant |  |
| `bail.garantie.duree` | Durée de l'engagement | duree |  |
| `bail.date_etat_des_lieux` | Date de l'état des lieux d'entrée | date |  |
| `bail.diagnostics` | Diagnostics annexés | liste |  |
| `bail.diagnostics[].nature` | Nature | texte |  |
| `bail.diagnostics[].date` | Date | date |  |

**Contrôles de cohérence**

- Le bien loué est une entité du dossier ; sa désignation n'est jamais recopiée dans le module.

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Date de fin calculée à partir de la prise d'effet : terme au jour anniversaire ou à la veille ?
- Prorata du premier loyer : par jours calendaires du mois, sur trente jours, ou absent ?
- Montant maximal du dépôt de garantie : le modèle doit-il le contrôler ? Si oui, règle et source à confirmer avec l'utilisateur.


### Droit du travail (`travail`)

Contrat de travail, temps de travail, rémunération, clauses, rupture.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `travail.employeur` | employeur | employeur | employeurs | employeurs | 1..n | physique, morale |
| `travail.salarie` | salarié | salariée | salariés | salariées | 1..n | physique |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `travail.contrat` | Contrat | groupe |  |
| `travail.contrat.nature` | Nature | choix : Contrat à durée indéterminée / Contrat à durée déterminée / Contrat d'apprentissage / Contrat de professionnalisation / Autre |  |
| `travail.contrat.motif_recours` | Motif de recours (CDD) | texte_long |  |
| `travail.contrat.personne_remplacee` | Personne remplacée (CDD de remplacement) | texte |  |
| `travail.contrat.date_debut` | Date d'entrée en fonctions | date |  |
| `travail.contrat.date_terme` | Terme précis (CDD) | date |  |
| `travail.contrat.duree_minimale` | Durée minimale (CDD sans terme précis) | duree |  |
| `travail.contrat.periode_essai` | Période d'essai | groupe |  |
| `travail.contrat.periode_essai.duree` | Durée | duree |  |
| `travail.contrat.periode_essai.renouvelable` | Renouvelable | booleen |  |
| `travail.contrat.periode_essai.duree_renouvellement` | Durée du renouvellement | duree |  |
| `travail.emploi` | Emploi | groupe |  |
| `travail.emploi.intitule` | Intitulé du poste | texte |  |
| `travail.emploi.fonctions` | Fonctions | texte_long |  |
| `travail.emploi.statut` | Statut | texte | Ex. : employé, agent de maîtrise, cadre. |
| `travail.emploi.classification` | Classification (niveau, échelon, coefficient) | texte |  |
| `travail.emploi.convention_collective` | Convention collective (intitulé) | texte |  |
| `travail.emploi.idcc` | IDCC | texte |  |
| `travail.emploi.lieu_travail` | Lieu de travail | adresse |  |
| `travail.temps_travail` | Temps de travail | groupe |  |
| `travail.temps_travail.regime` | Régime | choix : Temps plein / Temps partiel / Forfait en heures / Forfait en jours |  |
| `travail.temps_travail.duree_hebdomadaire` | Durée hebdomadaire (heures) | decimal |  |
| `travail.temps_travail.jours_forfait` | Nombre de jours du forfait annuel | entier |  |
| `travail.temps_travail.repartition` | Répartition des horaires | texte_long |  |
| `travail.remuneration` | Rémunération | groupe |  |
| `travail.remuneration.brut_mensuel` | Salaire brut mensuel | montant |  |
| `travail.remuneration.brut_annuel` | Rémunération brute annuelle | montant |  |
| `travail.remuneration.variable` | Rémunération variable (modalités) | texte_long |  |
| `travail.remuneration.primes` | Primes et avantages | liste |  |
| `travail.remuneration.primes[].intitule` | Intitulé | texte |  |
| `travail.remuneration.primes[].montant` | Montant | montant |  |
| `travail.remuneration.primes[].modalites` | Modalités | texte |  |
| `travail.non_concurrence` | Clause de non-concurrence | groupe |  |
| `travail.non_concurrence.stipulee` | Stipulée | booleen |  |
| `travail.non_concurrence.duree` | Durée | duree |  |
| `travail.non_concurrence.perimetre` | Périmètre géographique | texte |  |
| `travail.non_concurrence.activites` | Activités visées | texte |  |
| `travail.non_concurrence.contrepartie` | Contrepartie financière (expression) | texte | Ex. : « 30 % de la rémunération mensuelle moyenne » : expression saisie, pas de calcul implicite. |
| `travail.mobilite` | Clause de mobilité | groupe |  |
| `travail.mobilite.stipulee` | Stipulée | booleen |  |
| `travail.mobilite.zone` | Zone géographique | texte |  |
| `travail.rupture` | Rupture du contrat | groupe |  |
| `travail.rupture.mode` | Mode de rupture | choix : Licenciement pour motif personnel / Licenciement pour motif économique / Rupture conventionnelle / Démission / Prise d'acte / Résiliation judiciaire / Arrivée du terme du CDD / Rupture de la période d'essai / … |  |
| `travail.rupture.date_convocation` | Date de la convocation à l'entretien préalable | date |  |
| `travail.rupture.date_entretien` | Date de l'entretien préalable | date |  |
| `travail.rupture.date_notification` | Date de notification de la rupture | date |  |
| `travail.rupture.date_fin_contrat` | Date de fin du contrat | date |  |
| `travail.rupture.preavis` | Préavis | groupe |  |
| `travail.rupture.preavis.duree` | Durée | duree |  |
| `travail.rupture.preavis.execution` | Exécution | choix : exécuté / dispensé par l'employeur / non exécuté à la demande du salarié |  |
| `travail.rupture.motifs` | Énoncé des motifs | texte_long |  |
| `travail.rupture.salaire_reference` | Salaire de référence (saisi) | montant | Saisi par l'utilisateur, ou calculé selon une formule arrêtée au balisage. |
| `travail.rupture.sommes` | Sommes dues ou versées | liste |  |
| `travail.rupture.sommes[].intitule` | Intitulé | texte |  |
| `travail.rupture.sommes[].montant` | Montant | montant |  |
| `travail.rupture.sommes[].base_calcul` | Base de calcul affichée | texte |  |

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Ancienneté : arrêtée à la notification, à la fin du préavis exécuté ou non ? Périodes de suspension prises en compte ?
- Salaire de référence : quelle formule, et laquelle retenir si plusieurs sont applicables ?
- Toute indemnité légale ou conventionnelle calculée par le modèle : règle, source, version datée.


### Droit des sociétés (`societes`)

Constitution, capital et titres, apports, associés, dirigeants, décisions collectives, cessions de titres. La société elle-même est une personne morale du dossier.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `societes.societe` | société | société | sociétés | sociétés | 1 | morale |
| `societes.associe` | associé | associée | associés | associées | 0..n | physique, morale |
| `societes.dirigeant` | dirigeant | dirigeante | dirigeants | dirigeantes | 0..n | physique, morale |
| `societes.commissaire_aux_comptes` | commissaire aux comptes | commissaire aux comptes | commissaires aux comptes | commissaires aux comptes | 0..n | physique, morale |
| `societes.cedant` | cédant | cédante | cédants | cédantes | 0..n | physique, morale |
| `societes.cessionnaire` | cessionnaire | cessionnaire | cessionnaires | cessionnaires | 0..n | physique, morale |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `societes.objet_social` | Objet social | texte_long |  |
| `societes.duree_societe` | Durée de la société | duree |  |
| `societes.date_constitution` | Date de signature des statuts | date |  |
| `societes.date_immatriculation` | Date d'immatriculation | date |  |
| `societes.exercice` | Exercice social | groupe |  |
| `societes.exercice.ouverture` | Date d'ouverture (jour et mois) | texte |  |
| `societes.exercice.cloture` | Date de clôture (jour et mois) | texte |  |
| `societes.exercice.cloture_premier_exercice` | Clôture du premier exercice | date |  |
| `societes.titres` | Titres | groupe |  |
| `societes.titres.nature` | Nature | choix : actions / parts sociales |  |
| `societes.titres.nombre` | Nombre total de titres | entier |  |
| `societes.titres.valeur_nominale` | Valeur nominale | montant |  |
| `societes.apports` | Apports | liste |  |
| `societes.apports[].apporteur` | Apporteur | renvoi → personne |  |
| `societes.apports[].nature` | Nature | choix : en numéraire / en nature / en industrie |  |
| `societes.apports[].description` | Description (apport en nature) | texte_long |  |
| `societes.apports[].montant` | Montant ou valeur | montant |  |
| `societes.apports[].titres_attribues` | Titres attribués | entier |  |
| `societes.apports[].liberation` | Fraction libérée (%) | pourcentage |  |
| `societes.repartition` | Répartition du capital | liste |  |
| `societes.repartition[].titulaire` | Titulaire | renvoi → personne |  |
| `societes.repartition[].nombre_titres` | Nombre de titres | entier |  |
| `societes.mandats` | Mandats sociaux | liste |  |
| `societes.mandats[].personne` | Personne | renvoi → personne |  |
| `societes.mandats[].fonction` | Fonction | texte |  |
| `societes.mandats[].date_nomination` | Date de nomination | date |  |
| `societes.mandats[].duree_mandat` | Durée du mandat | texte |  |
| `societes.mandats[].remuneration` | Rémunération (modalités) | texte |  |
| `societes.decision_collective` | Décision collective | groupe |  |
| `societes.decision_collective.nature` | Nature | choix : assemblée générale ordinaire / assemblée générale extraordinaire / assemblée générale mixte / décision unanime constatée dans un acte / décision de l'associé unique / consultation écrite |  |
| `societes.decision_collective.date` | Date | date |  |
| `societes.decision_collective.heure` | Heure | heure |  |
| `societes.decision_collective.lieu` | Lieu | texte |  |
| `societes.decision_collective.mode_convocation` | Mode de convocation | texte |  |
| `societes.decision_collective.date_convocation` | Date de la convocation | date |  |
| `societes.decision_collective.president_seance` | Président de séance | renvoi → personne |  |
| `societes.decision_collective.secretaire` | Secrétaire | renvoi → personne |  |
| `societes.decision_collective.titres_presents` | Titres présents ou représentés | entier |  |
| `societes.decision_collective.ordre_du_jour` | Ordre du jour | liste de texte |  |
| `societes.decision_collective.resolutions` | Résolutions | liste |  |
| `societes.decision_collective.resolutions[].numero` | Numéro | entier |  |
| `societes.decision_collective.resolutions[].intitule` | Intitulé | texte |  |
| `societes.decision_collective.resolutions[].texte` | Texte | texte_long |  |
| `societes.decision_collective.resolutions[].resultat` | Résultat | choix : adoptée / rejetée |  |
| `societes.decision_collective.resolutions[].voix_pour` | Voix pour | entier |  |
| `societes.decision_collective.resolutions[].voix_contre` | Voix contre | entier |  |
| `societes.decision_collective.resolutions[].abstentions` | Abstentions | entier |  |
| `societes.cession_titres` | Cession de titres | groupe |  |
| `societes.cession_titres.nombre` | Nombre de titres cédés | entier |  |
| `societes.cession_titres.prix_unitaire` | Prix unitaire | montant |  |
| `societes.cession_titres.prix_total` | Prix total | montant |  |
| `societes.cession_titres.date_jouissance` | Date de jouissance | date |  |
| `societes.cession_titres.agrement_requis` | Agrément requis | booleen |  |

**Contrôles de cohérence**

- Somme des titres de la répartition = nombre total de titres.
- Nombre de titres × valeur nominale = capital de la société.
- Somme des apports (hors industrie) = capital.
- Prix total = nombre × prix unitaire, si les deux sont saisis.
- Voix pour + contre + abstentions ≤ titres présents ou représentés.

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Règles de quorum et de majorité appliquées par le modèle : légales ou statutaires, et lesquelles ?


### Droit de la famille (`famille`)

Union, régime matrimonial, enfants, autorité parentale, résidence, contribution à l'entretien, prestation compensatoire, patrimoine.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `famille.conjoint_1` | époux | épouse | époux | épouses | 1 | physique ; variantes : partenaire, concubin |
| `famille.conjoint_2` | époux | épouse | époux | épouses | 1 | physique ; variantes : partenaire, concubin |
| `famille.enfant` | enfant | enfant | enfants | enfants | 0..n | physique |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `famille.union` | Union | groupe |  |
| `famille.union.nature` | Nature | choix : mariage / pacte civil de solidarité / concubinage |  |
| `famille.union.date` | Date | date |  |
| `famille.union.lieu` | Lieu (commune) | texte |  |
| `famille.union.regime` | Régime matrimonial ou patrimonial | choix : communauté réduite aux acquêts / séparation de biens / participation aux acquêts / communauté universelle / séparation des patrimoines (pacs) / indivision (pacs) / régime étranger / autre |  |
| `famille.union.contrat_mariage` | Contrat de mariage | groupe |  |
| `famille.union.contrat_mariage.notaire` | Notaire | renvoi → personne (physique) |  |
| `famille.union.contrat_mariage.date` | Date | date |  |
| `famille.union.date_separation` | Date de la séparation de fait | date |  |
| `famille.union.date_mesures_provisoires` | Date de la décision sur les mesures provisoires | date |  |
| `famille.cas_divorce` | Cas de divorce | choix : consentement mutuel par acte sous signature privée / consentement mutuel judiciaire / acceptation du principe de la rupture / altération définitive du lien conjugal / faute |  |
| `famille.enfants` | Situation des enfants | liste |  |
| `famille.enfants[].enfant` | Enfant | renvoi → personne (physique) |  |
| `famille.enfants[].autorite_parentale` | Autorité parentale | choix : exercée en commun / exclusive (conjoint 1) / exclusive (conjoint 2) |  |
| `famille.enfants[].residence` | Résidence | choix : chez le conjoint 1 / chez le conjoint 2 / en alternance / chez un tiers |  |
| `famille.enfants[].droit_visite` | Droit de visite et d'hébergement | choix : classique / élargi / réduit / libre / en espace de rencontre / aucun |  |
| `famille.enfants[].modalites` | Modalités détaillées | texte_long |  |
| `famille.enfants[].contribution` | Contribution à l'entretien et à l'éducation | groupe |  |
| `famille.enfants[].contribution.montant` | Montant | montant |  |
| `famille.enfants[].contribution.periodicite` | Périodicité | choix : mensuelle / annuelle |  |
| `famille.enfants[].contribution.debiteur` | Débiteur | choix : conjoint 1 / conjoint 2 |  |
| `famille.enfants[].contribution.intermediation` | Versement par intermédiation financière | booleen |  |
| `famille.enfants[].contribution.indexation` | Modalités d'indexation | texte |  |
| `famille.prestation_compensatoire` | Prestation compensatoire | groupe |  |
| `famille.prestation_compensatoire.forme` | Forme | choix : capital / rente / mixte |  |
| `famille.prestation_compensatoire.creancier` | Créancier | choix : conjoint 1 / conjoint 2 |  |
| `famille.prestation_compensatoire.montant` | Montant | montant |  |
| `famille.prestation_compensatoire.modalites` | Modalités de versement | texte_long |  |
| `famille.patrimoine` | Éléments du patrimoine | liste |  |
| `famille.patrimoine[].designation` | Désignation | texte |  |
| `famille.patrimoine[].bien` | Bien du dossier, le cas échéant | renvoi → bien_immobilier |  |
| `famille.patrimoine[].qualification` | Qualification | choix : commun / propre (conjoint 1) / propre (conjoint 2) / indivis |  |
| `famille.patrimoine[].valeur` | Valeur | montant |  |
| `famille.patrimoine[].attribution` | Attribution proposée | texte |  |

**Contrôles de cohérence**

- Les références « enfant » de la liste visent des personnes rattachées au rôle enfant.
- Débiteur et créancier désignent l'un des deux conjoints.

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Définition des fins de semaine (« premier week-end du mois ») et des vacances (zone, découpage, années paires ou impaires) : à fixer au balisage.
- Minorité des enfants : appréciée à quelle date de référence ?


### Contrats d'affaires (`contrats_affaires`)

Prestation, vente, distribution, licence, franchise, mandat, agence, cession de fonds de commerce, prêt, garanties ; prix, durée, paiement, responsabilité, litiges.

**Rôles**

| Rôle | Masc. sing. | Fém. sing. | Masc. plur. | Fém. plur. | Cardinalité | Natures |
|---|---|---|---|---|---|---|
| `contrats_affaires.prestataire` | prestataire | prestataire | prestataires | prestataires | 1..n | physique, morale |
| `contrats_affaires.client` | client | cliente | clients | clientes | 1..n | physique, morale |
| `contrats_affaires.vendeur` | vendeur | venderesse | vendeurs | venderesses | 1..n | physique, morale |
| `contrats_affaires.acquereur` | acquéreur | acquéreuse | acquéreurs | acquéreuses | 1..n | physique, morale |
| `contrats_affaires.fournisseur` | fournisseur | fournisseuse | fournisseurs | fournisseuses | 1..n | physique, morale |
| `contrats_affaires.distributeur` | distributeur | distributrice | distributeurs | distributrices | 1..n | physique, morale |
| `contrats_affaires.concedant` | concédant | concédante | concédants | concédantes | 1..n | physique, morale |
| `contrats_affaires.licencie` | licencié | licenciée | licenciés | licenciées | 1..n | physique, morale |
| `contrats_affaires.franchiseur` | franchiseur | franchiseur | franchiseurs | franchiseurs | 1..n | physique, morale |
| `contrats_affaires.franchise` | franchisé | franchisée | franchisés | franchisées | 1..n | physique, morale |
| `contrats_affaires.mandant` | mandant | mandante | mandants | mandantes | 1..n | physique, morale |
| `contrats_affaires.mandataire` | mandataire | mandataire | mandataires | mandataires | 1..n | physique, morale |
| `contrats_affaires.agent_commercial` | agent commercial | agente commerciale | agents commerciaux | agentes commerciales | 1..n | physique, morale |
| `contrats_affaires.cedant` | cédant | cédante | cédants | cédantes | 1..n | physique, morale |
| `contrats_affaires.cessionnaire` | cessionnaire | cessionnaire | cessionnaires | cessionnaires | 1..n | physique, morale |
| `contrats_affaires.preteur` | prêteur | prêteuse | prêteurs | prêteuses | 1..n | physique, morale |
| `contrats_affaires.emprunteur` | emprunteur | emprunteuse | emprunteurs | emprunteuses | 1..n | physique, morale |
| `contrats_affaires.garant` | garant | garante | garants | garantes | 0..n | physique, morale |

**Champs**

| Chemin | Libellé | Type | Remarques |
|---|---|---|---|
| `contrats_affaires.objet` | Objet du contrat | texte_long |  |
| `contrats_affaires.date_effet` | Date d'effet | date |  |
| `contrats_affaires.duree` | Durée | groupe |  |
| `contrats_affaires.duree.duree` | Durée initiale | duree |  |
| `contrats_affaires.duree.reconduction` | Reconduction | choix : aucune / tacite / expresse |  |
| `contrats_affaires.duree.duree_reconduction` | Durée de chaque reconduction | duree |  |
| `contrats_affaires.duree.preavis` | Préavis de non-reconduction ou de résiliation | duree |  |
| `contrats_affaires.prix` | Prix | groupe |  |
| `contrats_affaires.prix.montant` | Montant | montant |  |
| `contrats_affaires.prix.base` | Base | choix : hors taxes / toutes taxes comprises |  |
| `contrats_affaires.prix.taux_tva` | Taux de TVA | pourcentage |  |
| `contrats_affaires.prix.modalites` | Modalités de détermination | texte_long |  |
| `contrats_affaires.prix.paiement` | Paiement | groupe |  |
| `contrats_affaires.prix.paiement.delai` | Délai | duree |  |
| `contrats_affaires.prix.paiement.point_depart` | Point de départ | choix : date d'émission de la facture / fin de mois / livraison ou exécution |  |
| `contrats_affaires.prix.paiement.moyen` | Moyen de paiement | texte |  |
| `contrats_affaires.prix.paiement.penalites_retard` | Pénalités de retard (expression) | texte | Saisie telle que stipulée ; aucun taux légal n'est prérempli. |
| `contrats_affaires.prix.paiement.indemnite_recouvrement` | Indemnité forfaitaire de recouvrement | montant | Saisie par l'utilisateur ; aucun montant légal n'est prérempli. |
| `contrats_affaires.prix.paiement.escompte` | Escompte pour paiement anticipé | texte |  |
| `contrats_affaires.prix.revision` | Révision du prix | groupe |  |
| `contrats_affaires.prix.revision.indice` | Indice | texte |  |
| `contrats_affaires.prix.revision.formule` | Formule | texte_long |  |
| `contrats_affaires.prix.revision.periodicite` | Périodicité | texte |  |
| `contrats_affaires.exclusivite` | Exclusivité | groupe |  |
| `contrats_affaires.exclusivite.stipulee` | Stipulée | booleen |  |
| `contrats_affaires.exclusivite.territoire` | Territoire | texte |  |
| `contrats_affaires.exclusivite.perimetre` | Produits ou services | texte |  |
| `contrats_affaires.exclusivite.beneficiaire` | Bénéficiaire (rôle) | texte |  |
| `contrats_affaires.objectifs` | Objectifs | liste |  |
| `contrats_affaires.objectifs[].periode` | Période | texte |  |
| `contrats_affaires.objectifs[].montant` | Montant | montant |  |
| `contrats_affaires.duree_confidentialite` | Durée de l'obligation de confidentialité | duree |  |
| `contrats_affaires.non_concurrence` | Non-concurrence | groupe |  |
| `contrats_affaires.non_concurrence.stipulee` | Stipulée | booleen |  |
| `contrats_affaires.non_concurrence.duree` | Durée | duree |  |
| `contrats_affaires.non_concurrence.territoire` | Territoire | texte |  |
| `contrats_affaires.non_concurrence.activites` | Activités | texte |  |
| `contrats_affaires.non_concurrence.contrepartie` | Contrepartie | texte |  |
| `contrats_affaires.responsabilite` | Responsabilité et assurance | groupe |  |
| `contrats_affaires.responsabilite.plafond` | Plafond de responsabilité | montant |  |
| `contrats_affaires.responsabilite.base_plafond` | Base du plafond (expression) | texte |  |
| `contrats_affaires.responsabilite.assureur` | Assureur | texte |  |
| `contrats_affaires.responsabilite.police` | Numéro de police | texte |  |
| `contrats_affaires.responsabilite.garantie_assurance` | Montant de garantie | montant |  |
| `contrats_affaires.livraison` | Livraison | groupe |  |
| `contrats_affaires.livraison.incoterm` | Incoterm | choix : EXW / FCA / CPT / CIP / DAP / DPU / DDP / FAS / … |  |
| `contrats_affaires.livraison.version_incoterms` | Version des Incoterms | texte |  |
| `contrats_affaires.livraison.lieu` | Lieu | texte |  |
| `contrats_affaires.livraison.delai` | Délai | duree |  |
| `contrats_affaires.propriete_intellectuelle` | Propriété intellectuelle | groupe |  |
| `contrats_affaires.propriete_intellectuelle.droits` | Droits cédés ou concédés | texte_long |  |
| `contrats_affaires.propriete_intellectuelle.territoire` | Territoire | texte |  |
| `contrats_affaires.propriete_intellectuelle.duree` | Durée | duree |  |
| `contrats_affaires.propriete_intellectuelle.remuneration` | Rémunération | texte |  |
| `contrats_affaires.fonds_de_commerce` | Fonds de commerce cédé | groupe |  |
| `contrats_affaires.fonds_de_commerce.designation` | Désignation et activité | texte_long |  |
| `contrats_affaires.fonds_de_commerce.adresse` | Adresse d'exploitation | adresse |  |
| `contrats_affaires.fonds_de_commerce.elements` | Éléments compris dans la cession | liste de texte |  |
| `contrats_affaires.fonds_de_commerce.prix_incorporels` | Prix des éléments incorporels | montant |  |
| `contrats_affaires.fonds_de_commerce.prix_corporels` | Prix du matériel et des éléments corporels | montant |  |
| `contrats_affaires.fonds_de_commerce.prix_marchandises` | Prix des marchandises | montant |  |
| `contrats_affaires.fonds_de_commerce.chiffres` | Chiffres d'affaires et résultats | liste |  |
| `contrats_affaires.fonds_de_commerce.chiffres[].exercice` | Exercice | texte |  |
| `contrats_affaires.fonds_de_commerce.chiffres[].chiffre_affaires` | Chiffre d'affaires | montant |  |
| `contrats_affaires.fonds_de_commerce.chiffres[].resultat` | Résultat | montant |  |
| `contrats_affaires.fonds_de_commerce.sequestre` | Séquestre | renvoi → personne |  |
| `contrats_affaires.pret` | Prêt | groupe |  |
| `contrats_affaires.pret.capital` | Capital prêté | montant |  |
| `contrats_affaires.pret.taux` | Taux d'intérêt (expression) | texte |  |
| `contrats_affaires.pret.duree` | Durée | duree |  |
| `contrats_affaires.pret.echeancier` | Modalités de remboursement | texte_long |  |
| `contrats_affaires.garantie` | Garantie | groupe |  |
| `contrats_affaires.garantie.nature` | Nature | choix : cautionnement / garantie autonome / lettre d'intention / autre |  |
| `contrats_affaires.garantie.montant_maximal` | Montant maximal | montant |  |
| `contrats_affaires.garantie.duree` | Durée | duree |  |
| `contrats_affaires.litiges` | Règlement des litiges | groupe |  |
| `contrats_affaires.litiges.mode` | Mode | choix : juridictions étatiques / arbitrage / médiation ou conciliation préalable puis juridictions |  |
| `contrats_affaires.litiges.juridiction_competente` | Juridiction désignée | texte |  |
| `contrats_affaires.litiges.institution_arbitrale` | Institution arbitrale ou règlement | texte |  |
| `contrats_affaires.litiges.siege_arbitrage` | Siège de l'arbitrage | texte |  |
| `contrats_affaires.litiges.nombre_arbitres` | Nombre d'arbitres | choix : un / trois |  |
| `contrats_affaires.litiges.langue_arbitrage` | Langue de l'arbitrage | texte |  |
| `contrats_affaires.litiges.loi_applicable` | Loi applicable | texte |  |
| `contrats_affaires.langue_contrat` | Langue du contrat | texte |  |

**Contrôles de cohérence**

- Prix total de cession du fonds = somme des prix ventilés, si le modèle les additionne.
- Montant TTC = montant HT × (1 + taux de TVA), arrondi au centime : règle d'arrondi à confirmer au balisage.

**Questions à poser au balisage si le modèle calcule ou applique une règle**

- Toute valeur légale (taux de pénalités, indemnité forfaitaire, plafonds de délais de paiement) : le modèle la reprend-il telle quelle ou la fait-il saisir ? Si elle est intégrée, source et date de gel à arrêter.

## Modules prévus

`dommage_corporel`, `assurance`, `consommation`, `construction`, `vente_immobiliere`, `successions_liberalites`, `procedures_collectives`, `voies_execution (au-delà du module procédure)`, `droit_penal`, `contentieux_administratif`, `propriete_intellectuelle`, `baux_ruraux`, `securite_sociale`.
