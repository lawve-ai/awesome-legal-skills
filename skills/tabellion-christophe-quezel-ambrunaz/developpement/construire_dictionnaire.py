# -*- coding: utf-8 -*-
"""Construit le dictionnaire de données tabellion (JSON canonique).

Le dictionnaire est un schéma de données, non un recueil de règles de droit :
il ne contient aucune valeur légale par défaut (taux, montants, délais).
Les règles propres à un modèle sont arrêtées au balisage, avec l'utilisateur.
"""
import json, os

VERSION = "0.2.0"
DATE = "2026-10-05"

# ---------------------------------------------------------------- constructeurs
def champ(id, libelle, type, **kw):
    d = {"id": id, "libelle": libelle, "type": type}
    d.update(kw)
    return d

def groupe(id, libelle, champs, **kw):
    return champ(id, libelle, "groupe", champs=champs, **kw)

def liste(id, libelle, champs=None, element=None, **kw):
    d = champ(id, libelle, "liste", **kw)
    if champs is not None:
        d["champs"] = champs
    if element is not None:
        d["element"] = element
    return d

def choix(id, libelle, valeurs, **kw):
    return champ(id, libelle, "choix", valeurs=valeurs, **kw)

def v(id, libelle, **kw):
    d = {"id": id, "libelle": libelle}
    d.update(kw)
    return d

def ref(id, libelle, cible, **kw):
    return champ(id, libelle, "reference", cible=cible, **kw)

def role(id, ms, fs, mp, fp, cardinalite="1..n", natures=("physique", "morale"), **kw):
    d = {"id": id,
         "libelles": {"ms": ms, "fs": fs, "mp": mp, "fp": fp},
         "cardinalite": cardinalite,
         "natures": list(natures)}
    d.update(kw)
    return d

# ---------------------------------------------------------------- types
TYPES = {
    "texte": {"description": "Texte court, sur une ligne.",
              "rendus": ["tel_quel"]},
    "texte_long": {"description": "Texte sur plusieurs lignes ou paragraphes ; les sauts de paragraphe sont reproduits dans le document."},
    "entier": {"description": "Nombre entier.", "rendus": ["chiffres", "lettres", "ordinal", "ordinal_abrege", "romain"]},
    "decimal": {"description": "Nombre décimal, virgule décimale à l'affichage.", "rendus": ["chiffres", "lettres"]},
    "montant": {"description": "Valeur et devise.",
                "stockage": {"valeur": "décimal, point décimal", "devise": "code ISO 4217, EUR par défaut"},
                "rendus": ["chiffres", "lettres", "lettres_puis_chiffres", "chiffres_puis_lettres"],
                "parametres": {"orthographe_nombres": ["traditionnelle", "rectifiee_1990"]}},
    "pourcentage": {"description": "Taux exprimé en pour cent (3,5 et non 0,035).", "rendus": ["chiffres", "lettres"]},
    "date": {"description": "Date du calendrier grégorien.", "stockage": "AAAA-MM-JJ",
             "rendus": ["longue", "courte", "lettres", "iso"],
             "exemples_rendus": {"longue": "5 octobre 2026", "courte": "05/10/2026",
                                 "lettres": "cinq octobre deux mille vingt-six"}},
    "heure": {"description": "Heure.", "stockage": "HH:MM", "rendus": ["courte", "lettres"]},
    "texte_transformations": {"description": "Transformations applicables à toute valeur rendue, après le rendu propre au type.", "rendus": ["majuscules", "minuscules", "initiale_majuscule"]},
    "duree": {"description": "Durée exprimée dans une unité.",
              "stockage": {"valeur": "entier", "unite": ["jours", "semaines", "mois", "annees"]},
              "rendus": ["chiffres", "lettres"]},
    "booleen": {"description": "Oui ou non ; sert de condition aux blocs optionnels.", "rendus": ["oui_non"]},
    "choix": {"description": "Une valeur parmi une liste fermée ; chaque valeur porte un libellé, éventuellement un genre.", "rendus": ["libelle", "long"]},
    "adresse": {"description": "Adresse postale structurée (voir entité adresse).", "rendus": ["ligne", "bloc"]},
    "telephone": {"description": "Numéro de téléphone, conservé tel que saisi."},
    "courriel": {"description": "Adresse électronique.", "validation": "forme local@domaine"},
    "identifiant": {"description": "Numéro normalisé, contrôlé par une règle de format ou une clé (voir validation du champ).", "rendus": ["tel_quel", "groupe"]},
    "reference": {"description": "Renvoi vers une entité du dossier (personne, bien, compte) par son identifiant ; jamais de recopie."},
    "groupe": {"description": "Ensemble de champs formant une unité."},
    "liste": {"description": "Suite répétable d'éléments ; rendue par énumération, puces, numérotation ou tableau.",
              "rendus": ["nombre", "enumeration_ou"]},
}

VALIDATIONS = {
    "siren": "9 chiffres, clé de Luhn",
    "siret": "14 chiffres, clé de Luhn",
    "tva_fr": "FR + clé de 2 chiffres + SIREN ; clé = (12 + 3 × (SIREN mod 97)) mod 97",
    "rna": "W + 9 caractères",
    "iban": "clé ISO 13616 (modulo 97)",
    "nir": "13 chiffres + clé de 2 chiffres = 97 − (NIR mod 97) ; Corse : 2A → 19, 2B → 18 avant calcul",
    "code_postal_fr": "5 chiffres",
}

# ---------------------------------------------------------------- entités
FORMES = [
    v("sa", "SA", long="société anonyme", generique="société", genre="f"),
    v("sas", "SAS", long="société par actions simplifiée", generique="société", genre="f"),
    v("sasu", "SASU", long="société par actions simplifiée unipersonnelle", generique="société", genre="f"),
    v("sarl", "SARL", long="société à responsabilité limitée", generique="société", genre="f"),
    v("eurl", "EURL", long="entreprise unipersonnelle à responsabilité limitée", generique="société", genre="f"),
    v("snc", "SNC", long="société en nom collectif", generique="société", genre="f"),
    v("sca", "SCA", long="société en commandite par actions", generique="société", genre="f"),
    v("scs", "SCS", long="société en commandite simple", generique="société", genre="f"),
    v("sci", "SCI", long="société civile immobilière", generique="société", genre="f"),
    v("sc", "SC", long="société civile", generique="société", genre="f"),
    v("scp", "SCP", long="société civile professionnelle", generique="société", genre="f"),
    v("selarl", "SELARL", long="société d'exercice libéral à responsabilité limitée", generique="société", genre="f"),
    v("selas", "SELAS", long="société d'exercice libéral par actions simplifiée", generique="société", genre="f"),
    v("scop", "SCOP", long="société coopérative de production", generique="société", genre="f"),
    v("gie", "GIE", long="groupement d'intérêt économique", generique="groupement", genre="m"),
    v("association", "Association", long="association", generique="association", genre="f"),
    v("fondation", "Fondation", long="fondation", generique="fondation", genre="f"),
    v("syndicat_coproprietaires", "Syndicat des copropriétaires", long="syndicat des copropriétaires",
      generique="syndicat des copropriétaires", genre="m"),
    v("syndicat_professionnel", "Syndicat professionnel", long="syndicat professionnel", generique="syndicat", genre="m"),
    v("etablissement_public", "Établissement public", long="établissement public", generique="établissement", genre="m"),
    v("commune", "Commune", long="commune", generique="commune", genre="f"),
    v("departement", "Département", long="département", generique="département", genre="m"),
    v("region", "Région", long="région", generique="région", genre="f"),
    v("etat", "État", long="État", generique="État", genre="m"),
    v("societe_etrangere", "Société de droit étranger", long="société de droit étranger", generique="société", genre="f"),
    v("autre", "Autre", aide="Préciser la forme ; le genre grammatical doit alors être renseigné."),
]

ADRESSE = [
    champ("numero", "Numéro", "texte", exemple="12"),
    choix("indice", "Indice de répétition", [v("bis", "bis"), v("ter", "ter"), v("quater", "quater")], exemple=""),
    champ("voie", "Type et libellé de la voie", "texte", exemple="rue de l'Exemple"),
    champ("complement", "Complément (bâtiment, escalier, étage)", "texte", exemple=""),
    champ("lieu_dit", "Lieu-dit", "texte", exemple=""),
    champ("code_postal", "Code postal", "texte", validation="code_postal_fr si pays = France", exemple="00000"),
    champ("commune", "Commune", "texte", exemple="Exempleville"),
    champ("cedex", "Cedex", "texte", exemple=""),
    champ("pays", "Pays", "texte", aide="Laisser vide pour la France.", exemple=""),
]

PHYSIQUE = [
    choix("civilite", "Civilité", [v("monsieur", "Monsieur", genre="m"), v("madame", "Madame", genre="f")],
          exemple="madame"),
    champ("nom", "Nom de famille", "texte", aide="Rendu en capitales dans les désignations.", exemple="ESSAI"),
    champ("nom_naissance", "Nom de naissance, s'il diffère", "texte", exemple=""),
    champ("nom_usage", "Nom d'usage", "texte", exemple=""),
    champ("prenoms", "Prénoms", "texte", aide="Tous les prénoms, dans l'ordre de l'état civil.", exemple="Jeanne, Marie"),
    champ("prenom_usuel", "Prénom usuel", "texte", exemple="Jeanne"),
    champ("date_naissance", "Date de naissance", "date", exemple="1980-01-15"),
    groupe("lieu_naissance", "Lieu de naissance", [
        champ("commune", "Commune", "texte", exemple="Exempleville"),
        champ("departement", "Département (numéro ou nom)", "texte", exemple="99"),
        champ("pays", "Pays, si hors de France", "texte", exemple=""),
    ]),
    champ("nationalite", "Nationalité", "texte", aide="Au féminin : « de nationalité française ».", exemple="française"),
    champ("profession", "Profession", "texte", exemple="architecte"),
    champ("domicile", "Domicile", "adresse"),
    choix("capacite", "Capacité", [
        v("majeur_capable", "Majeur capable"),
        v("mineur", "Mineur"),
        v("tutelle", "Majeur en tutelle"),
        v("curatelle", "Majeur en curatelle"),
        v("curatelle_renforcee", "Majeur en curatelle renforcée"),
        v("sauvegarde_justice", "Majeur sous sauvegarde de justice"),
        v("habilitation_familiale", "Majeur sous habilitation familiale"),
        v("mandat_protection_future", "Majeur bénéficiant d'un mandat de protection future"),
    ], sensible=True, exemple="majeur_capable"),
    liste("representants", "Représentants (tuteur, curateur, administrateur légal…)", champs=[
        ref("personne", "Personne", "personne"),
        champ("qualite", "Qualité", "texte", exemple="tuteur"),
        champ("decision", "Décision de désignation (juridiction, date)", "texte"),
    ]),
    champ("date_deces", "Date du décès", "date", exemple=""),
    champ("lieu_deces", "Lieu du décès", "texte", exemple=""),
    champ("nir", "Numéro de sécurité sociale", "identifiant", validation="nir", sensible=True,
          exemple="100019999999980"),
    groupe("qualite_professionnelle", "Exercice d'une profession réglementée", [
        choix("profession_reglementee", "Profession", [
            v("avocat", "Avocat"), v("commissaire_de_justice", "Commissaire de justice"),
            v("notaire", "Notaire"), v("expert_judiciaire", "Expert judiciaire"),
            v("mediateur", "Médiateur"), v("administrateur_judiciaire", "Administrateur judiciaire"),
            v("mandataire_judiciaire", "Mandataire judiciaire"), v("expert_comptable", "Expert-comptable"),
            v("commissaire_aux_comptes", "Commissaire aux comptes"), v("autre", "Autre")]),
        champ("ressort", "Barreau, compagnie ou ressort", "texte", exemple="Exempleville"),
        champ("toque", "Toque ou case", "texte"),
        ref("structure_exercice", "Structure d'exercice", "personne", natures=["morale"]),
        champ("adresse_professionnelle", "Adresse professionnelle", "adresse"),
    ]),
]

MORALE = [
    choix("forme_juridique", "Forme juridique", FORMES, exemple="sas"),
    champ("forme_precisee", "Forme juridique (si « Autre »)", "texte", exemple=""),
    choix("genre_grammatical", "Genre grammatical", [v("m", "Masculin"), v("f", "Féminin")],
          aide="Déduit de la forme ; à renseigner seulement pour « Autre » ou pour corriger."),
    champ("denomination", "Dénomination sociale", "texte", exemple="ALPHA ESSAI"),
    champ("sigle", "Sigle", "texte", exemple=""),
    champ("nom_commercial", "Nom commercial", "texte", exemple=""),
    champ("enseigne", "Enseigne", "texte", exemple=""),
    champ("capital", "Capital social", "montant", exemple={"valeur": 10000, "devise": "EUR"}),
    champ("capital_variable", "Capital variable", "booleen", exemple=False),
    groupe("immatriculation", "Immatriculation", [
        choix("registre", "Registre", [
            v("rcs", "Registre du commerce et des sociétés"),
            v("rne", "Registre national des entreprises"),
            v("rm", "Répertoire des métiers"),
            v("rna", "Répertoire national des associations"),
            v("etranger", "Registre étranger"), v("autre", "Autre")], exemple="rcs"),
        champ("greffe", "Greffe ou ville d'immatriculation", "texte", exemple="Exempleville"),
        champ("numero", "Numéro", "texte", aide="Pour le RCS, en principe le SIREN.", exemple="000 000 000"),
    ]),
    champ("siren", "SIREN", "identifiant", validation="siren", exemple="000000000"),
    champ("siret", "SIRET de l'établissement", "identifiant", validation="siret", exemple=""),
    champ("tva_intracommunautaire", "Numéro de TVA intracommunautaire", "identifiant", validation="tva_fr",
          exemple="FR12000000000"),
    champ("rna", "Numéro RNA", "identifiant", validation="rna", exemple=""),
    champ("siege", "Siège", "adresse"),
    champ("etablissement", "Établissement concerné, s'il diffère du siège", "adresse", exemple=""),
    liste("representants_legaux", "Représentants légaux", champs=[
        ref("personne", "Personne", "personne"),
        champ("qualite", "Qualité", "texte", exemple="président"),
        champ("pouvoirs", "Origine des pouvoirs (statuts, délibération du…)", "texte"),
    ]),
]

ENTITES = {
    "adresse": {"libelle": "Adresse", "champs": ADRESSE},
    "personne": {
        "libelle": "Personne",
        "prefixe_identifiant": "P",
        "discriminant": "nature",
        "commun": [
            choix("nature", "Nature", [v("physique", "Personne physique"), v("morale", "Personne morale")]),
            champ("telephone", "Téléphone", "telephone"),
            champ("courriel", "Courriel", "courriel"),
            champ("adresse_correspondance", "Adresse de correspondance, si elle diffère", "adresse", exemple=""),
        ],
        "physique": PHYSIQUE,
        "morale": MORALE,
        "derives": [
            v("genre", "Genre grammatical",
              regle="Personne physique : genre de la civilité. Personne morale : genre_grammatical, à défaut celui de la forme."),
            v("designation_courte", "Désignation courte",
              regle="« Madame Jeanne ESSAI » ; « la société ALPHA ESSAI » (article + nom générique de la forme + dénomination)."),
            v("designation_complete", "Désignation complète",
              regle="Physique : civilité, prénoms, NOM, « né(e) le … à … », nationalité, profession, « demeurant … ». "
                    "Morale : nom générique, dénomination, forme longue, capital, immatriculation, siège, "
                    "« prise en la personne de son représentant légal » ou désignation du représentant. "
                    "Les éléments vides sont omis avec leur ponctuation. L'ordre et les mentions retenus par un modèle "
                    "sont fixés au balisage, non par le dictionnaire."),
            v("nom_complet", "Nom complet", regle="« Jeanne ESSAI » (prénom usuel, à défaut premier prénom, et NOM) ; dénomination pour une personne morale."),
            v("age", "Âge", regle="En années révolues à une date de référence ; la date de référence est TOUJOURS déclarée par le modèle."),
            v("majeur", "Majorité", regle="Âge ≥ 18 à la date de référence déclarée par le modèle."),
        ],
    },
    "bien_immobilier": {
        "libelle": "Bien immobilier",
        "prefixe_identifiant": "B",
        "champs": [
            choix("nature", "Nature", [
                v("appartement", "Appartement"), v("maison", "Maison"), v("local_commercial", "Local commercial"),
                v("local_professionnel", "Local professionnel"), v("bureaux", "Bureaux"), v("terrain", "Terrain"),
                v("immeuble", "Immeuble entier"), v("stationnement", "Emplacement de stationnement"),
                v("cave", "Cave"), v("autre", "Autre")], exemple="appartement"),
            champ("designation", "Désignation", "texte_long", exemple="Un appartement de trois pièces principales."),
            champ("adresse", "Adresse", "adresse"),
            champ("batiment", "Bâtiment", "texte"),
            champ("etage", "Étage", "texte", exemple="2e"),
            liste("cadastre", "Références cadastrales", champs=[
                champ("prefixe", "Préfixe", "texte"),
                champ("section", "Section", "texte", exemple="AB"),
                champ("numero", "Numéro", "texte", exemple="123"),
                champ("lieu_dit", "Lieu-dit ou adresse cadastrale", "texte"),
                champ("contenance", "Contenance", "texte", exemple="00 ha 05 a 20 ca"),
            ]),
            champ("copropriete", "Bien en copropriété", "booleen", exemple=True),
            liste("lots", "Lots de copropriété", champs=[
                champ("numero", "Numéro de lot", "texte", exemple="12"),
                champ("description", "Description", "texte"),
                champ("tantiemes", "Quote-part des parties communes", "texte", exemple="125/10000"),
            ]),
            champ("surface_habitable", "Surface habitable (m²)", "decimal", exemple=62.5),
            champ("surface_privative", "Superficie de la partie privative (m²)", "decimal"),
            champ("nombre_pieces", "Nombre de pièces principales", "entier", exemple=3),
            liste("annexes", "Annexes et dépendances", element="texte"),
            champ("epoque_construction", "Époque ou année de construction", "texte"),
            choix("classe_energie", "Classe énergétique", [v(c, c) for c in "ABCDEFG"]),
            choix("classe_climat", "Classe climat (GES)", [v(c, c) for c in "ABCDEFG"]),
        ],
    },
    "vehicule": {
        "libelle": "Véhicule",
        "prefixe_identifiant": "V",
        "champs": [
            champ("categorie", "Catégorie", "texte", exemple="voiture particulière"),
            champ("marque", "Marque", "texte"),
            champ("modele", "Modèle", "texte"),
            champ("immatriculation", "Immatriculation", "texte"),
            champ("numero_identification", "Numéro d'identification (VIN)", "texte"),
            champ("date_premiere_immatriculation", "Date de première immatriculation", "date"),
            ref("proprietaire", "Propriétaire", "personne"),
        ],
    },
    "compte_bancaire": {
        "libelle": "Compte bancaire",
        "prefixe_identifiant": "C",
        "champs": [
            ref("titulaire", "Titulaire", "personne"),
            champ("etablissement", "Établissement teneur du compte", "texte", exemple="BANQUE EXEMPLE"),
            champ("iban", "IBAN", "identifiant", validation="iban", sensible=True,
                  exemple="FR7699999000000000000000130"),
            champ("bic", "BIC", "texte"),
        ],
    },
}

# ---------------------------------------------------------------- modules
MODULES = []

MODULES.append({
    "id": "acte",
    "libelle": "Acte et dossier",
    "description": "Données communes à tout document : références, date et lieu, signataires, annexes. Toujours présent.",
    "roles": [
        role("redacteur", "rédacteur", "rédactrice", "rédacteurs", "rédactrices", "0..1"),
        role("signataire", "signataire", "signataire", "signataires", "signataires", "0..n"),
    ],
    "champs": [
        champ("reference_interne", "Référence interne du dossier", "texte", exemple="ESSAI-2026-001"),
        champ("intitule", "Intitulé du document", "texte"),
        champ("date_acte", "Date de l'acte", "date", exemple="2026-10-05"),
        champ("lieu_acte", "Lieu de l'acte", "texte", exemple="Exempleville"),
        champ("nombre_exemplaires", "Nombre d'exemplaires originaux", "entier", exemple=2),
        champ("date_reference", "Date de référence des calculs", "date",
              aide="Date à laquelle sont calculés âges, anciennetés et durées écoulées, lorsque le modèle n'en fixe pas d'autre."),
        liste("annexes", "Annexes", champs=[
            champ("numero", "Numéro", "texte"),
            champ("intitule", "Intitulé", "texte"),
        ]),
        liste("evenements", "Chronologie des faits", champs=[
            champ("date", "Date", "date"),
            champ("lieu", "Lieu", "texte"),
            champ("description", "Description", "texte_long"),
        ]),
    ],
    "points_a_trancher": [
        "Le document est-il daté de sa signature, de son établissement ou laissé en blanc pour la signature manuscrite ?",
    ],
})

MODULES.append({
    "id": "procedure_civile",
    "libelle": "Procédure civile et contentieux",
    "description": "Juridiction, parties à l'instance, conseils, numéros, audiences, décision attaquée, demandes, pièces.",
    "roles": [
        role("demandeur", "demandeur", "demanderesse", "demandeurs", "demanderesses"),
        role("defendeur", "défendeur", "défenderesse", "défendeurs", "défenderesses"),
        role("requerant", "requérant", "requérante", "requérants", "requérantes"),
        role("appelant", "appelant", "appelante", "appelants", "appelantes"),
        role("intime", "intimé", "intimée", "intimés", "intimées"),
        role("intervenant_volontaire", "intervenant volontaire", "intervenante volontaire",
             "intervenants volontaires", "intervenantes volontaires", "0..n"),
        role("appele_en_cause", "appelé en cause", "appelée en cause", "appelés en cause", "appelées en cause", "0..n"),
        role("creancier_poursuivant", "créancier poursuivant", "créancière poursuivante",
             "créanciers poursuivants", "créancières poursuivantes", "0..n"),
        role("debiteur_saisi", "débiteur saisi", "débitrice saisie", "débiteurs saisis", "débitrices saisies", "0..n"),
        role("tiers_saisi", "tiers saisi", "tiers saisi", "tiers saisis", "tiers saisis", "0..n",
             aide="Usage invariable en genre dans la pratique ; modifiable au balisage."),
    ],
    "champs": [
        groupe("juridiction", "Juridiction saisie", [
            choix("type", "Juridiction", [
                v("tribunal_judiciaire", "Tribunal judiciaire", genre="m"),
                v("tribunal_de_commerce", "Tribunal de commerce", genre="m"),
                v("tribunal_activites_economiques", "Tribunal des activités économiques", genre="m"),
                v("conseil_de_prudhommes", "Conseil de prud'hommes", genre="m"),
                v("tribunal_paritaire_baux_ruraux", "Tribunal paritaire des baux ruraux", genre="m"),
                v("cour_d_appel", "Cour d'appel", genre="f"),
                v("cour_de_cassation", "Cour de cassation", genre="f"),
                v("tribunal_administratif", "Tribunal administratif", genre="m"),
                v("cour_administrative_d_appel", "Cour administrative d'appel", genre="f"),
                v("conseil_d_etat", "Conseil d'État", genre="m"),
                v("autre", "Autre")], exemple="tribunal_judiciaire"),
            champ("ville", "Siège", "texte", exemple="Exempleville"),
            champ("formation", "Formation ou fonction", "texte",
                  aide="Ex. : juge aux affaires familiales, juge de l'exécution, juge des contentieux de la protection, président statuant en référé, chambre sociale.",
                  exemple="président statuant en référé"),
            champ("chambre", "Chambre, pôle ou section", "texte"),
            champ("adresse", "Adresse de la juridiction", "adresse"),
        ]),
        choix("nature_instance", "Nature de l'instance", [
            v("fond", "Instance au fond"), v("refere", "Référé"), v("requete", "Requête"),
            v("procedure_accelere_fond", "Procédure accélérée au fond"),
            v("injonction_payer", "Injonction de payer"), v("appel", "Appel"),
            v("cassation", "Pourvoi en cassation"), v("execution", "Exécution"), v("autre", "Autre")],
            exemple="refere"),
        champ("representation_obligatoire", "Représentation par avocat obligatoire", "booleen",
              aide="Renseigné par l'utilisateur ; le dictionnaire ne le déduit pas."),
        champ("numero_rg", "Numéro de répertoire général", "texte"),
        champ("numero_portalis", "Numéro Portalis", "texte"),
        champ("date_introduction", "Date de l'acte introductif", "date"),
        champ("date_signification", "Date de signification", "date"),
        groupe("audience", "Audience", [
            champ("date", "Date", "date", exemple="2026-12-01"),
            champ("heure", "Heure", "heure", exemple="09:30"),
            champ("salle", "Salle", "texte"),
            champ("nature", "Nature de l'audience", "texte", aide="Ex. : orientation, mise en état, plaidoiries."),
        ]),
        groupe("decision_attaquee", "Décision attaquée ou exécutée", [
            champ("juridiction", "Juridiction", "texte"),
            champ("date", "Date", "date"),
            champ("numero_rg", "Numéro RG", "texte"),
            choix("nature", "Nature", [v("jugement", "Jugement", genre="m"), v("ordonnance", "Ordonnance", genre="f"),
                                        v("arret", "Arrêt", genre="m"), v("sentence", "Sentence arbitrale", genre="f")]),
            champ("date_signification", "Date de signification", "date"),
            champ("chefs_critiques", "Chefs de décision critiqués", "texte_long"),
        ]),
        liste("conseils", "Conseils des parties", champs=[
            ref("partie", "Partie", "personne"),
            ref("avocat_postulant", "Avocat postulant", "personne", natures=["physique"]),
            ref("avocat_plaidant", "Avocat plaidant", "personne", natures=["physique"]),
        ]),
        ref("commissaire_de_justice", "Commissaire de justice instrumentaire", "personne"),
        liste("demandes", "Demandes chiffrées", champs=[
            champ("intitule", "Intitulé", "texte"),
            champ("montant", "Montant", "montant"),
            champ("fondement", "Fondement invoqué (saisi par l'utilisateur)", "texte"),
        ]),
        champ("frais_irrepetibles", "Frais irrépétibles demandés", "montant",
              aide="Somme demandée au titre de l'article 700 du code de procédure civile."),
        champ("distraction_depens", "Distraction des dépens demandée", "booleen"),
        liste("bordereau_pieces", "Bordereau de pièces", champs=[
            champ("numero", "Numéro", "texte", exemple="1"),
            champ("intitule", "Intitulé", "texte", exemple="Contrat de bail"),
            champ("date", "Date", "date"),
        ]),
    ],
    "controles": [
        "Chaque partie de la liste « conseils » est rattachée à un rôle du dossier.",
        "Date d'audience postérieure à la date de l'acte introductif.",
    ],
    "points_a_trancher": [
        "Le modèle calcule-t-il un délai (comparution, appel, prescription) ? Si oui : point de départ, computation (jours francs ou non), report des samedis, dimanches et jours fériés : à arrêter avec l'utilisateur, avec la source.",
        "Mentions de désignation des parties exigées par l'acte : ordre et contenu à confirmer au balisage.",
    ],
})

MODULES.append({
    "id": "bail",
    "libelle": "Baux",
    "description": "Baux d'habitation, commerciaux, professionnels et dérogatoires : parties, bien, durée, loyer, charges, indexation, garanties.",
    "roles": [
        role("bailleur", "bailleur", "bailleresse", "bailleurs", "bailleresses"),
        role("preneur", "preneur", "preneuse", "preneurs", "preneuses",
             variantes={"locataire": {"ms": "locataire", "fs": "locataire", "mp": "locataires", "fp": "locataires"}}),
        role("caution", "caution", "caution", "cautions", "cautions", "0..n"),
        role("mandataire_gestion", "mandataire", "mandataire", "mandataires", "mandataires", "0..1"),
    ],
    "champs": [
        choix("type_bail", "Type de bail", [
            v("habitation_vide", "Habitation, logement nu"), v("habitation_meublee", "Habitation, logement meublé"),
            v("mobilite", "Bail mobilité"), v("commercial", "Bail commercial"),
            v("derogatoire", "Bail dérogatoire"), v("professionnel", "Bail professionnel"),
            v("mixte", "Bail mixte"), v("autre", "Autre")], exemple="habitation_vide"),
        ref("bien", "Bien loué", "bien_immobilier"),
        champ("destination", "Destination des lieux", "texte", exemple="habitation principale"),
        champ("date_prise_effet", "Date de prise d'effet", "date", exemple="2026-11-01"),
        champ("duree", "Durée", "duree", exemple={"valeur": 3, "unite": "annees"}),
        groupe("loyer", "Loyer", [
            champ("montant", "Montant", "montant", exemple={"valeur": 850, "devise": "EUR"}),
            choix("periodicite", "Périodicité", [v("mensuel", "mensuel"), v("trimestriel", "trimestriel"),
                                                  v("annuel", "annuel")], exemple="mensuel"),
            choix("terme", "Terme", [v("a_echoir", "à échoir"), v("echu", "échu")], exemple="a_echoir"),
            champ("jour_exigibilite", "Jour d'exigibilité", "entier", exemple=1),
            champ("assujetti_tva", "Assujetti à la TVA", "booleen", exemple=False),
        ]),
        groupe("charges", "Charges", [
            choix("mode", "Mode", [v("provision", "provision avec régularisation"), v("forfait", "forfait"),
                                   v("refacturation", "refacturation au réel")], exemple="provision"),
            champ("montant", "Montant par période", "montant", exemple={"valeur": 60, "devise": "EUR"}),
        ]),
        champ("depot_garantie", "Dépôt de garantie", "montant", exemple={"valeur": 850, "devise": "EUR"}),
        groupe("indexation", "Révision ou indexation", [
            champ("stipulee", "Clause stipulée", "booleen", exemple=True),
            champ("indice", "Indice", "texte", aide="Ex. : IRL, ILC, ILAT, ICC.", exemple="IRL"),
            champ("trimestre_reference", "Trimestre de référence", "texte", exemple="2e trimestre 2026"),
            champ("valeur_reference", "Valeur de l'indice de référence", "decimal",
                  aide="Donnée évolutive : saisie par l'utilisateur, jamais préremplie."),
            champ("date_revision", "Date de révision", "texte", exemple="chaque date anniversaire du bail"),
        ]),
        groupe("encadrement", "Encadrement des loyers", [
            champ("applicable", "Encadrement applicable", "booleen"),
            champ("loyer_reference", "Loyer de référence (€/m²)", "decimal"),
            champ("loyer_reference_majore", "Loyer de référence majoré (€/m²)", "decimal"),
            champ("complement_loyer", "Complément de loyer", "montant"),
            champ("justification_complement", "Justification du complément", "texte_long"),
        ]),
        champ("franchise", "Franchise de loyer", "duree"),
        champ("droit_entree", "Droit d'entrée ou pas-de-porte", "montant"),
        champ("clause_resolutoire", "Clause résolutoire", "booleen", exemple=True),
        champ("solidarite_preneurs", "Solidarité entre preneurs", "booleen", exemple=True),
        groupe("garantie", "Garantie", [
            choix("nature", "Nature", [v("caution_simple", "cautionnement simple"),
                                       v("caution_solidaire", "cautionnement solidaire"),
                                       v("garantie_autonome", "garantie autonome"),
                                       v("dispositif_public", "dispositif public ou paritaire"), v("autre", "autre")]),
            champ("montant_maximal", "Montant maximal garanti", "montant"),
            champ("duree", "Durée de l'engagement", "duree"),
        ]),
        champ("date_etat_des_lieux", "Date de l'état des lieux d'entrée", "date"),
        liste("diagnostics", "Diagnostics annexés", champs=[
            champ("nature", "Nature", "texte"), champ("date", "Date", "date")]),
    ],
    "controles": [
        "Le bien loué est une entité du dossier ; sa désignation n'est jamais recopiée dans le module.",
    ],
    "points_a_trancher": [
        "Date de fin calculée à partir de la prise d'effet : terme au jour anniversaire ou à la veille ?",
        "Prorata du premier loyer : par jours calendaires du mois, sur trente jours, ou absent ?",
        "Montant maximal du dépôt de garantie : le modèle doit-il le contrôler ? Si oui, règle et source à confirmer avec l'utilisateur.",
    ],
})

MODULES.append({
    "id": "travail",
    "libelle": "Droit du travail",
    "description": "Contrat de travail, temps de travail, rémunération, clauses, rupture.",
    "roles": [
        role("employeur", "employeur", "employeur", "employeurs", "employeurs",
             aide="La pratique emploie « l'employeur » quel que soit le genre ; modifiable au balisage."),
        role("salarie", "salarié", "salariée", "salariés", "salariées", "1..n", natures=["physique"]),
    ],
    "champs": [
        groupe("contrat", "Contrat", [
            choix("nature", "Nature", [v("cdi", "Contrat à durée indéterminée"), v("cdd", "Contrat à durée déterminée"),
                                       v("apprentissage", "Contrat d'apprentissage"),
                                       v("professionnalisation", "Contrat de professionnalisation"),
                                       v("autre", "Autre")], exemple="cdi"),
            champ("motif_recours", "Motif de recours (CDD)", "texte_long"),
            champ("personne_remplacee", "Personne remplacée (CDD de remplacement)", "texte"),
            champ("date_debut", "Date d'entrée en fonctions", "date", exemple="2026-11-02"),
            champ("date_terme", "Terme précis (CDD)", "date"),
            champ("duree_minimale", "Durée minimale (CDD sans terme précis)", "duree"),
            groupe("periode_essai", "Période d'essai", [
                champ("duree", "Durée", "duree", exemple={"valeur": 2, "unite": "mois"}),
                champ("renouvelable", "Renouvelable", "booleen", exemple=False),
                champ("duree_renouvellement", "Durée du renouvellement", "duree")]),
        ]),
        groupe("emploi", "Emploi", [
            champ("intitule", "Intitulé du poste", "texte", exemple="assistant juridique"),
            champ("fonctions", "Fonctions", "texte_long"),
            champ("statut", "Statut", "texte", aide="Ex. : employé, agent de maîtrise, cadre."),
            champ("classification", "Classification (niveau, échelon, coefficient)", "texte"),
            champ("convention_collective", "Convention collective (intitulé)", "texte"),
            champ("idcc", "IDCC", "texte"),
            champ("lieu_travail", "Lieu de travail", "adresse"),
        ]),
        groupe("temps_travail", "Temps de travail", [
            choix("regime", "Régime", [v("temps_plein", "Temps plein"), v("temps_partiel", "Temps partiel"),
                                       v("forfait_heures", "Forfait en heures"), v("forfait_jours", "Forfait en jours")],
                  exemple="temps_plein"),
            champ("duree_hebdomadaire", "Durée hebdomadaire (heures)", "decimal", exemple=35),
            champ("jours_forfait", "Nombre de jours du forfait annuel", "entier"),
            champ("repartition", "Répartition des horaires", "texte_long"),
        ]),
        groupe("remuneration", "Rémunération", [
            champ("brut_mensuel", "Salaire brut mensuel", "montant", exemple={"valeur": 2500, "devise": "EUR"}),
            champ("brut_annuel", "Rémunération brute annuelle", "montant"),
            champ("variable", "Rémunération variable (modalités)", "texte_long"),
            liste("primes", "Primes et avantages", champs=[
                champ("intitule", "Intitulé", "texte"), champ("montant", "Montant", "montant"),
                champ("modalites", "Modalités", "texte")]),
        ]),
        groupe("non_concurrence", "Clause de non-concurrence", [
            champ("stipulee", "Stipulée", "booleen", exemple=False),
            champ("duree", "Durée", "duree"),
            champ("perimetre", "Périmètre géographique", "texte"),
            champ("activites", "Activités visées", "texte"),
            champ("contrepartie", "Contrepartie financière (expression)", "texte",
                  aide="Ex. : « 30 % de la rémunération mensuelle moyenne » : expression saisie, pas de calcul implicite."),
        ]),
        groupe("mobilite", "Clause de mobilité", [
            champ("stipulee", "Stipulée", "booleen", exemple=False),
            champ("zone", "Zone géographique", "texte")]),
        groupe("rupture", "Rupture du contrat", [
            choix("mode", "Mode de rupture", [
                v("licenciement_personnel", "Licenciement pour motif personnel"),
                v("licenciement_economique", "Licenciement pour motif économique"),
                v("rupture_conventionnelle", "Rupture conventionnelle"),
                v("demission", "Démission"), v("prise_d_acte", "Prise d'acte"),
                v("resiliation_judiciaire", "Résiliation judiciaire"),
                v("fin_cdd", "Arrivée du terme du CDD"), v("rupture_periode_essai", "Rupture de la période d'essai"),
                v("depart_retraite", "Départ à la retraite"), v("mise_retraite", "Mise à la retraite"),
                v("autre", "Autre")]),
            champ("date_convocation", "Date de la convocation à l'entretien préalable", "date"),
            champ("date_entretien", "Date de l'entretien préalable", "date"),
            champ("date_notification", "Date de notification de la rupture", "date"),
            champ("date_fin_contrat", "Date de fin du contrat", "date"),
            groupe("preavis", "Préavis", [
                champ("duree", "Durée", "duree"),
                choix("execution", "Exécution", [v("execute", "exécuté"), v("dispense", "dispensé par l'employeur"),
                                                 v("non_execute", "non exécuté à la demande du salarié")])]),
            champ("motifs", "Énoncé des motifs", "texte_long"),
            champ("salaire_reference", "Salaire de référence (saisi)", "montant",
                  aide="Saisi par l'utilisateur, ou calculé selon une formule arrêtée au balisage."),
            liste("sommes", "Sommes dues ou versées", champs=[
                champ("intitule", "Intitulé", "texte"), champ("montant", "Montant", "montant"),
                champ("base_calcul", "Base de calcul affichée", "texte")]),
        ]),
    ],
    "points_a_trancher": [
        "Ancienneté : arrêtée à la notification, à la fin du préavis exécuté ou non ? Périodes de suspension prises en compte ?",
        "Salaire de référence : quelle formule, et laquelle retenir si plusieurs sont applicables ?",
        "Toute indemnité légale ou conventionnelle calculée par le modèle : règle, source, version datée.",
    ],
})

MODULES.append({
    "id": "societes",
    "libelle": "Droit des sociétés",
    "description": "Constitution, capital et titres, apports, associés, dirigeants, décisions collectives, cessions de titres. La société elle-même est une personne morale du dossier.",
    "roles": [
        role("societe", "société", "société", "sociétés", "sociétés", "1", natures=["morale"],
             aide="Désignation par le nom générique de la forme."),
        role("associe", "associé", "associée", "associés", "associées", "0..n"),
        role("dirigeant", "dirigeant", "dirigeante", "dirigeants", "dirigeantes", "0..n"),
        role("commissaire_aux_comptes", "commissaire aux comptes", "commissaire aux comptes",
             "commissaires aux comptes", "commissaires aux comptes", "0..n"),
        role("cedant", "cédant", "cédante", "cédants", "cédantes", "0..n"),
        role("cessionnaire", "cessionnaire", "cessionnaire", "cessionnaires", "cessionnaires", "0..n"),
    ],
    "champs": [
        champ("objet_social", "Objet social", "texte_long"),
        champ("duree_societe", "Durée de la société", "duree", exemple={"valeur": 99, "unite": "annees"}),
        champ("date_constitution", "Date de signature des statuts", "date"),
        champ("date_immatriculation", "Date d'immatriculation", "date"),
        groupe("exercice", "Exercice social", [
            champ("ouverture", "Date d'ouverture (jour et mois)", "texte", exemple="1er janvier"),
            champ("cloture", "Date de clôture (jour et mois)", "texte", exemple="31 décembre"),
            champ("cloture_premier_exercice", "Clôture du premier exercice", "date")]),
        groupe("titres", "Titres", [
            choix("nature", "Nature", [v("actions", "actions", genre="f"), v("parts_sociales", "parts sociales", genre="f")],
                  exemple="actions"),
            champ("nombre", "Nombre total de titres", "entier", exemple=1000),
            champ("valeur_nominale", "Valeur nominale", "montant", exemple={"valeur": 10, "devise": "EUR"})]),
        liste("apports", "Apports", champs=[
            ref("apporteur", "Apporteur", "personne"),
            choix("nature", "Nature", [v("numeraire", "en numéraire"), v("nature", "en nature"),
                                       v("industrie", "en industrie")]),
            champ("description", "Description (apport en nature)", "texte_long"),
            champ("montant", "Montant ou valeur", "montant"),
            champ("titres_attribues", "Titres attribués", "entier"),
            champ("liberation", "Fraction libérée (%)", "pourcentage")]),
        liste("repartition", "Répartition du capital", champs=[
            ref("titulaire", "Titulaire", "personne"),
            champ("nombre_titres", "Nombre de titres", "entier")]),
        liste("mandats", "Mandats sociaux", champs=[
            ref("personne", "Personne", "personne"),
            champ("fonction", "Fonction", "texte", exemple="président"),
            champ("date_nomination", "Date de nomination", "date"),
            champ("duree_mandat", "Durée du mandat", "texte"),
            champ("remuneration", "Rémunération (modalités)", "texte")]),
        groupe("decision_collective", "Décision collective", [
            choix("nature", "Nature", [v("ago", "assemblée générale ordinaire", genre="f"),
                                       v("age", "assemblée générale extraordinaire", genre="f"),
                                       v("agm", "assemblée générale mixte", genre="f"),
                                       v("unanime_acte", "décision unanime constatée dans un acte", genre="f"),
                                       v("associe_unique", "décision de l'associé unique", genre="f"),
                                       v("consultation_ecrite", "consultation écrite", genre="f")]),
            champ("date", "Date", "date"), champ("heure", "Heure", "heure"),
            champ("lieu", "Lieu", "texte"),
            champ("mode_convocation", "Mode de convocation", "texte"),
            champ("date_convocation", "Date de la convocation", "date"),
            ref("president_seance", "Président de séance", "personne"),
            ref("secretaire", "Secrétaire", "personne"),
            champ("titres_presents", "Titres présents ou représentés", "entier"),
            liste("ordre_du_jour", "Ordre du jour", element="texte"),
            liste("resolutions", "Résolutions", champs=[
                champ("numero", "Numéro", "entier"),
                champ("intitule", "Intitulé", "texte"),
                champ("texte", "Texte", "texte_long"),
                choix("resultat", "Résultat", [v("adoptee", "adoptée", genre="f"), v("rejetee", "rejetée", genre="f")]),
                champ("voix_pour", "Voix pour", "entier"), champ("voix_contre", "Voix contre", "entier"),
                champ("abstentions", "Abstentions", "entier")])]),
        groupe("cession_titres", "Cession de titres", [
            champ("nombre", "Nombre de titres cédés", "entier"),
            champ("prix_unitaire", "Prix unitaire", "montant"),
            champ("prix_total", "Prix total", "montant"),
            champ("date_jouissance", "Date de jouissance", "date"),
            champ("agrement_requis", "Agrément requis", "booleen")]),
    ],
    "controles": [
        "Somme des titres de la répartition = nombre total de titres.",
        "Nombre de titres × valeur nominale = capital de la société.",
        "Somme des apports (hors industrie) = capital.",
        "Prix total = nombre × prix unitaire, si les deux sont saisis.",
        "Voix pour + contre + abstentions ≤ titres présents ou représentés.",
    ],
    "points_a_trancher": [
        "Règles de quorum et de majorité appliquées par le modèle : légales ou statutaires, et lesquelles ?",
    ],
})

MODULES.append({
    "id": "famille",
    "libelle": "Droit de la famille",
    "description": "Union, régime matrimonial, enfants, autorité parentale, résidence, contribution à l'entretien, prestation compensatoire, patrimoine.",
    "roles": [
        role("conjoint_1", "époux", "épouse", "époux", "épouses", "1", natures=["physique"],
             variantes={"partenaire": {"ms": "partenaire", "fs": "partenaire", "mp": "partenaires", "fp": "partenaires"},
                        "concubin": {"ms": "concubin", "fs": "concubine", "mp": "concubins", "fp": "concubines"}}),
        role("conjoint_2", "époux", "épouse", "époux", "épouses", "1", natures=["physique"],
             variantes={"partenaire": {"ms": "partenaire", "fs": "partenaire", "mp": "partenaires", "fp": "partenaires"},
                        "concubin": {"ms": "concubin", "fs": "concubine", "mp": "concubins", "fp": "concubines"}}),
        role("enfant", "enfant", "enfant", "enfants", "enfants", "0..n", natures=["physique"]),
    ],
    "champs": [
        groupe("union", "Union", [
            choix("nature", "Nature", [v("mariage", "mariage"), v("pacs", "pacte civil de solidarité"),
                                       v("concubinage", "concubinage")], exemple="mariage"),
            champ("date", "Date", "date"),
            champ("lieu", "Lieu (commune)", "texte"),
            choix("regime", "Régime matrimonial ou patrimonial", [
                v("communaute_legale", "communauté réduite aux acquêts"),
                v("separation_biens", "séparation de biens"),
                v("participation_acquets", "participation aux acquêts"),
                v("communaute_universelle", "communauté universelle"),
                v("pacs_separation", "séparation des patrimoines (pacs)"),
                v("pacs_indivision", "indivision (pacs)"), v("etranger", "régime étranger"), v("autre", "autre")]),
            groupe("contrat_mariage", "Contrat de mariage", [
                ref("notaire", "Notaire", "personne", natures=["physique"]),
                champ("date", "Date", "date")]),
            champ("date_separation", "Date de la séparation de fait", "date"),
            champ("date_mesures_provisoires", "Date de la décision sur les mesures provisoires", "date")]),
        choix("cas_divorce", "Cas de divorce", [
            v("consentement_mutuel_conventionnel", "consentement mutuel par acte sous signature privée"),
            v("consentement_mutuel_judiciaire", "consentement mutuel judiciaire"),
            v("acceptation", "acceptation du principe de la rupture"),
            v("alteration_definitive", "altération définitive du lien conjugal"),
            v("faute", "faute")]),
        liste("enfants", "Situation des enfants", champs=[
            ref("enfant", "Enfant", "personne", natures=["physique"]),
            choix("autorite_parentale", "Autorité parentale", [
                v("conjointe", "exercée en commun"), v("exclusive_conjoint_1", "exclusive (conjoint 1)"),
                v("exclusive_conjoint_2", "exclusive (conjoint 2)")]),
            choix("residence", "Résidence", [v("conjoint_1", "chez le conjoint 1"), v("conjoint_2", "chez le conjoint 2"),
                                             v("alternee", "en alternance"), v("tiers", "chez un tiers")]),
            choix("droit_visite", "Droit de visite et d'hébergement", [
                v("classique", "classique"), v("elargi", "élargi"), v("reduit", "réduit"), v("libre", "libre"),
                v("espace_rencontre", "en espace de rencontre"), v("aucun", "aucun")]),
            champ("modalites", "Modalités détaillées", "texte_long"),
            groupe("contribution", "Contribution à l'entretien et à l'éducation", [
                champ("montant", "Montant", "montant"),
                choix("periodicite", "Périodicité", [v("mensuelle", "mensuelle"), v("annuelle", "annuelle")]),
                choix("debiteur", "Débiteur", [v("conjoint_1", "conjoint 1"), v("conjoint_2", "conjoint 2")]),
                champ("intermediation", "Versement par intermédiation financière", "booleen"),
                champ("indexation", "Modalités d'indexation", "texte")])]),
        groupe("prestation_compensatoire", "Prestation compensatoire", [
            choix("forme", "Forme", [v("capital", "capital"), v("rente", "rente"), v("mixte", "mixte")]),
            choix("creancier", "Créancier", [v("conjoint_1", "conjoint 1"), v("conjoint_2", "conjoint 2")]),
            champ("montant", "Montant", "montant"),
            champ("modalites", "Modalités de versement", "texte_long")]),
        liste("patrimoine", "Éléments du patrimoine", champs=[
            champ("designation", "Désignation", "texte"),
            ref("bien", "Bien du dossier, le cas échéant", "bien_immobilier"),
            choix("qualification", "Qualification", [v("commun", "commun"), v("propre_conjoint_1", "propre (conjoint 1)"),
                                                     v("propre_conjoint_2", "propre (conjoint 2)"), v("indivis", "indivis")]),
            champ("valeur", "Valeur", "montant"),
            champ("attribution", "Attribution proposée", "texte")]),
    ],
    "controles": [
        "Les références « enfant » de la liste visent des personnes rattachées au rôle enfant.",
        "Débiteur et créancier désignent l'un des deux conjoints.",
    ],
    "points_a_trancher": [
        "Définition des fins de semaine (« premier week-end du mois ») et des vacances (zone, découpage, années paires ou impaires) : à fixer au balisage.",
        "Minorité des enfants : appréciée à quelle date de référence ?",
    ],
})

MODULES.append({
    "id": "contrats_affaires",
    "libelle": "Contrats d'affaires",
    "description": "Prestation, vente, distribution, licence, franchise, mandat, agence, cession de fonds de commerce, prêt, garanties ; prix, durée, paiement, responsabilité, litiges.",
    "roles": [
        role("prestataire", "prestataire", "prestataire", "prestataires", "prestataires"),
        role("client", "client", "cliente", "clients", "clientes"),
        role("vendeur", "vendeur", "venderesse", "vendeurs", "venderesses"),
        role("acquereur", "acquéreur", "acquéreuse", "acquéreurs", "acquéreuses"),
        role("fournisseur", "fournisseur", "fournisseuse", "fournisseurs", "fournisseuses"),
        role("distributeur", "distributeur", "distributrice", "distributeurs", "distributrices"),
        role("concedant", "concédant", "concédante", "concédants", "concédantes"),
        role("licencie", "licencié", "licenciée", "licenciés", "licenciées"),
        role("franchiseur", "franchiseur", "franchiseur", "franchiseurs", "franchiseurs"),
        role("franchise", "franchisé", "franchisée", "franchisés", "franchisées"),
        role("mandant", "mandant", "mandante", "mandants", "mandantes"),
        role("mandataire", "mandataire", "mandataire", "mandataires", "mandataires"),
        role("agent_commercial", "agent commercial", "agente commerciale", "agents commerciaux", "agentes commerciales"),
        role("cedant", "cédant", "cédante", "cédants", "cédantes"),
        role("cessionnaire", "cessionnaire", "cessionnaire", "cessionnaires", "cessionnaires"),
        role("preteur", "prêteur", "prêteuse", "prêteurs", "prêteuses"),
        role("emprunteur", "emprunteur", "emprunteuse", "emprunteurs", "emprunteuses"),
        role("garant", "garant", "garante", "garants", "garantes", "0..n"),
    ],
    "champs": [
        champ("objet", "Objet du contrat", "texte_long"),
        champ("date_effet", "Date d'effet", "date"),
        groupe("duree", "Durée", [
            champ("duree", "Durée initiale", "duree"),
            choix("reconduction", "Reconduction", [v("aucune", "aucune"), v("tacite", "tacite"), v("expresse", "expresse")]),
            champ("duree_reconduction", "Durée de chaque reconduction", "duree"),
            champ("preavis", "Préavis de non-reconduction ou de résiliation", "duree")]),
        groupe("prix", "Prix", [
            champ("montant", "Montant", "montant"),
            choix("base", "Base", [v("ht", "hors taxes"), v("ttc", "toutes taxes comprises")]),
            champ("taux_tva", "Taux de TVA", "pourcentage"),
            champ("modalites", "Modalités de détermination", "texte_long"),
            groupe("paiement", "Paiement", [
                champ("delai", "Délai", "duree"),
                choix("point_depart", "Point de départ", [v("facture", "date d'émission de la facture"),
                                                          v("fin_de_mois", "fin de mois"),
                                                          v("livraison", "livraison ou exécution")]),
                champ("moyen", "Moyen de paiement", "texte"),
                champ("penalites_retard", "Pénalités de retard (expression)", "texte",
                      aide="Saisie telle que stipulée ; aucun taux légal n'est prérempli."),
                champ("indemnite_recouvrement", "Indemnité forfaitaire de recouvrement", "montant",
                      aide="Saisie par l'utilisateur ; aucun montant légal n'est prérempli."),
                champ("escompte", "Escompte pour paiement anticipé", "texte")]),
            groupe("revision", "Révision du prix", [
                champ("indice", "Indice", "texte"), champ("formule", "Formule", "texte_long"),
                champ("periodicite", "Périodicité", "texte")])]),
        groupe("exclusivite", "Exclusivité", [
            champ("stipulee", "Stipulée", "booleen"),
            champ("territoire", "Territoire", "texte"),
            champ("perimetre", "Produits ou services", "texte"),
            champ("beneficiaire", "Bénéficiaire (rôle)", "texte")]),
        liste("objectifs", "Objectifs", champs=[
            champ("periode", "Période", "texte"), champ("montant", "Montant", "montant")]),
        champ("duree_confidentialite", "Durée de l'obligation de confidentialité", "duree"),
        groupe("non_concurrence", "Non-concurrence", [
            champ("stipulee", "Stipulée", "booleen"),
            champ("duree", "Durée", "duree"), champ("territoire", "Territoire", "texte"),
            champ("activites", "Activités", "texte"), champ("contrepartie", "Contrepartie", "texte")]),
        groupe("responsabilite", "Responsabilité et assurance", [
            champ("plafond", "Plafond de responsabilité", "montant"),
            champ("base_plafond", "Base du plafond (expression)", "texte"),
            champ("assureur", "Assureur", "texte"), champ("police", "Numéro de police", "texte"),
            champ("garantie_assurance", "Montant de garantie", "montant")]),
        groupe("livraison", "Livraison", [
            choix("incoterm", "Incoterm", [v(c, c) for c in
                                           ["EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF"]]),
            champ("version_incoterms", "Version des Incoterms", "texte", exemple="2020"),
            champ("lieu", "Lieu", "texte"), champ("delai", "Délai", "duree")]),
        groupe("propriete_intellectuelle", "Propriété intellectuelle", [
            champ("droits", "Droits cédés ou concédés", "texte_long"),
            champ("territoire", "Territoire", "texte"), champ("duree", "Durée", "duree"),
            champ("remuneration", "Rémunération", "texte")]),
        groupe("fonds_de_commerce", "Fonds de commerce cédé", [
            champ("designation", "Désignation et activité", "texte_long"),
            champ("adresse", "Adresse d'exploitation", "adresse"),
            liste("elements", "Éléments compris dans la cession", element="texte"),
            champ("prix_incorporels", "Prix des éléments incorporels", "montant"),
            champ("prix_corporels", "Prix du matériel et des éléments corporels", "montant"),
            champ("prix_marchandises", "Prix des marchandises", "montant"),
            liste("chiffres", "Chiffres d'affaires et résultats", champs=[
                champ("exercice", "Exercice", "texte"),
                champ("chiffre_affaires", "Chiffre d'affaires", "montant"),
                champ("resultat", "Résultat", "montant")]),
            ref("sequestre", "Séquestre", "personne")]),
        groupe("pret", "Prêt", [
            champ("capital", "Capital prêté", "montant"),
            champ("taux", "Taux d'intérêt (expression)", "texte"),
            champ("duree", "Durée", "duree"),
            champ("echeancier", "Modalités de remboursement", "texte_long")]),
        groupe("garantie", "Garantie", [
            choix("nature", "Nature", [v("cautionnement", "cautionnement"), v("garantie_autonome", "garantie autonome"),
                                       v("lettre_intention", "lettre d'intention"), v("autre", "autre")]),
            champ("montant_maximal", "Montant maximal", "montant"),
            champ("duree", "Durée", "duree")]),
        groupe("litiges", "Règlement des litiges", [
            choix("mode", "Mode", [v("juridictions", "juridictions étatiques"), v("arbitrage", "arbitrage"),
                                   v("mediation_prealable", "médiation ou conciliation préalable puis juridictions")]),
            champ("juridiction_competente", "Juridiction désignée", "texte"),
            champ("institution_arbitrale", "Institution arbitrale ou règlement", "texte"),
            champ("siege_arbitrage", "Siège de l'arbitrage", "texte"),
            choix("nombre_arbitres", "Nombre d'arbitres", [v("1", "un"), v("3", "trois")]),
            champ("langue_arbitrage", "Langue de l'arbitrage", "texte"),
            champ("loi_applicable", "Loi applicable", "texte")]),
        champ("langue_contrat", "Langue du contrat", "texte"),
    ],
    "controles": [
        "Prix total de cession du fonds = somme des prix ventilés, si le modèle les additionne.",
        "Montant TTC = montant HT × (1 + taux de TVA), arrondi au centime : règle d'arrondi à confirmer au balisage.",
    ],
    "points_a_trancher": [
        "Toute valeur légale (taux de pénalités, indemnité forfaitaire, plafonds de délais de paiement) : le modèle la reprend-il telle quelle ou la fait-il saisir ? Si elle est intégrée, source et date de gel à arrêter.",
    ],
})

MODULES_PREVUS = [
    "dommage_corporel", "assurance", "consommation", "construction", "vente_immobiliere",
    "successions_liberalites", "procedures_collectives", "voies_execution (au-delà du module procédure)",
    "droit_penal", "contentieux_administratif", "propriete_intellectuelle", "baux_ruraux",
    "securite_sociale",
]

CONVENTIONS = {
    "identifiants": "Identifiants en français, en minuscules, sans diacritiques, mots séparés par « _ » (date_naissance). "
                    "Les libellés affichés sont en français accentué. Raison : une balise saisie dans Word ne doit pas dépendre "
                    "de la normalisation Unicode des accents (NFC/NFD) ni de la correction automatique.",
    "chemins": "Une balise désigne une valeur par un chemin : rôle ou module, puis champ. "
               "Exemples : {{bail.loyer.montant}}, {{bail.bailleur.designation_complete}}, {{acte.date_acte}}.",
    "personnes_et_roles": "Les personnes, biens, véhicules et comptes sont saisis une seule fois dans le dossier et désignés "
                          "par identifiant (P1, B1…). Les modèles déclarent des rôles (module.role) que l'utilisateur "
                          "rattache aux personnes. La même personne peut tenir des rôles dans plusieurs modèles.",
    "accords": "Le genre et le nombre d'un rôle se déduisent des personnes qui y sont rattachées : singulier ou pluriel selon "
               "leur nombre ; au pluriel, féminin seulement si toutes sont de genre féminin (règle traditionnelle ; paramétrable). "
               "Une personne morale prend le genre de son nom générique (« la société X, demanderesse »).",
    "termes_definis": "Dans les contrats, le rôle est souvent un terme défini invariable (« ci-après le Bailleur »). "
                      "Le modèle choisit, au balisage, entre terme défini invariable et qualité accordée ; seuls les "
                      "participes et adjectifs (« dénommé(e) », « né(e) ») s'accordent alors.",
    "absence_de_regles_de_droit": "Le dictionnaire ne contient aucune règle de droit ni valeur légale (taux, montants, délais). "
                                  "Les règles qu'un modèle met en œuvre sont arrêtées au balisage avec l'utilisateur, avec leur "
                                  "source ; les valeurs évolutives (indices, taux) sont figées dans le formulaire avec leur date "
                                  "de gel, au-delà de laquelle le calcul est refusé.",
    "champs_sensibles": "Les champs marqués sensibles (santé, protection juridique, NIR, IBAN) sont signalés à la saisie ; le "
                        "formulaire rappelle que le fichier .json n'est pas chiffré.",
    "valeurs_fictives": "Les exemples du dictionnaire sont manifestement fictifs (ESSAI, Exempleville, code postal 00000, "
                        "SIREN 000000000, banque 99999). Préchargés pour le test, ils sont marqués dans le dossier ; le "
                        "formulaire refuse la génération finale tant qu'une valeur fictive subsiste, sauf confirmation expresse.",
    "trame": "Le dictionnaire commun est une trame, jamais bloquante. Le manifeste d'un modèle peut lui ajouter des champs "
             "(à une entité, un module, un groupe ou une liste), des modules, des rôles, des attributs de rôle, et modifier des "
             "libellés. Rien n'est supprimé : le formulaire n'affiche que ce que le modèle utilise. Les données des extensions "
             "sont rangées dans le dossier au même endroit que celles du dictionnaire, ce qui préserve leur réutilisation.",
    "attributs_de_role": "Un attribut de rôle porte une donnée propre à une personne en tant qu'elle tient un rôle dans l'acte "
                         "(parts cédées, origine de propriété), distincte des données de la personne elle-même.",
    "variables_locales": "Une valeur simple propre au modèle, sans vocation à être réutilisée, peut aller dans local.<champ>. "
                         "Une donnée réutilisable ou structurée relève plutôt d'une extension.",
    "compatibilite": "Le dossier déclare la version du dictionnaire. Les champs inconnus d'un formulaire sont conservés "
                     "intacts à l'export, pour ne pas détruire les données destinées à un autre modèle.",
    "une_instance_par_module": "Un dossier contient au plus une instance de chaque module (un bail, une instance). "
                               "Plusieurs instances supposent plusieurs dossiers, en v0.1.",
}

DOSSIER_FORMAT = {
    "format": "tabellion-dossier",
    "cles": {
        "format": "toujours « tabellion-dossier »",
        "version_dictionnaire": "version du dictionnaire utilisée",
        "cree_le / modifie_le": "horodatage ISO 8601",
        "personnes": "objet { P1: {...}, P2: {...} }",
        "biens": "objet { B1: {...} }",
        "vehicules": "objet { V1: {...} }",
        "comptes": "objet { C1: {...} }",
        "roles": "objet { 'module.role': [identifiants] }",
        "attributs_roles": "objet { 'module.role': { identifiant: { attribut: valeur } } }",
        "types_extensions": "objet { chemin: type } des extensions employées ; permet de déceler un même nom employé avec deux types",
        "modules": "objet { module: { champ: valeur } }",
        "local": "objet { identifiant_modele: { champ: valeur } }",
        "decisions": "objet { identifiant_modele: { options: { id: true|false }, choix: { id: id_cas } } }",
        "valeurs_fictives": "liste des chemins encore fictifs",
        "extensions": "réservé ; conservé tel quel",
    },
}


def construire():
    return {
        "nom": "Dictionnaire de données tabellion",
        "version": VERSION,
        "date": DATE,
        "statut": "projet soumis à critique",
        "conventions": CONVENTIONS,
        "format_dossier": DOSSIER_FORMAT,
        "types": TYPES,
        "validations": VALIDATIONS,
        "entites": ENTITES,
        "modules": MODULES,
        "modules_prevus": MODULES_PREVUS,
    }


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "dictionnaire.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(construire(), fh, ensure_ascii=False, indent=2)
    print(out)
