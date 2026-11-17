"""Public HTTP reader. DNS is checked AND pinned per hop; no cookies/credentials."""
from __future__ import annotations
import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit, urljoin
from urllib.robotparser import RobotFileParser
import httpx

AGENT = 'WellpackIntelligence/3.0 (public marketing research; local prototype)'
MAX_BYTES = 2_500_000
class FetchError(Exception): pass

def canonical(raw: str) -> str:
    if not isinstance(raw, str) or len(raw) > 2000:raise FetchError('URL invalide.')
    p = urlsplit(raw.strip())
    try: port = p.port
    except ValueError: raise FetchError('Port invalide.')
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise FetchError('Utiliser une URL http(s) publique, sans identifiants.')
    if port not in (None, 80, 443) or (port == 80 and p.scheme != 'http') or (port == 443 and p.scheme != 'https'):
        raise FetchError('Seuls les ports web standard sont autorisés.')
    host = p.hostname.lower().rstrip('.').encode('idna').decode()
    if host == 'localhost' or host.endswith(('.local', '.internal', '.localhost', '.home', '.test', '.invalid')) or '.' not in host:
        raise FetchError('Adresse locale ou réservée interdite.')
    try: ipaddress.ip_address(host)
    except ValueError: pass
    else: raise FetchError('Utiliser un nom de domaine public, pas une adresse IP.')
    return urlunsplit((p.scheme,host,p.path or '/',p.query,''))

async def resolve_public(host: str, port: int) -> list[str]:
    try:
        items = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout=6)
    except (OSError, asyncio.TimeoutError): raise FetchError('Résolution DNS impossible pour '+host)
    ips = list(dict.fromkeys(x[4][0] for x in items))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):raise FetchError('Destination privée/réservée refusée.')
    return sorted(ips, key=lambda x: ':' in x)

@dataclass
class Page:
    url: str
    status: int
    text: str
    content_type: str = 'text/html'

class SafeHTTP:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(12, connect=6), trust_env=False, follow_redirects=False)
        self.robots: dict[str, tuple[RobotFileParser | None,str]] = {}
        self.host_times: dict[str,float] = {}
        self.gate = asyncio.Semaphore(3)
    async def close(self): await self.client.aclose()
    async def get(self, raw: str, *, enforce_robots: bool = True) -> Page:
        url = canonical(raw)
        for _ in range(5):
            p = urlsplit(url)
            if enforce_robots:
                allowed, reason = await self.allowed(url)
                if not allowed: raise FetchError(reason)
            ips = await resolve_public(p.hostname, 443 if p.scheme == 'https' else 80)
            async with self.gate:
                now=asyncio.get_running_loop().time()
                delay=max(0,self.host_times.get(p.hostname,0)+0.5-now)
                if delay: await asyncio.sleep(delay)
                self.host_times[p.hostname]=asyncio.get_running_loop().time()
                target=httpx.URL(url).copy_with(host=ips[0])
                try:
                    async with self.client.stream('GET',target,headers={'Host':p.hostname,'User-Agent':AGENT,'Accept':'text/html,application/xhtml+xml,application/xml,application/rss+xml,application/json;q=0.8'},extensions={'sni_hostname':p.hostname}) as r:
                        if r.status_code in (301,302,303,307,308):
                            if not r.headers.get('location'): raise FetchError('Redirection sans destination.')
                            url=canonical(urljoin(url,r.headers['location'])); continue
                        ct=r.headers.get('content-type','').lower()
                        if r.status_code in (401,403,429): raise FetchError(f'Accès refusé ou limité (HTTP {r.status_code}). Aucun contournement.')
                        if r.status_code>=500: raise FetchError(f'Serveur indisponible (HTTP {r.status_code}).')
                        if not any(x in ct for x in ('text/','json','xml')) and r.status_code<400:raise FetchError('Format non pris en charge (HTML/JSON/XML uniquement).')
                        data=bytearray()
                        async for part in r.aiter_bytes():
                            data.extend(part)
                            if len(data)>MAX_BYTES: raise FetchError('Page trop volumineuse : collecte arrêtée à 2,5 Mo.')
                        return Page(url,r.status_code,bytes(data).decode(r.encoding or 'utf-8',errors='replace'),ct)
                except httpx.HTTPError as exc: raise FetchError('Connexion impossible : '+type(exc).__name__) from exc
        raise FetchError('Trop de redirections.')
    async def allowed(self,url: str) -> tuple[bool,str]:
        p=urlsplit(url);origin=f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            try:
                response=await self.get(origin+'/robots.txt',enforce_robots=False)
                if response.status in (404,410): self.robots[origin]=(None,'')
                elif response.status!=200: self.robots[origin]=(None,'robots.txt inaccessible : lecture suspendue par prudence.')
                else:
                    robot=RobotFileParser();robot.parse(response.text.splitlines());self.robots[origin]=(robot,'')
            except FetchError as exc: self.robots[origin]=(None,'robots.txt : '+str(exc))
        robot,error=self.robots[origin]
        if error: return False,error
        if robot and not robot.can_fetch('WellpackIntelligence',url): return False,'Lecture non autorisée par robots.txt.'
        if robot and (robot.crawl_delay('WellpackIntelligence') or robot.crawl_delay('*') or 0)>5:
            return False,'Délai robots.txt supérieur au budget de ce prototype ; collecte suspendue.'
        if robot:
            delay=robot.crawl_delay('WellpackIntelligence') or robot.crawl_delay('*') or 0
            if delay: await asyncio.sleep(delay)
        return True,''
