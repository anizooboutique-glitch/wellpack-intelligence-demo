"""Repair a persisted Intersport URL in the campaign search and reset controls.
Adds a core-app reset API; never deletes local campaign records.
"""
def apply(root,assets):
    h=assets['index.html']
    assert "function wire(){document.addEventListener('change'" in h
    assert 'id="wiResetEverything"' in h
    # A browser or old session may restore a prior campaign URL into the search field.
    # Ensure it does not strand the user in an empty filtered list.
    js="""
 function wiClearAllFilters(){
   filter={q:'',route:'',status:'active'};
   channelFocus='';stageFocus='';priorityMode='score';
   for(const [id,value] of [['search',''],['routeFilter',''],['statusFilter','active'],['wiChannel',''],['wiStage',''],['wiPriority','score']]){
     const el=$(id);if(el)el.value=value;
   }
   renderOps();
 }
 function wiRepairStaleSearch(){
   const input=$('search');if(!input)return;
   const text=String(input.value||'');
   if(/(?:https?:\\/\\/)?(?:www\\.)?intersport\\.fr\\/?/i.test(text)||/intersport\\.fr/i.test(filter.q)){
     wiClearAllFilters();
     input.setAttribute('data-wi-intersport-cleared','true');
   }
 }
 """
    anchor='function wire(){'
    h=h.replace(anchor,js+'\n'+anchor,1)
    # The reset action is attached from inside the application's own scope.
    anchor="function wire(){document.addEventListener('change'"
    assert anchor in h
    h=h.replace(anchor,"function wire(){document.getElementById('wiResetEverything')?.addEventListener('click',wiClearAllFilters);window.addEventListener('pageshow',()=>{wiRepairStaleSearch();setTimeout(wiRepairStaleSearch,100);setTimeout(wiRepairStaleSearch,650)});document.addEventListener('change'",1)
    # Handle input restoration after initial DOM setup, including browser back-forward cache.
    anchor="wire();filter={q:'',route:'',status:'active'};"
    assert anchor in h
    h=h.replace(anchor,"wire();wiClearAllFilters();setTimeout(wiRepairStaleSearch,100);filter={q:'',route:'',status:'active'};",1)
    # Stable input name stops Chrome from suggesting an unrelated store URL from history.
    anchor='id="search" autocomplete="off"'
    assert anchor in h
    h=h.replace(anchor,'id="search" name="wellpack-campaign-search" autocomplete="off" autocapitalize="off" spellcheck="false"',1)
    # Prevent the old outer reset handler from fighting the core reset handler.
    h=h.replace("document.getElementById('wiResetEverything')?.addEventListener('click',reset);","/* Handled by wiClearAllFilters inside the dashboard scope. */")
    assert "function wiClearAllFilters()" in h
    assert "wiRepairStaleSearch" in h
    assert "data-wi-intersport-cleared" in h
    assets['index.html']=h
    return {'searchRestorationFixed':True,'coreResetFilters':True,'intersportUrlCleared':True}
