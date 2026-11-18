"""Repair homepage navigation and filters; preserve local edits and campaign data."""
import re
def apply(root,assets):
    h=assets['index.html']
    # The three-item showcase was an opaque extra layer before the full campaign grid.
    start=h.index('<section class="wi-v2-radar"')
    end=h.index('</section>',start)+len('</section>')
    banner='''<div class="wi-fixed-overview" id="wiOverview">
    <div><span class="wi-fixed-eyebrow">WELLPACK INTELLIGENCE · RADAR COMMERCIAL</span>
      <h2>Vos opportunités de campagnes</h2>
      <p><strong id="wiTotalActive">—</strong> campagnes disponibles, dont <strong id="wiLocalCount">—</strong> propositions locales · SMS, RCS et LP</p>
    </div>
    <div class="wi-fixed-actions"><button type="button" id="wiExploreNow">Voir toutes les campagnes ↓</button><button type="button" id="wiResetEverything">Réinitialiser tous les filtres</button></div>
    </div>'''
    h=h[:start]+banner+h[end:]
    # Internal filter variables and renderOps live inside the first IIFE.
    # The previously appended second script cannot access them and raises ReferenceError.
    stale=re.search(r'<script>(document\.addEventListener\(\x27change\x27,e=>\{if\(e\.target\.id===\x27wiChannel\x27\).*?\}\);)</script>',h,re.S)
    assert stale,'Could not identify broken external filter binding'
    change_handler=stale.group(1)
    h=h[:stale.start()]+h[stale.end():]
    assert 'function wire(){' in h
    h=h.replace('function wire(){','function wire(){'+change_handler,1)
    # A browser restoring the old search input must not show stale Intersport text.
    h=h.replace('id="search" placeholder=', 'id="search" autocomplete="off" placeholder=',1)
    boot="wire();$('radarCoverageBtn').onclick=openCoverage;"
    assert boot in h
    h=h.replace(boot,"wire();filter={q:'',route:'',status:'active'};$('search').value='';$('routeFilter').value='';$('statusFilter').value='active';"+boot[len('wire();'):],1)
    # Intersport was deleted previously, but the one-time deletion migrator did
    # not handle older copies restored later or a subsequent backend resync.
    marker='function pruneManaged(){'
    assert marker in h
    h=h.replace(marker,marker+"""
 for(const c of state.clients.filter(isOldIntersport))markRemoved(c.id);
 for(const o of state.ops.filter(isOldIntersport))if(o.clientId)markRemoved(o.clientId);
 state.ops=state.ops.filter(o=>!isOldIntersport(o));
 """,1)
    # Ensure the existing list is visible and stays in normal document flow.
    css='''<style id="wi-home-repair">
@media screen{html,body{min-height:100%;height:auto!important;overflow-y:auto!important}#page-opportunities{overflow:visible!important}#ideaListHeading{scroll-margin-top:22px}}
.wi-fixed-overview{margin:5px 0 20px;padding:20px 23px;border:1px solid #323232;border-radius:16px;background:#202020;color:#fff;display:flex;align-items:center;justify-content:space-between;gap:16px}
.wi-fixed-eyebrow{font-size:10px;letter-spacing:1.4px;color:#f8e535;font-weight:800}
.wi-fixed-overview h2{font-size:24px;margin:7px 0 3px;letter-spacing:-.5px;color:#fff;line-height:1.25}
.wi-fixed-overview p{font-size:12px;color:#d5d5d5;margin:3px 0}
.wi-fixed-overview strong{color:#f8e535;font-size:14px}
.wi-fixed-actions{display:flex;gap:9px;flex-wrap:wrap}
.wi-fixed-actions button{border-radius:9px;padding:12px 14px;border:1px solid #727272;cursor:pointer;background:transparent;color:#fff;font-size:12px;font-weight:650}
.wi-fixed-actions button:first-child{background:#f8e535;color:#181818;border-color:#f8e535;font-weight:800}
#campaignFilters{display:flex;flex-wrap:wrap!important;gap:9px}#campaignFilters[hidden]{display:none!important}
@media(max-width:790px){.wi-fixed-overview{align-items:flex-start;flex-direction:column;padding:18px}.wi-fixed-overview h2{font-size:21px}}
</style>'''
    assert '</head>' in h
    h=h.replace('</head>',css+'</head>',1)
    # Button actions only touch browser input events: no access to the IIFE is required.
    handler='''<script id="wi-home-fix-actions">(()=>{
const scroll=()=>{const list=document.getElementById('ideaListHeading');if(list){list.hidden=false;list.scrollIntoView({behavior:'smooth',block:'start'})}else window.scrollTo({top:0,behavior:'smooth'})};
const reset=()=>{
 const configs=[['search','','input'],['routeFilter','','change'],['statusFilter','active','change'],['wiChannel','','change'],['wiStage','','change'],['wiPriority','score','change']];
 configs.forEach(([id,value,type])=>{const el=document.getElementById(id);if(!el)return;el.value=value;el.dispatchEvent(new Event(type,{bubbles:true}))});
 scroll();
};
document.getElementById('wiResetEverything')?.addEventListener('click',reset);
document.getElementById('wiExploreNow')?.addEventListener('click',scroll);
})();</script>'''
    h=h.replace('</body>',handler+'</body>',1)
    assert 'id="wiFixedThree"' not in h
    assert '<section class="wi-v2-radar"' not in h
    assert 'id="wiResetEverything"' in h
    assert "function wire(){document.addEventListener('change'" in h
    assert h.count('id="search"')==1
    assets['index.html']=h
    return {'fixedHomepage':True,'brokenFilterScopeRepaired':True,'clearFilters':True,'scrollRestored':True,'intersportPermanentlyExcluded':True}
