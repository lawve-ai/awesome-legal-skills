#!/usr/bin/env node
/*
 * build_nds.js — assemble le sujet d'entraînement de note de synthèse CRFPA
 * et sa grille de notation.
 *
 * Par défaut, DEUX fichiers Word distincts : le sujet (dossier documentaire)
 * et la grille de notation, pour que le sujet puisse être distribué sans le
 * corrigé. Le décompte de pages annoncé en page de garde ne compte que les
 * pages du sujet.
 *
 * Usage :
 *   node build_nds.js dossier.json [dossier_de_sortie] [--unique]
 *
 *   --unique : produit un fichier unique, sujet puis grille commençant sur la
 *              page suivante, dans une section dont la pagination repart à 1.
 *
 * Schéma attendu de dossier.json :
 * {
 *   "session": "2027",
 *   "date_epreuve": "lundi 6 septembre 2027",
 *   "sujet": "LE SECRET DES AFFAIRES",        // en capitales
 *   "slug": "secret_des_affaires",             // pour les noms de fichiers
 *   "code_sujet": "27CRFPA-NS1-ENTR",          // pied de page, facultatif
 *   "documents": [
 *     {
 *       "n": 1,
 *       "intitule": "Cass. com., 12 mars 2025, n° 23-14567, publié au bulletin",
 *       "contenu": ["premier paragraphe", "deuxième paragraphe"],
 *       "a_completer": false,                  // true = emplacement à remplir
 *       "saut_de_page": false,                 // true = commence en haut de page
 *       "note_insertion": "Extrait à insérer par l'enseignant. Référence : ...",
 *       // Champs de travail, ignorés à la mise en page mais lus par
 *       // tirer_ordre.py et verifier_verbatim.py :
 *       "id": "cass_com_2025_23_14567",        // identifiant stable
 *       "registre": "jurisprudence",           // texte | jurisprudence | doctrine
 *                                              // | institutionnel | non_juridique
 *       "nature": "extrait",                   // extrait (verbatim) | notice
 *       "saga": "secret_sante",                // facultatif
 *       "couple_avec": null,                   // id de la décision commentée
 *       "cle_de_voute": false,
 *       "date": "2025-03-12",
 *       "source": {
 *         "fichier": "sources/cass_com_2025_23_14567.txt",
 *         "identifiant": "n° 23-14567",
 *         "outil": "Judilibre",
 *         "statut": "libre"                    // libre | droits
 *       }
 *     }
 *   ],
 *   "grille": {
 *     "resumes": [{ "n": 1, "texte": "..." }],
 *     "problematique": ["paragraphe 1", "paragraphe 2"],
 *     "themes": [
 *       {
 *         "titre": "Thème I : La reconnaissance du secret",
 *         "points": 5,
 *         "sous_themes": [
 *           { "titre": "Le secret comme bien", "documents": "document 2, document 7" }
 *         ]
 *       }
 *     ],
 *     "plan": [
 *       { "niveau": 1, "texte": "I. Les nécessités de la protection" },
 *       { "niveau": 2, "texte": "A. Pourquoi protéger ? (Thème I)" },
 *       { "niveau": 3, "texte": "1. La valeur économique" }
 *     ]
 *   }
 * }
 *
 * Les documents sont écrits dans l'ordre du tableau : c'est à l'appelant
 * d'avoir tiré cet ordre sous contraintes avant d'écrire le JSON.
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execSync } = require("child_process");
const {
  Document, Packer, Paragraph, TextRun, PageBreak, PageNumber,
  AlignmentType, Footer, BorderStyle, TabStopType, convertMillimetersToTwip,
} = require("docx");

const MENTION =
  "Sujet d'entraînement original, document non officiel, sans lien avec la " +
  "Commission nationale de l'examen d'accès au CRFPA.";

const RECOMMANDATIONS = [
  "Extraits des recommandations de la Commission nationale à destination des jurys et des correcteurs d'épreuve, relativement à l'épreuve d'admissibilité de \"Note de synthèse rédigée en cinq heures\" (article 5-1° de l'arrêté du 17 octobre 2016) :",
  "« L'épreuve est destinée à apprécier, notamment, les capacités de synthèse du candidat : la limite de quatre pages ne doit pas être dépassée.",
  "La qualité rédactionnelle est prise en compte (les déficiences orthographiques et syntaxiques, les impropriétés de termes, l'inélégance de style, les obstacles divers à la lisibilité du texte sont sanctionnés).",
  "Un plan apparent (avec des titres concis), dont la structuration est laissée à la libre appréciation du candidat, s'il n'est pas obligatoire, est recommandé.",
  "La note de synthèse doit consister en une synthèse objective des éléments du dossier documentaire, et seules les informations contenues dans le dossier peuvent être utilisées. La référence au numéro du document peut s'avérer nécessaire à la bonne compréhension de la synthèse et est recommandée.",
  "Une brève introduction est recommandée. Une conclusion n'est pas nécessaire ».",
];

const FONT = "Arial";

function p(text, opts = {}) {
  const {
    bold = false, italics = false, size = 22, align = AlignmentType.JUSTIFIED,
    before = 0, after = 120, underline = false, indent = null, keepNext = false,
    border = null,
  } = opts;
  return new Paragraph({
    alignment: align,
    spacing: { before, after, line: 276 },
    keepNext,
    ...(indent ? { indent } : {}),
    ...(border ? { border } : {}),
    children: [
      new TextRun({
        text, bold, italics, size, font: FONT,
        ...(underline ? { underline: {} } : {}),
      }),
    ],
  });
}

// Encadré utilisé pour faire ressortir l'intitulé du sujet.
function cadre() {
  const t = { style: BorderStyle.SINGLE, size: 6, color: "000000", space: 12 };
  return { top: t, bottom: t, left: t, right: t };
}

function blank(n = 1) {
  return Array.from({ length: n }, () =>
    new Paragraph({ children: [new TextRun({ text: "", font: FONT, size: 22 })] }));
}

// Nombre total de pages de la partie en cours. Word connaît le champ
// SECTIONPAGES, mais LibreOffice le rend vide : quand le nombre est connu
// (calculé par un premier passage de conversion), on l'écrit en clair.
function pagesRun(total, size = 22) {
  if (typeof total === "number" && total > 0) {
    return new TextRun({ text: String(total), font: FONT, size });
  }
  return new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size });
}

function footer(code, total) {
  return new Footer({
    children: [
      new Paragraph({
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: "999999", space: 6 } },
        tabStops: [{ type: TabStopType.RIGHT, position: convertMillimetersToTwip(160) }],
        children: [
          new TextRun({ text: code || "", font: FONT, size: 16 }),
          new TextRun({ text: "\t", font: FONT, size: 16 }),
          new TextRun({ text: "Page : ", font: FONT, size: 16 }),
          new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 }),
          new TextRun({ text: "/", font: FONT, size: 16 }),
          pagesRun(total, 16),
        ],
      }),
      new Paragraph({
        children: [new TextRun({
          text: "Document d'entraînement non officiel",
          font: FONT, size: 14, italics: true, color: "666666",
        })],
      }),
    ],
  });
}

function sectionProps(code, redemarrer = false, total = null) {
  return {
    properties: {
      page: {
        margin: {
          top: convertMillimetersToTwip(25), bottom: convertMillimetersToTwip(22),
          left: convertMillimetersToTwip(25), right: convertMillimetersToTwip(25),
        },
        ...(redemarrer ? { pageNumbers: { start: 1 } } : {}),
      },
    },
    footers: { default: footer(code, total) },
  };
}

function sujetChildren(d, pagesSujet = null) {
  const aCompleter = d.documents.filter((x) => x.a_completer).length;
  const C = AlignmentType.CENTER;

  const garde = [
    ...blank(2),
    p("ENTRAÎNEMENT À L'EXAMEN D'ACCÈS AU CRFPA", { bold: true, align: C, size: 28 }),
    p(`SESSION ${d.session}`, { bold: true, align: C, size: 28 }),
    ...(d.date_epreuve ? [p(d.date_epreuve, { align: C, size: 24 })] : []),
    ...blank(2),
    p("NOTE DE SYNTHÈSE", { bold: true, align: C, size: 36 }),
    ...blank(1),
    // L'intitulé du sujet figure dès la page de garde, encadré, pour qu'il ne
    // puisse pas passer inaperçu.
    p("Sujet de l'épreuve", { align: C, italics: true, size: 20, after: 80 }),
    p(d.sujet, { align: C, bold: true, size: 32, border: cadre(), after: 200 }),
    ...blank(1),
    p("Durée de l'épreuve : 5 heures", { align: C }),
    p("Coefficient : 3", { align: C }),
    p("Documents autorisés : Néant", { align: C }),
    ...blank(1),
    new Paragraph({
      alignment: C,
      spacing: { after: 120 },
      children: [
        new TextRun({ text: "Ce sujet comporte ", font: FONT, size: 22 }),
        pagesRun(pagesSujet),
        new TextRun({ text: " pages numérotées de 1/", font: FONT, size: 22 }),
        pagesRun(pagesSujet),
        new TextRun({ text: " à ", font: FONT, size: 22 }),
        pagesRun(pagesSujet),
        new TextRun({ text: "/", font: FONT, size: 22 }),
        pagesRun(pagesSujet),
        new TextRun({ text: ".", font: FONT, size: 22 }),
      ],
    }),
    ...blank(2),
    p(MENTION, { align: C, italics: true, size: 20 }),
    ...(aCompleter > 0
      ? [p(
          `${aCompleter} document${aCompleter > 1 ? "s" : ""} comporte${aCompleter > 1 ? "nt" : ""} un emplacement à compléter par l'enseignant à partir de ses bases documentaires.`,
          { align: C, italics: true, size: 20 })]
      : []),
    new Paragraph({ children: [new PageBreak()] }),
  ];

  const recos = [
    ...RECOMMANDATIONS.map((t, i) => p(t, { italics: true, size: 21, after: i === 0 ? 200 : 140 })),
    ...blank(3),
    p("À partir des documents joints, vous établirez une note de synthèse sur le sujet suivant :", { after: 400 }),
    p(d.sujet, { align: C, bold: true, italics: true, size: 32, border: cadre() }),
    new Paragraph({ children: [new PageBreak()] }),
  ];

  const liste = [
    p(`NOTE DE SYNTHÈSE — ${d.sujet}`, { align: C, bold: true, size: 22, after: 240 }),
    p("Liste des documents :", { bold: true, after: 240 }),
    ...d.documents.map((doc) => p(`DOCUMENT ${doc.n} : ${doc.intitule}`, { after: 160 })),
    new Paragraph({ children: [new PageBreak()] }),
  ];

  const corps = [];
  d.documents.forEach((doc, idx) => {
    corps.push(p(`DOCUMENT ${doc.n} : ${doc.intitule}`, {
      bold: true, underline: true, align: AlignmentType.LEFT,
      before: idx === 0 ? 0 : 240, after: 200, keepNext: true,
    }));
    if (doc.a_completer) {
      corps.push(p(doc.note_insertion ||
        "Extrait à insérer par l'enseignant à partir de ses bases documentaires.",
        { italics: true, after: 160 }));
    }
    (doc.contenu || []).forEach((para) => corps.push(p(para)));
    // Les documents s'enchaînent sur la même page, comme dans les sujets réels.
    // Forcer un saut avec "saut_de_page": true sur le document suivant.
    if (idx < d.documents.length - 1 && d.documents[idx + 1].saut_de_page) {
      corps.push(new Paragraph({ children: [new PageBreak()] }));
    }
  });

  return [...garde, ...recos, ...liste, ...corps];
}

function grilleChildren(d) {
  const g = d.grille || {};
  const C = AlignmentType.CENTER;
  const total = (g.themes || []).reduce((s, t) => s + (t.points || 0), 0);

  const children = [
    p(`ENTRAÎNEMENT À L'EXAMEN D'ACCÈS AU CRFPA — SESSION ${d.session}`, { align: C, bold: true, size: 24 }),
    p("NOTE DE SYNTHÈSE", { align: C, bold: true, size: 24, after: 80 }),
    p(d.sujet, { align: C, bold: true, size: 28, border: cadre(), after: 200 }),
    p("GRILLE DE NOTATION", { align: C, bold: true, size: 28, after: 200 }),
    p("Document d'entraînement non officiel, sans lien avec la Commission nationale de l'examen d'accès au CRFPA.",
      { align: C, italics: true, size: 20, after: 320 }),

    p("Rappel des recommandations applicables à l'épreuve", { bold: true, size: 24, after: 160 }),
    ...RECOMMANDATIONS.slice(1).map((t) => p(t, { italics: true, size: 21, after: 140 })),

    p("Résumé des documents du dossier", { bold: true, size: 24, before: 320, after: 200 }),
  ];

  (g.resumes || []).forEach((r) => {
    const doc = d.documents.find((x) => x.n === r.n);
    children.push(p(`DOCUMENT ${r.n} : ${doc ? doc.intitule : ""}`, {
      bold: true, after: 120, keepNext: true,
    }));
    const paras = Array.isArray(r.texte) ? r.texte : [r.texte];
    paras.forEach((t) => children.push(p(t, { after: 200 })));
  });

  children.push(p("Problématique générale", { bold: true, size: 24, before: 320, after: 200 }));
  (g.problematique || []).forEach((t) => children.push(p(t)));

  children.push(p("Thèmes particuliers", { bold: true, size: 24, before: 320, after: 200 }));
  (g.themes || []).forEach((t) => {
    children.push(p(`${t.titre} (${t.points} points)`, { bold: true, after: 120, keepNext: true }));
    (t.sous_themes || []).forEach((st) => {
      children.push(p(`- ${st.titre} (${st.documents})`, {
        after: 100, indent: { left: convertMillimetersToTwip(8) },
      }));
    });
  });
  children.push(p(`Total : ${total} points.`, { italics: true, before: 160, after: 200 }));

  children.push(p("Plan indicatif", { bold: true, size: 24, before: 320, after: 200 }));
  (g.plan || []).forEach((entry) => {
    const lvl = entry.niveau || 1;
    children.push(p(entry.texte, {
      align: AlignmentType.LEFT,
      bold: lvl === 1,
      after: lvl === 1 ? 120 : 80,
      indent: { left: convertMillimetersToTwip((lvl - 1) * 8) },
    }));
  });

  children.push(p("Qualité rédactionnelle", { bold: true, size: 24, before: 320, after: 160 }));
  children.push(p(
    "La structuration du plan est laissée à la libre appréciation du candidat : un plan différent, cohérent et couvrant les mêmes thèmes, ne doit pas être pénalisé. Les déficiences orthographiques et syntaxiques, les impropriétés de termes, l'inélégance de style et les obstacles divers à la lisibilité du texte sont sanctionnés."));

  return children;
}

function docUnique(d, pagesSujet = null, pagesGrille = null) {
  const codeGrille = d.code_sujet ? `${d.code_sujet} — GRILLE` : "GRILLE DE NOTATION";
  return new Document({
    creator: "note-de-synthese-crfpa",
    title: `Note de synthèse d'entraînement et grille — ${d.sujet}`,
    sections: [
      { ...sectionProps(d.code_sujet, false, pagesSujet), children: sujetChildren(d, pagesSujet) },
      { ...sectionProps(codeGrille, true, pagesGrille), children: grilleChildren(d) },
    ],
  });
}

function docSujet(d, pagesSujet = null) {
  return new Document({
    creator: "note-de-synthese-crfpa",
    title: `Note de synthèse d'entraînement — ${d.sujet}`,
    sections: [{ ...sectionProps(d.code_sujet, false, pagesSujet), children: sujetChildren(d, pagesSujet) }],
  });
}

function docGrille(d) {
  const codeGrille = d.code_sujet ? `${d.code_sujet} — GRILLE` : "GRILLE DE NOTATION";
  return new Document({
    creator: "note-de-synthese-crfpa",
    title: `Grille de notation — ${d.sujet}`,
    sections: [{ ...sectionProps(codeGrille), children: grilleChildren(d) }],
  });
}

// Premier passage : convertir un document en PDF pour compter ses pages.
// Si LibreOffice n'est pas disponible, on renvoie null et les champs Word
// prennent le relais.
function compterPages(buffer) {
  try {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "nds-"));
    const docx = path.join(dir, "mesure.docx");
    fs.writeFileSync(docx, buffer);
    const soffice = fs.existsSync("/mnt/skills/public/docx/scripts/office/soffice.py")
      ? "python3 /mnt/skills/public/docx/scripts/office/soffice.py"
      : "soffice";
    execSync(`${soffice} --headless --convert-to pdf --outdir ${dir} ${docx}`,
      { stdio: "ignore", timeout: 180000 });
    const out = execSync(`pdfinfo ${path.join(dir, "mesure.pdf")}`, { encoding: "utf8" });
    const m = out.match(/Pages:\s+(\d+)/);
    return m ? parseInt(m[1], 10) : null;
  } catch (e) {
    return null;
  }
}

function verifier(d) {
  const problemes = [];
  if (!d.sujet) problemes.push("champ 'sujet' manquant");
  if (!d.documents || d.documents.length < 14) problemes.push("moins de 14 documents");
  if (d.documents && d.documents.length > 22) problemes.push("plus de 22 documents");
  const sansRegistre = (d.documents || []).filter((x) => !x.registre).map((x) => x.n);
  if (sansRegistre.length) problemes.push(`documents sans registre : ${sansRegistre.join(", ")}`);
  const sansSource = (d.documents || [])
    .filter((x) => !x.a_completer && x.nature !== "notice" && !(x.source && x.source.fichier))
    .map((x) => x.n);
  if (sansSource.length) problemes.push(`extraits sans fichier source (verbatim non contrôlable) : ${sansSource.join(", ")}`);
  if (!d.tirage) problemes.push("aucun champ 'tirage' : l'ordre n'a pas été tiré par tirer_ordre.py");
  if (d.grille) {
    const total = (d.grille.themes || []).reduce((s, t) => s + (t.points || 0), 0);
    if (total !== 20) problemes.push(`total des points = ${total} au lieu de 20`);
    const resumes = new Set((d.grille.resumes || []).map((r) => r.n));
    const manquants = (d.documents || []).filter((x) => !resumes.has(x.n)).map((x) => x.n);
    if (manquants.length) problemes.push(`documents sans résumé dans la grille : ${manquants.join(", ")}`);
    const cites = (d.grille.themes || [])
      .flatMap((t) => (t.sous_themes || []).map((s) => s.documents)).join(" ");
    const orphelins = (d.documents || [])
      .filter((x) => !new RegExp(`document\\s*${x.n}\\b`, "i").test(cites))
      .map((x) => x.n);
    if (orphelins.length) problemes.push(`documents rattachés à aucun thème : ${orphelins.join(", ")}`);
  } else {
    problemes.push("aucune grille dans le JSON");
  }
  return problemes;
}

async function main() {
  const args = process.argv.slice(2);
  const unique = args.includes("--unique");
  const [jsonPath, outDir = "/mnt/user-data/outputs"] =
    args.filter((a) => !a.startsWith("--"));
  if (!jsonPath) {
    console.error("Usage : node build_nds.js dossier.json [dossier_de_sortie] [--unique]");
    process.exit(1);
  }
  const d = JSON.parse(fs.readFileSync(jsonPath, "utf8"));

  const problemes = verifier(d);
  if (problemes.length) {
    console.warn("Avertissements :");
    problemes.forEach((x) => console.warn("  - " + x));
  }

  fs.mkdirSync(outDir, { recursive: true });
  const slug = d.slug || "note_de_synthese";
  const suffixe = `${slug}_${d.session || ""}`;

  const pagesSujet = d.pages_sujet || compterPages(await Packer.toBuffer(docSujet(d)));
  if (!pagesSujet) {
    console.warn("  - décompte de pages non calculé (LibreOffice indisponible) : le nombre affiché en page de garde est un champ Word, à vérifier à l'ouverture.");
  }

  if (!unique || !d.grille) {
    const fSujet = path.join(outDir, `sujet_nds_${suffixe}.docx`);
    fs.writeFileSync(fSujet, await Packer.toBuffer(docSujet(d, pagesSujet)));
    console.log("Écrit : " + fSujet);
    if (d.grille) {
      const fGrille = path.join(outDir, `grille_nds_${suffixe}.docx`);
      fs.writeFileSync(fGrille, await Packer.toBuffer(docGrille(d)));
      console.log("Écrit : " + fGrille);
    }
  } else {
    const pagesGrille = compterPages(await Packer.toBuffer(docGrille(d)));
    const fUnique = path.join(outDir, `nds_${suffixe}_sujet_et_grille.docx`);
    fs.writeFileSync(fUnique, await Packer.toBuffer(docUnique(d, pagesSujet, pagesGrille)));
    console.log("Écrit : " + fUnique);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
