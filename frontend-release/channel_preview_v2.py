"""Render the actual chosen SMS/RCS/LP channel in proposal page 3.
Prevents confusing a proposed SMS campaign with an RCS recommendation.
"""
from pathlib import Path

def apply(root,assets):
    h=assets['index.html']
    root=Path(root)/'frontend-release'
    css=(root/'channel-preview.css').read_text(encoding='utf-8')
    js=(root/'channel-preview.js').read_text(encoding='utf-8')
    needle='window.WIRCS.render(op,m)'
    assert h.count(needle)==1,'Unexpected PDF preview renderer'
    h=h.replace(needle,'window.WIChannels.render(op,m)',1)
    assert '</head>' in h
    h=h.replace('</head>','<style id="wi-channel-preview">'+css+'</style><script>'+js+'</script></head>',1)
    # Expiry checks do not claim sources were re-verified after the recorded date.
    old='function issues(){if(!op||!m)return [];const a=[];'
    assert old in h
    h=h.replace(old,old+"""
  if(m.sourceType!=='client' && (op.evidence||[]).some(e=>e.url&&e.validUntil&&E.validDate(e.validUntil)&&e.validUntil<settings.date))
    a.push('Une source de cette recommandation a dépassé sa date de vérification. Recontrôler les faits, le stock et les conditions avant diffusion.');
""",1)
    assert 'window.WIChannels.render(op,m)' in h
    assert 'wi-channel-landing' in h
    assert 'date de vérification' in h
    assets['index.html']=h
    return {'trueChannelPreview':True,'smsLpMockup':True,'rcsUnchanged':True,'staleSourceWarning':True}
