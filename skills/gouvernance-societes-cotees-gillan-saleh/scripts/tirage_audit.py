#!/usr/bin/env python3
# tirage_audit.py — Tirage aléatoire STRATIFIÉ des citations d'index soumises à l'audit neutre.
#
# Population : toutes les citations « … » d'au moins 30 caractères normalisés des fichiers d'index
# (même définition que controle_citations_v2.py). Strates : les fichiers d'index. Allocation :
# proportionnelle à l'effectif, plancher de 2 par fichier, total TAILLE. Graine fixée et imprimée :
# quiconque relance le script avec la même graine sur la même version obtient le même tirage.
#
# USAGE : python3 scripts/tirage_audit.py --seed 20260904 --taille 60 --out /home/claude/verif/tirage.md
# Après un audit ayant révélé un écart : corriger, puis RETIRER avec une NOUVELLE graine.

import re, os, glob, random, argparse, math
ap=argparse.ArgumentParser(); ap.add_argument('--seed',type=int,required=True); ap.add_argument('--taille',type=int,default=60)
ap.add_argument('--build',default='/home/claude/build/gouvernance-emetteurs-cotes'); ap.add_argument('--out',required=True)
A=ap.parse_args()

EMPRUNT=re.compile(r'(rapport\s+AMF\s+20\\d\\d|rapport\s+HCGE\s+20\\d\\d|Rapport\s+AMF\s+20\\d\\d)[^.]{0,40}?p\\.\\s*\\d+',re.I)
def emprunt(avant):
    """v1.3 : une entrée peut citer un AUTRE document du corpus en le déclarant (« régime restitué par
    le rapport AMF 2021, p. 15 »). Le dossier d'audit doit le dire, sinon l'auditeur cherche la citation
    dans le mauvais document (audit du 14 septembre 2026, T25)."""
    m=EMPRUNT.search(avant)
    return m.group(0) if m else ''
def norm(s):
    s=s.replace('\u2019',"'"); s=re.sub(r'[«»"“”\u00a0]',' ',s).lower()
    return re.sub(r'[^a-z0-9àâäéèêëîïôöùûüçœæ]','',s)
def pages_rev(ctx):
    """v1.1 : première page annoncée dans l'entrée AVANT la citation (page de l'entrée), pas la dernière
    de la ligne — qui pouvait être la pagination d'un document cité en référence (audit S14)."""
    out=[]
    for m in re.finditer(r'p?p\.?\s*(\d+(?:\s*[-–—à]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–—à]\s*\d+)?)*)',ctx): out.append(m.group(1).strip())
    return out[0] if out else '?'

pop={}
for f in sorted(glob.glob(A.build+'/index_*.md')):
    b=os.path.basename(f); txt=open(f,encoding='utf-8').read(); L=[]
    for m in re.finditer(r'«\s*(.+?)\s*»',txt,re.S):
        q=m.group(1)
        if len(norm(q))<30: continue
        ligne=txt.count('\n',0,m.start())+1
        # contexte = l'entrée entière (de la dernière puce de premier niveau à la fin de la ligne courante)
        # v1.2 : la page annoncée est d'abord cherchée sur la LIGNE de l'entrée ; la puce mère
        # ne sert que si la ligne n'en porte aucune (audit du 10 sept. 2026 : S32).
        k=txt.rfind('\n',0,m.start())+1
        if pages_rev(txt[k:m.start()])=='?' and pages_rev(txt[m.end():txt.find('\n',m.end())])=='?':
            k=txt.rfind('\n- ',0,m.start()); k=k if k>=0 else max(0,m.start()-400)
        fin=txt.find('\n',m.end()); fin=fin if fin>=0 else len(txt)
        pg=pages_rev(txt[k:m.start()]) if pages_rev(txt[k:m.start()])!='?' else pages_rev(txt[m.end():fin])
        if pg=='?':   # puce parente ou intertitre porteur de la page
            kk=k
            while kk>0 and pg=='?':
                k2=txt.rfind('\n',0,kk-1)+1; line=txt[k2:kk-1]
                if line.strip() and line.lstrip().startswith(('-','#','|','*')): pg=pages_rev(line)
                if line.startswith('#'): break
                kk=k2
        emp=emprunt(txt[txt.rfind('\n',0,m.start())+1:m.start()])
        L.append((ligne,q.replace('\\',''),(pg+' — SOURCE : '+emp) if emp else pg))
    if L: pop[b]=L
N=sum(len(v) for v in pop.values())
# allocation proportionnelle, plancher 2, ajustée au total
alloc={b:max(2,round(A.taille*len(v)/N)) for b,v in pop.items()}
while sum(alloc.values())>A.taille:
    b=max(alloc,key=lambda x:(alloc[x]-2,len(pop[x]))); 
    if alloc[b]<=2: break
    alloc[b]-=1
while sum(alloc.values())<A.taille:
    b=max(pop,key=lambda x:len(pop[x])/alloc[x]); alloc[b]+=1
rng=random.Random(A.seed); rows=[]
for b in sorted(pop):
    for (ligne,q,pg) in sorted(rng.sample(pop[b],min(alloc[b],len(pop[b])))):
        rows.append((b,ligne,pg,q))
out=[f"# Tirage stratifié — graine {A.seed}, {len(rows)} citations sur {N} ({len(pop)} strates)\n",
     "Rejouable : `python3 scripts/tirage_audit.py --seed %d --taille %d` sur la même version du skill.\n"%(A.seed,A.taille),
     "| n° | fichier | ligne | page annoncée | citation |","|---|---|---|---|---|"]
for i,(b,l,pg,q) in enumerate(rows,1):
    out.append(f"| S{i:02d} | {b} | {l} | {pg} | « {q.replace('|','¦').replace(chr(10),' ')} » |")
open(A.out,'w',encoding='utf-8').write('\n'.join(out)+'\n')
print(f"{len(rows)} citations tirées sur {N} ; allocation : "+', '.join(f"{b.replace('index_','').replace('.md','')} {alloc[b]}" for b in sorted(pop)))
