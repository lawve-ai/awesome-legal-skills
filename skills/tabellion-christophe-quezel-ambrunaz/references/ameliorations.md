# Améliorations du formulaire à proposer

Après la première livraison, proposer deux à quatre améliorations choisies pour le modèle en cause, et non la liste entière. Chacune se réalise par le balisage ou le manifeste, sans toucher au moteur.

| Amélioration | Moyen | Utile lorsque |
|---|---|---|
| Aides contextuelles | `aides` dans le manifeste | Une rubrique prête à confusion (« destination des lieux », « chefs critiqués ») |
| Contrôles de cohérence | `controles` | Des sommes doivent s'équilibrer, une date doit en précéder une autre, un montant doit rester sous un plafond convenu |
| Contrôle bloquant | `"bloquant": true` | Une incohérence rendrait l'acte inutilisable |
| Champ calculé | `calculs` | Une date d'échéance, un total, un prorata, une ancienneté (règle confirmée) |
| Table de valeurs figées | `tables` + `table()` | Un taux ou un indice est appliqué ; la date de gel est affichée et le calcul est refusé au-delà |
| Variante plutôt que saisie libre | `[[CHOIX]]` | Une même stipulation existe en deux ou trois rédactions éprouvées |
| Option nommée | `[[OPTION]]` | Une clause est tantôt retenue, tantôt écartée |
| Passage conditionnel | `[[SI]]` | Une mention dépend des données (personne morale, pluralité, montant nul) : une question de moins pour l'utilisateur |
| Numérotation dynamique | `{{compteur}}`, `{{renvoi}}` | Des articles optionnels font varier la numérotation |
| Répétition | `[[POUR CHAQUE]]` | Un nombre variable de parties, de pièces ou d'échéances |
| Montants et dates en lettres | `|lettres_puis_chiffres`, `|lettres` | Actes notariés, reconnaissances de dette, actes de procédure |
| Accords | `|accord`, `|qualite` | Les parties peuvent être plusieurs, de genre ou de nature différents |
| Réutilisation entre modèles | chemins du dictionnaire plutôt que `local.*` | Le même dossier alimente plusieurs actes (bail puis commandement de payer, assignation puis conclusions) |
| Désignation sur mesure | composition des champs | La formule de désignation du cabinet diffère de celle du dictionnaire |
| Bordereau de pièces | lignes répétées sur `procedure_civile.bordereau_pieces` | Conclusions et assignations |

Les améliorations qui ne relèvent pas du formulaire se mentionnent séparément, comme simples suggestions. Elles touchent la rédaction (clause obscure, référence périmée) et supposent l'accord de l'utilisateur et, pour le fond, une skill de rédaction juridique.
