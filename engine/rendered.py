"""Optional reader; never bypass robots, access refusals or logins."""
import httpx
from urllib.parse import urlsplit
from . import config
from .net import SafeHTTP,Page,FetchError,canonical,resolve_public,MAX_BYTES
class ResearchHTTP(SafeHTTP):
    def __init__(self):super().__init__();self.render_calls=0
    async def render(self,url):
        if not config.get('FIRECRAWL_API_KEY') or self.render_calls>=3:return None
        url=canonical(url)
        allowed,reason=await self.allowed(url)
        if not allowed:raise FetchError(reason)
        p=urlsplit(url);await resolve_public(p.hostname,443 if p.scheme=='https' else 80)
        config.reserve('firecrawl');self.render_calls+=1
        async with httpx.AsyncClient(timeout=50,trust_env=False,follow_redirects=False) as client:
            try:r=await client.post('https://api.firecrawl.dev/v2/scrape',headers={'Authorization':'Bearer '+config.get('FIRECRAWL_API_KEY')},json={'url':url,'formats':['rawHtml'],'onlyMainContent':False,'timeout':30000,'maxAge':0,'proxy':'basic'})
            except httpx.HTTPError as exc:raise FetchError('Lecture enrichie indisponible.') from exc
        if r.status_code!=200:raise FetchError('Lecture enrichie indisponible (HTTP '+str(r.status_code)+').')
        data=r.json().get('data',{});meta=data.get('metadata',{})
        status=int(meta.get('statusCode',200))
        if status!=200:raise FetchError('Le site refuse la lecture enrichie.')
        final=canonical(meta.get('sourceURL') or url)
        p=urlsplit(final);await resolve_public(p.hostname,443 if p.scheme=='https' else 80)
        allowed,reason=await self.allowed(final)
        if not allowed:raise FetchError(reason)
        html=data.get('rawHtml') or data.get('html') or ''
        if len(html.encode())>MAX_BYTES:raise FetchError('Page enrichie trop volumineuse.')
        return Page(final,200,html) if html else None
