"""Plain-language titles and three source-qualified promotional test cases."""
import json,re,copy
from pathlib import Path
TITLES={
'ikea':('IKEA — Tables extensibles pour les repas de fêtes','Tables extensibles pour recevoir'),
'decathlon':('Decathlon — Courir le soir avec un éclairage adapté','Un éclairage pour courir le soir'),
'picard':('Picard — Préparer les apéritifs des fêtes','Des bouchées chaudes pour votre apéritif'),
'norauto':('Norauto — Faire vérifier sa batterie avant l’hiver','Diagnostic de la batterie et de l’alternateur'),
'darty':('Darty — Faire réparer son four avant les fêtes','Faire réparer son four'),
'leroy-merlin':('Leroy Merlin — Louer une shampouineuse avant les fêtes','Louer une shampouineuse'),
'bonsoirs':('Bonsoirs — Choisir une couette pour l’hiver','Choisir sa couette et ses dimensions'),
'loom':('Loom — Mettre en avant les pulls en laine mérinos','Les pulls en laine mérinos'),
'wecandoo':('Wecandoo — Offrir un atelier d’artisan à Noël','Offrir un atelier d’artisan'),
'chocolat-francais':('Le chocolat des Français — Calendrier de l’Avent : stock à confirmer','Calendrier de l’Avent : disponibilité à confirmer'),
'bergamotte':('Bergamotte — Offrir un abonnement de bouquets à Noël','Un abonnement de bouquets à offrir'),
'chez-bogato':('Chez Bogato — Commander son dessert de Noël','Commander son dessert de Noël'),
}
PROMOS=[
 dict(slug='midas-promotions',brand='Midas',sector='other',title='Midas — Promouvoir les offres Black Friday en centre',
 product='Offres Black Friday sur la révision, les batteries, les plaquettes et les pneus',
 benefit='Choisir la remise qui correspond à son entretien, puis prendre rendez-vous dans un centre participant.',
 hook='Black Friday Midas : découvrez les offres entretien.',moment='Black Friday, avant les déplacements de fin d’année',end='2026-11-28',device='RCS + LP',objective='service',
 pitch='Une campagne d’enseigne réunit les offres en cours. Le destinataire choisit son besoin : révision, batterie, freinage ou pneus. Chaque carte affiche ses conditions et mène au parcours officiel de rendez-vous.',
 why='Les promotions publiées ont des échéances différentes. La campagne se termine le 28 novembre pour ne pas prolonger les offres freinage et pneus ; une seconde vague révision/batterie demanderait un nouveau message.',
 insight='Une campagne entretien multioffres peut répondre à plusieurs besoins sans présumer qu’un véhicule a une panne.',
 smsA='Midas : Black Friday sur la revision, les batteries, le freinage et les pneus. Offres, dates et RDV : {LIEN} {STOP}',
 smsB='Midas : un entretien a prevoir ? Decouvrez nos offres Black Friday et prenez RDV. Conditions : {LIEN} {STOP}',
 rcs=[['Black Friday Midas','Révision, batteries, plaquettes et pneus : choisissez l’offre adaptée. Conditions et dates propres à chaque offre.','Voir les offres'],['Révision et batteries : -20%*','Jusqu’au 26/12/2026. Révision hors prestations complémentaires ; batteries éligibles montées en atelier, hors main-d’œuvre.','Voir les conditions'],['Plaquettes : -30%*','Ferodo et Midas Origin’All, hors main-d’œuvre. RDV sur midas.fr dans les centres participants jusqu’au 28/11/2026.','Prendre RDV'],['2e pneu Hankook : -25%*','Kinergy 4S2. Commande et RDV en ligne avec montage de deux pneus minimum, avant le 28/11/2026. Quota à revalider.','Voir les pneus']],
 lp=[['Toutes les offres','Présenter chaque remise avec son périmètre, ses dates et ses exclusions ; jamais « -30% sur tout ».'],['Choisir son entretien','Quatre entrées : révision, batterie, freinage, pneus. Reprendre les conditions de la page officielle.'],['Prendre rendez-vous','Redirection vers midas.fr et les centres participants. Ne pas substituer un formulaire tiers aux conditions d’éligibilité web.']],
 reason='Le RCS présente plusieurs services sans encombrer le SMS. Une LP n’est utile que pour la localisation et la synthèse ; sinon, lien direct vers les offres officielles.',
 cta='Voir les offres et prendre RDV',primary='Rendez-vous confirmés attribuables par message délivré, avec suivi validé.',secondary='Clics par offre et débuts de réservation ; un clic ne vaut pas un rendez-vous.',
 target='Contacts ayant consenti au canal, dans les zones des centres participants ; exclure les oppositions et éviter les relances aux personnes ayant déjà réservé.',
 art='Visuel officiel Black Friday Midas puis cartes par service. Même poids visuel pour les remises et leurs périmètres. Aucun diagnostic mécanique présumé.',
 gate='Confirmer les centres, les créneaux, les dates et le quota pneus. Ne pas confondre la comparaison « 50% moins cher » avec une remise de 50%.',
 fact='La page officielle annonce -20% révision/batteries jusqu’au 26/12/2026 ; -30% sur plaquettes éligibles et -25% sur le 2e pneu Hankook 4S2 jusqu’au 28/11/2026, avec conditions web et exclusions propres.',
 url='https://www.midas.fr/promotions-midas/black-friday',source='Page officielle indexée ; lecture directe indisponible. Conditions à recontrôler avant diffusion.'),
 dict(slug='generale-optique-promotions',brand='Générale d’Optique',sector='optics',title='Générale d’Optique — Promouvoir l’offre deuxième et troisième paire',
 product='Offre multi-équipement : une première paire et des montures de deuxième/troisième paire à -50% selon conditions',
 benefit='Présenter plusieurs usages des lunettes et orienter vers un conseil en magasin, sans imposer une référence de monture.',
 hook='Besoin de plusieurs paires ? Découvrez l’offre multi-équipement.',moment='Campagne de fin d’année ; offre permanente, sans fausse date limite',end='2026-12-06',device='SMS + LP',objective='visit',
 pitch='Un SMS présente l’offre multi-équipement et renvoie vers une page expliquant les usages, les montures éligibles et la prise de rendez-vous locale. Il ne promet ni paires gratuites ni remboursement.',
 why='Le choix de fin novembre est une proposition de calendrier, pas une fin d’offre. Le coupon téléchargeable jusqu’au 13 novembre n’est pas utilisé pour recruter de nouveaux bénéficiaires.',
 insight='La promotion s’adresse à un besoin de plusieurs paires, pas à une monture précise. Le conseil magasin reste nécessaire pour expliquer l’éligibilité.',
 smsA="Generale d'Optique : 1re paire achetee, des montures de 2e/3e paire a -50%*. RDV et conditions : {LIEN} {STOP}",
 smsB="Generale d'Optique : plusieurs paires, plusieurs usages. Decouvrez notre offre multi-equipement et prenez RDV : {LIEN} {STOP}",
 rcs=[['L’offre multi-équipement','Après achat d’une première paire, découvrez les conditions pour votre deuxième et troisième paire.','Voir l’offre'],['Des usages différents','Quotidien, soleil ou sport : choix selon besoins et modèles éligibles. Pas de promesse médicale.','Voir les conditions'],['Un conseil en magasin','Vérifiez les conditions de montures et de verres avec votre opticien.','Prendre RDV']],
 lp=[['Comprendre l’offre','Préciser l’achat initial, la même correction et les catégories éligibles. Ne pas étendre une remise monture au prix complet monture + verres.'],['Choisir selon ses usages','Présenter des exemples optique, solaire et sport éligibles, sans diagnostic ni bénéfice médical inventé.'],['Trouver son opticien','Afficher les magasins participants et un lien de rendez-vous officiel ; reprendre les exclusions et non-cumuls.']],
 reason='Le SMS suffit pour faire connaître une offre large. La LP clarifie les conditions et mène au rendez-vous ; un RCS constitue une variante, pas un achat imposé.',
 cta='Découvrir l’offre et prendre RDV',primary='Rendez-vous confirmés attribuables par message délivré.',secondary='Consultation des conditions et choix d’un magasin ; achats uniquement si un suivi fiable est prévu.',
 target='Adultes ayant consenti au canal, proches des magasins concernés. Aucun ciblage déduit d’un problème de vue ou de données de santé.',
 art='Visuel officiel de l’offre et plusieurs montures éligibles. Pourcentage accompagné d’un astérisque lisible ; pas de mention « gratuit ».',
 gate='Faire valider le libellé -50% par l’enseigne : la page de présentation et les conditions détaillées n’ont pas exactement le même périmètre. Confirmer montures, verres, exclusions et magasins.',
 fact='L’offre multi-équipement prévoit un achat initial et des paires supplémentaires sous conditions. Le détail prévoit -50% sur des montures éligibles ; la présentation est plus large. Aucun délai de fin d’année ni coupon encore téléchargeable n’est affirmé.',
 url='https://www.generale-optique.com/mentions-legales-offres-en-cours/conditions-des-offres-en-cours',source='Pages officielles consultées ; écart de formulation à faire valider par l’enseigne.'),
 dict(slug='sephora-promotions',brand='Sephora',sector='other',title='Sephora — Promouvoir le Black Friday sur les parfums et coffrets',
 product='Black Friday : -30% sur les parfums et coffrets parfums, hors Point Rouge',
 benefit='Faire connaître une remise sur plusieurs marques et formats, puis laisser choisir le parfum ou le coffret.',
 hook='Black Friday : -30% sur les parfums et coffrets, hors Point Rouge.',moment='Black Friday et préparation des cadeaux de Noël',end='2026-11-30',device='SMS',objective='visit',
 pitch='Un SMS porte l’offre d’enseigne plutôt qu’un parfum unique. Le lien ouvre la sélection officielle, avec la possibilité de chercher son magasin. Un carrousel peut présenter parfums et coffrets sans réduire la campagne à une référence.',
 why='L’offre indexée couvre le 16 au 30 novembre 2026. La fin novembre peut servir aux achats cadeaux ; ce contexte est une proposition marketing, pas une hausse de ventes démontrée.',
 insight='Une offre large permet de s’adresser à plusieurs préférences sans supposer le parfum préféré du destinataire.',
 smsA='Sephora : Black Friday, -30% sur parfums et coffrets parfum, hors Point Rouge, jusqu au 30/11. Conditions : {LIEN} {STOP}',
 smsB='Sephora : preparez vos cadeaux ! -30% sur parfums et coffrets, hors Point Rouge, jusqu au 30/11. Conditions : {LIEN} {STOP}',
 rcs=[['Black Friday : -30%','Parfums et coffrets parfums, hors Point Rouge. Jusqu’au 30/11/2026. Conditions applicables.','Voir les offres'],['Choisir un parfum','Plusieurs marques et formats éligibles. Ne pas illustrer avec des références exclues.','Voir les parfums'],['Choisir un coffret','Coffrets parfums éligibles pour préparer les cadeaux. Stock à vérifier.','Voir les coffrets']],
 lp=[['Destination : page officielle','Pas de nouvelle LP obligatoire : réutiliser la page Black Friday avec ses filtres et conditions.'],['Deux entrées utiles','Parfums et coffrets ; ne pas promettre une remise sur tout le magasin.'],['Préparer l’achat','Afficher la fin de l’offre et les exclusions ; lien magasin ou commande selon le parcours confirmé.']],
 reason='Le SMS rend l’avantage immédiatement lisible. La page officielle évite une étape inutile ; la LP n’est à créer que pour un besoin local non couvert.',
 cta='Voir les parfums et coffrets',primary='Achats attribuables par message délivré lorsque le suivi est disponible.',secondary='Clics qualifiés, consultation de la sélection, choix magasin ; pas de visite comptée à partir d’un clic.',
 target='Contacts opt-in dans les zones des magasins ou desservies en ligne ; aucune préférence olfactive présumée, contrôle de la pression commerciale.',
 art='Charte Black Friday Sephora. Mosaïque de plusieurs parfums et coffrets éligibles, sans afficher de produits Point Rouge exclus.',
 gate='Reconfirmer les dates et les conditions : les résultats indexés décrivent novembre 2026, mais une ouverture de page a redirigé vers l’accueil. Ne pas cumuler automatiquement les offres web supplémentaires.',
 fact='Les pages officielles indexées indiquent -30% sur parfums et coffrets, hors Point Rouge, du 16 au 30/11/2026, non cumulable et dans la limite des stocks. L’ouverture directe a redirigé : validation préalable obligatoire.',
 url='https://www.sephora.fr/black-friday-all/',source='Contenu officiel indexé ; redirection constatée sur une page dédiée. À reconfirmer avant envoi.')
]
def encode(x):return json.dumps(x,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
def apply(root,assets):
 h=assets['index.html']
 sm=re.search(r'window\.WITestState=(.*?);window\.WITestCases=',h,re.S)
 mm=re.search(r'window\.WITestCases=(.*?);\s*</script>',h,re.S)
 state=json.loads(sm.group(1));meta=json.loads(mm.group(1));old=copy.deepcopy(state)
 for op in state['ops']:
  slug=op['id'].removeprefix('test-20261117-')
  if slug not in TITLES:continue
  title,lp=TITLES[slug]
  op['creative']['title']=title;op['creative']['lpTitle']=lp
  op['proposal']['concept']=title;op['proposal']['lpTitle']=lp
  meta[op['id']]['title']=title
 for p in PROMOS:
  p=copy.deepcopy(p);slug=p['slug'];id='test-20261117-'+slug;cid='test-brand-'+slug
  p.update(id=id,size='Grande enseigne',kind='Promotion d’enseigne',start='2026-11-23',geo='Magasins / centres participants ; périmètre à confirmer.',test='Comparer les deux accroches sur des groupes distincts et comparables, avec les mêmes offres, dates et destination. Décider sur la conversion finale, pas seulement les clics.',goal=p['primary'],handoff='Opération d’enseigne prête à adapter au réseau. Aucun devis, aucune promesse de résultat.',ask='Valider les conditions, les établissements participants et le suivi avant production.',sources=[dict(title=p['brand']+' — conditions officielles',url=p['url'],fact=p['fact'],mode='index',accessedAt='2026-11-17',publishedAt='')])
  op=copy.deepcopy(state['ops'][0]);op.update(id=id,clientId=cid,brand=p['brand'],sector=p['sector'],objective=p['objective'],device=p['device'],start=p['start'],end=p['end'],leadDays=3,geo=p['geo'],creative={},evidence=[],proposal={},checks={'products':False,'scope':False,'production':False,'editorial':False})
  op['focus']=dict(product=p['product'],benefit=p['benefit'],moment=p['moment'],hook=p['hook'],offer='',offerConfirmed=False)
  op['creative']={k:p[k] for k in ('title','pitch','insight','why','art','handoff','target','ask')}
  op['creative'].update(sms=p['smsA'],lpTitle=p['product'],kpi=p['primary'],rcs=[dict(zip(('title','body','cta'),x)) for x in p['rcs']],lp=[dict(zip(('title','body'),x)) for x in p['lp']])
  op['evidence']=[dict(id=id+'-source',kind='brand',claim=p['fact'],url=p['url'],observedAt='2026-11-17',validUntil='2026-11-23',reviewed=False,collected=False,sourceType='manual_official_index',excerpt=p['source'],publishedAt=''),dict(id=id+'-season',kind='hypothesis',claim=p['why'],url='',observedAt='2026-11-17',reviewed=False,collected=False,sourceType='editorial_reasoning')]
  op['proposal']=dict(audience='unknown',partner='',concept=p['title'],product=p['product'],benefit=p['benefit'],moment=p['moment'],hook=p['hook'],target=p['target'],region=p['geo'],start=p['start'],end=p['end'],channel=p['device'],sms=p['smsA'],lpTitle=p['product'],cta=p['cta'],destination=p['url'],proofNote=p['source']+' '+p['fact'],proofURL=p['url'],proofDate='2026-11-17',sourceType='public',reason=p['reason'],rcsTitle=p['rcs'][0][0],rcsBody=p['rcs'][0][1],rcsCTA=p['rcs'][0][2],lpBody=p['lp'][0][1],kpis=p['primary'],nextStep=p['ask'],sender='WellPack · démonstration',contact='',goal=p['goal'],imageCaption='Visuel de principe — visuel officiel à fournir.',visualBrief=p['art'],brandColor='#232323',approval={'product':False,'feasibility':False,'editorial':False},whiteLabel=False)
  op['notes']='CAS DE TEST ÉDITORIAL — NON VALIDÉ PAR LA MARQUE. Aucun lien commercial avec WellPack affirmé.\n\nÀ VÉRIFIER : '+p['gate']+'\n\nVARIANTE A\n'+p['smsA']+'\n\nVARIANTE B\n'+p['smsB']+'\n\nTEST\n'+p['test']+'\n\nSOURCES\n'+p['source']+'\n'+p['url']
  state['ops'].append(op);state['clients'].append(dict(id=cid,name=p['brand'],sector=p['sector'],routeType='unknown',partner='',website='',catalogue=p['url'],geo=p['geo']));meta[id]=p
 h=h[:mm.start(1)]+encode(meta)+h[mm.end(1):]
 sm=re.search(r'window\.WITestState=(.*?);window\.WITestCases=',h,re.S);h=h[:sm.start(1)]+encode(state)+h[sm.end(1):]
 migrations=[]
 for before,after in zip(old['ops'],state['ops']):
  migrations.append(dict(id=before['id'],oldTitle=before['creative']['title'],title=after['creative']['title'],oldLP=before['creative']['lpTitle'],lp=after['creative']['lpTitle'],oldConcept=before['proposal']['concept']))
 code="""
// Replace untouched sample headings only; user-written titles are preserved.
for(const m of %s){const o=state.ops.find(x=>x.id===m.id);if(!o)continue;
 if(o.creative?.title===m.oldTitle)o.creative.title=m.title;
 if(o.creative?.lpTitle===m.oldLP)o.creative.lpTitle=m.lp;
 if(o.proposal?.concept===m.oldConcept)o.proposal.concept=m.title;
 if(o.proposal?.lpTitle===m.oldLP)o.proposal.lpTitle=m.lp;
}
"""%encode(migrations)
 anchor='state.settings.date=today;';assert anchor in h;h=h.replace(anchor,code+'\n'+anchor,1)
 labels={'12 offres réelles. 12 opérations à tester.':'15 campagnes à tester : produits, services et promotions.','12 offres réelles.<br>12 opérations à tester.':'15 campagnes à tester.<br>Produits, services et promotions.','12 cas':'15 cas','12 présentations':'15 présentations','Une offre. Une action. Une mesure.':'Objectif, messages et résultats à mesurer','Ce que votre public<br>voit. Et ce qu’il fait.':'Messages et parcours client','Un axe clair.<br>Un plan pour l’activer.':'Calendrier et étapes de lancement','Ce qui est lu. Ce qui ne l’est pas.':'Sources disponibles et limites de l’analyse','Pourquoi certaines offres ne deviennent pas des axes':'Pourquoi certaines offres n’ont pas de recommandation','Creative studio / éditeur':'Modifier les textes','Des sources aux idées,<br>avec une seule clé.':'Configurer la recherche et la rédaction IA','Une offre précise.<br>Une opportunité concrète.':'Offre et objectif de campagne'}
 for a,b in labels.items():h=h.replace(a,b)
 assets['index.html']=h
 for a,b in labels.items():assets['live.js']=assets['live.js'].replace(a,b)
 aip=Path(root)/'engine'/'ai.py';ai=aip.read_text()
 if 'Tu es' in ai:
  ai=ai.replace('Tu es','Règle de rédaction : titres descriptifs en français simple, avec l’offre ou le service et l’objectif. Aucun slogan abstrait, jeu de mots obscur ou jargon dans les titres de rapport. Les accroches publicitaires restent réservées aux messages SMS/RCS. Tu es',1);aip.write_text(ai)
 return {'cases':len(state['ops']),'presentations':len(state['ops'])}
