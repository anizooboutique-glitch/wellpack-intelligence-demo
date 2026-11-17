"""Small, explainable rule engine. No made-up promotions, forecasts or performance."""
from __future__ import annotations
import re
from datetime import date,timedelta
from .crawl import norm,uid,now,compact

PROFILES=[
 dict(key='extendable_table',all=['table'],any=['extensible','rallonge'],sector='home',months=[10,11,12],moment='Préparer les repas de fin d’année',hook='Vous recevez pour les fêtes ?',title='Plus de convives, la même pièce.',need='accueillir des invités sans réserver toute l’année la surface d’une grande table',action='montrer la table fermée puis dépliée, avec ses dimensions officielles',cta='Voir les dimensions',feature='extensible'),
 dict(key='convertible_sofa',all=['canape'],any=['convertible','couchage'],sector='home',months=[],moment='Recevoir des proches à la maison · angle permanent',hook='Un couchage en plus ?',title='Le salon sait aussi recevoir la nuit.',need='disposer d’un couchage occasionnel sans chambre supplémentaire',action='présenter le passage du canapé au couchage et renvoyer vers la fiche exacte',cta='Voir le canapé',feature='convertible'),
 dict(key='thermal',all=[],any=['thermique','polaire','merinos','isolation thermique'],sector='sport',months=[10,11,12,1,2],moment='Préparation des sorties d’hiver · saison, pas prévision météo',hook='Vous préparez vos sorties d’hiver ?',title='Le bon équipement avant de sortir.',need='choisir un équipement adapté aux sorties de saison',action='mettre en avant la caractéristique thermique publiée et son usage, sans annoncer de vague de froid',cta='Voir le modèle',feature='thermique'),
 dict(key='watch',all=['montre'],any=['bracelet interchangeable','interchangeable','personnalisable','gravure'],sector='watch',months=[11,12],moment='Recherche de cadeaux de fin d’année',hook='Un cadeau à personnaliser ?',title='Un cadeau qui lui ressemble.',need='choisir un cadeau selon les goûts du destinataire',action='montrer les possibilités de personnalisation effectivement documentées et diriger vers le modèle',cta='Voir le modèle',feature='personnalisation'),
 dict(key='adjustment',all=['lunette'],any=['ajustage','ajustement','ajuster'],sector='optics',months=[],moment='Besoin d’ajuster une monture · service permanent',hook='Vos lunettes glissent ?',title='Une monture à ajuster, pas à remplacer.',need='faire ajuster sa monture existante',action='présenter le service et orienter vers ses conditions d’accès, sans promettre gratuité ni résultat médical',cta='Voir le service',feature='ajustage'),
 dict(key='repair',all=[],any=['reparation','reparer','entretien','revision'],sector='other',months=[],moment='Besoin d’entretien ou de réparation · service permanent',hook='Un équipement à entretenir ?',title='Faire durer plutôt que remplacer.',need='accéder au service d’entretien ou de réparation documenté',action='expliquer le périmètre exact du service et diriger vers la prise de contact existante',cta='Voir les conditions',feature='entretien')
]

def matching_profile(offer,today):
    content=norm(offer['title']+' '+offer['excerpt'])
    for p in PROFILES:
        if p['months'] and today.month not in p['months']:continue
        if all(x in content for x in p['all']) and any(x in content for x in p['any']):
            if p['key']=='repair' and offer['kind']!='service':continue
            return p
    return None

def as_evidence(s):
    return dict(id=s['id'],kind='brand',claim=s['title']+' — '+s['excerpt'][:430],url=s['url'],observedAt=s['observedAt'][:10],reviewed=False,collected=True,sourceType=s['kind'],excerpt=s['excerpt'][:600],publishedAt=s.get('publishedAt',''))

def sms_copy(brand,offer,hook,cta):
    text=f"{brand} : {hook} Découvrez {offer['title']}. {cta} : {{LIEN}} {{STOP}}"
    if len(text)>155:text=f"{brand} : Découvrez {offer['title']}. {cta} : {{LIEN}} {{STOP}}"
    return text

def operation(brand,offer,p,report,*,today=None,model_copy=None):
    today=today or date.today();m=model_copy or {};seasonal=bool(p['months'])
    evidence=[as_evidence(offer)]
    sig=next((n for n in report['news'] if n['id']==m.get('signal_id') and n.get('verifiedContent')),None)
    if sig:evidence.append(as_evidence(sig))
    quote=m.get('proof_quote') or offer['excerpt'][:230]
    moment=(sig['title'] if sig else p['moment'])[:130]
    rationale=m.get('rationale') or f"La fiche décrit « {offer['title']} ». Notre hypothèse marketing : répondre au besoin de {p['need']}. L’activation consiste à {p['action']}."
    nowreason=(f"Publication source datée du {sig['publishedAt'][:10]}. " if sig else ('Rapprochement avec une période récurrente, pas une tendance mesurée. ' if seasonal else 'Proposition de service ou d’usage permanent : aucune actualité urgente n’est prétendue. '))+moment
    start=today+timedelta(days=14);end=start+timedelta(days=21)
    if seasonal and today.month==12:end=min(end,date(today.year,12,24))
    if end<start:return None
    objective='service' if offer['kind']=='service' else 'select'
    opid='live-'+uid(brand['id'],offer['id'],p['key'],today.year if seasonal else 'permanent')
    title=m.get('title') or p['title'];sms=m.get('sms') or sms_copy(brand['name'],offer,m.get('hook') or p['hook'],p['cta'])
    inference_label='Piste IA sourcée · à relire' if m else 'Piste métier sourcée · à relire'
    return dict(id=opid,clientId=brand['id'],brand=brand['name'],sector=p['sector'],routeType=brand.get('routeType','unknown'),partner=brand.get('partner',''),geo=brand.get('geo',''),start=start.isoformat(),end=end.isoformat(),leadDays=10,objective=objective,assets=False,agent=False,existingPage=True,device='',fixture=False,angle=0,checks={},notes='',created=now(),updated=now(),evidence=evidence,
        focus={'product':offer['title'],'benefit':quote[:240],'moment':moment,'hook':m.get('hook') or p['hook'],'offer':'','offerConfirmed':False},
        live={'mode':'ai' if m else 'rules','label':inference_label,'offerId':offer['id'],'offerURL':offer['url'],'rule':p['key'],'rationale':rationale,'trigger':nowreason,'readAt':report['readAt'],'warning':'Lecture automatisée, non validation humaine. Stock, zone, offre et faisabilité restent à confirmer.','coverage':report['coverage'],'draftPeriod':True},
        creative={
            'title':title,'pitch':f"Promouvoir {offer['title']} en partant d’un besoin précis : {p['need']}. {m.get('angle') or p['action'].capitalize()+'.'}",
            'insight':rationale,'why':nowreason,'sms':sms,'art':f"Utiliser un visuel officiel de {offer['title']}. Illustrer : {p['action']}. Aucun visuel produit n’est téléchargé ni inventé automatiquement.",
            'lpTitle':offer['title'],'handoff':f"Proposer à l’agence ou à la marque un axe centré sur {offer['title']}, avec l’extrait source et le parcours ci-joint. Aucune relation avec une agence n’est déduite du web.",
            'target':m.get('audience') or 'Audience à définir selon le besoin décrit et les capacités de ciblage disponibles. Ne pas supposer de segment comportemental accessible.',
            'kpi':'Messages délivrés, clics vers la fiche et actions attribuables si un suivi est prévu. Aucune performance prévisionnelle.',
            'ask':'Confirmer la disponibilité du produit ou service, la zone et la période ; valider le message et la destination.',
            'rcs':[{'title':offer['title'],'body':quote[:240],'cta':p['cta']},{'title':m.get('hook') or p['hook'],'body':'Montrer le produit ou le service avec des éléments officiels validés.','cta':p['cta']}],
            'lp':[{'title':offer['title'],'body':quote[:350]},{'title':'Comprendre avant de choisir','body':'Reprendre uniquement les caractéristiques publiées, les conditions confirmées et un CTA vers la fiche source.'}]
        })

def propose_rules(brand,report,today=None):
    today=today or date.today();ops=[];rejected=[];used=set()
    for offer in report['offers']:
        if offer.get('availability') in ('OutOfStock','Discontinued','SoldOut'):
            rejected.append({'offer':offer['title'],'reason':'Indisponibilité publiée : pas d’activation proposée.'});continue
        p=matching_profile(offer,today)
        if not p:
            rejected.append({'offer':offer['title'],'reason':'Offre lue, mais aucun rapprochement suffisamment spécifique dans le moteur métier.'});continue
        if p['key'] in used:continue
        op=operation(brand,offer,p,report,today=today)
        if op:ops.append(op);used.add(p['key'])
        if len(ops)>=3:break
    return ops,rejected[:30]
