"""Enrich presentation mockups with brand-specific RCS and editable media.
Does not change the recommended channel, promotions, approvals or paid APIs.
"""
from pathlib import Path

def apply(root, assets):
    path=Path(root)/'frontend-release'
    css=(path/'rcs-studio.css').read_text(encoding='utf-8')
    js=(path/'rcs-studio.js').read_text(encoding='utf-8')
    # Upload previews must use data URLs: the live CSP intentionally forbids blob URLs.
    old="const url=URL.createObjectURL(f),img=new Image();"
    new="const url=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Lecture du fichier impossible.'));reader.readAsDataURL(f)}),img=new Image();"
    assert old in js
    js=js.replace(old,new,1)
    h=assets['index.html']
    assert 'window.WIRCS=' not in h
    # Keep the existing model and sanitization: additional field is explicitly allowed.
    assert h.count('rcsTitle:100,rcsBody:300,rcsCTA:35')==2
    h=h.replace('rcsTitle:100,rcsBody:300,rcsCTA:35','rcsTitle:100,rcsBody:300,rcsCTA:35,rcsCardsJSON:2400000')
    h=h.replace("reason:prospectReason(o,o.device||E.recommend(o).choice),rcsTitle:","rcsCardsJSON:'',reason:prospectReason(o,o.device||E.recommend(o).choice),rcsTitle:",1)
    # Render in the same four-page document, using the full original carousel.
    a=h.index("  const p3=sheet(3,'doc-experience',")
    b=h.index("  const p4=sheet(4,",a)
    h=h[:a]+"  const p3=sheet(3,'doc-experience',window.WIRCS.render(op,m),draft);\n"+h[b:]
    anchor="  renderStatus();markSaved();\n }\n function pageBar"
    assert anchor in h
    h=h.replace(anchor,"  window.WIRCS.mountEditor($('proposalForm'),op,m,changed);\n"+anchor,1)
    # Better strategy-page visual, explicitly labelled as proposed graphic artwork.
    old="function imagePanel(cls=''){return"
    new="function imagePanel(cls=''){if(!m.imageData&&!cls)return `<div class=\"doc-visual\">${window.WIRCS.hero(op,m)}</div>`;return"
    assert old in h
    h=h.replace(old,new,1)
    old="if(!m.imageData)a.push('Ajouter un visuel approuvé pour illustrer le RCS.');"
    new="if(!window.WIRCS.cards(op,m).every(c=>!!c.imageData))a.push('Ajouter les visuels approuvés des cartes RCS.');if(window.WIRCS.cards(op,m).some(c=>String(c.cta||'').length>25))a.push('Raccourcir les boutons RCS à 25 caractères maximum.');"
    assert old in h
    h=h.replace(old,new,1)
    # Reset the interactive preview for print so every card appears exactly once.
    h=h.replace("function print(){if(!m)return;changed();", "async function print(){if(!m)return;window.WIRCS.reset(op.id);changed();await Promise.race([Promise.all(Array.from(document.querySelectorAll('#proposalPages img')).map(i=>i.decode?i.decode().catch(()=>{}):Promise.resolve())),new Promise(r=>setTimeout(r,1200))]);",1)
    assert '</head>' in h
    h=h.replace('</head>','<style id="rcs-studio-style">'+css+'</style><script>'+js+'</script></head>',1)
    assert 'rcsCardsJSON:2400000' in h and 'window.WIRCS.render(op,m)' in h
    assets['index.html']=h
    return {'rcsShowcase':True,'brandThemes':15,'editableCarousel':True}
