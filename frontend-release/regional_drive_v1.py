"""Editorial pilot: eight regional drive-to-store campaigns with cited source URLs.
Data-only scenarios, not authorized advertisements or live offers.
"""
import copy,json,re
from pathlib import Path

def dump(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')

def apply(root,assets):
    h=assets['index.html']
    f=Path(root)/'frontend-release'/'regional_drive_data.json'
    entries=json.loads(f.read_text(encoding='utf-8'))['cases']
    sm=re.search(r'window\\.WITestState=(.*?);window\\.WITestCases=',h,re.S)
    mm=re.search(r'window\\.WITestCases=(.*?);\\s*</script>',h,re.S)
    assert sm and mm,'Missing editorial collection'
    state=json.loads(sm.group(1));meta=json.loads(mm.group(1))
    assert len(entries)==8 and len({c['city'] for c in entries})==8
    for c in entries:
        slug=c['slug'];oid='test-20261118-local-'+slug;cid='test-brand-local-'+slug
        if any(o['id']==oid for o in state['ops']):continue
        op=copy.deepcopy(state['ops'][0])
        op.update(id=oid,clientId=cid,brand=c['brand'],sector=c['sector'],objective='visit',
          routeType='unknown',partner='',geo=c['location'],start=c['start'],end=c['end'],
          device='RCS + LP',archived=False,brief=True,fixture=False,angle=0,
          created='2026-11-18T13:00:00+01:00',updated='2026-11-18T13:00:00+01:00')
        op['focus']={'product':c['product'],'benefit':c['benefit'],'moment':c['moment'],
          'hook':c['title'],'offer':'','offerConfirmed':False}
        op['checks']={'products':False,'scope':False,'production':False,'editorial':False}
        rcs=[{'title':v[0],'body':v[1],'cta':v[2]} for v in c['rcs']]
        lp=[{'title':v[0],'body':v[1]} for v in c['lp']]
        art='Maquette locale '+c['city']+' aux couleurs évocatrices de la marque. Visuels officiels à fournir ; ne pas présenter le graphisme de démonstration comme un BAT approuvé.'
        op['creative']={'title':c['title'],'pitch':c['pitch'],'insight':c['benefit'],
          'why':c['why'],'sms':c['sms'],'art':art,'lpTitle':c['product'],
          'handoff':'Proposition de drive-to-store locale, non commandée et sans chiffrage. Toutes les informations à confirmer auprès de l’annonceur.',
          'target':c['target'],'kpi':c['kpi'],'ask':c['check'],'rcs':rcs,'lp':lp}
        op['evidence']=[{'id':oid+'-source-'+str(i),'kind':'brand',
          'claim':c['fact'],'url':v[1],'observedAt':'2026-11-18',
          'validUntil':'2026-11-25','reviewed':False,'collected':False,
          'sourceType':'manual_official_page','excerpt':v[0],
          'publishedAt':''} for i,v in enumerate(c['sources'],1)]
        op['evidence'].append({'id':oid+'-season','kind':'hypothesis',
          'claim':c['why'],'url':'','observedAt':'2026-11-18',
          'reviewed':False,'collected':False,'sourceType':'editorial_reasoning'})
        dest=c['sources'][0][1]
        op['proposal']={'audience':'unknown','partner':'','concept':c['title'],
          'product':c['product'],'benefit':c['benefit'],'moment':c['moment'],
          'hook':c['title'],'target':c['target'],'region':c['location'],
          'start':c['start'],'end':c['end'],'channel':'RCS + LP',
          'sms':c['sms'],'lpTitle':c['product'],'cta':c['rcs'][-1][2],
          'destination':dest,'proofNote':c['fact']+' / '+c['check'],
          'proofURL':dest,'proofDate':'2026-11-18','sourceType':'public',
          'reason':c['why'],'rcsTitle':rcs[0]['title'],
          'rcsBody':rcs[0]['body'],'rcsCTA':rcs[0]['cta'],
          'lpBody':lp[0]['body'],'kpis':c['kpi'],
          'nextStep':'Confirmer les stocks, horaires, offres et créneaux avec '+c['brand']+' avant toute diffusion.',
          'sender':'WellPack · démonstration','contact':'',
          'goal':'Générer des visites au point de vente',
          'imageCaption':'Piste graphique de démonstration — image officielle à intégrer.',
          'visualBrief':art,'brandColor':c['color'],
          'approval':{'product':False,'feasibility':False,'editorial':False},
          'whiteLabel':False}
        op['notes']='CAS DE TEST NON VALIDÉ PAR '+c['brand'].upper()+'.\\n\\n'
        op['notes']+='OBJECTIF : drive-to-store à '+c['city']+'\\n\\n'
        op['notes']+='JUSTIFICATION : '+c['why']+'\\n\\n'
        op['notes']+='SMS : '+c['sms']+'\\n\\n'
        op['notes']+='MESURE : '+c['kpi']+'\\n\\n'
        op['notes']+='À VALIDER : '+c['check']+'\\n\\nSOURCES :\\n'+'\\n'.join(v[0]+': '+v[1] for v in c['sources'])
        state['ops'].append(op)
        state['clients'].append({'id':cid,'name':c['brand'],'sector':c['sector'],
            'routeType':'unknown','partner':'','website':'',
            'catalogue':dest,'geo':c['location']})
        meta[oid]={'slug':slug,'brand':c['brand'],'city':c['city'],
           'title':c['title'],'product':c['product'],'benefit':c['benefit'],
           'moment':c['moment'],'url':dest,'source':'Sources officielles. Vérification nécessaire avant diffusion.',
           'fact':c['fact'],'device':'RCS + LP','rcs':c['rcs'],'lp':c['lp'],
           'target':c['target'],'gate':c['check'],'end':c['end']}
    assert len(state['ops'])==23 and len(state['clients'])==23
    h=h[:mm.start(1)]+dump(meta)+h[mm.end(1):]
    sm=re.search(r'window\\.WITestState=(.*?);window\\.WITestCases=',h,re.S)
    h=h[:sm.start(1)]+dump(state)+h[sm.end(1):]
    # Only update the explanatory demo count; preserve custom names and user edits.
    h=h.replace('15 campagnes à tester : produits, services et promotions.',
      '23 campagnes à tester : produits, services, promotions et commerces locaux.')
    h=h.replace('15 campagnes à tester.<br>Produits, services et promotions.',
      '23 campagnes à tester.<br>Produits, services et commerces locaux.')
    h=h.replace('15 présentations','23 présentations')
    h=h.replace('15 cas','23 cas')
    assets['index.html']=h
    return {'localDriveCases':8,'cities':8,'allCases':23,'localPDFs':8}
