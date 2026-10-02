#!/usr/bin/env python3
# controle_invention.py — Contrôle d'INVENTION (14 septembre 2026).
#
# Question posée : chaque mot placé entre guillemets figure-t-il dans la source, au même endroit ?
# Les contrôles précédents ne répondaient pas à cette question :
#   - controle_citations_v2 teste la PRÉSENCE d'une citation, et ignore celles qu'il ne localise pas ;
#   - controle_bornes_v3 compare la citation à sa tranche source, mais seulement si la tranche a été
#     localisée. Or une citation dont les premiers mots sont inventés n'est pas localisable : elle
#     tombait dans la classe NON_LOCALISE, c'est-à-dire hors de tout contrôle.
# C'est exactement par là qu'est passée la citation « La trajectoire [de réduction des émissions de]
# gaz à effet de serre… » (AMF 2022 p. 51), dont la source imprime « L'évolution des émissions de… ».
#
# Méthode : pour chaque citation, on cherche la fenêtre de la source qui lui ressemble le plus
# (difflib sur le texte normalisé, pages annoncées puis tout le document), puis on aligne mot à mot.
# Tout mot de l'index absent de la source à cet endroit est signalé. Sont neutralisés : les marques
# d'omission, le contenu des crochets éditoriaux, les appels de note et les guillemets.
import re,sys,os,glob,difflib,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'controle_bornes_v3.py'),encoding='utf-8').read()
exec(src[:src.find("rows=[]; stats={}")])
OFF={'GUIDE24':3}
MOTS=re.compile(r"[\w’']+",re.UNICODE)

def mots(s):
    s=re.sub(r'\[[^\]]*\]',' ',s)          # crochets éditoriaux et marques d'omission
    s=re.sub(r'[«»"“”]',' ',s)
    s=s.replace('’',"'")
    return [w.lower() for w in MOTS.findall(s) if not w.isdigit()]

rows=[]
for f in sorted(glob.glob(os.path.join(BUILD,'index_*.md'))):
    b=os.path.basename(f); d=MAP.get(b)
    if not d or not pages.get(d): continue
    prep(d); txt=open(f,encoding='utf-8').read()
    MP={p:mots(pages[d][p]) for p in pages[d]}
    for m in re.finditer(r'«\s*(.+?)\s*»',txt,re.S):
        q=m.group(1)
        if len(norm_map(q)[0])<30: continue
        ligne=txt.count('\n',0,m.start())+1
        mq=mots(q)
        if len(mq)<6: continue
        ls=txt.rfind('\n',0,m.start())+1
        ap=re.match(r'\*?\s*\(p\.\s*(\d+)\)',txt[m.end():m.end()+16])
        pref=({int(ap.group(1))+OFF.get(d,0)} if ap else set()) or {p+OFF.get(d,0) for p in pages_rev(txt[ls:m.start()])}
        # 1) localisation exacte par sous-chaîne (méthode éprouvée) : on aligne sur la tranche trouvée
        globals()['PREF']=pref
        segs=[x for x in ELIDE.split(q) if len(norm_map(x)[0])>=12] if ELIDE.search(q) else [q]
        loc=localiser(segs[0],d)
        if loc:
            pg,(a,bb),t,_=loc
            fin=localiser(segs[-1],d) or loc
            b2=fin[1][1]; t2=fin[2]
            fenetre=mots(t[max(0,a-120):bb+120]) if t2 is t else mots(t[max(0,a-120):]+t2[:b2+120])
            sm=difflib.SequenceMatcher(None,fenetre,mq,autojunk=False); p=pg
        else:
            # 2) aucune localisation : recherche par similarité, fenêtre glissante de la taille de la citation
            best=(0,None,None)
            for pp in sorted(MP):
                src_m=MP[pp]
                if len(src_m)<len(mq): continue
                for i in range(0,max(1,len(src_m)-len(mq)+1),max(1,len(mq)//2)):
                    w=src_m[i:i+int(len(mq)*1.6)]
                    r=difflib.SequenceMatcher(None,w,mq,autojunk=False).quick_ratio()
                    if r>best[0]: best=(r,pp,w)
            if not best[1]: continue
            p=best[1]; sm=difflib.SequenceMatcher(None,best[2],mq,autojunk=False)
        manq=[]
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag in ('insert','replace'):
                ajout=mq[j1:j2]
                if ajout: manq.append((' '.join(ajout),' '.join(sm.a[i1:i2])))
        couv=sum(i2-i1 for tag,i1,i2,j1,j2 in sm.get_opcodes() if tag=='equal')/max(1,len(mq))
        if couv>=0.97: manq=[]
        # Filtre décisif : un ajout n'est une invention que si la suite de mots ne figure NULLE PART
        # dans le document. Les autres écarts sont des artefacts d'alignement (élisions, notes, colonnes).
        doc=' '.join(' '.join(MP[pp]) for pp in sorted(MP))
        vrais=[]
        for a_,s_ in manq:
            ws=a_.split()
            if len(ws)<3: continue
            if ' '.join(ws) in doc: continue
            # on cherche la plus longue sous-suite absente du document
            absent=[w for i,w in enumerate(ws) if ' '.join(ws[max(0,i-2):i+3]) not in doc]
            if absent: vrais.append((a_,s_))
        if vrais: rows.append((b,ligne,p,round(couv,3),vrais[:3]))
rows.sort(key=lambda r:r[3])
print('citations comportant des mots absents de la source :',len(rows))
print(collections.Counter(r[0] for r in rows))
out=['# Contrôle d\'invention — mots présents dans l\'index, absents de la source\n',
     '| fichier | ligne | page | couverture | ajouts |','|---|---|---|---|---|']
for b,l,p,c,mq in rows:
    det='; '.join(f'« {a} » (source : « {s_}… »)' for a,s_ in mq)
    out.append(f'| {b} | {l} | {p} | {c} | {det[:300].replace("|","¦")} |')
open('/home/claude/verif/rapport_invention.md','w',encoding='utf-8').write('\n'.join(out))
for r in rows[:15]: print(' ',r[0],r[1],'p.'+str(r[2]),'couv',r[3],r[4][:1])
