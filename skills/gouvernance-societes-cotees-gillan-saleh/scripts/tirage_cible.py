#!/usr/bin/env python3
# tirage_cible.py — Tirage stratifié par TYPE DE DIFFICULTÉ (complément de tirage_audit.py).
#
# tirage_audit.py stratifie par fichier : il mesure le taux d'écart moyen du corpus.
# Ce script stratifie par classe de risque, pour éprouver les points où les cinq audits
# précédents ont trouvé des écarts : élisions, guillemets de second niveau, crochets
# éditoriaux, chiffres et références normalisables, citations longues, plages de pages,
# citations non localisables par sous-chaîne. Il ne mesure pas un taux moyen : il cherche
# les défauts là où ils se logent.
#
# USAGE : python3 scripts/tirage_cible.py --seed N --par-classe 8 --out fichier.md
import re,sys,os,glob,random,argparse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'controle_bornes_v3.py'),encoding='utf-8').read()
exec(src[:src.find("rows=[]; stats={}")])
ap=argparse.ArgumentParser(); ap.add_argument('--seed',type=int,required=True)
ap.add_argument('--par-classe',type=int,default=8); ap.add_argument('--out',required=True)
A=ap.parse_args()

EMPRUNT=re.compile(r'(rapport\s+AMF\s+20\\d\\d|rapport\s+HCGE\s+20\\d\\d|Rapport\s+AMF\s+20\\d\\d)[^.]{0,40}?p\\.\\s*\\d+',re.I)
def emprunt(avant):
    """v1.3 : une entrée peut citer un AUTRE document du corpus en le déclarant (« régime restitué par
    le rapport AMF 2021, p. 15 »). Le dossier d'audit doit le dire, sinon l'auditeur cherche la citation
    dans le mauvais document (audit du 14 septembre 2026, T25)."""
    m=EMPRUNT.search(avant)
    return m.group(0) if m else ''
def page_de(txt,m,ls,le):
    a=re.match(r'\*?\s*\(p\.\s*(\d+(?:\s*-\s*\d+)?)\)',txt[m.end():m.end()+20])
    if a: return a.group(1)
    for ctx in (txt[ls:m.start()],txt[m.end():le]):
        mm=re.search(r'p?p\.\s*(\d+(?:\s*[-–]\s*\d+)?)',ctx)
        if mm: return mm.group(1)
    k=ls
    while k>0:
        k2=txt.rfind('\n',0,k-1)+1; line=txt[k2:k-1]
        if line.strip() and line.lstrip().startswith(('-','#','|','*')):
            mm=re.search(r'p?p\.\s*(\d+(?:\s*[-–]\s*\d+)?)',line)
            if mm: return mm.group(1)
        if line.startswith('#'): break
        k=k2
        if k==0: break
    return '?'

CL={'élision':lambda q:bool(ELIDE.search(q)),
    'guillemet de second niveau':lambda q:'"' in q,
    'crochet éditorial':lambda q:bool(re.search(r'\[[^…\]]{1,40}\]',q)),
    'chiffres et références':lambda q:bool(re.search(r'\d+\s*%|\bn°|L\.\s?\d',q)),
    'citation longue':lambda q:len(q)>600}
pool={k:[] for k in CL}; pool['plage de pages']=[]; pool['non localisable']=[]
for f in sorted(glob.glob(os.path.join(BUILD,'index_*.md'))):
    b=os.path.basename(f); d=MAP.get(b)
    if not d or not pages.get(d): continue
    prep(d); txt=open(f,encoding='utf-8').read()
    for m in re.finditer(r'«\s*(.+?)\s*»',txt,re.S):
        q=m.group(1)
        if len(norm_map(q)[0])<30: continue
        ls=txt.rfind('\n',0,m.start())+1; le=txt.find('\n',m.end()); le=le if le>=0 else len(txt)
        pg=page_de(txt,m,ls,le); ligne=txt.count('\n',0,m.start())+1
        rec=(b,ligne,pg,q)
        for k,test in CL.items():
            if test(q): pool[k].append(rec)
        if '-' in pg: pool['plage de pages'].append(rec)
        globals()['PREF']=set()
        segs=[s for s in ELIDE.split(q) if len(norm_map(s)[0])>=12] if ELIDE.search(q) else [q]
        if not localiser(segs[0],d): pool['non localisable'].append(rec)
rng=random.Random(A.seed); out=[]; n=0
for k in sorted(pool):
    ech=sorted(rng.sample(pool[k],min(A.par_classe,len(pool[k]))))
    out.append(f"\n### Classe « {k} » — {len(ech)} tirées sur {len(pool[k])}\n")
    out.append("| n° | Fichier, ligne | Page annoncée | Citation |\n|---|---|---|---|")
    for b,l,pg,q in ech:
        n+=1; out.append(f"| T{n:02d} | {b}, l. {l} | p. {pg} | « {q.replace('|','¦').replace(chr(10),' ')} » |")
open(A.out,'w',encoding='utf-8').write(f"# Tirage ciblé par classe de risque — graine {A.seed}, {n} citations\n"+'\n'.join(out)+'\n')
print(f"{n} citations tirées ; classes : "+', '.join(f"{k} {len(pool[k])}" for k in sorted(pool)))
