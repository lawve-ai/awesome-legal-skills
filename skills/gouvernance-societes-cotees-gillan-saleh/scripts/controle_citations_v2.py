#!/usr/bin/env python3
# controle_citations.py — Contrôle binaire de copie des citations des index du skill
# gouvernance-emetteurs-cotes contre le corpus PDF. Version 2.3 du 27 août 2026 : le corpus
# est préparé par `scripts/extraire_corpus.py` (extraction sans -layout câblée) ; un document
# dont le répertoire de corpus est vide est classé NON VÉRIFIABLE et non INTROUVABLE.
# Version 2.2 du 14 juillet 2026 :
# parseur d'annonces v2.2 — annonces composites (toutes pages), fenêtre avant+après,
# plafond au nb de pages du document, conformité si présence à une page annoncée
# (avec ou sans offset). Historique v2 du 11 juillet 2026 :
# ajoute la passe segmentée des élisions signalées ([…], [...], [mot]) — chaque
# segment >= 20 caractères normalisés doit figurer, dans l'ordre, sur une page ou
# une paire de pages adjacentes. Verdict CONFORME (segments) le cas échéant.
# USAGE : (1) copier le skill installé vers BUILD ; (2) `python3 scripts/extraire_corpus.py`
# (prépare CORPUS/<CLE>/N.txt ; archives zip -> unzip, vrais PDF -> pdftotext SANS -layout,
# règle câblée dans le script et non plus confiée à l'opérateur) ; (3) exécuter le présent script.
# v2.4 (8 sept. 2026) : page EXACTE — la tolérance ±1 masquait des pages inexactes (audit du 4-8 sept., S32/S43/S51).
# Verdicts : CONFORME / PAGE (erronée) / NON RETROUVÉE / NON VÉRIFIABLE (source absente).
#
# « NON RETROUVÉE » ne veut pas dire « citation fantôme » : le contrôle cherche une suite continue de
# caractères dans le texte extrait, et l'extraction insère parfois un folio, un bloc de notes ou une
# colonne voisine EN PLEIN MILIEU de la phrase. Les 42 citations dans ce cas au 14 septembre 2026 ont
# toutes été confrontées à la page et sont conformes ; s'y ajoutent les citations empruntées à un autre
# document du corpus, déclarées comme telles dans l'entrée. Voir REPRISE_ETAT.md.
# Auto-détection des décalages systématiques de pagination (imprimée vs PDF).

import re, sys, os, glob
BUILD='/home/claude/build/gouvernance-emetteurs-cotes'; CORPUS='/home/claude/tests'
os_out='/home/claude/verif'
MAP={'index_AMF_2020.md':'AMF_2020','index_AMF_2022.md':'AMF_2022','index_AMF_2023.md':'AMF_2023',
'index_AMF_2024.md':'AMF_2024','index_HCGE_2020.md':'HCGE_2020','index_HCGE_2021.md':'HCGE_2021',
'index_HCGE_2022.md':'HCGE_2022','index_HCGE_2023.md':'HCGE_2023','index_HCGE_2024.md':'HCGE_2024',
'index_HCGE_2025.md':'HCGE_2025','code-afep-medef-references.md':'CODE','index_ESMA_ECEP_2025.md':'ESMA_UP','index_AMF_2021.md':'AMF_2021_UP','index_AMF_2025.md':'AMF_2025_UP','index_Senat_Rietmann_2025.md':'SENAT','recurrences_nominatives.md':'GLOBAL','index_HCGE_GUIDE_APPLICATION_2024.md':'GUIDE24','index_Guide_HCGE_2025.md':'GUIDE25','index_AMF_DOC_2021_02.md':'DOC2102',
'index_AMF_DURABILITE_2024.md':'DURABILITE_2024','index_AMF_DOC_2025_08.md':'DOC2508','index_AMF_CSRD_WAY_FORWARD_2025.md':'CSRD','index_PARIS_EUROPLACE_DIALOGUE_2024.md':'EUROPLACE'}
def norm(s,strip_digits=False):
    s=s.replace('\u2019',"'").replace('\r',' ').replace('\xad','').replace('\u0002','')
    s=re.sub(r'[«»"“”\u00a0]',' ',s).lower()
    s=s.replace('œ','oe').replace('æ','ae')
    s=re.sub(r'[^a-z0-9àâäéèêëîïôöùûüçœæ]','',s)
    return re.sub(r'\d+','',s) if strip_digits else s

ELIDE=re.compile(r'\[\s*(?:…|\.\.\.)\s*\]|\(\s*(?:…|\.\.\.)\s*\)|\[[^\]]{1,60}\]')
def _segments(q):
    return [s for s in (norm(x) for x in ELIDE.split(q)) if len(s)>=20]
def _segs_in(text,segs):
    pos=0
    for s in segs:
        i=text.find(s,pos)
        if i<0: return False
        pos=i+len(s)
    return True
def cherche_segments(q,d):
    segs=_segments(q)
    if not ELIDE.search(q) or not segs: return None
    segd=[re.sub(r'\\d+','',s) for s in segs]
    _prep(d); ordre=sorted(pages[d])
    for p in ordre:
        if _segs_in(NC[d][p],segs): return p
    for i,p in enumerate(ordre[:-1]):
        if _segs_in(NC[d][p]+NC[d][ordre[i+1]],segs): return p
    for p in ordre:
        if _segs_in(ND[d][p],segd): return p
    for i,p in enumerate(ordre[:-1]):
        if _segs_in(ND[d][p]+ND[d][ordre[i+1]],segd): return p
    return None

def _pagine_hcge2023():
    """Génère CORPUS/HCGE_2023/N.txt depuis le blob si absent. Les numéros de page
    imprimés figurent en lignes isolées dans le flux (séquence 10..124, saut 27->30
    = intercalaire 2e partie sans numéro). Le bloc liminaire (pages 1-9) -> 9.txt."""
    d=os.path.join(CORPUS,'HCGE_2023')
    if os.path.isdir(d) and glob.glob(d+'/*.txt'): return
    os.makedirs(d,exist_ok=True)
    try: b=open('/mnt/project/15661-hcge-2024-rapport-hcge-2023-fr-0212.pdf',encoding='utf-8',errors='ignore').read()
    except FileNotFoundError: return
    L=b.replace('\r\n','\n').replace('\r','\n').split('\n')
    cand=[(i,int(l.strip())) for i,l in enumerate(L) if re.fullmatch(r'\s*\d{1,3}\s*',l) and 3<=int(l.strip())<=124]
    mk=[]; att=None
    for i,n in cand:
        if att is None:
            if n==10: mk=[(i,n)]; att=11
            continue
        if n==att or (att<n<=att+3): mk.append((i,n)); att=n+1
    for k,(i,n) in enumerate(mk):
        fin=mk[k+1][0] if k+1<len(mk) else len(L)
        open(f'{d}/{n}.txt','w').write('\n'.join(L[i+1:fin]))
    open(f'{d}/9.txt','w').write('\n'.join(L[:mk[0][0]]))
_pagine_hcge2023()

pages={}
for d in set(MAP.values()):
    if d=='HCGE_2023_BLOB': continue
    pdir=os.path.join(CORPUS,d); pages[d]={}
    for t in glob.glob(pdir+'/*.txt'):
        try: n=int(os.path.basename(t)[:-4])
        except: continue
        pages[d][n]=open(t,encoding='utf-8',errors='ignore').read()
try: blob=open('/mnt/project/15661-hcge-2024-rapport-hcge-2023-fr-0212.pdf',encoding='utf-8',errors='ignore').read()
except FileNotFoundError: blob=''
def pages_rev(ctx,maxp=None):
    """v2.2 : collecte TOUTES les pages annoncées de la fenêtre (annonces composites),
    plafonnées au nombre de pages du document (écarte les paginations de références
    doctrinales type « Bull. Joly, p. 633 »)."""
    out=set()
    for m in re.finditer(r'p?p\.?\s*(\d+(?:\s*[-–—à]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–—à]\s*\d+)?)*)',ctx):
        for seg in m.group(1).split(','):
            seg=seg.strip()
            mm=re.match(r'(\d+)(?:\s*[-–—à]\s*(\d+))?$',seg)
            if not mm: continue
            a=int(mm.group(1)); b=int(mm.group(2)) if mm.group(2) else a
            out|=set(range(min(a,b),max(a,b)+1)) if b>=a and b-a<6 else {a}
    if maxp: out={p for p in out if 1<=p<=maxp}
    return out
def present_a(nq,nqd,q,d,c):
    """v2.2 : la citation est-elle présente à la page c (±1, paire), tous modes ?"""
    _prep(d); ordre=sorted(pages[d])
    for p in (c,):
        if p in NC[d] and (nq in NC[d][p] or (nqd and nqd in ND[d][p])): return True
        if p in NC[d]:
            i=ordre.index(p)
            if i+1<len(ordre):
                q2=ordre[i+1]
                # v2.4 : la paire p/p+1 n'est admise que si la citation CHEVAUCHE la coupure,
                # pas si elle tient entière sur p+1 (audit du 8 sept. 2026 : S32, S43, S51).
                seule_sur_suivante = nq in NC[d][q2] or (nqd and nqd in ND[d][q2])
                if not seule_sur_suivante and (nq in NC[d][p]+NC[d][q2] or (nqd and nqd in ND[d][p]+ND[d][q2])): return True
    S=_segments(q)
    if ELIDE.search(q) and S:
        for p in (c,):
            if p in NC[d] and _segs_in(NC[d][p],S): return True
    return False
NC={}; ND={}
def _prep(d):
    if d in NC: return
    P=pages[d]; o=sorted(P)
    NC[d]={p:norm(P[p]) for p in o}; ND[d]={p:norm(P[p],True) for p in o}
def pages_ou(nq,nqd,d):
    """v2.4 : toutes les pages où la citation figure entière (exact ou sans chiffres)."""
    _prep(d); return sorted(p for p in pages[d] if nq in NC[d][p] or (nqd and nqd in ND[d][p]))
PAGE_FIX=[]; PLAGE_FIX=[]
def cherche(nq,nqd,d):
    _prep(d); P=pages[d]; ordre=sorted(P)
    for p in ordre:
        if nq in NC[d][p]: return (p,'exact')
    for i,p in enumerate(ordre[:-1]):
        if nq in NC[d][p]+NC[d][ordre[i+1]]: return (p,'apagepaire')
    for p in ordre:
        if nqd and nqd in ND[d][p]: return (p,'sansdigits')
    for i,p in enumerate(ordre[:-1]):
        if nqd and nqd in ND[d][p]+ND[d][ordre[i+1]]: return (p,'apagepaire')
    return None
def cherche_global(nq,nqd):
    for d in pages:
        r=cherche(nq,nqd,d)
        if r: return (d,)+r
    return None
OFFSETS={}; DELTAS={}
def _run():
    global TOT,rows
    TOT=dict(cit=0,conf=0,page=0,intr=0,nv=0,plage=0); rows=[]; PAGE_FIX.clear(); PLAGE_FIX.clear()

    for f in sorted(glob.glob(BUILD+'/index_*.md'))+[BUILD+'/code-afep-medef-references.md',BUILD+'/recurrences_nominatives.md']:
        b=os.path.basename(f); txt=open(f,encoding='utf-8').read(); d=MAP.get(b)
        s=dict(cit=0,conf=0,page=0,intr=0,nv=0,plage=0); anom=[]
        for m in re.finditer(r'«\s*(.+?)\s*»',txt,re.S):
            q=m.group(1); nq=norm(q)
            if len(nq)<30: continue
            s['cit']+=1; nqd=norm(q,True)
            maxp=max(pages[d]) if d and d in pages and pages[d] else None
            # v2.4 : page annoncée = celle de l'ENTRÉE (ligne courante), d'abord avant la citation,
            # sinon après sur la même ligne, sinon la puce parente. Plus de fenêtre de 260 caractères
            # qui absorbait les pages des entrées voisines (audit du 8 sept. 2026 : S32, S43, S51).
            ls=txt.rfind('\n',0,m.start())+1; le=txt.find('\n',m.end()); le=le if le>=0 else len(txt)
            # v2.5 : une annotation « (p. N) » placée juste après la citation prime sur la page de l'entrée
            apres=re.match(r'\*?\s*\(p\.\s*(\d+)\)',txt[m.end():m.end()+16])
            prev=({int(apres.group(1))} if apres else set()) or pages_rev(txt[ls:m.start()],maxp) or pages_rev(txt[m.end():le],maxp)
            if not prev:
                # puce parente : remonter aux lignes précédentes moins indentées
                ind=len(txt[ls:m.start()])-len(txt[ls:m.start()].lstrip(' '))
                k=ls
                while k>0 and not prev:
                    k2=txt.rfind('\n',0,k-1)+1; line=txt[k2:k-1]
                    if line.strip() and (len(line)-len(line.lstrip(' ')))<ind and line.lstrip().startswith(('-','#','|','*')):
                        prev=pages_rev(line,maxp); break
                    if line.startswith('#'): break
                    k=k2
                    if k==0: break
            if False and b=='index_HCGE_2023.md':
                sb=_segments(q)
                if nq in norm(blob) or (nqd and nqd in norm(blob,True)) or (ELIDE.search(q) and sb and _segs_in(norm(blob),sb)): s['conf']+=1
                else: s['intr']+=1; anom.append(('NON RETROUVÉE',q[:100],''))
                continue
            if d=='GLOBAL':
                g=cherche_global(nq,nqd)
                if g: s['conf']+=1
                else: s['intr']+=1; anom.append(('INTROUVABLE (tous docs)',q[:100],''))
                continue
            # source absente OU répertoire de corpus vide -> NON VÉRIFIABLE, jamais INTROUVABLE :
            # un PDF manquant n'est pas un défaut d'index (cf. GUIDE24, 257 citations, 27 août 2026).
            if not d or d not in pages or not pages[d]: s['nv']+=1; continue
            r=cherche(nq,nqd,d)
            if r is None:
                ps=cherche_segments(q,d)
                if ps is not None:
                    off=OFFSETS.get(d,0)
                    if prev and not any(ps==c+off or ps==c for c in prev) \
                       and not any(present_a(nq,nqd,q,d,c+off) or present_a(nq,nqd,q,d,c) for c in prev):
                        s['page']+=1; anom.append(('PAGE (segments)',q[:80],f'rev. {sorted(prev)} → p. {ps}'))
                        PAGE_FIX.append((f,m.start(),sorted(prev),[ps-off],ps-off))
                    else: s['conf']+=1
                    if len(prev)>1:
                        seules=[c for c in prev if (c+off) in NC[d] and (nq in NC[d][c+off] or (nqd and nqd in ND[d][c+off]))]
                        if seules:
                            s['plage']=s.get('plage',0)+1
                            anom.append(('PLAGE',q[:80],f'plage annoncée {sorted(prev)} ; citation entière p. {seules}'))
                            if len(seules)==1: PLAGE_FIX.append((f,m.end(),seules[0]))
                    continue
                s['intr']+=1; anom.append(('NON RETROUVÉE',q[:100],f'pages rev. {sorted(prev)}'))
            else:
                p,mode=r
                off=OFFSETS.get(d,0)
                if prev and not any(p==c+off or p==c or (mode=='apagepaire' and (p+1==c or p+1==c+off)) for c in prev) \
                   and not any(present_a(nq,nqd,q,d,c+off) or present_a(nq,nqd,q,d,c) for c in prev):
                    s['page']+=1; anom.append(('PAGE',q[:80],f'rev. {sorted(prev)} → p. {p} (présente p. {pages_ou(nq,nqd,d)})'))
                    PAGE_FIX.append((f,m.start(),sorted(prev),[x-off for x in pages_ou(nq,nqd,d)],p-off))
                    if prev: DELTAS.setdefault(d,{}); dd=p-min(prev); DELTAS[d][dd]=DELTAS[d].get(dd,0)+1
                else: s['conf']+=1
                if len(prev)>1:
                    seules=[c for c in prev if (c+off) in NC[d] and (nq in NC[d][c+off] or (nqd and nqd in ND[d][c+off]))]
                    if seules:
                        s['plage']=s.get('plage',0)+1
                        anom.append(('PLAGE',q[:80],f'plage annoncée {sorted(prev)} ; citation entière p. {seules}'))
                        if len(seules)==1: PLAGE_FIX.append((f,m.end(),seules[0]))
        for k in TOT: TOT[k]+=s[k]
        rows.append((b,s,anom))
_run()
# Passe 2 : applique les décalages modaux détectés (>=10 anomalies, mode >=60%)
for d,dd in DELTAS.items():
    tot=sum(dd.values()); mode,cnt=max(dd.items(),key=lambda x:x[1])
    if tot>=10 and cnt/tot>=0.6 and mode!=0: OFFSETS[d]=mode
if OFFSETS:
    print('Décalages détectés et appliqués:',OFFSETS); _run()
if '--annoter-plages' in sys.argv:
    import collections
    byf=collections.defaultdict(list)
    for f,pos,pg in PLAGE_FIX: byf[f].append((pos,pg))
    n=0
    for f,L in byf.items():
        t=open(f,encoding='utf-8').read()
        for pos,pg in sorted(L,reverse=True):
            suite=t[pos:pos+14]
            if re.match(r'\*?\s*\(p\.',suite): continue
            j=pos+1 if t[pos:pos+1]=='*' else pos
            t=t[:j]+f' (p. {pg})'+t[j:]; n+=1
        open(f,'w',encoding='utf-8').write(t)
    print(f'PLAGES ANNOTÉES : {n} citations dans {len(byf)} fichiers')
if '--corriger-pages' in sys.argv:
    import collections
    byf=collections.defaultdict(list)
    for f,pos,prev,trouve,p in PAGE_FIX: byf[f].append((pos,prev,trouve,p))
    n=0; skip=[]
    for f,L in byf.items():
        t=open(f,encoding='utf-8').read()
        for pos,prev,trouve,p in sorted(L,reverse=True):
            if len(trouve)!=1: skip.append((os.path.basename(f),t.count('\n',0,pos)+1,prev,trouve)); continue
            ls=t.rfind('\n',0,pos)+1; le=t.find('\n',pos); le=le if le>=0 else len(t)
            line=t[ls:le]; done=False
            for a in sorted(prev,key=lambda x:-abs(x-trouve[0])):
                # remplace le numéro annoncé le plus proche AVANT la citation, dans un motif de page
                for mm in reversed(list(re.finditer(r'(p?p\.\s*(?:\d+\s*[-–—à,]\s*)*)'+str(a)+r'(?!\d)',line[:pos-ls]))):
                    line=line[:mm.start()]+mm.group(1)+str(trouve[0])+line[mm.end():]; done=True; break
                if done: break
            if done: t=t[:ls]+line+t[le:]; n+=1
            else: skip.append((os.path.basename(f),t.count('\n',0,pos)+1,prev,trouve))
        open(f,'w',encoding='utf-8').write(t)
    print(f'PAGES CORRIGÉES : {n} ; non corrigées (à traiter à la main) : {skip}')
out=[f"# Contrôle raffiné — {TOT['cit']} citations : {TOT['conf']} conformes, {TOT['page']} pages erronées, {TOT['intr']} non retrouvées, {TOT['nv']} non vérifiables (PDF absent)\n"]
for b,s,anom in rows:
    if s['cit']==0: continue
    out.append(f"\n## {b} — {s['cit']} cit. : {s['conf']} conf / {s['page']} page / {s['intr']} intr / {s['nv']} nv")
    for typ,q,det in anom: out.append(f"- **{typ}** « {q}… » {det}")
os.makedirs(os_out,exist_ok=True) or open(os_out+'/rapport_raffine.md','w').write('\n'.join(out))
print(out[0])
for b,s,a in rows:
    if s['intr'] or s['page']: print(f"{b}: {s['intr']} intr, {s['page']} page (sur {s['cit']})")
