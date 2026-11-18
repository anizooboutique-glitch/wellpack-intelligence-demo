"""Phase 1: prioritize verified opportunities, support SMS/RCS/LP and a light sales pipeline.
No unverified ROI claims, no new paid API, no destructive change to existing editorial data.
"""
def apply(root,assets):
    h=assets['index.html']
    extra_js="\nfunction opportunityRank(o){\n const now=state.settings.date||new Date().toISOString().slice(0,10);\n const ev=(o.evidence||[]).filter(e=>e.url&&/^https?:/.test(e.url));\n const dated=ev.filter(e=>!e.validUntil||e.validUntil>=now);\n const expired=!!o.end&&o.end<now;\n const future=!!o.start&&!!o.end&&!expired;\n const local=!!o.geo&&o.geo.length>12;\n const structured=!!o.focus?.product&&!!o.focus?.benefit&&!!o.focus?.moment;\n const route=!!(o.proposal?.destination||o.creative?.lp?.length);\n let score=20+(ev.length?15:0)+(dated.length?10:0)+(future?20:0)+(local?15:0)+(structured?15:0)+(route?5:0);\n if(expired)score=Math.min(score,35);\n if(!dated.length)score=Math.min(score,55);\n if(o.live?.stale)score=Math.min(score,45);\n score=Math.min(100,score);\n const reason=expired?'Période dépassée : nouveau calendrier nécessaire':!ev.length?'Aucune source externe citée':!dated.length?'Source à recontrôler':future?'Fenêtre commerciale cohérente, sous réserve de validation':'Période à confirmer';\n return {score,reason,source:dated.length>0,expired};\n}\nfunction opportunityChannel(o){return String(o.proposal?.channel||o.device||E.recommend(o).choice||'SMS')}\nfunction opportunityStage(o){return ['new','review','outreach','sent','discussion','won'].includes(o.salesStage)?o.salesStage:'new'}\nconst STAGES={new:'À étudier',review:'À qualifier',outreach:'À contacter',sent:'Proposition envoyée',discussion:'En discussion',won:'Campagne gagnée'};\nlet channelFocus='',priorityMode='score',stageFocus='';\n"
    anchor='function cardMarkup(o){'
    assert anchor in h
    h=h.replace(anchor,extra_js+'\n'+anchor,1)
    # Persist stage through existing state sanitation and import/export.
    clean="archiveReason:text(o.archiveReason,1000),brief:o.brief===true"
    assert clean in h
    h=h.replace(clean,"archiveReason:text(o.archiveReason,1000),salesStage:['new','review','outreach','sent','discussion','won'].includes(o.salesStage)?o.salesStage:'new',brief:o.brief===true",1)
    # Clear priority, without claiming predictive performance.
    a=h.index('function cardMarkup(o){');b=h.index('function renderOps(){',a)
    part=h[a:b]
    assert 'const r=E.recommend(o),ctx=radarContext(o),t=E.timing(o,state.settings.date);' in part
    part=part.replace('const r=E.recommend(o),ctx=radarContext(o),t=E.timing(o,state.settings.date);',
      'const r=E.recommend(o),ctx=radarContext(o),t=E.timing(o,state.settings.date),pr=opportunityRank(o);',1)
    part=part.replace('<h3>${esc(o.creative.title)}</h3>',
      '<div class="wi-op-score"><span><strong>${pr.score}/100</strong> · potentiel éditorial indicatif</span><small>${esc(pr.reason)}</small></div><h3>${esc(o.creative.title)}</h3>',1)
    assert '<div class="opmeta"><span>${esc(E.routeLabel(o))}</span>' in part
    part=part.replace('<div class="opmeta"><span>${esc(E.routeLabel(o))}</span>',
      '<div class="wi-stage"><label for="stage-${esc(o.id)}">Suivi commercial</label><select id="stage-${esc(o.id)}" data-salesstage="${esc(o.id)}" aria-label="Suivi commercial de ${esc(o.brand)}">${Object.entries(STAGES).map(([key,v])=>\x60<option value="${key}" ${opportunityStage(o)===key?"selected":""}>${esc(v)}</option>\x60).join("")}</select></div><div class="opmeta"><span>${esc(E.routeLabel(o))}</span>',1)
    # Add direct access to the existing editable client proposal and PDF.
    part=part.replace('Voir la recommandation →</button></div></article>',
      'Voir la recommandation →</button><button type="button" class="wi-proposal-shortcut" data-propose-fast="${esc(o.id)}">Présentation SMS / RCS / LP →</button></div></article>',1)
    h=h[:a]+part+h[b:]
    # Campaign list: filters and ordering, respecting the historical controls.
    a=h.index('function renderOps(){');b=h.index('function renderClients(){',a)
    part=h[a:b]
    old="const filtered=Boolean(filter.q||filter.route||filter.status!=='active');"
    assert old in part
    part=part.replace(old,"const filtered=Boolean(filter.q||filter.route||filter.status!=='active'||channelFocus||stageFocus);",1)
    old='}).sort(activeOrder);'
    assert old in part
    part=part.replace(old,"&&( !channelFocus || opportunityChannel(o).includes(channelFocus) || (channelFocus==='LP'&&opportunityChannel(o).includes('LP')) )&&(!stageFocus||opportunityStage(o)===stageFocus)}).sort((a,b)=>priorityMode==='date'?activeOrder(a,b):opportunityRank(b).score-opportunityRank(a).score||activeOrder(a,b));",1)
    marker="$('opgrid').innerHTML=arr.map(cardMarkup).join('');"
    assert marker in part
    part=part.replace(marker,"$('prioritySummary').textContent=arr.length+' recommandations · scores éditoriaux indicatifs, non prédictifs · sources et stocks à vérifier avant prospection';\n "+marker,1)
    marker="$$('[data-open]').forEach(b=>b.onclick=()=>openDetail(b.dataset.open));"
    assert marker in part
    part=part.replace(marker,marker+"""
 $$('[data-propose-fast]').forEach(b=>b.onclick=()=>openProposal(b.dataset.proposeFast));
 $$('[data-salesstage]').forEach(s=>s.onchange=()=>{const op=state.ops.find(o=>o.id===s.dataset.salesstage);if(!op)return;op.salesStage=s.value;persist();renderOps();toast('Suivi commercial enregistré localement.')});
""",1)
    h=h[:a]+part+h[b:]
    start=h.index('<div class="toolbar" id="campaignFilters">')
    end=h.index('</div>',start)
    extras='''<select id="wiChannel" aria-label="Filtrer par dispositif"><option value="">Tous les canaux</option><option value="SMS">SMS</option><option value="RCS">RCS</option><option value="LP">Landing pages</option></select><select id="wiStage" aria-label="Filtrer par état commercial"><option value="">Tous les statuts</option><option value="new">À étudier</option><option value="review">À qualifier</option><option value="outreach">À contacter</option><option value="sent">Proposition envoyée</option><option value="discussion">En discussion</option><option value="won">Campagne gagnée</option></select><select id="wiPriority" aria-label="Ordonner les campagnes"><option value="score">Potentiel éditorial</option><option value="date">Date / urgence</option></select>'''
    h=h[:end]+extras+h[end:]
    assert '<div class="opgrid" id="opgrid"></div>' in h
    h=h.replace('<div class="opgrid" id="opgrid"></div>','<div class="wi-priority-summary" id="prioritySummary" aria-live="polite"></div><div class="opgrid" id="opgrid"></div>',1)
    # Bind filters at document initialization, avoiding reliance on a second event library.
    event_js="""document.addEventListener('change',e=>{if(e.target.id==='wiChannel'){channelFocus=e.target.value;renderOps()}if(e.target.id==='wiStage'){stageFocus=e.target.value;renderOps()}if(e.target.id==='wiPriority'){priorityMode=e.target.value;renderOps()}});"""
    assert '</script>' in h
    # Inline controls run after the original scripts and do not modify the API.
    h=h.replace('</body>', '<script>'+event_js+'</script></body>',1)
    # Fix index filters showing reset state: reset all additional filters.
    reset="filter={q:'',route:'',status:'active'};$('search').value='';$('routeFilter').value='';$('statusFilter').value='active';renderOps();"
    h=h.replace(reset,"filter={q:'',route:'',status:'active'};channelFocus='';stageFocus='';priorityMode='score';$('wiChannel').value='';$('wiStage').value='';$('wiPriority').value='score';$('search').value='';$('routeFilter').value='';$('statusFilter').value='active';renderOps();")
    css='''<style id="wi-phase1-style">
.wi-priority-summary{margin:12px 0 16px;font-size:12px;color:var(--muted,#6b6b6b);line-height:1.5}
.wi-op-score{display:flex;flex-direction:column;gap:3px;padding:10px 12px;margin:10px 0 2px;border-radius:10px;background:rgba(246,217,53,.12);font-size:12px}
.wi-op-score strong{font-size:15px;color:inherit}.wi-op-score small{color:var(--muted,#676767);font-size:11px}
.wi-stage{display:flex;align-items:center;justify-content:space-between;gap:9px;margin-top:13px;font-size:12px;color:inherit}
.wi-stage select{min-width:145px;max-width:190px;border-radius:8px;border:1px solid #c7c7c7;padding:7px 8px;background:var(--card,#fff);color:inherit;font:inherit}
.wi-proposal-shortcut{font:inherit;background:none;border:0;padding:8px 0;text-align:left;text-decoration:underline;cursor:pointer;color:inherit}
#campaignFilters{flex-wrap:wrap;gap:8px}#campaignFilters select{max-width:220px}
</style>'''
    h=h.replace('</head>',css+'</head>',1)
    assert 'id="wiChannel"' in h and 'opportunityRank(o)' in h
    assert 'data-propose-fast' in h and 'salesStage' in h
    assets['index.html']=h
    return {'prioritization':True,'channelFilters':['SMS','RCS','LP'],'pipeline':True,'pdfShortcuts':True}
