"""Bounded discovery of visual assets declared in public brand pages.

No credential forwarding, no scraper bypass, no persistent uploads. Each returned
image is traceable to a page actually fetched from the brand website.
"""
from __future__ import annotations
import asyncio
import base64
import ipaddress
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
import httpx
from .net import SafeHTTP, FetchError, canonical, resolve_public, AGENT

MAX_IMAGE_BYTES=2_400_000
MAX_CANDIDATES=18
TTL=900
TOKENS:dict[str,tuple[float,str,str,str]]={}
LOCK=asyncio.Lock()

def clean(v,n=160):
    return re.sub(r'\s+',' ',str(v or '')).strip()[:n]

def picture_url(base,raw):
    try:
        value=clean(raw,1900)
        if not value or value.startswith(('data:','blob:')):return None
        url=canonical(urljoin(base,value))
        if re.search(r'\.(svg|gif|pdf|mp4|avif)(?:\?|$)',url,re.I):return None
        return url
    except (ValueError,FetchError):return None

def image_candidates(html,page_url,query=''):
    soup=BeautifulSoup(html,'html.parser')
    found:dict[str,dict]={}
    terms=[s for s in re.split(r'[\W_]+',query.casefold()) if len(s)>3][:16]
    def add(raw,description='',rank=0):
        url=picture_url(page_url,raw)
        if not url:return
        label=clean(description)
        text=(label+' '+urlsplit(url).path).casefold()
        if re.search(r'favicon|logo[-_.]|icon[-_.]|sprite|tracking|pixel|transparent|placeholder|flags|payment|badge',text):return
        score=rank+sum(12 for t in terms if t in text)
        if re.search(r'produit|product|packshot|collection|visuel|hero|banner|banni[eè]re|boutique',text):score+=7
        old=found.get(url)
        if old is None or score>old['score']:
            found[url]={'url':url,'label':label or 'Visuel de la page','sourcePage':page_url,'score':score}
    for item in soup.select('meta[property="og:image"],meta[name="twitter:image"],meta[property="og:image:secure_url"]')[:12]:
        add(item.get('content'),'Image de partage',38)
    for img in soup.select('main img,article img,[class*=product] img,[class*=hero] img,img')[:350]:
        label=img.get('alt') or img.get('title') or ''
        if img.get('width') and str(img.get('width')).isdigit() and int(img['width'])<160:continue
        if img.get('height') and str(img.get('height')).isdigit() and int(img['height'])<100:continue
        for att in ('data-src','data-original','data-lazy-src','src'):
            if img.get(att):add(img.get(att),label,16);break
        srcset=img.get('srcset') or img.get('data-srcset') or ''
        if srcset:
            entries=[chunk.strip().split(' ')[0] for chunk in srcset.split(',') if chunk.strip()]
            if entries:add(entries[-1],label,20)
    for script in soup.select('script[type="application/ld+json"]')[:15]:
        try:
            import json
            obj=json.loads(script.string or script.get_text())
        except (ValueError,TypeError):continue
        stack=[obj]
        while stack:
            x=stack.pop()
            if isinstance(x,list):stack.extend(x[:45]);continue
            if not isinstance(x,dict):continue
            name=clean(x.get('name',''))
            imgs=x.get('image') or x.get('thumbnailUrl')
            if isinstance(imgs,str):add(imgs,name,34)
            elif isinstance(imgs,list):
                for v in imgs[:10]:
                    if isinstance(v,str):add(v,name,34)
                    elif isinstance(v,dict):add(v.get('url') or v.get('contentUrl'),name,34)
            for key in ('@graph','offers','hasPart','mainEntity'):
                if key in x:stack.append(x[key])
    return sorted(found.values(),key=lambda x:-x['score'])[:MAX_CANDIDATES]

async def discover(website,extra='',query=''):
    first=canonical(website)
    pages=[first]
    if extra:
        second=canonical(extra)
        if urlsplit(second).hostname==urlsplit(first).hostname and second!=first:
            pages.insert(0,second)
    reader=SafeHTTP()
    images=[];seen=set();warnings=[]
    try:
        for page in pages[:2]:
            try:
                response=await asyncio.wait_for(reader.get(page),timeout=19)
                if response.status!=200:raise FetchError('Page HTTP '+str(response.status))
                if not any(v in response.content_type for v in ('html','xml')):raise FetchError('Page non HTML')
                for item in image_candidates(response.text,response.url,query):
                    if item['url'] not in seen:
                        images.append(item);seen.add(item['url'])
            except (FetchError,asyncio.TimeoutError) as exc:
                warnings.append(page+' : '+str(exc))
    finally:await reader.close()
    images=sorted(images,key=lambda x:-x['score'])[:MAX_CANDIDATES]
    async with LOCK:
        now=time.monotonic()
        for key,record in list(TOKENS.items()):
            if record[0]<now:del TOKENS[key]
        if len(TOKENS)>250:
            for key in list(TOKENS)[:len(TOKENS)-220]:del TOKENS[key]
        for i in images:
            token=secrets.token_urlsafe(24)
            TOKENS[token]=(now+TTL,i['url'],i['sourcePage'],i['label'])
            i['token']=token
            i.pop('score',None)
    return {'images':images,'warnings':warnings,'sourceCount':len(pages),'rights':'Images issues de pages publiques : droits et utilisation commerciale à valider auprès de la marque.'}

async def import_image(token):
    async with LOCK:
        record=TOKENS.get(token)
        if not record or record[0]<time.monotonic():
            raise FetchError('Sélection expirée : relancez la recherche de photos.')
        _,url,page,label=record
    # No raw URL from callers: only a recent asset directly discovered in public HTML.
    client=httpx.AsyncClient(timeout=httpx.Timeout(12,connect=6),trust_env=False,follow_redirects=False)
    reader=SafeHTTP()
    try:
        current=canonical(url)
        origin=urlsplit(page).hostname
        for _ in range(4):
            p=urlsplit(current)
            allowed,reason=await reader.allowed(current)
            if not allowed:raise FetchError(reason)
            ips=await resolve_public(p.hostname,443 if p.scheme=='https' else 80)
            target=httpx.URL(current).copy_with(host=ips[0])
            try:
                async with client.stream('GET',target,headers={'Host':p.hostname,'User-Agent':AGENT,'Accept':'image/jpeg,image/png,image/webp'},extensions={'sni_hostname':p.hostname}) as res:
                    if res.status_code in (301,302,303,307,308):
                        location=res.headers.get('location')
                        if not location:raise FetchError('Redirection image sans destination.')
                        current=canonical(urljoin(current,location));continue
                    if res.status_code!=200:raise FetchError('Photo inaccessible (HTTP '+str(res.status_code)+').')
                    kind=res.headers.get('content-type','').lower().split(';')[0].strip()
                    if kind not in ('image/jpeg','image/png','image/webp'):
                        raise FetchError('Format de photo non pris en charge.')
                    data=bytearray()
                    async for chunk in res.aiter_bytes():
                        data.extend(chunk)
                        if len(data)>MAX_IMAGE_BYTES:raise FetchError('Photo trop lourde (limite 2,4 Mo).')
                    binary=bytes(data)
                    magic=(kind=='image/jpeg' and binary.startswith(b'\xff\xd8\xff')) or (kind=='image/png' and binary.startswith(b'\x89PNG\r\n\x1a\n')) or (kind=='image/webp' and binary.startswith(b'RIFF') and binary[8:12]==b'WEBP')
                    if not magic:raise FetchError('Contenu de photo non conforme au format annoncé.')
                    return {'imageData':'data:'+kind+';base64,'+base64.b64encode(binary).decode('ascii'),
                            'url':current,'sourcePage':page,'label':label,'rights':'Utilisation commerciale et droits visuels à confirmer.'}
            except httpx.HTTPError as exc:
                raise FetchError('Téléchargement de photo impossible : '+type(exc).__name__) from exc
        raise FetchError('Trop de redirections pour cette photo.')
    finally:
        await client.aclose();await reader.close()
