# Développement du dictionnaire

Outils de maintenance, inutiles à l'usage courant de la skill.

1. Modifier `construire_dictionnaire.py`. Le dictionnaire ne contient aucune règle de droit ; tout exemple y reste manifestement fictif.
2. `python3 construire_dictionnaire.py` régénère `../references/dictionnaire.json`.
3. `python3 controler_dictionnaire.py` contrôle les identifiants, les renvois, les types et les sommes de contrôle des exemples, puis éprouve `dossier-exemple.json`.
4. `python3 generer_lisible.py` régénère `../references/dictionnaire.md`.

Incrémenter `VERSION` : le chiffre mineur pour un ajout, le chiffre majeur pour un chemin supprimé ou renommé. Les formulaires préviennent l'utilisateur qui ouvre un dossier dont la version majeure diffère.
