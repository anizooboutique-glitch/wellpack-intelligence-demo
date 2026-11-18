"""Protect the complete opportunity grid from malformed or incomplete campaign rows.
No campaign records are removed or rewritten; detailed pages and PDFs remain available.
"""
def apply(root,assets):
    h=assets['index.html']
    a=h.index('function cardMarkup(o){')
    b=h.index('function renderOps(){',a)
    # The old renderer assumed every opportunity had a populated creative.sms.
    # A single missing string aborted all rendering after the count was updated.
    safe=r'''function cardMarkup(o){
 const id=esc(String(o.id||'')),brand=esc(String(o.brand||'Enseigne à compléter'));
 const creative=o.creative||{},focus=o.focus||{},m=o.proposal||{};
 const title=esc(String(creative.title||m.concept||o.brand||'Campagne à qualifier'));
 const product=esc(String(focus.product||m.product||'Offre ou service à préciser'));
 const message=esc(String(creative.sms||m.sms||'Message à compléter et faire valider.').replaceAll('{LIEN}','[lien]').replaceAll('{STOP}','[désinscription]'));
 const channel=esc(String(m.channel||o.device||'SMS / RCS / LP'));
 const location=esc(String(o.geo||m.region||'Périmètre à confirmer'));
 let scoreText='À qualifier';
 try{if(typeof opportunityRank==='function')scoreText=String(opportunityRank(o).score)+'/100 · potentiel éditorial indicatif'}catch(err){console.warn('Score indisponible',o.id)}
 let stage='new';
 try{if(typeof opportunityStage==='function')stage=opportunityStage(o)}catch(err){}
 const stages=typeof STAGES==='object'?STAGES:{new:'À étudier',review:'À qualifier',outreach:'À contacter',sent:'Proposition envoyée',discussion:'En discussion',won:'Campagne gagnée'};
 const options=Object.entries(stages).map(([k,v])=>'<option value="'+esc(k)+'"'+(stage===k?' selected':'')+'>'+esc(v)+'</option>').join('');
 return '<article class="opcard radar-card">'+
 '<div class="opbrand"><b>'+brand+'</b><span class="tag neutral">À vérifier avant diffusion</span></div>'+
 '<h3>'+title+'</h3>'+
 '<div class="radar-offer"><b>OFFRE OU SERVICE</b><span>'+product+'</span></div>'+
 '<div class="radar-signal"><b>LOCALISATION</b><p>'+location+'</p></div>'+
 '<div class="card-message"><span>MESSAGE SMS · À ADAPTER</span><p>'+message+'</p></div>'+
 '<div class="radar-meta"><span>'+channel+'</span><span>'+esc(scoreText)+'</span></div>'+
 '<div class="wi-stage"><label>Suivi commercial</label><select data-salesstage="'+id+'">'+options+'</select></div>'+
 '<div class="opmeta"><button data-open="'+id+'" type="button">Voir la recommandation →</button>'+
 '<button type="button" class="wi-proposal-shortcut" data-propose-fast="'+id+'">Présentation PDF →</button></div>'+
 '</article>';
}
'''
    h=h[:a]+safe+h[b:]
    assert "const arr=all.filter(o=>" in h
    # Build each card separately, recording faults without blocking others.
    marker="$('opgrid').innerHTML=arr.map(cardMarkup).join('');"
    assert h.count(marker)==1
    replacement=r"""$('opgrid').innerHTML=arr.map(o=>{
  try{return cardMarkup(o)}
  catch(err){
    console.error('Wellpack carte non rendue',o.id,err);
    const id=esc(String(o.id||'')),brand=esc(String(o.brand||'Enseigne'));
    return '<article class="opcard radar-card"><h3>'+brand+'</h3><p>Cette recommandation nécessite une vérification de ses données.</p><button type="button" data-open="'+id+'">Ouvrir la recommandation →</button></article>';
  }
 }).join('');
 $('opgrid').setAttribute('data-wi-rendered-cards',String($('opgrid').querySelectorAll('.opcard').length));
 if(arr.length&&!$('opgrid').querySelector('.opcard')){
   $('opgrid').innerHTML='<div class="empty-clear"><h2>Un problème empêche d’afficher les cartes.</h2><p>Les campagnes sont conservées. Rechargez la page ou ouvrez Mes présentations.</p></div>';
 }
 """
    h=h.replace(marker,replacement,1)
    # Retain existing data-open + presentation actions, even if the previous binding was moved.
    if "$$('[data-propose-fast]').forEach" not in h:
        bind="$$('[data-open]').forEach(b=>b.onclick=()=>openDetail(b.dataset.open));"
        assert bind in h
        h=h.replace(bind,bind+"\n $$('[data-propose-fast]').forEach(b=>b.onclick=()=>openProposal(b.dataset.proposeFast));",1)
    assert 'data-wi-rendered-cards' in h
    assert 'Message à compléter et faire valider.' in h
    assert "creative.sms||m.sms" in h
    assets['index.html']=h
    return {'safeCardRendering':True,'rowIsolation':True,'renderedCountAttribute':True,'fullGrid':True}
