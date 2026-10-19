/* Moteur tabellion — assemble le document à partir du modèle compilé et du dossier.
   Aucune connexion, aucune bibliothèque externe, aucune analyse XML : le modèle compilé
   ne contient que des fragments XML déjà vérifiés, que le moteur concatène.
   Le même fichier s'exécute dans le formulaire et dans les tests (Node). */
(function (racine, fabrique) {
  if (typeof module === "object" && module.exports) module.exports = fabrique();
  else racine.Tabellion = fabrique();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var NBSP = "\u00a0";
  var SAUT_LIGNE = "\u2028";

  // ================================================================ nombres en lettres
  var UNITES = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze",
    "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf"];
  var DIZAINES = { 2: "vingt", 3: "trente", 4: "quarante", 5: "cinquante", 6: "soixante" };

  function moinsDeCent(n, rect, finale) {
    if (n < 20) return UNITES[n];
    var d = Math.floor(n / 10), u = n % 10, et = rect ? "-et-" : " et ";
    if (d === 7) return u === 1 ? "soixante" + et + "onze" : "soixante-" + UNITES[10 + u];
    if (d === 8) return u === 0 ? (finale ? "quatre-vingts" : "quatre-vingt") : "quatre-vingt-" + UNITES[u];
    if (d === 9) return "quatre-vingt-" + UNITES[10 + u];
    if (u === 0) return DIZAINES[d];
    if (u === 1) return DIZAINES[d] + et + "un";
    return DIZAINES[d] + "-" + UNITES[u];
  }

  function moinsDeMille(n, rect, finale) {
    var c = Math.floor(n / 100), r = n % 100, sep = rect ? "-" : " ", morceaux = [];
    if (c === 1) morceaux.push("cent");
    else if (c > 1) morceaux.push(UNITES[c] + sep + (r === 0 && finale ? "cents" : "cent"));
    if (r > 0 || c === 0) morceaux.push(moinsDeCent(r, rect, finale));
    return morceaux.join(sep);
  }

  /* Entier positif en lettres. finale : vingt et cent prennent la marque du pluriel
     lorsqu'ils terminent le nombre ou précèdent millions et milliards (noms), non devant mille. */
  function nombreEnLettres(n, rect) {
    if (!isFinite(n) || n < 0 || Math.floor(n) !== n) throw new Error("entier positif attendu : " + n);
    if (n >= 1e12) throw new Error("nombre trop grand pour être écrit en lettres : " + n);
    if (n === 0) return "zéro";
    var sep = rect ? "-" : " ";
    var milliards = Math.floor(n / 1e9), millions = Math.floor(n / 1e6) % 1000,
      milliers = Math.floor(n / 1000) % 1000, reste = n % 1000;
    var noms = [], bas = [];
    if (milliards) noms.push(milliards === 1 ? "un milliard" : moinsDeMille(milliards, rect, true) + " milliards");
    if (millions) noms.push(millions === 1 ? "un million" : moinsDeMille(millions, rect, true) + " millions");
    if (milliers) bas.push(milliers === 1 ? "mille" : moinsDeMille(milliers, rect, false) + sep + "mille");
    if (reste) bas.push(moinsDeMille(reste, rect, true));
    if (bas.length) noms.push(bas.join(sep));
    return noms.join(" ");
  }

  function decimalEnLettres(x, rect) {
    var neg = x < 0, s = String(Math.abs(x));
    if (s.indexOf("e") >= 0) s = Math.abs(x).toFixed(10).replace(/0+$/, "");
    var parties = s.split("."), ent = nombreEnLettres(parseInt(parties[0], 10), rect);
    var res = ent;
    if (parties[1] && parseInt(parties[1], 10) !== 0) {
      var dec = parties[1].replace(/0+$/, ""), zeros = dec.match(/^0*/)[0].length;
      res += " virgule " + Array(zeros + 1).join("zéro ") + nombreEnLettres(parseInt(dec, 10), rect);
    }
    return (neg ? "moins " : "") + res;
  }

  function montantEnLettres(valeur, rect) {
    var neg = valeur < 0, total = Math.round(Math.abs(valeur) * 100);
    var e = Math.floor(total / 100), c = total % 100, s = "";
    if (e > 0 || c === 0) {
      s = nombreEnLettres(e, rect);
      s += (e > 0 && e % 1000000 === 0) ? " d'euros" : (e > 1 ? " euros" : " euro");
    }
    if (c > 0) s += (s ? " et " : "") + nombreEnLettres(c, rect) + (c > 1 ? " centimes" : " centime");
    return (neg ? "moins " : "") + s;
  }

  function ordinalEnLettres(n, rect) {
    if (n === 1) return "premier";
    var s = nombreEnLettres(n, rect).replace(/(vingt|cent)s$/, "$1");
    if (/cinq$/.test(s)) return s + "uième";
    if (/neuf$/.test(s)) return s.slice(0, -1) + "vième";
    if (/e$/.test(s)) return s.slice(0, -1) + "ième";
    return s + "ième";
  }

  function romain(n) {
    if (n <= 0 || n >= 4000) throw new Error("numérotation romaine impossible : " + n);
    var t = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
      [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]], s = "";
    t.forEach(function (p) { while (n >= p[0]) { s += p[1]; n -= p[0]; } });
    return s;
  }

  function lettreRang(n) {
    if (n < 1 || n > 26) throw new Error("numérotation par lettre limitée à 26 éléments : " + n);
    return String.fromCharCode(96 + n);
  }

  // ================================================================ nombres en chiffres
  function grouper(entier, seuil) {
    var s = String(entier);
    if (entier < seuil) return s;
    return s.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  }

  function nombreEnChiffres(x, decimales, seuil) {
    var neg = x < 0, a = Math.abs(x);
    var s = decimales == null ? String(a) : a.toFixed(decimales);
    if (s.indexOf("e") >= 0) s = a.toFixed(6).replace(/\.?0+$/, "");
    var p = s.split(".");
    return (neg ? "−" : "") + grouper(parseInt(p[0], 10), seuil) + (p[1] ? "," + p[1] : "");
  }

  function montantEnChiffres(m, param) {
    var v = Number(m.valeur), cent = Math.round(Math.abs(v) * 100) % 100;
    var dec = (param === "toujours" || cent !== 0) ? 2 : 0;
    var devise = (m.devise || "EUR") === "EUR" ? "€" : m.devise;
    return nombreEnChiffres(arrondi(v, 2), dec, 1000) + NBSP + devise;
  }

  // ================================================================ dates
  var MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
    "novembre", "décembre"];

  function lireDate(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
    if (!m) return null;
    return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  }
  function ecrireDate(d) { return d.toISOString().slice(0, 10); }
  function joursDansMois(a, m) { return new Date(Date.UTC(a, m + 1, 0)).getUTCDate(); }

  function ajouterMois(iso, n) {
    var d = lireDate(iso); if (!d) return null;
    var a = d.getUTCFullYear(), m = d.getUTCMonth() + n, j = d.getUTCDate();
    var a2 = a + Math.floor(m / 12), m2 = ((m % 12) + 12) % 12;
    return ecrireDate(new Date(Date.UTC(a2, m2, Math.min(j, joursDansMois(a2, m2)))));
  }
  function ajouterJours(iso, n) {
    var d = lireDate(iso); if (!d) return null;
    d.setUTCDate(d.getUTCDate() + n);
    return ecrireDate(d);
  }

  function paques(a) {   // algorithme de Meeus, Jones et Butcher (calendrier grégorien)
    var A = a % 19, B = Math.floor(a / 100), C = a % 100, D = Math.floor(B / 4), E = B % 4,
      F = Math.floor((B + 8) / 25), G = Math.floor((B - F + 1) / 3), H = (19 * A + B - D - G + 15) % 30,
      I = Math.floor(C / 4), K = C % 4, L = (32 + 2 * E + 2 * I - H - K) % 7, M = Math.floor((A + 11 * H + 22 * L) / 451),
      mois = Math.floor((H + L - 7 * M + 114) / 31), jour = ((H + L - 7 * M + 114) % 31) + 1;
    return ecrireDate(new Date(Date.UTC(a, mois - 1, jour)));
  }

  function joursFeries(a, alsaceMoselle) {
    var p = paques(a), f = {};
    ["01-01", "05-01", "05-08", "07-14", "08-15", "11-01", "11-11", "12-25"].forEach(function (x) { f[a + "-" + x] = 1; });
    f[ajouterJours(p, 1)] = 1; f[ajouterJours(p, 39)] = 1; f[ajouterJours(p, 50)] = 1;
    if (alsaceMoselle) { f[ajouterJours(p, -2)] = 1; f[a + "-12-26"] = 1; }
    return f;
  }

  function prorogation(iso, alsace) {
    var d = iso;
    for (var i = 0; i < 15; i++) {
      var dt = lireDate(d), js = dt.getUTCDay();
      if (js !== 0 && js !== 6 && !joursFeries(dt.getUTCFullYear(), alsace)[d]) return d;
      d = ajouterJours(d, 1);
    }
    return d;
  }

  function ecartMois(a, b) {
    var d1 = lireDate(a), d2 = lireDate(b); if (!d1 || !d2) return null;
    var m = (d2.getUTCFullYear() - d1.getUTCFullYear()) * 12 + d2.getUTCMonth() - d1.getUTCMonth();
    if (d2.getUTCDate() < d1.getUTCDate()) m -= 1;
    return m;
  }

  function dateLongue(iso) {
    var d = lireDate(iso); if (!d) return iso;
    var j = d.getUTCDate();
    return (j === 1 ? "1er" : j) + " " + MOIS[d.getUTCMonth()] + " " + d.getUTCFullYear();
  }
  function dateLettres(iso, rect) {
    var d = lireDate(iso); if (!d) return iso;
    var j = d.getUTCDate();
    return (j === 1 ? "premier" : nombreEnLettres(j, rect)) + " " + MOIS[d.getUTCMonth()] + " " +
      nombreEnLettres(d.getUTCFullYear(), rect);
  }
  function dateCourte(iso) { var p = iso.split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }

  function arrondi(x, n) {
    var f = Math.pow(10, n || 0);
    return (x < 0 ? -1 : 1) * Math.round(Math.abs(x) * f + 1e-9) / f;
  }

  // ================================================================ utilitaires
  function vide(v) {
    if (v === null || v === undefined || v === "") return true;
    if (Array.isArray(v)) return v.length === 0;
    if (typeof v === "object") {
      if ("valeur" in v) return v.valeur === null || v.valeur === undefined || v.valeur === "";
      return Object.keys(v).every(function (k) { return vide(v[k]); });
    }
    return false;
  }
  function majInitiale(s) { return s ? s.charAt(0).toLocaleUpperCase("fr") + s.slice(1) : s; }
  function premierPrenom(p) { return (p.prenom_usuel || (p.prenoms || "").split(/[,\s]+/)[0] || "").trim(); }
  function enumeration(liste, conj) {
    liste = liste.filter(function (s) { return s !== ""; });
    if (liste.length <= 1) return liste.join("");
    return liste.slice(0, -1).join(", ") + " " + (conj || "et") + " " + liste[liste.length - 1];
  }
  function de(s) {   // élision : « d'Exempleville », « de Lyon »
    return /^[aeéèêëiîïoôuûùyAEÉÈÊËIÎÏOÔUÛÙY]/.test(s || "") ? "d'" + s : "de " + s;
  }
  function echapperXml(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  var COLLECTIONS = { personne: "personnes", bien_immobilier: "biens", vehicule: "vehicules", compte_bancaire: "comptes" };

  // ================================================================ contexte
  function Contexte(dico, modele, dossier) {
    this.dico = dico; this.modele = modele; this.dossier = dossier || {};
    this.modules = {}; dico.modules.forEach(function (m) { this.modules[m.id] = m; }, this);
    this.decisions = ((this.dossier.decisions || {})[modele.id]) || { options: {}, choix: {} };
    this.decisions.options = this.decisions.options || {}; this.decisions.choix = this.decisions.choix || {};
    this.locales = ((this.dossier.local || {})[modele.id]) || {};
    this.param = modele.parametres || {};
    this.rect = this.param.orthographe_nombres === "rectifiee_1990";
    this.portees = []; this.manquants = {}; this.alertes = []; this.compteurs = {}; this.ancres = {};
    this.ancresFinales = null; this.cacheCalculs = {};
    var formes = {};
    champ(dico.entites.personne.morale, "forme_juridique").valeurs.forEach(function (v) { formes[v.id] = v; });
    this.formes = formes;
  }
  Contexte.prototype.manque = function (lib) { this.manquants[lib] = true; };
  Contexte.prototype.alerte = function (s) { if (this.alertes.indexOf(s) < 0) this.alertes.push(s); };

  function champ(champs, id) {
    for (var i = 0; i < (champs || []).length; i++) if (champs[i].id === id) return champs[i];
    return null;
  }

  // ================================================================ personnes
  function genre(ctx, p) {
    if (!p) return null;
    if (p.nature === "morale") {
      if (p.genre_grammatical) return p.genre_grammatical;
      var f = ctx.formes[p.forme_juridique];
      return f && f.genre ? f.genre : null;
    }
    return p.civilite === "madame" ? "f" : p.civilite === "monsieur" ? "m" : null;
  }
  function libellePersonne(ctx, p) {
    if (!p) return "personne non désignée";
    if (p.nature === "morale") return p.denomination || "personne morale sans dénomination";
    return [premierPrenom(p), (p.nom || "").toUpperCase()].join(" ").trim() || "personne sans nom";
  }
  function accorder(g, pluriel, formes) {
    if (formes.length === 2) return pluriel ? formes[1] : formes[0];
    return formes[(g === "f" ? 1 : 0) + (pluriel ? 2 : 0)];
  }
  function exiger(ctx, p, champ_, lib) {
    if (vide(p[champ_])) { ctx.manque(libellePersonne(ctx, p) + " › " + lib); return false; }
    return true;
  }

  function designationCourte(ctx, p) {
    if (p.nature === "morale") {
      var f = ctx.formes[p.forme_juridique];
      exiger(ctx, p, "forme_juridique", "Forme juridique");
      exiger(ctx, p, "denomination", "Dénomination sociale");
      var gen = f && f.generique ? f.generique : (p.forme_precisee || "personne morale");
      var g = genre(ctx, p);
      var art = /^[aeéèêiîoôuûyAEÉÈÊIÎOÔUÛY]/.test(gen) ? "l'" : (g === "f" ? "la " : "le ");
      return art + gen + " " + (p.denomination || "");
    }
    exiger(ctx, p, "civilite", "Civilité"); exiger(ctx, p, "nom", "Nom");
    var civ = p.civilite === "madame" ? "Madame" : p.civilite === "monsieur" ? "Monsieur" : "";
    return [civ, premierPrenom(p), (p.nom || "").toUpperCase()].filter(Boolean).join(" ");
  }

  function adresseLigne(a, bloc) {
    if (!a) return "";
    var l1 = [a.numero, a.indice, a.voie].filter(Boolean).join(" ");
    var ville = [a.code_postal, a.commune, a.cedex ? "Cedex " + a.cedex : ""].filter(Boolean).join(" ");
    return [l1, a.complement, a.lieu_dit, ville, a.pays].filter(Boolean).join(bloc ? SAUT_LIGNE : ", ");
  }

  function designationComplete(ctx, p) {
    var g = genre(ctx, p), s;
    function ac(m, f) { return g === "f" ? f : m; }
    if (p.nature === "morale") {
      var f = ctx.formes[p.forme_juridique];
      s = designationCourte(ctx, p);
      if (f && f.long && p.forme_juridique !== "autre") s += ", " + f.long;
      else if (p.forme_precisee) s += ", " + p.forme_precisee;
      if (!vide(p.capital)) s += (p.capital_variable ? " à capital variable" : "") + " au capital de " + montantEnChiffres(p.capital, ctx.param.centimes);
      else if (p.capital_variable) s += " à capital variable";
      var im = p.immatriculation || {};
      if (im.numero) {
        var reg = {
          rcs: ac("immatriculé", "immatriculée") + " au registre du commerce et des sociétés" + (im.greffe ? " " + de(im.greffe) : ""),
          rne: ac("immatriculé", "immatriculée") + " au registre national des entreprises",
          rm: ac("immatriculé", "immatriculée") + " au répertoire des métiers" + (im.greffe ? " " + de(im.greffe) : ""),
          rna: ac("déclaré", "déclarée") + " au répertoire national des associations"
        }[im.registre] || (ac("immatriculé", "immatriculée") + (im.greffe ? " à " + im.greffe : ""));
        s += ", " + reg + " sous le numéro " + im.numero;
      } else ctx.alerte("Immatriculation non renseignée pour " + libellePersonne(ctx, p) + " : mention omise.");
      if (p.siege) s += ", dont le siège est situé " + adresseLigne(p.siege);
      else ctx.alerte("Siège non renseigné pour " + libellePersonne(ctx, p) + " : mention omise.");
      var reps = (p.representants_legaux || []).filter(function (r) { return r && r.personne; });
      if (reps.length) {
        s += ", " + ac("représenté", "représentée") + " par " + enumeration(reps.map(function (r) {
          var rp = ctx.dossier.personnes[r.personne];
          return (rp ? designationCourte(ctx, rp) : "?") + (r.qualite ? ", en sa qualité de " + r.qualite : "");
        }));
      } else s += ", " + ac("pris", "prise") + " en la personne de son représentant légal domicilié en cette qualité audit siège";
      return s;
    }
    s = [p.civilite === "madame" ? "Madame" : p.civilite === "monsieur" ? "Monsieur" : "", p.prenoms || premierPrenom(p),
      (p.nom || "").toUpperCase()].filter(Boolean).join(" ");
    exiger(ctx, p, "civilite", "Civilité"); exiger(ctx, p, "nom", "Nom"); exiger(ctx, p, "prenoms", "Prénoms");
    if (p.date_naissance) {
      s += ", " + ac("né", "née") + " le " + dateLongue(p.date_naissance);
      var ln = p.lieu_naissance || {};
      if (ln.commune) s += " à " + ln.commune + (ln.departement ? " (" + ln.departement + ")" : "") + (ln.pays ? ", " + ln.pays : "");
    } else ctx.alerte("Date de naissance non renseignée pour " + libellePersonne(ctx, p) + " : mention omise.");
    if (p.nationalite) s += ", de nationalité " + p.nationalite;
    if (p.profession) s += ", " + p.profession;
    if (p.domicile && !vide(p.domicile)) s += ", demeurant " + adresseLigne(p.domicile);
    else ctx.alerte("Domicile non renseigné pour " + libellePersonne(ctx, p) + " : mention omise.");
    var rs = (p.representants || []).filter(function (r) { return r && r.personne; });
    if (rs.length && p.capacite && p.capacite !== "majeur_capable") {
      s += ", " + ac("représenté", "représentée") + " par " + enumeration(rs.map(function (r) {
        var rp = ctx.dossier.personnes[r.personne];
        return (rp ? designationCourte(ctx, rp) : "?") + (r.qualite ? ", en sa qualité de " + r.qualite : "");
      }));
    }
    return s;
  }

  function age(naissance, reference) {
    var d1 = lireDate(naissance), d2 = lireDate(reference);
    if (!d1 || !d2) return null;
    var a = d2.getUTCFullYear() - d1.getUTCFullYear();
    if (d2.getUTCMonth() < d1.getUTCMonth() || (d2.getUTCMonth() === d1.getUTCMonth() && d2.getUTCDate() < d1.getUTCDate())) a--;
    return a;
  }
  function dateReference(ctx) {
    var a = (ctx.dossier.modules || {}).acte || {};
    var d = a.date_reference || a.date_acte;
    if (!d) ctx.manque("Acte › Date de référence des calculs (ou date de l'acte)");
    return d;
  }

  function derive(ctx, p, nom) {
    if (!p) return null;
    switch (nom) {
      case "designation_courte": return designationCourte(ctx, p);
      case "designation_complete": return designationComplete(ctx, p);
      case "nom_complet": return p.nature === "morale" ? (p.denomination || "") : [premierPrenom(p), (p.nom || "").toUpperCase()].join(" ").trim();
      case "genre": return genre(ctx, p);
      case "age": exiger(ctx, p, "date_naissance", "Date de naissance"); return age(p.date_naissance, dateReference(ctx));
      case "majeur": var x = age(p.date_naissance, dateReference(ctx)); return x === null ? null : x >= 18;
    }
    return null;
  }
  var DERIVES = { designation_courte: "texte", designation_complete: "texte", nom_complet: "texte", genre: "texte",
    age: "entier", majeur: "booleen" };

  // ================================================================ résolution des chemins
  function trouverPortee(ctx, nom) {
    for (var i = ctx.portees.length - 1; i >= 0; i--) if (ctx.portees[i].nom === nom) return ctx.portees[i];
    return null;
  }

  function depuisChamp(ctx, def, v, lib) {
    var t = def.type;
    if (t === "groupe") return { nat: "groupe", v: v || {}, def: def, lib: lib };
    if (t === "liste") return def.champs ? { nat: "liste", v: v || [], def: def, lib: lib } : { nat: "listeval", v: v || [], def: def, lib: lib };
    if (t === "reference") {
      var coll = (ctx.dossier[COLLECTIONS[def.cible]] || {});
      var obj = v ? coll[v] : null;
      if (def.cible === "personne") return { nat: "personne", v: obj, lib: lib };
      return { nat: "entite", v: obj, def: ctx.dico.entites[def.cible], cible: def.cible, lib: lib };
    }
    return { nat: "val", v: v, def: def, type: t, lib: lib };
  }

  function developper(items) {
    var out = [];
    items.forEach(function (it) {
      if (it.nat === "liste") it.v.forEach(function (el) { out.push({ nat: "groupe", v: el || {}, def: it.def, lib: it.lib }); });
      else if (it.nat === "listeval") it.v.forEach(function (el) { out.push({ nat: "val", v: el, type: it.def.element, def: { type: it.def.element }, lib: it.lib }); });
      else out.push(it);
    });
    return out;
  }

  function champsPersonne(ctx) {
    var p = ctx.dico.entites.personne;
    return p.commun.concat(p.physique, p.morale);
  }

  function etape(ctx, res, seg) {
    var items = [], multiple = res.multiple;
    developper(res.items).forEach(function (it) {
      var def, v;
      if (it.nat === "personne") {
        var p = it.v;
        if (DERIVES[seg]) { items.push({ nat: "val", v: p ? derive(ctx, p, seg) : null, type: DERIVES[seg], def: { type: DERIVES[seg] }, lib: it.lib + " › " + seg }); return; }
        def = champ(champsPersonne(ctx), seg);
        if (!def && it.role && it.role.attributs) {   // attribut de la personne en tant qu'elle tient ce rôle
          var ad = champ(it.role.attributs, seg);
          var ar = (((ctx.dossier.attributs_roles || {})[it.cleRole] || {})[it.pid]) || {};
          items.push(depuisChamp(ctx, ad, ar[seg], (p ? libellePersonne(ctx, p) : it.lib) + " (" + it.role.libelles.ms + ") › " + ad.libelle));
          return;
        }
        items.push(depuisChamp(ctx, def, p ? p[seg] : null, (p ? libellePersonne(ctx, p) : it.lib) + " › " + def.libelle));
        return;
      }
      if (it.nat === "entite") {
        def = champ(it.def.champs, seg);
        items.push(depuisChamp(ctx, def, it.v ? it.v[seg] : null, it.lib + " › " + def.libelle));
        return;
      }
      if (it.nat === "groupe") {
        def = champ(it.def.champs, seg);
        items.push(depuisChamp(ctx, def, (it.v || {})[seg], it.lib + " › " + def.libelle));
        return;
      }
      if (it.nat === "val" && it.v && typeof it.v === "object") {
        v = it.v[seg];
        var t = seg === "valeur" ? "decimal" : "texte";
        var ad = it.type === "adresse" ? champ(ctx.dico.entites.adresse.champs, seg) : null;
        items.push({ nat: "val", v: v, type: t, def: { type: t }, lib: it.lib + " › " + (ad ? ad.libelle : seg) });
        return;
      }
      items.push({ nat: "val", v: null, type: "texte", def: { type: "texte" }, lib: it.lib + " › " + seg });
    });
    if (res.items.some(function (it) { return it.nat === "liste" || it.nat === "listeval"; })) multiple = true;
    return { items: items, multiple: multiple, role: null };
  }

  function resoudre(ctx, segs) {
    var tete = segs[0], reste = segs.slice(1), res;
    var portee = trouverPortee(ctx, tete);
    if (portee) {
      if (reste.length && reste[0].charAt(0) === "#") {
        var m = reste[0], r = portee.rang, n = portee.nombre;
        var v = { "#rang": r, "#premier": r === 1, "#dernier": r === n, "#avant_dernier": r === n - 1, "#nombre": n }[m];
        return { items: [{ nat: "val", v: v, type: typeof v === "boolean" ? "booleen" : "entier", def: {}, lib: m }], multiple: false };
      }
      res = { items: [portee.item], multiple: false };
    } else if (tete === "local") {
      var loc = ctx.modele.locales_def[reste[0]];
      return { items: [depuisChamp(ctx, loc, ctx.locales[reste[0]], loc.libelle)], multiple: false };
    } else if (tete === "calcul") {
      var c = ctx.modele.calculs[reste[0]];
      return { items: [{ nat: "val", v: c.element_de ? calculDeLigne(ctx, reste[0]) : calcul(ctx, reste[0]), type: c.type, def: { type: c.type }, lib: c.libelle }], multiple: false };
    } else if (tete === "option") {
      return { items: [{ nat: "val", v: !!ctx.decisions.options[reste[0]], type: "booleen", def: {}, lib: reste[0] }], multiple: false };
    } else if (tete === "choix") {
      var dch = ctx.modele.decisions.choix[reste[0]];
      return { items: [{ nat: "val", v: ctx.decisions.choix[reste[0]] || null, type: "choix_document", def: dch, lib: dch.libelle }], multiple: false };
    } else {
      var mod = ctx.modules[tete];
      var role = (mod.roles || []).filter(function (x) { return x.id === reste[0]; })[0];
      if (role) {
        var cle = tete + "." + role.id, ids = ((ctx.dossier.roles || {})[cle]) || [];
        var lib = "Rôle « " + role.libelles.ms + " »";
        res = {
          items: ids.map(function (id) {
            var p = (ctx.dossier.personnes || {})[id];
            return { nat: "personne", v: p || null, lib: lib + " (" + id + ")", role: role, cleRole: cle, pid: id };
          }), multiple: true, role: role, cleRole: cle, libRole: lib
        };
        reste = reste.slice(1);
      } else {
        res = { items: [{ nat: "groupe", v: ((ctx.dossier.modules || {})[tete]) || {}, def: { champs: mod.champs }, lib: mod.libelle }], multiple: false };
      }
    }
    for (var i = 0; i < reste.length; i++) res = etape(ctx, res, reste[i]);
    return res;
  }

  // ================================================================ mise en forme
  function formater(ctx, it, rendu) {
    var v = it.v, t = it.type || (it.nat === "personne" ? "personne" : "texte");
    if (it.nat === "personne") return v ? designationCourte(ctx, v) : "";
    if (vide(v) && t !== "booleen") return null;
    switch (t) {
      case "entier":
        if (rendu === "lettres") return nombreEnLettres(Number(v), ctx.rect);
        if (rendu === "ordinal") return ordinalEnLettres(Number(v), ctx.rect);
        if (rendu === "ordinal_abrege") return Number(v) === 1 ? "1er" : v + "e";
        if (rendu === "romain") return romain(Number(v));
        return nombreEnChiffres(Number(v), null, 10000);
      case "decimal":
        return rendu === "lettres" ? decimalEnLettres(Number(v), ctx.rect) : nombreEnChiffres(Number(v), null, 10000);
      case "pourcentage":
        return rendu === "lettres" ? decimalEnLettres(Number(v), ctx.rect) + " pour cent" : nombreEnChiffres(Number(v), null, 10000) + NBSP + "%";
      case "montant":
        if ((v.devise || "EUR") !== "EUR" && rendu && rendu !== "chiffres") {
          ctx.alerte("Montant en " + v.devise + " : l'écriture en lettres n'est disponible qu'en euros ; chiffres retenus.");
          return montantEnChiffres(v, ctx.param.centimes);
        }
        var ch = montantEnChiffres(v, ctx.param.centimes), le = (v.devise || "EUR") === "EUR" ? montantEnLettres(Number(v.valeur), ctx.rect) : ch;
        if (rendu === "lettres") return le;
        if (rendu === "lettres_puis_chiffres") return le + " (" + ch + ")";
        if (rendu === "chiffres_puis_lettres") return ch + " (" + le + ")";
        return ch;
      case "date":
        if (!lireDate(v)) { ctx.alerte("Date invalide : " + v); return String(v); }
        if (rendu === "courte") return dateCourte(v);
        if (rendu === "lettres") return dateLettres(v, ctx.rect);
        if (rendu === "iso") return v;
        return dateLongue(v);
      case "heure":
        var hm = String(v).split(":"), h = parseInt(hm[0], 10), mn = parseInt(hm[1] || "0", 10);
        if (rendu === "lettres") return nombreEnLettres(h, ctx.rect).replace(/^un$/, "une") + (h > 1 ? " heures" : " heure") + (mn ? " " + nombreEnLettres(mn, ctx.rect) : "");
        return h + NBSP + "h" + (mn ? NBSP + (mn < 10 ? "0" : "") + mn : "");
      case "duree":
        var n = Number(v.valeur), u = v.unite;
        var noms = { jours: ["jour", "jours"], semaines: ["semaine", "semaines"], mois: ["mois", "mois"], annees: ["an", "ans"] }[u] || [u, u];
        var nom = n > 1 ? noms[1] : noms[0];
        if (rendu === "chiffres") return n + NBSP + nom;
        var l = nombreEnLettres(n, ctx.rect);
        if (u === "semaines") l = l.replace(/(^|[\s-])un$/, "$1une");
        return l + " " + nom;
      case "booleen": return v === true ? "oui" : v === false ? "non" : null;
      case "choix":
        var val = (it.def.valeurs || []).filter(function (x) { return x.id === v; })[0];
        if (!val) return String(v);
        return rendu === "long" && val.long ? val.long : val.libelle;
      case "choix_document":
        return (it.def.cas || {})[v] || String(v);
      case "identifiant":
        if (rendu === "groupe") {
          var s = String(v).replace(/\s/g, "");
          return /^[A-Z]{2}\d{2}/.test(s) ? s.replace(/(.{4})/g, "$1 ").trim() : s.length === 14 ? s.replace(/^(\d{3})(\d{3})(\d{3})(\d{5})$/, "$1 $2 $3 $4") : s.replace(/(\d{3})(?=\d)/g, "$1 ");
        }
        return String(v);
      case "adresse": return adresseLigne(v, rendu === "bloc");
      default: return String(v);
    }
  }

  function transformer(nom, s) {
    if (s === null) return s;
    if (nom === "majuscules") return s.toLocaleUpperCase("fr");
    if (nom === "minuscules") return s.toLocaleLowerCase("fr");
    if (nom === "initiale_majuscule") return majInitiale(s);
    return s;
  }

  function genreEtNombre(ctx, res, items) {
    var pers = items.filter(function (it) { return it.nat === "personne"; });
    if (!pers.length) return { g: "m", pl: items.length > 1, n: items.length };
    var gs = pers.map(function (it) {
      var g = genre(ctx, it.v);
      if (!g) ctx.manque((it.v ? libellePersonne(ctx, it.v) : it.lib) + " › Civilité ou forme juridique (accord)");
      return g;
    });
    var fem = gs.every(function (g) { return g === "f"; });
    return { g: fem ? "f" : "m", pl: pers.length > 1, n: pers.length };
  }

  function rendreValeur(ctx, noeud) {
    var res = resoudre(ctx, noeud.p), items = developper(res.items);
    if (res.role && !items.length) ctx.manque(res.libRole + " : aucune personne désignée");
    items.forEach(function (it) { if (it.nat === "personne" && !it.v) ctx.manque(it.lib + " : personne introuvable"); });
    var chaines = null, conj = "et";
    for (var i = 0; i < noeud.r.length; i++) {
      var nom = noeud.r[i][0], params = noeud.r[i][1];
      if (nom === "majuscules" || nom === "minuscules" || nom === "initiale_majuscule") {
        if (!chaines) chaines = items.map(function (it) { return formater(ctx, it, null); });
        chaines = chaines.map(function (s) { return transformer(nom, s); });
      } else if (nom === "nombre") {
        items = [{ nat: "val", type: "entier", v: items.length, def: {} }]; chaines = null;
      } else if (nom === "accord") {
        var gn = genreEtNombre(ctx, res, items); chaines = [accorder(gn.g, gn.pl, params)];
      } else if (nom === "qualite") {
        var gq = genreEtNombre(ctx, res, items), lb = res.role.libelles;
        if (params.length) lb = res.role.variantes[params[0]];
        chaines = [lb[(gq.g === "f" ? "f" : "m") + (gq.pl ? "p" : "s")]];
      } else if (nom === "enumeration_ou") {
        conj = "ou";
      } else {
        chaines = items.map(function (it) { return formater(ctx, it, nom); });
      }
    }
    if (!chaines) chaines = items.map(function (it) { return formater(ctx, it, null); });
    chaines = chaines.map(function (s, k) {
      if (s === null || s === undefined) {
        var lib = (items[k] && items[k].lib) || noeud.p.join(".");
        ctx.manque(lib);
        return "[À COMPLÉTER : " + lib + "]";
      }
      return s;
    });
    return enumeration(chaines, conj);
  }

  // ================================================================ expressions
  function brut(it) {
    if (it.nat === "personne") return it.v;
    if (it.type === "montant") return it.v && it.v.valeur !== undefined && it.v.valeur !== "" ? Number(it.v.valeur) : null;
    if (it.nat === "liste" || it.nat === "listeval") return it.v;
    return it.v === undefined ? null : it.v;
  }
  function deballer(x) {
    if (x && x.__res) {
      var items = developper(x.__res.items);
      if (x.__res.multiple) return items.map(brut);
      return items.length ? brut(items[0]) : null;
    }
    return x;
  }
  function verite(v) {
    if (v === null || v === undefined || v === "" || v === false || v === 0) return false;
    if (Array.isArray(v)) return v.length > 0;
    if (typeof v === "object") {
      if ("valeur" in v && "unite" in v) return Number(v.valeur) > 0;
      return !vide(v);
    }
    return true;
  }
  function nombreOuNul(ctx, x, lib) {
    var v = deballer(x);
    if (v === null || v === undefined || v === "") { ctx.manque(lib); return null; }
    if (typeof v === "object" && "valeur" in v) v = v.valeur;
    var n = Number(v);
    if (isNaN(n)) { ctx.alerte("Valeur non numérique dans un calcul : " + v); return null; }
    return n;
  }
  function libExpr(x) { return x && x.__res ? (developper(x.__res.items)[0] || {}).lib || "valeur" : "valeur"; }

  function evaluer(ctx, e) {
    switch (e.k) {
      case "num": case "str": case "bool": return e.v;
      case "chemin": return { __res: resoudre(ctx, e.p) };
      case "et": return verite(deballer(evaluer(ctx, e.a))) && verite(deballer(evaluer(ctx, e.b)));
      case "ou": return verite(deballer(evaluer(ctx, e.a))) || verite(deballer(evaluer(ctx, e.b)));
      case "non": return !verite(deballer(evaluer(ctx, e.a)));
      case "est": return evaluerPredicat(ctx, e) !== e.neg;
      case "op": return evaluerOp(ctx, e);
      case "fn": return evaluerFonction(ctx, e);
    }
    throw new Error("expression inconnue " + e.k);
  }

  function evaluerPredicat(ctx, e) {
    var x = evaluer(ctx, e.a), items = x && x.__res ? developper(x.__res.items) : [];
    var pers = items.filter(function (it) { return it.nat === "personne" && it.v; });
    var v = deballer(x);
    switch (e.pred) {
      case "PLURIEL": return items.length > 1;
      case "SINGULIER": return items.length === 1;
      case "FEMININ": return pers.length > 0 && pers.every(function (it) { var g = genre(ctx, it.v); if (!g) ctx.manque(libellePersonne(ctx, it.v) + " › Civilité ou forme juridique"); return g === "f"; });
      case "MASCULIN": return pers.length > 0 && !pers.every(function (it) { return genre(ctx, it.v) === "f"; });
      case "PERSONNE MORALE": return pers.length > 0 && pers.every(function (it) { return it.v.nature === "morale"; });
      case "PERSONNE PHYSIQUE": return pers.length > 0 && pers.every(function (it) { return it.v.nature !== "morale"; });
      case "RENSEIGNE": return Array.isArray(v) ? v.some(function (y) { return !vide(y); }) : !vide(v);
      case "VIDE": return Array.isArray(v) ? v.every(vide) : vide(v);
      case "VRAI": return v === true;
      case "FAUX": return v === false;
    }
    throw new Error("prédicat inconnu " + e.pred);
  }

  function evaluerOp(ctx, e) {
    var a = evaluer(ctx, e.a), b = evaluer(ctx, e.b);
    if (["+", "-", "*", "/"].indexOf(e.op) >= 0) {
      var x = nombreOuNul(ctx, a, libExpr(a)), y = nombreOuNul(ctx, b, libExpr(b));
      if (x === null || y === null) return null;
      if (e.op === "+") return x + y;
      if (e.op === "-") return x - y;
      if (e.op === "*") return x * y;
      if (y === 0) { ctx.alerte("Division par zéro dans un calcul."); return null; }
      return x / y;
    }
    var va = deballer(a), vb = deballer(b);
    function norm(v) { return v && typeof v === "object" && "valeur" in v && !("unite" in v) ? Number(v.valeur) : v; }
    va = norm(va); vb = norm(vb);
    if (e.op === "=" || e.op === "!=") {
      var eg = Array.isArray(va) ? va.some(function (z) { return z === vb || String(z) === String(vb); })
        : (va === vb || (va !== null && vb !== null && String(va) === String(vb)));
      return e.op === "=" ? eg : !eg;
    }
    if (va === null || vb === null || va === undefined || vb === undefined) { ctx.manque(libExpr(va === null ? a : b)); return false; }
    if (typeof va === "number" || typeof vb === "number") { va = Number(va); vb = Number(vb); }
    return { "<": va < vb, ">": va > vb, "<=": va <= vb, ">=": va >= vb }[e.op];
  }

  function aplatir(v) {
    var out = [];
    (Array.isArray(v) ? v : [v]).forEach(function (x) { if (Array.isArray(x)) out = out.concat(aplatir(x)); else out.push(x); });
    return out;
  }

  function evaluerFonction(ctx, e) {
    var nom = e.nom;
    if (nom === "si") return verite(deballer(evaluer(ctx, e.args[0]))) ? evaluer(ctx, e.args[1]) : evaluer(ctx, e.args[2]);
    var brutArgs = e.args.map(function (a) { return evaluer(ctx, a); });
    var args = brutArgs.map(deballer);
    function date(i) {
      var v = args[i];
      if (v && v.nature) v = v.date_naissance;
      if (!lireDate(v)) { ctx.manque(libExpr(brutArgs[i])); return null; }
      return v;
    }
    function num(i) { return nombreOuNul(ctx, brutArgs[i], libExpr(brutArgs[i])); }
    function chiffre(v) { if (v && typeof v === "object" && "valeur" in v) v = v.valeur; return v === null || v === undefined || v === "" ? null : Number(v); }
    var d, n;
    switch (nom) {
      case "ajouter_jours": d = date(0); n = num(1); return d && n !== null ? ajouterJours(d, n) : null;
      case "ajouter_mois": d = date(0); n = num(1); return d && n !== null ? ajouterMois(d, n) : null;
      case "ajouter_annees": d = date(0); n = num(1); return d && n !== null ? ajouterMois(d, 12 * n) : null;
      case "ajouter_duree":
        d = date(0); var du = args[1];
        if (!d || !du || vide(du)) { if (!du || vide(du)) ctx.manque(libExpr(brutArgs[1])); return null; }
        var k = Number(du.valeur);
        return { jours: ajouterJours(d, k), semaines: ajouterJours(d, 7 * k), mois: ajouterMois(d, k), annees: ajouterMois(d, 12 * k) }[du.unite];
      case "veille": d = date(0); return d ? ajouterJours(d, -1) : null;
      case "lendemain": d = date(0); return d ? ajouterJours(d, 1) : null;
      case "prorogation": d = date(0); return d ? prorogation(d, args.length > 1 && verite(args[1])) : null;
      case "ecart_jours": var a1 = date(0), a2 = date(1); return a1 && a2 ? Math.round((lireDate(a2) - lireDate(a1)) / 864e5) : null;
      case "ecart_mois": var b1 = date(0), b2 = date(1); return b1 && b2 ? ecartMois(b1, b2) : null;
      case "ecart_annees": var c1 = date(0), c2 = date(1); return c1 && c2 ? Math.floor(ecartMois(c1, c2) / 12) : null;
      case "age": var n1 = date(0), r1 = date(1); return n1 && r1 ? age(n1, r1) : null;
      case "somme":
        var vals = aplatir(args[0]).map(chiffre);
        if (vals.some(function (x) { return x === null || isNaN(x); })) { ctx.manque(libExpr(brutArgs[0])); return null; }
        return vals.reduce(function (s, x) { return s + x; }, 0);
      case "nombre": return aplatir(args[0]).filter(function (x) { return !vide(x); }).length;
      case "min": case "max":
        var l = aplatir(args).map(chiffre).filter(function (x) { return x !== null; });
        return l.length ? Math[nom].apply(null, l) : null;
      case "arrondi": case "arrondi_inferieur": case "arrondi_superieur":
        var x = num(0), p = args.length > 1 ? num(1) : 0;
        if (x === null) return null;
        var f = Math.pow(10, p);
        if (nom === "arrondi") return arrondi(x, p);
        return (nom === "arrondi_inferieur" ? Math.floor(x * f + 1e-9) : Math.ceil(x * f - 1e-9)) / f;
      case "abs": var z = num(0); return z === null ? null : Math.abs(z);
      case "cumul":   // somme des n premières valeurs d'une liste (n = 0 : zéro)
        var lc = aplatir(args[0]).map(chiffre), nb = num(1);
        if (nb === null) return null;
        lc = lc.slice(0, Math.max(0, nb));
        if (lc.some(function (x) { return x === null || isNaN(x); })) { ctx.manque(libExpr(brutArgs[0])); return null; }
        return lc.reduce(function (s, x) { return s + x; }, 0);
      case "renseigne": return !vide(args[0]);
      case "table":
        var t = ctx.modele.tables[args[0]], cleT = args[1];
        if (!t || !(String(cleT) in t.valeurs)) {
          ctx.alerte("La table « " + (t ? t.libelle : args[0]) + " » (figée au " + (t ? dateLongue(t.date_gel) : "?") +
            ") ne contient pas de valeur pour « " + cleT + " » : calcul impossible sans mise à jour du formulaire.");
          ctx.manque("Table " + args[0] + " : " + cleT);
          return null;
        }
        return t.valeurs[String(cleT)];
    }
    throw new Error("fonction inconnue " + nom);
  }

  function calcul(ctx, id) {
    if (id in ctx.cacheCalculs) return ctx.cacheCalculs[id];
    var c = ctx.modele.calculs[id];
    ctx.cacheCalculs[id] = null;   // garde contre les définitions circulaires
    var sauvegarde = ctx.portees; ctx.portees = [];
    var v = deballer(evaluer(ctx, c.e));
    ctx.portees = sauvegarde;
    if (v !== null && v !== undefined) {
      if (c.type === "montant") v = { valeur: arrondi(Number(v), 2), devise: "EUR" };
      else if (c.type === "entier") v = Math.round(Number(v));
    }
    ctx.cacheCalculs[id] = v;
    return v;
  }

  /* Calcul de ligne : évalué pour l'élément courant de la boucle sur element_de, désigné par « element ». */
  function calculDeLigne(ctx, id) {
    var c = ctx.modele.calculs[id], portee = null;
    for (var i = ctx.portees.length - 1; i >= 0; i--) if (ctx.portees[i].liste === c.element_de) { portee = ctx.portees[i]; break; }
    if (!portee) { ctx.alerte("Calcul « " + c.libelle + " » employé hors de sa boucle."); return null; }
    var sauvegarde = ctx.portees;
    ctx.portees = [{ nom: "element", item: portee.item, rang: portee.rang, nombre: portee.nombre, liste: portee.liste }];
    var v = deballer(evaluer(ctx, c.e));
    ctx.portees = sauvegarde;
    if (v !== null && v !== undefined) {
      if (c.type === "montant") v = { valeur: arrondi(Number(v), 2), devise: "EUR" };
      else if (c.type === "entier") v = Math.round(Number(v));
    }
    return v;
  }

  // ================================================================ rendu de l'arbre
  function encoder(ctx, s, noeud) {
    var x = echapperXml(s);
    if (ctx.modele.format === "docx") {
      x = x.replace(/\t/g, '</w:t><w:tab/><w:t xml:space="preserve">')
        .replace(new RegExp(SAUT_LIGNE, "g"), '</w:t><w:br/><w:t xml:space="preserve">');
    } else {
      x = x.replace(/\t/g, "<text:tab/>").replace(new RegExp(SAUT_LIGNE, "g"), "<text:line-break/>")
        .replace(/ {2,}/g, function (m) { return ' <text:s text:c="' + (m.length - 1) + '"/>'; });
    }
    return x.replace(/\r?\n/g, noeud.ap + noeud.sp + noeud.av);
  }

  function formaterCompteur(ctx, n, rendus) {
    var s = String(n);
    rendus.forEach(function (r) {
      var nom = r[0];
      if (nom === "romain") s = romain(n);
      else if (nom === "romain_minuscule") s = romain(n).toLowerCase();
      else if (nom === "lettre") s = lettreRang(n);
      else if (nom === "lettre_majuscule") s = lettreRang(n).toUpperCase();
      else if (nom === "lettres") s = nombreEnLettres(n, ctx.rect);
      else if (nom === "ordinal") s = ordinalEnLettres(n, ctx.rect);
      else if (nom === "ordinal_abrege") s = n === 1 ? "1er" : n + "e";
      else if (nom === "chiffres") s = String(n);
      else s = transformer(nom, s);
    });
    return s;
  }

  function rendreNoeuds(ctx, noeuds, out) {
    for (var i = 0; i < noeuds.length; i++) {
      var n = noeuds[i];
      switch (n.t) {
        case "x": out.push(n.s); break;
        case "v": out.push(n.av + encoder(ctx, rendreValeur(ctx, n), n) + n.ap); break;
        case "si":
          var fait = false;
          for (var b = 0; b < n.b.length && !fait; b++) {
            if (verite(deballer(evaluer(ctx, n.b[b].c)))) { rendreNoeuds(ctx, n.b[b].n, out); fait = true; }
          }
          if (!fait && n.s) rendreNoeuds(ctx, n.s, out);
          break;
        case "opt":
          if (ctx.decisions.options[n.id] === true) rendreNoeuds(ctx, n.n, out);
          else if (ctx.decisions.options[n.id] === undefined) ctx.manque("Option « " + (ctx.modele.decisions.options[n.id] || n.id) + " » : retenir ou écarter");
          break;
        case "ch":
          var cas = ctx.decisions.choix[n.id];
          if (!cas) ctx.manque("Choix « " + ctx.modele.decisions.choix[n.id].libelle + " » : aucune possibilité retenue");
          else if (n.cas[cas]) rendreNoeuds(ctx, n.cas[cas], out);
          break;
        case "pour":
          var res = resoudre(ctx, n.l), items = developper(res.items);
          for (var k = 0; k < items.length; k++) {
            ctx.portees.push({ nom: n.v, item: items[k], rang: k + 1, nombre: items.length, liste: n.l.join(".") });
            rendreNoeuds(ctx, n.n, out);
            ctx.portees.pop();
          }
          break;
        case "cpt":
          ctx.compteurs[n.nom] = (ctx.compteurs[n.nom] || 0) + 1;
          var val = ctx.compteurs[n.nom];
          if (n.ancre) ctx.ancres[n.ancre] = val;
          out.push(n.av + encoder(ctx, formaterCompteur(ctx, val, n.r), n) + n.ap);
          break;
        case "ren":
          var cible = ctx.ancresFinales ? ctx.ancresFinales[n.ancre] : undefined;
          var txt;
          if (cible === undefined) {
            if (ctx.ancresFinales) ctx.alerte("Le renvoi « " + n.ancre + " » vise une stipulation absente du document généré.");
            txt = "[renvoi sans objet : " + n.ancre + "]";
          } else txt = formaterCompteur(ctx, cible, n.r);
          out.push(n.av + encoder(ctx, txt, n) + n.ap);
          break;
      }
    }
  }

  // ================================================================ corrections structurelles
  function retirerTableauxVides(xml, tbl, tr) {
    var re = new RegExp("<(/?)(" + tbl + "|" + tr + ")(?=[\\s>/])[^>]*?(/?)>", "g"), pile = [], suppr = [], m;
    while ((m = re.exec(xml))) {
      if (m[2] === tr) { if (m[1] !== "/" && pile.length) pile[pile.length - 1].lignes++; continue; }
      if (m[1] === "/") { var o = pile.pop(); if (o && o.lignes === 0) suppr.push([o.debut, re.lastIndex]); }
      else if (m[3] !== "/") pile.push({ debut: m.index, lignes: 0 });
    }
    suppr.sort(function (a, b) { return a[0] - b[0]; });
    var res = "", pos = 0;
    suppr.forEach(function (z) { if (z[0] >= pos) { res += xml.slice(pos, z[0]); pos = z[1]; } });
    return res + xml.slice(pos);
  }
  function corriger(format, xml) {
    if (format === "docx") {
      xml = retirerTableauxVides(xml, "w:tbl", "w:tr");
      xml = xml.replace(/(<w:tc\b[^>]*>(?:<w:tcPr>(?:(?!<\/w:tcPr>)[\s\S])*<\/w:tcPr>)?)(<\/w:tc>)/g, "$1<w:p/>$2");
    } else {
      xml = retirerTableauxVides(xml, "table:table", "table:table-row");
    }
    return xml;
  }

  // ================================================================ zip (stockage sans compression)
  var TABLE_CRC = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(o) { var c = 0xFFFFFFFF; for (var i = 0; i < o.length; i++) c = TABLE_CRC[(c ^ o[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function utf8(s) { return new TextEncoder().encode(s); }
  function depuisBase64(b) {
    var bin = atob(b), o = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) o[i] = bin.charCodeAt(i);
    return o;
  }

  /* Écrit une archive zip. Chaque entrée est soit du texte produit par le moteur (stocké sans compression),
     soit une entrée recopiée telle quelle du modèle d'origine (déjà compressée, CRC et taille connus). */
  function zipStocke(fichiers) {
    var d = new Date(), heure = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
      jour = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
    var locaux = [], central = [], decalage = 0;
    fichiers.forEach(function (f) {
      var nom = utf8(f.nom), methode = f.methode || 0;
      var crc = f.crc !== undefined ? f.crc : crc32(f.donnees);
      var taille = f.taille !== undefined ? f.taille : f.donnees.length, tailleComp = f.donnees.length;
      var h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(8, methode, true);
      h.setUint16(10, heure, true); h.setUint16(12, jour, true); h.setUint32(14, crc, true);
      h.setUint32(18, tailleComp, true); h.setUint32(22, taille, true); h.setUint16(26, nom.length, true); h.setUint16(28, 0, true);
      locaux.push(new Uint8Array(h.buffer), nom, f.donnees);
      var c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
      c.setUint16(10, methode, true); c.setUint16(12, heure, true); c.setUint16(14, jour, true); c.setUint32(16, crc, true);
      c.setUint32(20, tailleComp, true); c.setUint32(24, taille, true); c.setUint16(28, nom.length, true);
      c.setUint32(42, decalage, true);
      central.push(new Uint8Array(c.buffer), nom);
      decalage += 30 + nom.length + tailleComp;
    });
    var tailleCentral = central.reduce(function (s, x) { return s + x.length; }, 0);
    var fin = new DataView(new ArrayBuffer(22));
    fin.setUint32(0, 0x06054b50, true); fin.setUint16(8, fichiers.length, true); fin.setUint16(10, fichiers.length, true);
    fin.setUint32(12, tailleCentral, true); fin.setUint32(16, decalage, true);
    var morceaux = locaux.concat(central, [new Uint8Array(fin.buffer)]);
    var total = morceaux.reduce(function (s, x) { return s + x.length; }, 0), out = new Uint8Array(total), p = 0;
    morceaux.forEach(function (x) { out.set(x, p); p += x.length; });
    return out;
  }

  // ================================================================ aperçu en texte
  function apercu(format, xml) {
    var s = xml;
    if (format === "docx") {
      s = s.replace(/<w:tab\/>/g, "\t").replace(/<w:br\/>/g, "\n").replace(/<\/w:p>/g, "\n").replace(/<\/w:tc>/g, " | ");
      s = s.replace(/<w:(?:instrText|delText)\b[^>]*>[\s\S]*?<\/w:(?:instrText|delText)>/g, "");
    } else {
      s = s.replace(/<text:tab\/>/g, "\t").replace(/<text:line-break\/>/g, "\n")
        .replace(/<text:s text:c="(\d+)"\/>/g, function (m, n) { return Array(+n + 1).join(" "); })
        .replace(/<text:s\/>/g, " ").replace(/<\/text:(?:p|h)>/g, "\n").replace(/<\/table:table-cell>/g, " | ");
    }
    s = s.replace(/<[^>]+>/g, "").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, "&");
    return s.replace(/\n{3,}/g, "\n\n").trim();
  }

  // ================================================================ point d'entrée
  function preparer(modele) {
    if (!modele.locales_def) {
      modele.locales_def = {};
      (modele.locales || []).forEach(function (l) { modele.locales_def[l.id] = l; });
    }
    return modele;
  }

  function rendreParties(dico, modele, dossier) {
    preparer(modele);
    // première passe : compteurs et ancres ; seconde passe : document définitif
    var c1 = new Contexte(dico, modele, dossier);
    modele.parties.forEach(function (p) { rendreNoeuds(c1, p.arbre, []); });
    var ctx = new Contexte(dico, modele, dossier);
    ctx.ancresFinales = c1.ancres;
    var parties = {};
    modele.parties.forEach(function (p) {
      ctx.compteurs = ctx.compteurs || {};
      var out = []; rendreNoeuds(ctx, p.arbre, out);
      parties[p.nom] = corriger(modele.format, out.join(""));
    });
    var controles = (modele.controles || []).map(function (c) {
      var ok = verite(deballer(evaluer(ctx, c.c)));
      return { message: c.message, bloquant: c.bloquant, respecte: ok };
    });
    return { ctx: ctx, parties: parties, controles: controles };
  }

  function bilan(r, modele) {
    var principal = modele.format === "docx" ? "word/document.xml" : "content.xml";
    return {
      manquants: Object.keys(r.ctx.manquants),
      alertes: r.ctx.alertes,
      controles: r.controles,
      apercu: r.parties[principal] ? apercu(modele.format, r.parties[principal]) : "",
      calculs: Object.keys(modele.calculs || {}).filter(function (id) { return !modele.calculs[id].element_de; }).map(function (id) {
        return { id: id, libelle: modele.calculs[id].libelle, type: modele.calculs[id].type, valeur: calcul(r.ctx, id) };
      })
    };
  }

  function verifier(dico, modele, dossier) {
    return bilan(rendreParties(dico, modele, dossier), modele);
  }

  function generer(dico, modele, dossier) {
    var r = rendreParties(dico, modele, dossier), b = bilan(r, modele);
    b.octets = zipStocke(modele.fichiers.map(function (f) {
      if (f.gabarit) return { nom: f.nom, donnees: utf8(r.parties[f.nom]) };
      return { nom: f.nom, donnees: depuisBase64(f.b64), methode: f.methode, crc: f.crc, taille: f.taille };
    }));
    return b;
  }

  function nommer(dico, modele, dossier, p) {
    var ctx = new Contexte(dico, preparer(modele), dossier);
    if (!p) return "";
    var s = p.nature === "morale" ? ((ctx.formes[p.forme_juridique] || {}).libelle || "") + " " + (p.denomination || "")
      : [p.civilite === "madame" ? "Mme" : p.civilite === "monsieur" ? "M." : "", premierPrenom(p), (p.nom || "").toUpperCase()].join(" ");
    return s.replace(/\s+/g, " ").trim();
  }

  return {
    generer: generer, verifier: verifier, nommer: nommer, rendreParties: rendreParties, formater: function (dico, modele, type, v, rendu) {
      var ctx = new Contexte(dico, preparer(modele), {});
      return formater(ctx, { nat: "val", type: type, v: v, def: {} }, rendu);
    },
    nombreEnLettres: nombreEnLettres, montantEnLettres: montantEnLettres, ordinalEnLettres: ordinalEnLettres,
    decimalEnLettres: decimalEnLettres, dateLongue: dateLongue, dateLettres: dateLettres, ajouterMois: ajouterMois,
    prorogation: prorogation, paques: paques, zipStocke: zipStocke, apercu: apercu, montantEnChiffres: montantEnChiffres
  };
});
