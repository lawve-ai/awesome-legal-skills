#!/usr/bin/env python3
# controle_recurrences.py — Contrôle de la fiche des récurrences nominatives.
#
# La fiche ne contient plus que des éléments vérifiables : tables de présence générées depuis le corpus,
# identités et renommages tenus à la main, thèmes dont la page a été confrontée. Ce script vérifie que
# chaque page citée dans une ligne de thème porte bien le nom de la société.
import re,sys,os,unicodedata
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'controle_bornes_v3.py'),encoding='utf-8').read()
exec(src[:src.find("rows=[]; stats={}")])
CORPUS={'AMF 2020':'AMF_2020','AMF 2021':'AMF_2021_UP','AMF 2022':'AMF_2022','AMF 2023':'AMF_2023','AMF 2024':'AMF_2024',
 'AMF 2025':'AMF_2025_UP','HCGE 2020':'HCGE_2020','HCGE 2021':'HCGE_2021','HCGE 2022':'HCGE_2022','HCGE 2023':'HCGE_2023',
 'HCGE 2024':'HCGE_2024','HCGE 2025':'HCGE_2025','Sénat 2025':'SENAT'}
def pl(s):
    s=s.replace('\x02','')
    s=unicodedata.normalize('NFD',s).encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]','',s)
IDX={}
for lab,d in CORPUS.items():
    if d in pages: prep(d); IDX[lab]={p:pl(pages[d][p]) for p in pages[d]}
T=open(os.path.join(BUILD,'recurrences_nominatives.md'),encoding='utf-8').read().split('\n')
soc=None; bad=0; n=0
for i,l in enumerate(T,1):
    m=re.match(r'^### (.+)$',l)
    if m:
        nom=m.group(1).strip()
        soc=None if nom.startswith(('Principes','Légende','Trajectoires','Renommages')) else re.sub(r'\s*\(.*$','',nom).strip()
        continue
    if not soc or not l.startswith('- Thème'): continue
    for mm in re.finditer(r'\(([A-ZÉa-zé]+ 20\d\d)[^)]*?p\.\s*(\d+)',l):
        lab,p=mm.group(1),int(mm.group(2))
        if lab not in IDX: continue
        n+=1
        k=pl(soc); c=pl(soc.split()[0])
        if p not in IDX[lab] or not (k in IDX[lab][p] or (len(c)>=5 and c in IDX[lab][p])):
            print('  ÉCART',soc,'l.'+str(i),lab,'p.'+str(p),': nom absent de la page'); bad+=1
print(f'{n} pages de thèmes contrôlées ; {bad} écart(s)')
