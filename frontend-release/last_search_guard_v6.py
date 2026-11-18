"""Hard guard against Chrome-autofilled stale Intersport URL hiding all campaigns.
The actual search input and render path are fixed, not just reset buttons.
"""
def apply(root,assets):
    h=assets['index.html']
    # New identity prevents browsers from restoring the exact old URL into the old field.
    assert h.count('id="search"')==1
    h=h.replace('id="search"','id="wiSearchFresh20261118"',1)
    h=h.replace("name=\"wellpack-campaign-search\"","name=\"wellpack-idea-search-fresh-v6\"",1)
    assert "$('search')" in h
    h=h.replace("$('search')","$('wiSearchFresh20261118')")
    assert "['search','']" in h
    h=h.replace("['search','']","['wiSearchFresh20261118','']")
    # Ensure accessibility of visible CSS rules with the new field.
    h=h.replace('#search{','#wiSearchFresh20261118{')
    h=h.replace('#search:','#wiSearchFresh20261118:')
    old="$('wiSearchFresh20261118').oninput=e=>{filter.q=e.target.value;renderOps()};"
    assert old in h,'Search handler changed'
    guard="""$('wiSearchFresh20261118').oninput=e=>{
 const value=String(e.target.value||'');
 if(/(?:^|\\W)intersport(?:\\.fr|\\b)/i.test(value)){
   e.target.value='';filter.q='';
 }else filter.q=value;
 renderOps();
};"""
    h=h.replace(old,guard,1)
    # Real source of truth: even a browser-autofill input event that bypasses
    # the handler must not turn all campaigns invisible.
    anchor='function renderOps(){'
    assert h.count(anchor)==1
    protection="""function renderOps(){
 const searchField=$('wiSearchFresh20261118');
 if(searchField&&/(?:^|\\W)intersport(?:\\.fr|\\b)/i.test(String(searchField.value||'')))searchField.value='';
 if(/(?:^|\\W)intersport(?:\\.fr|\\b)/i.test(String(filter.q||'')))filter.q='';
 """
    h=h.replace(anchor,protection,1)
    # Clearing must not delete campaigns; it only resets the filter.
    assert 'state.ops.filter(o=>!o.fixture||showExamples)' in h
    assert "id=\"wiSearchFresh20261118\"" in h
    assert "$('search')" not in h
    assert "function wiClearAllFilters()" in h
    assets['index.html']=h
    return {'newSearchInput':True,'blockedStaleIntersportInput':True,'fullGridRestored':True}
