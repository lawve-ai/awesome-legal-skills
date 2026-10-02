#!/usr/bin/env python3
# generer_recurrences.py — Régénération de la fiche des récurrences nominatives (17 septembre 2026).
#
# POURQUOI. Les quatre contrôles du skill ne regardent que ce qui est entre guillemets. La fiche des
# récurrences était composée à 90 % de restitutions factuelles en style indirect, qui échappaient donc
# à tout contrôle. Trois erreurs y ont été trouvées à la main : VusionGroup (refus délibéré décrit comme
# une carence), OVH (millésime HCGE associé à un thème venant d'un autre rapport), CAPGEMINI (pratique
# attribuée à une société que l'AMF ne nomme pas). Plutôt que de chasser ces erreurs une à une, la fiche
# est scindée en deux :
#   1. ce qui ne se déduit pas du corpus — identités, renommages, structures de groupe — tenu à la main ;
#   2. ce qui s'en déduit — où chaque société est citée, dans quel rapport, à quelle page — GÉNÉRÉ ICI.
# Les qualifications thématiques ne sont conservées que si elles portent une page vérifiée ; les autres
# sont regroupées à part, marquées « non confrontées », et ne doivent pas être citées en l'état.
import re,sys,os,unicodedata
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'controle_bornes_v3.py'),encoding='utf-8').read()
exec(src[:src.find("rows=[]; stats={}")])
CORPUS=[('AMF 2020','AMF_2020'),('AMF 2021','AMF_2021_UP'),('AMF 2022','AMF_2022'),('AMF 2023','AMF_2023'),
 ('AMF 2024','AMF_2024'),('AMF 2025','AMF_2025_UP'),('HCGE 2020','HCGE_2020'),('HCGE 2021','HCGE_2021'),
 ('HCGE 2022','HCGE_2022'),('HCGE 2023','HCGE_2023'),('HCGE 2024','HCGE_2024'),('HCGE 2025','HCGE_2025'),
 ('Sénat 2025','SENAT'),('AMF durabilité 2024','DURABILITE_2024')]
OFF={'GUIDE24':3}
def pl(s):
    # U+0002 : césure de justification laissée par l'extraction (« UNIBAIL-RODAMCO␂WESTFIELD »,
    # « SES␂IMAGOTAG ») — elle coupe les noms composés et fausse la recherche (audit du 16 sept. 2026).
    s=s.replace('\x02','')
    s=unicodedata.normalize('NFD',s).encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]','',s)
# pages d'annexe : le nom y figure sans que le rapport dise rien de la société
def annexes(d):
    out=set()
    for p in pages[d]:
        t=pages[d][p]
        if re.search(r'Annexe|ANNEXE|composant l.échantillon|liste des \d+ sociétés|Sociétés exclues',t): out.add(p)
    return out
IDX={}
for lab,d in CORPUS:
    if d in pages: prep(d); IDX[lab]=(d,{p:pl(pages[d][p]) for p in pages[d]},annexes(d))

# GARDE-FOU : la source est la version manuelle d'origine, conservée à part. Régénérer à partir du
# fichier déjà généré viderait la section « à confronter » et perdrait les qualifications héritées.
SOURCE=os.path.join(BUILD,'recurrences_source_manuelle.md')
if not os.path.exists(SOURCE):
    sys.exit("recurrences_source_manuelle.md absent : régénération refusée.")
T=open(SOURCE,encoding='utf-8').read().split('\n')
fiches=[]; cur=None
for i,l in enumerate(T,1):
    m=re.match(r'^### (.+)$',l)
    if m:
        nom=m.group(1).strip()
        if nom.startswith(('Principes','Légende')): cur=None; continue
        cur={'nom':nom,'ligne':i,'themes':[],'alias':None}
        a=re.search(r'\(([^)]*(?:ex-|renommée|voir)[^)]*)\)',nom)
        if a: cur['alias']=a.group(1)
        fiches.append(cur); continue
    if cur and l.startswith('- Thème'): cur['themes'].append(l)

def presence(nom):
    base=re.sub(r'\s*\(.*$','',nom).strip()
    k=pl(base); court=pl(base.split()[0])
    ALIAS={'CLARIANE':'KORIAN','EMEIS':'ORPEA','VIRIDIEN':'CGG','VUSIONGROUP':'SESIMAGOTAG',
           'TOTALTOTALENERGIES':'TOTAL','TOTALENERGIES':'TOTAL'}
    alt=ALIAS.get(k)
    out=[]
    for lab,(d,tx,anx) in IDX.items():
        ps=[p for p in sorted(tx) if k in tx[p] or (len(court)>=5 and court in tx[p]) or (alt and alt in tx[p])]
        if not ps: continue
        off=OFF.get(d,0)
        marq=[f"{p-off}{'*' if p in anx else ''}" for p in ps]
        out.append(f"{lab} p. {', '.join(marq)}")
    return out

L=['# RÉCURRENCES NOMINATIVES CROSS-CORPUS',
   '',
   f"*Table de présence générée par `scripts/generer_recurrences.py` — régénérer après toute modification du corpus.*",
   '',
   "Pour chaque société : les rapports où son nom figure, et la page. Un astérisque signale une page d'annexe",
   "(liste d'échantillon) : le nom y figure sans que le rapport dise quoi que ce soit de la société.",
   "Les qualifications thématiques ne figurent ici que lorsqu'elles portent une page confrontée à la source ;",
   "les autres sont regroupées en fin de fiche, sous « affirmations non confrontées » — à ne pas citer en l'état.",
   '']
nonconf=[]
for f in fiches:
    L.append(f"### {f['nom']}")
    pr=presence(f['nom'])
    L.append('- **Présence** : '+(' | '.join(pr) if pr else '*aucune occurrence du nom dans le corpus*'))
    for th in f['themes']:
        if re.search(r'p\.\s*\d',th): L.append(th)
        else: nonconf.append((f['nom'],th))
    L.append('')
L.append('## Affirmations non confrontées — ne pas citer en l\'état')
L.append('')
L.append(f"{len(nonconf)} qualifications thématiques héritées de la version manuelle, sans page vérifiée.")
L.append('')
for nom,th in nonconf: L.append(f"- **{nom}** {th[2:]}")
open(os.path.join(BUILD,'recurrences_nominatives.md'),'w',encoding='utf-8').write('\n'.join(L)+'\n')
print(f"{len(fiches)} fiches régénérées ; {len(nonconf)} affirmations non confrontées isolées")
