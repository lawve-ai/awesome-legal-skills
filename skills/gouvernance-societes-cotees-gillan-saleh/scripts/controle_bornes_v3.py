#!/usr/bin/env python3
# controle_bornes_v3.py — Second étage du contrôle citationnel (v3.0, 4 septembre 2026).
#
# Le contrôle v2.3 (`controle_citations_v2.py`) teste la PRÉSENCE : la citation normalisée
# est-elle une sous-chaîne d'une page du corpus ? Il est aveugle, par construction, à la
# classe de défaut dominante relevée par les audits neutres d'août 2026 : les défauts de
# BORNAGE (troncature non signalée en tête ou en fin, ponctuation altérée, accent ajouté,
# appel de note absorbé ou mal attribué). Ce script prend chaque citation localisée par la
# méthode v2.3, retrouve la tranche EXACTE du texte source, et émet des SIGNAUX :
#
#   DEBUT   — la source ne commence pas une phrase là où la citation commence (caractère
#             précédent = lettre ou virgule) et la citation n'ouvre pas sur une élision.
#   FIN     — la source continue là où la citation s'arrête (caractère suivant = lettre,
#             virgule, puce…) et la citation ne ferme pas sur une élision.
#   PONCT   — la source porte une ponctuation terminale immédiatement après la tranche
#             (. ; : ! ?) que la citation ne reprend pas (information, non bloquant).
#   FIDELITE— écart caractère à caractère entre la tranche source et la citation, hors
#             espaces, sauts de ligne, guillemets et césures (accents, ponctuation interne,
#             casse, chiffres d'appel de note absorbés).
#   NOTE    — l'entrée annonce « note N » mais le chiffre d'appel qui suit la tranche
#             dans la source n'est pas N.
#
# Un signal n'est pas un verdict : il se confronte à la source. Les faux positifs
# documentés se consignent dans `liste_blanche_bornes.md` (fichier, ligne, type, motif).
#
# USAGE : après `extraire_corpus.py`, `python3 scripts/controle_bornes_v3.py`.
# Sortie : /home/claude/verif/rapport_bornes.md

import re, os, glob, sys, difflib, unicodedata
sys.path.insert(0, os.path.dirname(__file__))

BUILD='/home/claude/build/gouvernance-emetteurs-cotes'; CORPUS='/home/claude/tests'
OUT='/home/claude/verif'
MAP={'index_AMF_2020.md':'AMF_2020','index_AMF_2022.md':'AMF_2022','index_AMF_2023.md':'AMF_2023',
'index_AMF_2024.md':'AMF_2024','index_HCGE_2020.md':'HCGE_2020','index_HCGE_2021.md':'HCGE_2021',
'index_HCGE_2022.md':'HCGE_2022','index_HCGE_2023.md':'HCGE_2023','index_HCGE_2024.md':'HCGE_2024',
'index_HCGE_2025.md':'HCGE_2025','code-afep-medef-references.md':'CODE','index_ESMA_ECEP_2025.md':'ESMA_UP','index_AMF_2021.md':'AMF_2021_UP','index_AMF_2025.md':'AMF_2025_UP','index_Senat_Rietmann_2025.md':'SENAT','index_HCGE_GUIDE_APPLICATION_2024.md':'GUIDE24','index_Guide_HCGE_2025.md':'GUIDE25','index_AMF_DOC_2021_02.md':'DOC2102',
'index_AMF_DURABILITE_2024.md':'DURABILITE_2024','index_AMF_DOC_2025_08.md':'DOC2508','index_AMF_CSRD_WAY_FORWARD_2025.md':'CSRD','index_PARIS_EUROPLACE_DIALOGUE_2024.md':'EUROPLACE'}
KEEP=set('abcdefghijklmnopqrstuvwxyz0123456789àâäéèêëîïôöùûüç')

def norm_map(s, strip_digits=False):
    """Normalisation identique à v2.3, avec table de correspondance vers l'original."""
    out=[]; idx=[]
    for i,ch in enumerate(s):
        if ch in '\r\xad\x02': continue
        if ch=='\u2019': ch="'"
        ch=ch.lower()
        if ch=='œ': seq='oe'
        elif ch=='æ': seq='ae'
        else: seq=ch
        for c in seq:
            if c in KEEP and not (strip_digits and c.isdigit()):
                out.append(c); idx.append(i)
    return ''.join(out), idx

ELIDE=re.compile(r'\[\s*(?:…|\.\.\.)\s*\]|\(\s*(?:…|\.\.\.)\s*\)|\[[^\]]{1,60}\]')
LETTRE=re.compile(r'[^\W\d_]')
CONTINUE_CHARS=set(',─−–—•→▪◦-*')
TERMINAL=set('.;:!?')

pages={}
for d in set(MAP.values()):
    pdir=os.path.join(CORPUS,d); pages[d]={}
    for t in glob.glob(pdir+'/*.txt'):
        try: n=int(os.path.basename(t)[:-4])
        except: continue
        pages[d][n]=open(t,encoding='utf-8',errors='ignore').read()
NM={}
def prep(d):
    if d in NM: return
    P=pages[d]; o=sorted(P); NM[d]={}
    for i,p in enumerate(o):
        txt=P[p]; nxt=P[o[i+1]] if i+1<len(o) else ''
        NM[d][p]={'txt':txt+nxt,'n':norm_map(txt+nxt),'nd':norm_map(txt+nxt,True),'len1':len(txt)}

def pages_rev(ctx):
    out=set()
    for m in re.finditer(r'p?p\.?\s*(\d+(?:\s*[-–—à]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–—à]\s*\d+)?)*)',ctx):
        for seg in m.group(1).split(','):
            mm=re.match(r'(\d+)(?:\s*[-–—à]\s*(\d+))?$',seg.strip())
            if not mm: continue
            a=int(mm.group(1)); b=int(mm.group(2)) if mm.group(2) else a
            out|=set(range(min(a,b),max(a,b)+1)) if b>=a and b-a<6 else {a}
    return out
PREF=()
def localiser(q,d):
    """Retourne (page, span_original, texte_page_concat, strip) pour la première occurrence :
    d'abord sur les pages annoncées par l'entrée (PREF), puis dans l'ordre du document
    (v3.2, 8 sept. 2026 : audit S51 — même formule à deux pages, ponctuation différente)."""
    prep(d); nq,_=norm_map(q); nqd,_=norm_map(q,True)
    ordre=[p for p in sorted(PREF) if p in pages[d]]+[p for p in sorted(pages[d]) if p not in PREF]
    for strip in (False,True):
        key='nd' if strip else 'n'; needle=nqd if strip else nq
        if not needle: continue
        for p in ordre:
            e=NM[d][p]; ns,idx=e[key]
            i=ns.find(needle)
            if i>=0:
                a=idx[i]; b=idx[i+len(needle)-1]+1
                return p,(a,b),e['txt'],strip
    return None

def soft(s):
    """Nettoyage léger pour la comparaison de fidélité : espaces, sauts, guillemets, césures."""
    s=s.replace('\u2019',"'").replace('\xad','').replace('\x02','').replace('\u00a0',' ')
    s=re.sub(r'[«»"“”]','',s)
    s=re.sub(r'-\s*\n\s*','',s)           # césure de fin de ligne
    s=re.sub(r'\s+',' ',s).strip()
    s=s.replace('’',"'")   # v3.3 : '…' et '...' restent distincts (audit du 9 sept. 2026, S48)
    return s

def GLYPH(x):
    return x.replace('\u2011','-').replace('\u2010','-').replace('\u2018',"'").replace('\u201a',"'").replace('\u2019',"'").replace('\u02bc',"'")
def diffs(src,cit):
    """Écarts caractère à caractère hors casse ; renvoie une liste de (type, src_frag, cit_frag)."""
    out=[]
    sm=difflib.SequenceMatcher(None,src,cit,autojunk=False)
    ops=[o for o in sm.get_opcodes() if o[0]!='equal']
    for tag,i1,i2,j1,j2 in ops:
        # v3.3 : un écart touchant une extrémité de la citation relève des contrôles de bornes
        # (DEBUT / FIN / PONCT / PONCT_QUEUE), pas de la fidélité interne.
        if (j1==0 and i1==0) or (j2==len(cit) and i2==len(src)):
            out.append(('BORNE','','','','')); continue
        a=src[i1:i2]; b=cit[j1:j2]
        strip=lambda x: re.sub(r'[\s*\-•─−–—\uf0d8\uf0fc\u2022▪◦]','',x)
        if a.lower()==b.lower(): typ='CASSE_INIT' if (i1==0 and j1==0 and len(a)==1) else 'CASSE'
        elif strip(a)==strip(b): typ='PUCE'
        elif GLYPH(a)==GLYPH(b): typ='GLYPHE'
        elif a and b and unicodedata.normalize('NFD',a).encode('ascii','ignore')==unicodedata.normalize('NFD',b).encode('ascii','ignore'): typ='ACCENT'
        elif re.fullmatch(r'\s*\d{1,3}\s*',a or 'x') and not b: typ='APPEL_NOTE_RETIRE'
        elif re.fullmatch(r'\d+',b or 'x') and not a: typ='CHIFFRE_CIT'
        elif not a.strip() and not b.strip(): typ='ESPACE'
        elif (not a.strip() and b.strip() in '.,;:!?…') or (not b.strip() and a.strip() in '.,;:!?…'):
            typ='PONCT_INT'
        elif not a.strip() or not b.strip(): typ='TEXTE'
        elif a.strip() in '.,;:!?' and b.strip() in '.,;:!?': typ='PONCT_INT'
        else: typ='TEXTE'
        out.append((typ,src[max(0,i1-15):i2+15],cit[max(0,j1-15):j2+15],a,b))
    return out


# Entrées dont la frontière a été établie au RENDU DE PAGE (audit du 16 septembre 2026) : le script lit la
# couche texte et les signale à tort. Le rendu fait foi ; --corriger --elider ne doit pas y toucher.
BLANCHE={('index_AMF_2020.md',223),('index_AMF_2021.md',240),('index_AMF_2021.md',242),('index_AMF_2021.md',765),
 ('index_AMF_2023.md',318),('index_AMF_2023.md',397),('index_AMF_2025.md',398),('index_AMF_2025.md',399),
 ('index_AMF_CSRD_WAY_FORWARD_2025.md',19),('index_AMF_CSRD_WAY_FORWARD_2025.md',112),
 ('index_AMF_CSRD_WAY_FORWARD_2025.md',322),('index_AMF_CSRD_WAY_FORWARD_2025.md',379),
 ('index_AMF_DURABILITE_2024.md',144),('index_ESMA_ECEP_2025.md',76),('index_HCGE_2021.md',182)}
rows=[]; stats={}; WL={}; EDITS={}  # fichier -> {(start,end): nouvelle_citation}
CORRIGER='--corriger' in sys.argv; ELIDER='--elider' in sys.argv
files=sorted(glob.glob(BUILD+'/index_*.md'))+[BUILD+'/code-afep-medef-references.md']
for f in files:
    b=os.path.basename(f); d=MAP.get(b)
    if not d or not pages.get(d): continue
    txt=open(f,encoding='utf-8').read()
    st=stats[b]={'cit':0,'loc':0,'DEBUT':0,'FIN':0,'PONCT':0,'PONCT_AJOUT':0,'PONCT_QUEUE':0,'FIDELITE':0,'NOTE':0,'APPEL_CONSERVE':0,'ESPACE_SENSIBLE':0,'NONLOC':0}
    for m in re.finditer(r'«\s*(.+?)\s*»',txt,re.S):
        q=m.group(1); nq,_=norm_map(q)
        if len(nq)<30: continue
        st['cit']+=1
        ligne=txt.count('\n',0,m.start())+1
        elided=bool(ELIDE.search(q))
        # segments pour les citations élidées : on contrôle la borne de début du 1er segment
        # et la borne de fin du dernier ; la fidélité segment par segment.
        segs=[s for s in ELIDE.split(q) if len(norm_map(s)[0])>=12] if elided else [q]
        if not segs: continue
        first=segs[0]; last=segs[-1]
        ls=txt.rfind('\n',0,m.start())+1; le=txt.find('\n',m.end()); le=le if le>=0 else len(txt)
        PREF=pages_rev(txt[ls:m.start()]) or pages_rev(txt[m.end():le])
        if not PREF:   # puce parente moins indentée
            ind=len(txt[ls:m.start()])-len(txt[ls:m.start()].lstrip(' ')); k=ls
            while k>0:
                k2=txt.rfind('\n',0,k-1)+1; line=txt[k2:k-1]
                if line.strip() and (len(line)-len(line.lstrip(' ')))<ind and line.lstrip().startswith(('-','#','|','*')):
                    PREF=pages_rev(line); break
                if line.startswith('#'): break
                k=k2
        # v3.3 : si la citation ouvre sur un court fragment suivi d'un crochet éditorial ([aient], [sic]),
        # le segment de tête est reconstitué crochets ôtés pour ne pas poser d'élision sur une vraie frontière.
        # v3.4 : le segment de tête est reconstitué crochets ôtés — l'élision initiale est retirée d'abord,
        # et l'on essaie les deux lectures du crochet (mot substitué conservé, puis supprimé), pour ne pas
        # manquer une élision posée sur une vraie frontière (audit du 10 sept. 2026 : S16, S26).
        corps=re.sub(r'^\s*(\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.)\s*','',q)
        m0=ELIDE.search(corps)
        if m0 and len(norm_map(corps[:m0.start()])[0])<25:
            base=re.sub(r'\[\s*(?:…|\.\.\.)\s*\]','',corps)
            base=re.sub(r'\[\s*sic\s*\]','',base)            # mention éditoriale : absente de la source
            for var in (re.sub(r'\[([^\]]{1,60})\]',r'\1',base),   # substitution : mot présent dans la source
                        re.sub(r'\[[^\]]{1,60}\]','',base)):        # insertion : mot absent de la source
                head=' '.join(var.split()[:12])
                if len(norm_map(head)[0])>=20 and localiser(head,d): first=head; break
        loc_first=localiser(first,d)
        if not loc_first:
            st['NONLOC']+=1; rows.append((b,ligne,'NON_LOCALISE',q[:90].replace('\n',' '),'premier segment introuvable par sous-chaîne : confrontation manuelle','?')); continue
        st['loc']+=1
        p,(a,b0),page_txt,strip=loc_first
        sig=[]; newq=q
        # ---- borne de début
        opens_elided=bool(re.match(r'\s*(\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.)',q))
        pre=page_txt[max(0,a-80):a]; pre_s=pre.rstrip()
        prev_ch=pre_s[-1] if pre_s else ''
        BOUND=set('.!?«"“‘•─−–—▪□→\uf0d8\uf0fc\u2022')
        pre_raw=pre.rstrip(' \t')
        notes_p=set(re.findall(r'(?m)^\s*(\d{1,3})\s+\S',page_txt))
        mnum=re.search(r'(\d{1,3})\s*$',pre_raw)
        note_start = bool(mnum) and mnum.group(1) in notes_p and first.lstrip()[:1].isupper()
        # glyphes de puce des extractions (Wingdings) ; « ─ GOV 1 : » = étiquette d'item suivie de deux-points
        GLYPH_PUCE=r'-–—•▪□➲→\uf0d8\uf0fc\uf0a8\uf06c\uf02d\uf0b7\u2022'
        puce = bool(re.search(r'(?:^|\n)\s*(?:['+GLYPH_PUCE+r']|y|\(?[ivx]+\)|[a-z]\)|\d{1,2}[.)])\s*$',pre_raw)) \
            or bool(re.search(r'(?:^|\n)\s*['+GLYPH_PUCE+r'][^\n]{0,40}:\s*$',pre_raw))
        paragraphe = pre_raw.endswith('\n\n') or pre_raw.endswith('\n \n')
        # ligne précédente = titre de section (numérotation ou libellé court sans ponctuation finale)
        derl=[x for x in pre_raw.split('\n') if x.strip()]
        derl=derl[-1].strip() if derl else ''
        # ligne précédente = titre de section : numérotation, ou libellé court sans ponctuation finale
        # ne se terminant pas par un mot de liaison (sinon c'est une ligne de corps repliée).
        LIAISON=('et','ou','de','du','des','la','le','les','à','en','un','une','par','pour','dans','que','qui','sur','au','aux','ne','se','est','sont')
        dernier_mot=re.findall(r"[\w’']+",derl)[-1].lower() if re.findall(r"[\w’']+",derl) else ''
        titre = bool(pre_raw.endswith('\n')) and bool(
            re.match(r'^(\d+(\.\d+)*\.?|[IVX]+\.|[A-Z]\.)\s+\S',derl)
            or (len(derl)<60 and derl and derl[-1] not in '.!?,;:' and dernier_mot not in LIAISON
                and first.lstrip()[:1].isupper()))
        non_frontiere = prev_ch in ",;:'\u2019" or (LETTRE.match(prev_ch) and prev_ch.islower()) if prev_ch else False
        frontiere = (not prev_ch) or prev_ch in BOUND or puce or note_start or titre or (pre_raw.endswith('\n') and not non_frontiere)
        if opens_elided and frontiere:
            # « fort » = frontière certaine (ponctuation forte, guillemet ouvrant, puce, note, titre numéroté,
            # ligne blanche) ; sinon le cas est signalé pour confrontation, sans correction mécanique.
            titre_num = bool(re.match(r'^(\d+(\.\d+)*\.?|[IVX]+\.|[A-Z]\.)\s+\S',derl))
            fort = (not prev_ch) or prev_ch in BOUND or puce or note_start or titre_num or paragraphe or titre
            sig.append((('ELISION_SUPERFLUE/DEBUT' if fort else 'ELISION_SUPERFLUE/TITRE'),f"« […] » en tête alors que la source ouvre ici : …{soft(pre)[-60:]} ▌{soft(first)[:40]}"))
            if ELIDER and fort: newq=re.sub(r'^\s*(\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.)\s*','',newq)
        if not opens_elided and not frontiere:
            fc=first.lstrip()[:1]
            # intertitre : la source va à la ligne juste avant la tranche et la citation ouvre sur une majuscule
            intertitre = (fc.isupper() or fc.isdigit()) and pre.rstrip(' \t').endswith('\n') and not non_frontiere
            if fc=='[': intertitre=True   # ouverture déjà signalée par crochet éditorial ([P]ermettre)
            sig.append(('DEBUT' if not intertitre else 'DEBUT/INTERTITRE',f"source avant : …{soft(pre)[-70:]} ▌{soft(first)[:40]}"))
            if ELIDER and not intertitre: newq='[…] '+newq.lstrip()
        # ---- borne de fin (sur le dernier segment)
        loc_last=loc_first if last is first else localiser(last,d)
        if loc_last:
            p2,(a2,b2),page_txt2,_=loc_last
            closes_elided=bool(re.search(r'(\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.)\s*$',q))
            post=page_txt2[b2:b2+80]; post_s=post.lstrip()
            next_ch=post_s[0] if post_s else ''
            cit_end=q.rstrip()[-1] if q.strip() else ''
            # appel de note (1-3 chiffres collés) sauté avant lecture de la ponctuation source
            post_n=re.sub(r'^[ \t]*\d{1,3}(?=[ \t]*(?:[^\d\n.]|\.(?!\d))|[ \t]*$)','',post,count=1).lstrip() if not post.lstrip(' \t').startswith('\n') else post.lstrip()
            # queue de citation hors segments (ex. crochet éditorial « [du dirigeant] ») présente dans la source : on la saute
            # appariement sans chiffres (appels de note dans la tranche) : la borne de fin n'est fiable qu'après la plage numérique
            if loc_last[3]: post_n=re.sub(r'^[\s\d%]*','',post_n)   # v3.2 : ne saute que la plage numérique, jamais la ponctuation
            tail=q[q.rfind(last)+len(last):].strip().rstrip('»* ')
            if tail and not tail.startswith('[…') and not tail.startswith('[...') and post_n.startswith(tail): post_n=post_n[len(tail):].lstrip()
            eff_ch=post_n[0] if post_n else ''
            # v3.2 : queue complète de la citation (« .) », « ". ») identique au début de la source après la tranche → rien à signaler
            QN=lambda x: re.sub(r'[»”"“«″]','"',re.sub(r'\s','',x))
            tail_full=QN(re.search(r'[^\w\]]*$',q.rstrip().rstrip('»* ')).group(0).replace('[…]','').replace('[...]',''))
            if tail_full and QN(post).startswith(tail_full):
                if not re.match(r'[.!?;:]',QN(post)[len(tail_full):len(tail_full)+1] or ''):
                    next_ch=''   # queue identique, rien après : neutralise les contrôles de fin
                else:
                    # v3.3 : queue identique suivie d'une ponctuation terminale dans la source (« 2020). ») → on lit cette ponctuation (audit 2, S44)
                    k=0; j=0; pn=post_n
                    while k<len(tail_full) and j<len(pn):
                        if pn[j].isspace(): j+=1; continue
                        j+=1; k+=1
                    post_n=pn[j:].lstrip(); eff_ch=post_n[0] if post_n else ''
            # v3.4 : « […] » en queue posé sur une frontière réelle de la source (audit du 10 sept. 2026, S53) :
            # fin de phrase, guillemet fermant, ou fin du dernier item d'une énumération suivie d'un titre.
                            # l'énumération se poursuit-elle ? on regarde les trois lignes non vides suivantes
            lignes=[x.strip() for x in post.split('\n')[1:] if x.strip()][:3]
            bloc_suivant=any(re.match(r'[-–—─•▪□➲→\uf0d8\uf0fc\u2022]|y\s|\(?[ivx]+\)\s|[a-z]\)\s|\d{1,2}[.)]\s',x) for x in lignes)
            # rupture = la source s'arrête ici et le bloc suivant est un TITRE de section : rien n'est omis.
            # Un « : » ou un « ; » qui suit annonce au contraire une suite : la marque d'omission reste licite.
            reste_ligne=post.split('\n')[0].strip(' \t»”"*.0123456789')
            apres=[x.strip() for x in post.split('\n')[1:] if x.strip() and not x.strip().isdigit()][:1]
            titre_suivant=bool(apres) and len(apres[0])<70 and apres[0][-1] not in '.!?,;:' and not apres[0][0].isdigit()
            # exigence d'un vrai blanc de paragraphe : un simple retour à la ligne est un repli de mise en page
            rupture=(not reste_ligne) and bool(re.match(r'[^\n]*\n\s*\n',post)) and titre_suivant and not bloc_suivant
            if closes_elided:
                # garde-fou : si la source enchaîne immédiatement (lettre, virgule, point-virgule, tiret d'item),
                # la marque d'omission est licite quelle que soit la ponctuation lue plus loin.
                brut=post.lstrip()[:1]
                enchaine = bool(brut) and (LETTRE.match(brut) or brut in ',;:-–—')
                if not enchaine and ((not eff_ch) or eff_ch in '.!?»”' or rupture or puce_apres):
                    fort_fin=(not eff_ch) or eff_ch in '.!?»”'
                    sig.append((('ELISION_SUPERFLUE/FIN' if fort_fin else 'ELISION_SUPERFLUE/FIN_BLOC'),
                                f"« […] » en queue alors que la source s'arrête ici : {soft(last)[-40:]}▐ {soft(post)[:60]}"))
                    if ELIDER: newq=re.sub(r'\s*(\[\s*(?:…|\.\.\.)\s*\]|…|\.\.\.)\s*$','',newq)
            if not closes_elided and next_ch and not rupture:
                # fin d'item d'énumération = frontière (règle du 10 sept. 2026) : pas de marque d'omission attendue
                # intitulé de section cité entier : ligne courte sans ponctuation, la source passe à la ligne
                intitule = (len(soft(q))<100 and not soft(q).rstrip()[-1:] in '.;:,!?' and post.startswith('\n'))
                # glyphe de puce immédiatement après la tranche : l'item cité est complet (règle du 10 sept. 2026)
                puce_apres = bool(re.match(r'[-–—─•▪□➲→\uf0d8\uf0fc\uf0a8\uf06c\uf02d\uf0b7\u2022]',(post_n or '').lstrip()))
                fin_item = intitule or puce_apres or eff_ch in ';:' and any(re.match(r'[-–—─•▪□➲→\uf0d8\uf0fc\u2022]|y\s',x.strip()) for x in post.split('\n')[:3] if x.strip())
                if not fin_item and (LETTRE.match(eff_ch) or eff_ch in CONTINUE_CHARS or eff_ch in '([' or (eff_ch in ':;' and cit_end not in TERMINAL)):
                    sig.append(('FIN',f"{soft(last)[-40:]}▐ source après : {soft(post)[:70]}…"))
                    if ELIDER: newq=newq.rstrip()+' […]'
                elif eff_ch in TERMINAL and cit_end not in TERMINAL and (cit_end.isalnum() or cit_end in ')%'):
                    sig.append(('PONCT',f"source porte « {eff_ch} » après la tranche ; la citation finit sur « {cit_end} »"))
                tr_cit=re.sub(r'\s','',re.search(r'[^\w\]]*$',q.rstrip().rstrip('»* ')).group(0)).replace('…','').replace('[','').replace(']','')
                # appel de note collé après la tranche : sauté avant lecture de la traîne
                tr_src=re.sub(r'\s','',re.match(r'[^\w«]*',re.sub(r'^\d{1,3}(?!\d)','',post.lstrip())).group(0))
                Qn=lambda x: re.sub(r'\(\s*\.{3}\s*\)|\[\s*\.{3}\s*\]|\.{3}|…','',re.sub(r'[»”"“«″]','"',x))
                tr_cit,tr_src=Qn(tr_cit),Qn(tr_src)
                if tr_cit and not loc_last[3] and not tr_src.startswith(tr_cit) and not (tr_cit in TERMINAL and eff_ch and eff_ch!=tr_cit):
                    sig.append(('PONCT_QUEUE',f"traîne citation « {tr_cit} » ; source après la tranche : « {soft(post)[:40]} »"))
                if cit_end in TERMINAL and eff_ch and eff_ch!=cit_end:
                    sub=('SUBST' if eff_ch in TERMINAL else 'QUOTE' if eff_ch in '»"”' else 'PAREN' if eff_ch in ')]' else 'SUITE')
                    sig.append((f'PONCT_AJOUT/{sub}',f"la citation finit sur « {cit_end} » ; la source porte « {eff_ch} » : {soft(post)[:60]}"))
                    # correction mécanique : retirer la ponctuation ajoutée (en gardant une éventuelle étoile/italique hors guillemets)
                    newq=re.sub(r'[.;:!?]\s*$','',newq) if sub!='SUBST' else re.sub(r'[.;:!?](\s*)$',eff_ch+r'\1',newq)
                elif eff_ch in TERMINAL and cit_end not in TERMINAL and (cit_end.isalnum() or cit_end in ')%') and eff_ch in '.!?':
                    newq=newq.rstrip()+eff_ch
                elif next_ch.isdigit():
                    mnote=re.match(r'\s*(\d{1,3})',post)
                    n=mnote.group(1)
                    ctx=txt[m.end():m.end()+160].split('\n')[0]
                    ann=re.findall(r'\bnote\s+(\d{1,3})',ctx)
                    tranche=page_txt2[max(0,a2-5):b2+12]
                    if ann and n not in ann and not any(re.search(r'(?<!\d)'+x+r'(?!\d)',tranche) for x in ann):
                        sig.append(('NOTE',f"appel de note lu dans la source : {n} ; annoncé dans l'entrée : {', '.join(sorted(set(ann)))}"))
        # ---- appel de note conservé : nombre collé à un mot ou à un millésime, figurant comme note de la page
        notes=set(re.findall(r'(?m)^\s*(\d{1,3})\s+\S',page_txt))
        for mm in re.finditer(r'(?<=[A-Za-zéèêàç\)])(\d{1,3})(?=[\s,.;:]|$)|(?<=\b(?:19|20)\d\d)(\d{1,3})(?=[\s,.;:]|$)',q):
            n=mm.group(1) or mm.group(2)
            if n in notes: sig.append(('APPEL_CONSERVE',f"« …{q[max(0,mm.start()-25):mm.end()+5]} » — {n} est une note de la p. {p}"))
        # ---- espaces sensibles : espace devant % ou dans une référence d'article, différente entre index et texte extrait
        for s_ in segs:
            l=localiser(s_,d)
            if not l: continue
            _,(x,y),ptxt,_=l
            a_src=re.sub(r'[\u00a0\u202f]',' ',ptxt[x:y]); a_cit=re.sub(r'[\u00a0\u202f]',' ',s_)
            for pat in (r'\d ?%', r'[LR]\. ?\d[\d\- ]*\d'):
                ps=re.findall(pat,a_src); pc=re.findall(pat,a_cit)
                # v3.2 : HCGE 2024 et 2025 impriment une espace fine devant % (contrôle visuel du 8 sept. 2026 :
                # p. 15, 60, 64, 73, 79, 80, 90) que l'extraction supprime — l'index avec espace est conforme.
                if d in ('HCGE_2024','HCGE_2025') and pat==r'\d ?%' and all(' %' in x_ for x_ in pc): continue
                if ps!=pc and [x_.replace(' ','') for x_ in ps]==[x_.replace(' ','') for x_ in pc]:
                    sig.append(('ESPACE_SENSIBLE',f"source « {' ; '.join(ps)} » ¦ index « {' ; '.join(pc)} » — extraction non fiable sur les espaces fines : vérifier la page {p} visuellement"))
        # ---- fidélité, segment par segment
        for s in segs:
            l=localiser(s,d)
            if not l: continue
            _,(x,y),ptxt,_=l
            src=soft(ptxt[x:y]); cit=soft(s)
            for typ,sctx,cctx,fa,fb in diffs(src,cit):
                if typ in ('ESPACE','GLYPHE','APPEL_NOTE_RETIRE','PUCE','BORNE'): WL[typ]=WL.get(typ,0)+1; continue
                sig.append((f'FIDELITE/{typ}',f"source « {sctx} » | index « {cctx} »"))
                if typ=='CASSE_INIT' and s is segs[0]:
                    k=re.match(r'\s*',newq).end()
                    if newq[k].lower()==fa.lower(): newq=newq[:k]+fa+newq[k+1:]
        # v3.4 : ponctuation de fin des segments INTERNES (avant un « […] » médian) — audit du 10 sept. 2026, S25 :
        # un point-virgule ou un deux-points de la source rendu par un point n'était vu par aucun contrôle.
        for sg in segs[:-1]:
            l2=localiser(sg,d)
            if not l2: continue
            _,(x2,y2),t2,_=l2
            fin_cit=sg.rstrip()[-1:] 
            ap=re.sub(r'^[ \t]*\d{1,3}(?![\d.])','',t2[y2:y2+40]).lstrip()
            ap=ap[1:].lstrip() if ap[:1] in '»”"' and fin_cit not in '»”"' else ap
            if fin_cit in TERMINAL and ap[:1] and ap[0] in TERMINAL and ap[0]!=fin_cit:
                sig.append(('PONCT_SEGMENT',f"segment interne : la source porte « {ap[0]} », l'index « {fin_cit} » — …{soft(sg)[-40:]}"))
                if ELIDER: newq=newq.replace(sg,sg.rstrip()[:-1]+ap[0],1)
        # v3.5 : la source ouvre ou ferme des guillemets À L'INTÉRIEUR de la tranche citée, sans que l'index
        # les restitue : la citation fait passer pour cité un texte qui est de la plume du régulateur,
        # et inversement (audit du 10 sept. 2026 : S11, S21).
        for sg in segs:
            l3=localiser(sg,d)
            if not l3: continue
            _,(x3,y3),t3,_=l3
            gs=len(re.findall(r'[«»]',t3[x3:y3])); gi=len(re.findall(r'[«»"”“]',sg))
            if gs>gi:
                sig.append(('GUILLEMET_INTERNE',f"la source porte {gs} guillemet(s) dans la tranche, l'index {gi} : …{soft(t3[x3:y3])[:90]}…"))
        for typ,det in sig:
            if (b,ligne) in BLANCHE and typ.split('/')[0] in ('DEBUT','FIN'): continue
            k=typ.split('/')[0]; st[k]=st.get(k,0)+1
            rows.append((b,ligne,typ,q[:90].replace('\n',' '),det.replace('\n',' '),p))
        if newq!=q and (b,ligne) not in BLANCHE: EDITS.setdefault(f,{})[(m.start(1),m.end(1))]=newq

if CORRIGER:
    n=0
    for f,ed in EDITS.items():
        t=open(f,encoding='utf-8').read()
        for (a,b2),nq in sorted(ed.items(),reverse=True):
            t=t[:a]+nq+t[b2:]; n+=1
        open(f,'w',encoding='utf-8').write(t)
    print(f'CORRECTIONS APPLIQUÉES : {n} citations dans {len(EDITS)} fichiers')
os.makedirs(OUT,exist_ok=True)
out=['# Contrôle de bornes v3 — signaux à confronter\n',
     f"Fichiers : {len(stats)} ; citations : {sum(s['cit'] for s in stats.values())} ; localisées : {sum(s['loc'] for s in stats.values())}\n"]
tot={k:sum(s.get(k,0) for s in stats.values()) for k in ('DEBUT','FIN','PONCT','PONCT_AJOUT','PONCT_QUEUE','FIDELITE','NOTE','APPEL_CONSERVE','ESPACE_SENSIBLE','NONLOC','ELISION_SUPERFLUE')}
out.append('Signaux : '+', '.join(f"{k} {v}" for k,v in tot.items())+' — classes en liste blanche (non listées) : '+', '.join(f"{k} {v}" for k,v in WL.items())+'\n')
out.append('\n| fichier | ligne | type | citation | détail | p. source |\n|---|---|---|---|---|---|')
for b,l,typ,q,det,p in rows:
    out.append(f"| {b} | {l} | {typ} | {q.replace('|','¦')}… | {det.replace('|','¦')} | {p} |")
open(OUT+'/rapport_bornes.md','w',encoding='utf-8').write('\n'.join(out))
print(out[1]); print(out[2])
for b,s in stats.items():
    print(f"{b:40s} cit {s['cit']:4d} loc {s['loc']:4d}  "+' '.join(f"{k} {v}" for k,v in s.items() if k not in ('cit','loc') and v))
