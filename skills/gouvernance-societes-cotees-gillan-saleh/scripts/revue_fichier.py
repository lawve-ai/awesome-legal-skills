#!/usr/bin/env python3
# revue_fichier.py — Dossier de relecture exhaustive d'un fichier d'index (reprise du 10 septembre 2026).
#
# Pour CHAQUE citation du fichier, produit un enregistrement compact destiné à la lecture humaine :
#   page annoncée | tranche exacte de la source | 60 caractères avant | 60 caractères après | écarts caractère à caractère
# Les citations dont tous les contrôles automatiques passent sont marquées [auto] ; celles qui demandent
# une lecture portent la liste des signaux. Aucun verdict n'est rendu ici : le script prépare la relecture.
#
# USAGE : python3 scripts/revue_fichier.py index_HCGE_2020.md > /home/claude/verif/revue_HCGE_2020.md
import re,sys,os,difflib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'controle_bornes_v3.py'),encoding='utf-8').read()
exec(src[:src.find("rows=[]; stats={}")])
f=sys.argv[1]; b=os.path.basename(f); d=MAP[b]
full=os.path.join(BUILD,b); txt=open(full,encoding='utf-8').read()
out=[f'# Relecture exhaustive — {b} ({d})\n']
n=0
for m in re.finditer(r'«\s*(.+?)\s*»',txt,re.S):
    q=m.group(1)
    if len(norm_map(q)[0])<30: continue
    n+=1; ligne=txt.count('\n',0,m.start())+1
    ls=txt.rfind('\n',0,m.start())+1; le=txt.find('\n',m.end()); le=le if le>=0 else len(txt)
    ap=re.match(r'\*?\s*\(p\.\s*(\d+)\)',txt[m.end():m.end()+16])
    PREF=({int(ap.group(1))} if ap else set()) or pages_rev(txt[ls:m.start()]) or pages_rev(txt[m.end():le])
    globals()['PREF']=PREF
    segs=[s for s in ELIDE.split(q) if len(norm_map(s)[0])>=20] if ELIDE.search(q) else [q]
    r=localiser(segs[0],d)
    if not r:
        out.append(f"\n## {n} — l.{ligne} — p. annoncée {sorted(PREF) or '?'} — **NON LOCALISÉE**\nINDEX : {q[:300]}\n"); continue
    p,(a,bb),t,_=r
    # la tranche peut tomber dans la page suivante : NM concatène p et p+1 (correctif du 10 sept. 2026)
    o1=sorted(pages[d]); l1=NM[d][p]['len1']
    if a>=l1 and o1.index(p)+1<len(o1): p=o1[o1.index(p)+1]
    rl=localiser(segs[-1],d) or r
    p2=rl[0]; l2=NM[d][p2]['len1']
    if rl[1][0]>=l2 and o1.index(p2)+1<len(o1): p2=o1[o1.index(p2)+1]
    _,(a2,b2),t2,_=rl
    # v1.1 : soft() effaçait les guillemets de la source, masquant la frontière réelle des citations
    garde=lambda x: re.sub(r'\s+',' ',x.replace('\u2019',"'")).strip()
    pre=garde(t[max(0,a-70):a]); post=garde(t2[b2:b2+70])
    diffs=[]
    for sg in segs:
        l2=localiser(sg,d)
        if not l2: diffs.append(('SEGMENT NON LOCALISÉ',sg[:60],'')); continue
        _,(x,y),tt,_=l2
        for typ,sc,cc,fa,fb in diffs_fn(soft(tt[x:y]),soft(sg)) if False else []: pass
    out.append(f"\n## {n} — l.{ligne} — p. annoncée {sorted(PREF) or '?'} — trouvée p. {p}"
               f"{' / '+str(p2) if p2!=p else ''}\n"
               f"AVANT  : …{pre}\nINDEX  : {q}\nSOURCE : {soft(t[a:bb])[:400]}\nAPRÈS  : {post}…\n")
open(sys.argv[2] if len(sys.argv)>2 else '/dev/stdout','w',encoding='utf-8').write('\n'.join(out))
print(f'{n} citations',file=sys.stderr)
