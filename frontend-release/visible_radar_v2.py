"""Prominent v2 radar homepage, immediate actionable campaign links and dynamic stats."""
def apply(root,assets):
    h=assets['index.html']
    # Entirely additive homepage: existing navigation, forms, state and presentations remain intact.
    anchor='<div class="campaign-status" id="connectionNotice">'
    assert anchor in h
    hero='''<section class="wi-v2-radar" aria-label="Radar commercial version 2">
    <div class="wi-v2-top"><span class="wi-v2-eyebrow"><span class="wi-v2-pulse"></span> NOUVEAU · RADAR COMMERCIAL</span><span class="wi-v2-tag">Démonstration · veille automatique désactivée</span></div>
    <div class="wi-v2-head"><div><h2>Les bonnes enseignes.<br>Au bon moment.</h2><p>Prospection assistée · Campagnes SMS, RCS et LP · Opportunités locales classées pour vos équipes.</p></div><button type="button" class="wi-v2-cta" id="wiExploreNow">Explorer les opportunités <span aria-hidden="true">↗</span></button></div>
    <div class="wi-v2-statbar"><div><strong id="wiTotalActive">—</strong><span>Campagnes à qualifier</span></div><div><strong id="wiLocalCount">—</strong><span>Scénarios locaux</span></div><div><strong>3</strong><span>Leviers : SMS · RCS · LP</span></div></div>
    <div class="wi-v2-feature-top"><div><b>LES OPPORTUNITÉS À EXAMINER</b><span>Priorisation éditoriale indicative · validation humaine obligatoire</span></div><button class="wi-v2-all" type="button" id="wiAllIdeas">Toutes les campagnes ↓</button></div>
    <div class="wi-v2-feature-list" id="wiFeatured" aria-live="polite"><p>Chargement des campagnes…</p></div>
    </section>'''
    h=h.replace(anchor,hero+anchor,1)
    assert '<div class="topright">' in h
    h=h.replace('<span class="tag gray">Moteur local requis</span>','<span class="tag gray">Démo · Recherche IA inactive</span>',1)
    h=h.replace('Prototype 3.0 · démo & analyse','Prototype 3.1 · radar commercial · démo',1)
    # Feature top opportunities are computed from the same locally persisted state as cards.
    marker="const jobs=backendJobs.filter(j=>['queued','running'].includes(j.state));"
    assert marker in h
    injection="""const wiActive=all.filter(o=>!o.archived),wiRegional=wiActive.filter(o=>o.id?.startsWith('test-20261118-local-'));
 const wiTotal=$('wiTotalActive'),wiLocal=$('wiLocalCount'),wiFeatured=$('wiFeatured');
 if(wiTotal)wiTotal.textContent=String(wiActive.length);
 if(wiLocal)wiLocal.textContent=String(wiRegional.length);
 if(wiFeatured){
  const picks=wiActive.slice().sort((a,b)=>opportunityRank(b).score-opportunityRank(a).score).slice(0,3);
  wiFeatured.innerHTML=picks.length?picks.map((o,i)=>{
   const p=opportunityRank(o),ch=opportunityChannel(o),location=o.geo||o.proposal?.region||'Périmètre à préciser';
   return `<div class="wi-v2-pick">
     <div class="wi-v2-number">${String(i+1).padStart(2,'0')}</div>
     <div class="wi-v2-pick-info"><span class="wi-v2-brand">${esc(o.brand)}</span><h3>${esc(o.creative.title)}</h3><p>${esc(location)} · ${esc(ch)}</p></div>
     <div class="wi-v2-pick-action"><span title="Score éditorial indicatif">${p.score}/100</span><button type="button" data-wi-v2-detail="${esc(o.id)}">Voir le brief ↗</button><button type="button" data-wi-v2-pdf="${esc(o.id)}">Présentation PDF ↗</button></div>
   </div>`
  }).join(''):'<p>Aucune campagne active. Ajoutez une marque pour commencer.</p>';
  wiFeatured.querySelectorAll('[data-wi-v2-detail]').forEach(b=>b.onclick=()=>openDetail(b.dataset.wiV2Detail));
  wiFeatured.querySelectorAll('[data-wi-v2-pdf]').forEach(b=>b.onclick=()=>openProposal(b.dataset.wiV2Pdf));
 }
 """
    h=h.replace(marker,marker+'\n '+injection,1)
    # Stable, visible navigation to filters, not a decorative inert CTA.
    action="""const wiJump=()=>document.getElementById('ideaListHeading')?.scrollIntoView({behavior:'smooth',block:'start'});
document.getElementById('wiExploreNow')?.addEventListener('click',wiJump);
document.getElementById('wiAllIdeas')?.addEventListener('click',wiJump);"""
    h=h.replace('</body>','<script>'+action+'</script></body>',1)
    css='''<style id="wi-v2-visible-radar">
.wi-v2-radar{position:relative;margin:0 0 25px;padding:28px;border:1px solid #262626;border-radius:19px;background:#181818;color:#fff;overflow:hidden;box-shadow:0 12px 25px rgba(0,0,0,.09)}
.wi-v2-radar:before{content:"";position:absolute;right:-120px;top:-160px;width:410px;height:380px;border-radius:50%;background:radial-gradient(circle,rgba(249,231,17,.15),transparent 63%);pointer-events:none}
.wi-v2-top{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:10px;letter-spacing:1.35px}
.wi-v2-eyebrow{font-weight:800;color:#f5e822;display:flex;align-items:center;gap:9px}
.wi-v2-pulse{width:8px;height:8px;border-radius:50%;background:#f5e822;box-shadow:0 0 0 4px rgba(245,232,34,.16)}
.wi-v2-tag{font-weight:600;letter-spacing:0;color:#bcbcbc}
.wi-v2-head{position:relative;display:flex;gap:20px;justify-content:space-between;align-items:flex-end;margin:20px 0 23px}
.wi-v2-head h2{font-size:clamp(28px,3.6vw,48px);font-weight:850;line-height:1.04;letter-spacing:-1.7px;margin:0 0 12px}
.wi-v2-head p{font-size:13px;line-height:1.65;color:#ccc;max-width:510px;margin:0}
.wi-v2-cta{white-space:nowrap;background:#f5e822;color:#161616;padding:14px 18px;border:0;border-radius:10px;font-size:12px;font-weight:850;cursor:pointer}
.wi-v2-cta span{padding-left:10px}
.wi-v2-statbar{display:grid;grid-template-columns:1fr 1fr 1fr;border-top:1px solid #434343;border-bottom:1px solid #434343}
.wi-v2-statbar>div{padding:18px 20px 18px 0;display:flex;flex-direction:column;gap:3px}
.wi-v2-statbar>div+div{border-left:1px solid #434343;padding-left:20px}
.wi-v2-statbar strong{font-size:28px;line-height:1.1;font-weight:850;color:#f5e822}
.wi-v2-statbar span{font-size:11px;color:#c6c6c6}
.wi-v2-feature-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:22px 0 12px}
.wi-v2-feature-top>div{display:flex;flex-direction:column;gap:4px}
.wi-v2-feature-top b{font-size:11px;letter-spacing:1.1px}
.wi-v2-feature-top span{font-size:11px;color:#aaa}
.wi-v2-all{background:none;color:#f5e822;font-size:11px;border:0;cursor:pointer}
.wi-v2-feature-list{display:flex;flex-direction:column;gap:8px}
.wi-v2-pick{display:grid;grid-template-columns:42px 1fr auto;gap:13px;align-items:center;background:#242424;border:1px solid #414141;border-radius:10px;padding:14px 16px}
.wi-v2-number{font-size:19px;color:#dedede;font-weight:750}
.wi-v2-brand{font-size:11px;color:#f5e822;font-weight:800}
.wi-v2-pick-info h3{margin:3px 0 4px;font-size:13px!important;letter-spacing:-.1px;line-height:1.35;color:#fff}
.wi-v2-pick-info p{color:#c0c0c0;font-size:11px;margin:0;overflow-wrap:anywhere}
.wi-v2-pick-action{display:flex;flex-direction:column;align-items:end;gap:5px}
.wi-v2-pick-action span{color:#f5e822;font-size:12px;font-weight:750}
.wi-v2-pick-action button{background:none;border:0;color:#fff;font-size:11px;text-decoration:underline;text-underline-offset:3px;cursor:pointer;text-align:right}
@media(max-width:800px){.wi-v2-radar{padding:20px}.wi-v2-head{flex-direction:column;align-items:start}.wi-v2-statbar strong{font-size:22px}.wi-v2-pick{grid-template-columns:27px 1fr}.wi-v2-pick-action{grid-column:2;align-items:start;flex-direction:row;flex-wrap:wrap;gap:12px}.wi-v2-top{align-items:start;flex-direction:column}}
@media(max-width:500px){.wi-v2-statbar>div{padding:12px 7px}.wi-v2-statbar>div+div{padding-left:8px}.wi-v2-head h2{font-size:31px}.wi-v2-feature-top{flex-direction:column;align-items:start}}
</style>'''
    h=h.replace('</head>',css+'</head>',1)
    assert 'NOUVEAU · RADAR COMMERCIAL' in h and 'id="wiFeatured"' in h
    assert 'data-wi-v2-pdf' in h and 'opportunityRank(b).score' in h
    assets['index.html']=h
    return {'visibleRadar':True,'featuredOpportunities':3,'visibleVersion':'3.1'}
