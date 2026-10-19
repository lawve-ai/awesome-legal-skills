// Exécution du moteur hors navigateur, pour les tests : node rendre.js modele.json dico.json dossier.json sortie rapport.json
const fs = require("fs");
const path = require("path");
const T = require(path.join(__dirname, "..", "assets", "moteur.js"));
const [modele, dico, dossier] = process.argv.slice(2, 5).map(f => JSON.parse(fs.readFileSync(f, "utf8")));
const r = T.generer(dico, modele, dossier);
fs.writeFileSync(process.argv[5], Buffer.from(r.octets));
fs.writeFileSync(process.argv[6], JSON.stringify({ manquants: r.manquants, alertes: r.alertes, controles: r.controles,
  calculs: r.calculs, apercu: r.apercu }, null, 1));
