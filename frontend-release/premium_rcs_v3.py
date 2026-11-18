"""Upgrade RCS presentation page with three distinct premium, brand-led mockups.
No external assets or credentials; only visual layer changes, existing editor retained.
"""
from pathlib import Path

def apply(root,assets):
    h=assets['index.html']
    src=Path(root)/'frontend-release'
    css=(src/'premium_rcs_v3.css').read_text(encoding='utf-8')
    js=(src/'premium_rcs_v3.js').read_text(encoding='utf-8')
    assert 'window.WIRCS.render(op,m)' not in h, 'Must keep prior SMS/RCS/LP routing'
    assert 'window.WIChannels.render(op,m)' in h
    assert 'window.WIRCS=' in h
    assert 'window.WIChannels=' in h
    assert 'Personnaliser les cartes RCS' in h
    assert '<style id="rcs-studio-style">' in h
    h=h.replace('</head>','<style id="premium-rcs-v3-style">'+css+'</style><script id="premium-rcs-v3-script">'+js+'</script></head>',1)
    assert 'prem-pitch' in h and 'prem-row' in h and 'WIPremiumRCS' in h
    assets['index.html']=h
    return {'premiumRCS':True,'rcsDesignModes':['promo','service','local'],'fullCarouselOnPDF':True,'smsAndLPUnchanged':True}
