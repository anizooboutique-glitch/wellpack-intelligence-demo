"""Three sales-document formats without changing recommendation data or API.
The existing four-page PDF remains the default; other formats are selectable.
"""
from pathlib import Path

def apply(root,assets):
    folder=Path(root)/'frontend-release'
    css=(folder/'pitch_formats_v1.css').read_text(encoding='utf-8')
    js=(folder/'pitch_formats_v1.js').read_text(encoding='utf-8')
    h=assets['index.html']
    assert 'window.WIProposal={mount,print,checkLayout' in h
    assert 'window.WIPremiumRCS' in h
    assert 'brand-image-library-script' in h
    assert 'id="proposalPages"' in h
    assert '</body>' in h
    h=h.replace('</head>','<style id="wi-formats-v1-style">'+css+'</style></head>',1)
    h=h.replace('</body>','<script id="wi-formats-v1-script">'+js+'</script></body>',1)
    assert 'wf-mode-switch' in h and 'pitch_formats' not in h
    assert "window.WIProposal" in h and 'BRIEF' not in h[:500]
    assets['index.html']=h
    return {'salesFormats':['creative-4','express-2','internal-brief-2'],'qualityLayoutCheck':True,'editableFormats':True}
