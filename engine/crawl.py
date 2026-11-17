"""Bounded catalogue/site discovery + separate, explicitly unverified RSS headlines."""
from __future__ import annotations
import re,json,hashlib,unicodedata
from datetime import datetime,timezone,timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin,urlsplit,quote
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from .net import SafeHTTP,FetchError,canonical

def now():return datetime.now(timezone.utc).isoformat()
def norm(s):return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()).strip()
def compact(s,limit=1000):return re.sub(r'\s+',' ',BeautifulSoup(str(s),'html.parser').get_text(' ',strip=True)).strip()[:limit]
def uid(*parts):return hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()[:20]
def same_host(a,b):return urlsplit(a).hostname.removeprefix('www.')==urlsplit(b).hostname.removeprefix('www.')

def objects(value):
    if isinstance(value,list):
        for v in value:yield from objects(v)
    elif isinstance(value,dict):
        yield value
        for v in value.values():
            if isinstance(v,(dict,list)):yield from objects(v)

def source(kind,title,url,excerpt,**extra):
    return dict(id=uid(kind,url,title),kind=kind,title=compact(title,180),url=url,excerpt=compact(excerpt,900),observedAt=now(),**extra)

def extract(html,url):
    soup=BeautifulSoup(html,'html.parser')
    title=compact(soup.title.get_text() if soup.title else url,180)
    products=[];articles=[]
    for node in soup.select('script[type="application/ld+json"]')[:30]:
        try:data=json.loads(node.string or node.get_text())
        except (ValueError,TypeError):continue
        for o in objects(data):
            types=o.get('@type',[]);types=[types] if isinstance(types,str) else types
            if not isinstance(types,list):continue
            if any(t in types for t in ('Product','Service')):
                name=compact(o.get('name',''),180);description=compact(o.get('description',''),900)
                if len(name)<4 or not description:continue
                link=url
                try:
                    candidate=canonical(urljoin(url,str(o.get('url') or '')))
                    if same_host(url,candidate):link=candidate
                except FetchError:pass
                offers=o.get('offers',{});offers=offers if isinstance(offers,list) else [offers]
                avail=next((str(v.get('availability','')).split('/')[-1] for v in offers if isinstance(v,dict) and v.get('availability')),'unknown')
                products.append(source('service' if 'Service' in types else 'product',name,link,description,format='schema.org',availability=avail,pageURL=url))
            if any(t in types for t in ('NewsArticle','BlogPosting','Article')):
                date=str(o.get('datePublished',''))[:10]
                if re.match(r'^\d{4}-\d{2}-\d{2}$',date):
                    articles.append(source('brand_news',o.get('headline') or o.get('name') or title,url,o.get('description') or o.get('headline') or title,publishedAt=date,format='schema.org',verifiedContent=True))
    for n in soup(['script','style','noscript','svg','nav','footer','header']):n.decompose()
    main=soup.find('main') or soup
    text=compact(main.get_text(' ',strip=True),18000)
    h1=main.find('h1');desc=soup.find('meta',attrs={'name':'description'})
    path=norm(urlsplit(url).path)
    if not products and h1 and desc and re.search(r'\b(products?|produits?|services?|prestations?)\b',path):
        name=compact(h1.get_text(),180);description=compact(desc.get('content',''),900)
        if len(description)>35 and name and not re.fullmatch(r'(nos )?(produits|services|prestations)',norm(name)):
            products.append(source('service' if re.search(r'\b(services?|prestations?)\b',path) else 'product',name,url,description,format='html-explicit',availability='unknown',pageURL=url))
    articles=[a for a in articles if len(norm(a['excerpt']))>=20 and norm(a['excerpt']) in norm(text)]
    links=[]
    for a in BeautifulSoup(html,'html.parser').select('a[href]')[:1800]:
        try:u=canonical(urljoin(url,a['href']))
        except FetchError:continue
        if not same_host(u,url) or re.search(r'\.(pdf|jpg|png|zip|mp4)(\?|$)',u,re.I):continue
        label=norm(a.get_text(' ',strip=True)+' '+urlsplit(u).path)
        if re.search(r'\b(login|account|cart|panier|connexion|privacy|mentions|cgv|wishlist)\b',label):continue
        weight=0
        if re.search(r'\b(products?|produits?|services?|prestations?)\b',label):weight+=6
        if re.search(r'\b(collections?|catalogue|categories?|nouveautes?|nouveau|new)\b',label):weight+=4
        if re.search(r'\b(actualites?|news|blog|presse)\b',label):weight+=3
        if weight:links.append((weight,u))
    links=list(dict.fromkeys(u for _,u in sorted(links,reverse=True)))
    return {'title':title,'text':text,'offers':products,'articles':articles,'links':links,'hash':uid(text)}

def parse_news(xml,brand,at=None):
    at=at or datetime.now(timezone.utc);out=[]
    try:root=ET.fromstring(xml)
    except ET.ParseError:return []
    for item in root.findall('.//item')[:40]:
        title=item.findtext('title','');link=item.findtext('link','');date=item.findtext('pubDate','')
        if not re.search(r'(?<!\w)'+re.escape(norm(brand))+r'(?!\w)',norm(title)):continue
        try:
            pub=parsedate_to_datetime(date)
            if pub.tzinfo is None:pub=pub.replace(tzinfo=timezone.utc)
            if pub>at+timedelta(hours=1) or pub<at-timedelta(days=30):continue
            link=canonical(link)
        except (ValueError,TypeError,FetchError,OverflowError):continue
        out.append(source('news_headline',title,link,title,publishedAt=pub.isoformat(),format='rss-title',verifiedContent=False,publisher=compact(item.findtext('source',''),120)))
    return out[:8]

async def crawl_brand(brand,reader:SafeHTTP,progress,max_pages=10):
    report={'pages':[],'offers':[],'news':[],'warnings':[],'coverage':{'catalogue':'pending','news':'pending'},'readAt':now()}
    queue=[canonical(brand['website'])]
    if brand.get('catalogue'):queue.insert(0,canonical(brand['catalogue']))
    seen=set();tries=0;offerids=set();articleids=set()
    while queue and tries<max_pages:
        url=queue.pop(0)
        if url in seen:continue
        seen.add(url);tries+=1
        await progress('catalogue',f'Lecture {tries}/{max_pages} · {urlsplit(url).hostname}',len(report['pages']))
        try:
            page=await reader.get(url)
            if page.status!=200:raise FetchError(f'Page indisponible (HTTP {page.status}).')
            data=extract(page.text,page.url)
            if len(data['text'])<200 and not data['offers'] and hasattr(reader,'render'):
                try:
                    rendered=await reader.render(page.url)
                    if rendered:
                        candidate=extract(rendered.text,rendered.url)
                        if len(candidate['text'])>len(data['text']):page=rendered;data=candidate
                except (FetchError,RuntimeError) as exc:report['warnings'].append('Lecture enrichie : '+str(exc))
            if len(data['text'])<60:report['warnings'].append('Page pauvre en texte (contenu JavaScript possible) : '+page.url)
            report['pages'].append({'url':page.url,'title':data['title'],'observedAt':now(),'hash':data['hash'],'characters':len(data['text'])})
            for offer in data['offers']:
                if offer['id'] not in offerids:report['offers'].append(offer);offerids.add(offer['id'])
            for article in data['articles']:
                try:
                    age=(datetime.now(timezone.utc).date()-datetime.fromisoformat(article['publishedAt']).date()).days
                    if 0<=age<=45 and article['id'] not in articleids:report['news'].append(article);articleids.add(article['id'])
                except ValueError:pass
            queue.extend(u for u in data['links'][:40] if u not in seen and u not in queue)
            if tries==1 and not queue and not report['offers']:
                root=f'{urlsplit(url).scheme}://{urlsplit(url).netloc}'
                try:
                    sm=await reader.get(root+'/sitemap.xml')
                    if sm.status==200:
                        tree=ET.fromstring(sm.text)
                        urls=[e.text for e in tree.iter() if e.tag.endswith('loc') and e.text]
                        queue.extend(canonical(u) for u in urls[:150] if same_host(canonical(u),url) and not u.endswith('.xml') and re.search(r'product|produit|service|collection',u,re.I))
                except (FetchError,ET.ParseError,ValueError):pass
        except FetchError as exc:report['warnings'].append(f'{url} — {exc}')
    report['offers']=report['offers'][:80]
    report['coverage']['catalogue']='ok' if report['offers'] else ('partial' if report['pages'] else 'blocked')
    report['coverage']['bounded']=True;report['coverage']['pageLimit']=max_pages
    await progress('news','Recherche des titres d’actualité récents',len(report['pages']))
    feed='https://news.google.com/rss/search?q='+quote('"'+brand['name'].replace('"','')+'" when:30d')+'&hl=fr&gl=FR&ceid=FR:fr'
    try:
        page=await reader.get(feed)
        if page.status!=200:raise FetchError(f'Flux HTTP {page.status}')
        if not '<rss' in page.text[:500] and '<feed' not in page.text[:500]:raise FetchError('Flux non lisible.')
        report['news'].extend(parse_news(page.text,brand['name']))
        report['coverage']['news']='ok'
    except FetchError as exc:
        report['coverage']['news']='unavailable';report['warnings'].append('Actualités RSS : '+str(exc))
    return report
