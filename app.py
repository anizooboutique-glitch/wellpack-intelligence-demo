"""Single-workspace prototype: local use or password-protected evaluation hosting."""
from __future__ import annotations
import asyncio,os,uuid
from pathlib import Path
from contextlib import asynccontextmanager,suppress
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel,Field,field_validator
# Environment variables supplied by hosting override the optional local .env.
_env=Path(__file__).resolve().parent/'.env'
if _env.exists():
    for _line in _env.read_text(encoding='utf-8-sig').splitlines():
        if _line.strip() and not _line.lstrip().startswith('#') and '=' in _line:
            _k,_v=_line.strip().split('=',1);os.environ.setdefault(_k.strip(),_v.strip().strip(chr(34)).strip(chr(39)))
from engine.store import Store
from engine.net import SafeHTTP,FetchError,canonical
from engine.crawl import crawl_brand,now
from engine.recommend import propose_rules
from engine import ai,config,search,provider
from engine.rendered import ResearchHTTP
import security

BASE=Path(__file__).resolve().parent
store=Store(os.getenv('WELLPACK_DB',str(config.DATA/'wellpack.sqlite3')))
RUNNING:dict[str,asyncio.Task]={}
GATE=asyncio.Semaphore(2)
MAX_PAGES=max(2,min(20,int(os.getenv('MAX_PAGES_PER_SCAN','10'))))
AUTO=os.getenv('AUTO_SCAN','false').lower()=='true'
INTERVAL=max(6,int(os.getenv('SCAN_INTERVAL_HOURS','24')))

class Brand(BaseModel):
    id:str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
    name:str=Field(min_length=2,max_length=150)
    website:str=Field(max_length=2000)
    catalogue:str=Field(default='',max_length=2000)
    sector:str=Field(default='other',max_length=30)
    routeType:str=Field(default='unknown',max_length=30)
    partner:str=Field(default='',max_length=150)
    geo:str=Field(default='',max_length=300)
    @field_validator('website','catalogue')
    @classmethod
    def check_url(cls,v,info):
        if not v and info.field_name=='catalogue':return ''
        try:return canonical(v)
        except FetchError as exc:raise ValueError(str(exc))

async def scan(id,jid):
    async with GATE:
        reader=ResearchHTTP()
        async def progress(stage,message,pages):store.set_job(jid,id,'running',stage=stage,message=message,pages=pages)
        try:
            brand=store.brand(id)
            if not brand:raise FetchError('Marque absente.')
            store.set_job(jid,id,'running',message='Lecture des sources publiques',stage='catalogue')
            report=await asyncio.wait_for(crawl_brand(brand,reader,progress,MAX_PAGES),timeout=240)
            try:
                await asyncio.wait_for(search.enrich(brand,report,reader,progress),timeout=180)
            except asyncio.TimeoutError:report['warnings'].append('Recherche web interrompue à la limite de durée ; résultats partiels conservés.')
            await progress('recommendations','Rapprochement offre / contexte et contrôle des preuves',len(report['pages']))
            ops=[];rejected=[];mode='rules'
            if ai.configured() and report['offers']:
                try:ops,rejected=await ai.generate(brand,report);mode='ai'
                except (provider.ProviderError,config.LimitError) as exc:report['warnings'].append('IA non disponible : '+str(exc)+' Moteur métier utilisé.')
                except Exception as exc:report['warnings'].append('IA non disponible : moteur métier utilisé. '+type(exc).__name__)
            if mode=='rules':ops,rejected=propose_rules(brand,report)
            report['rejected']=rejected;report['mode']=mode;report['opCount']=len(ops)
            store.save_report(id,report,ops)
            status='partial' if report['warnings'] or not report['offers'] else 'done'
            store.set_job(jid,id,status,stage='complete',message=f"{len(report['pages'])} page(s) lue(s), {len(report['offers'])} offre(s), {len(ops)} piste(s).",finishedAt=now(),pages=len(report['pages']),offers=len(report['offers']),opportunities=len(ops))
        except asyncio.CancelledError:
            store.set_job(jid,id,'interrupted',message='Serveur arrêté ; relancer la collecte.');raise
        except Exception as exc:
            store.set_job(jid,id,'error',stage='error',message=str(exc)[:260] if isinstance(exc,FetchError) else 'Collecte interrompue : '+type(exc).__name__,finishedAt=now())
        finally:await reader.close();RUNNING.pop(id,None)

def enqueue(id):
    if id in RUNNING:
        return next((j for j in store.jobs() if j['brandId']==id and j['state'] in ('queued','running')),None)
    if len(RUNNING)>=20:raise HTTPException(429,'20 collectes déjà en attente. Réessayez après leur traitement.')
    jid=uuid.uuid4().hex;store.set_job(jid,id,'queued',stage='queued',message='Collecte en file d’attente',pages=0)
    RUNNING[id]=asyncio.create_task(scan(id,jid));return store.job(jid)

async def schedule():
    while True:
        if AUTO:
            for b in store.brands():
                last=b.get('lastScan')
                due=not last or datetime.fromisoformat(last)<datetime.now(timezone.utc)-timedelta(hours=INTERVAL)
                recent=next((j for j in store.jobs() if j['brandId']==b['id']),None)
                if recent and datetime.fromisoformat(recent['created'])>datetime.now(timezone.utc)-timedelta(hours=INTERVAL):due=False
                if due and b['id'] not in RUNNING and len(RUNNING)<20:enqueue(b['id'])
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app):
    security.validate_deployment()
    task=asyncio.create_task(schedule())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):await task
    pending=list(RUNNING.values())
    for t in pending:t.cancel()
    if pending:await asyncio.gather(*pending,return_exceptions=True)

app=FastAPI(title='WellPack Intelligence',version='3.0',lifespan=lifespan,docs_url='/api/docs',redoc_url=None)
hosts=['127.0.0.1','localhost','[::1]','testserver']
hosts += [h.strip() for h in os.getenv('ALLOWED_HOSTS','').split(',') if h.strip()]
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):hosts.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
app.add_middleware(TrustedHostMiddleware,allowed_hosts=hosts)

@app.middleware('http')
async def local_guard(request:Request,call_next):
    path=request.url.path
    if security.protected() and path not in ('/login','/api/login','/healthz') and not security.valid(request.cookies.get('wi_session')):
        if path.startswith('/api/'):
            return JSONResponse({'detail':'Connexion requise.'},status_code=401,headers={'Cache-Control':'no-store'})
        return RedirectResponse('/login',status_code=303)
    if request.url.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'):
            return JSONResponse({'detail':'Origine non autorisée.'},status_code=403)
        if request.headers.get('x-wellpack-request')!='local-app':
            return JSONResponse({'detail':'En-tête de sécurité manquant.'},status_code=403)
        try: content_length=int(request.headers.get('content-length','0'))
        except ValueError:return JSONResponse({'detail':'Taille de requête invalide.'},status_code=400)
        if content_length>250_000:return JSONResponse({'detail':'Requête trop volumineuse.'},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if config.production():response.headers['Strict-Transport-Security']='max-age=31536000'
    return response

@app.get('/')
async def index():return FileResponse(BASE/'static'/'index.html')
@app.get('/api/health')
async def health():
    return dict(version='3.0',mode='ai' if ai.configured() else 'rules',autoScan=AUTO,intervalHours=INTERVAL,maxPages=MAX_PAGES,config=config.public_config(),limits={'weather':False,'socialTrends':False,'news':'read dated sources + RSS titles separated','completeCatalogue':False})
@app.get('/api/state')
async def state():return dict(brands=store.brands(),jobs=store.jobs(),ops=store.opportunities())
@app.post('/api/brands')
async def brand(b:Brand):
    if not store.brand(b.id) and len(store.brands())>=100:raise HTTPException(400,'Prototype limité à 100 marques surveillées.')
    changed=store.upsert_brand(b.model_dump())
    job=enqueue(b.id) if changed else None
    return dict(brand=store.brand(b.id),job=job)
@app.post('/api/brands/{id}/scan')
async def launch(id:str):
    if not store.brand(id):raise HTTPException(404,'Marque inconnue.')
    last=next((j for j in store.jobs() if j['brandId']==id),None)
    if last and last['state'] not in ('queued','running') and datetime.fromisoformat(last['created'])>datetime.now(timezone.utc)-timedelta(seconds=60):raise HTTPException(429,'Une collecte vient d’être lancée ; évitez les relances répétées.')
    return enqueue(id)
@app.get('/api/brands/{id}/report')
async def report(id:str):
    r=store.report(id)
    if r is None:raise HTTPException(404,'Pas encore de rapport.')
    return r
@app.get('/api/jobs/{id}')
async def job(id:str):
    j=store.job(id)
    if not j:raise HTTPException(404,'Collecte inconnue.')
    return j

@app.get('/healthz')
async def healthz():return {'ok':True}
@app.get('/login')
async def login_page():return security.login_page() if security.protected() else RedirectResponse('/')
@app.post('/api/login')
async def login(request:Request):return await security.login(request)
@app.post('/api/logout')
async def logout():
    r=JSONResponse({'ok':True});r.delete_cookie('wi_session',path='/');return r

class Settings(BaseModel):
    apiKey:str=Field(default='',max_length=500)
    model:str=Field(default='gpt-4.1-mini',max_length=100)
    webSearch:bool=True
    consent:bool=False
    remove:bool=False

@app.get('/api/settings')
async def settings():return config.public_config()
@app.post('/api/settings')
async def save_settings(value:Settings):
    if RUNNING:raise HTTPException(409,'Attendez la fin des analyses avant de modifier le moteur.')
    if value.apiKey and not value.consent:raise HTTPException(400,'Confirmez l’autorisation des appels API facturés séparément.')
    try:config.save_local(value.apiKey,value.model,value.webSearch,value.remove)
    except ValueError as exc:raise HTTPException(400,str(exc))
    return config.public_config()
@app.post('/api/settings/test')
async def test_provider():
    if not ai.configured():raise HTTPException(400,'Ajoutez une clé API dans la configuration.')
    try:
        await provider.response({'model':config.get('OPENAI_MODEL','gpt-4.1-mini'),'store':False,'input':'Réponds uniquement OK.','max_output_tokens':32})
        return {'ok':True,'message':'Clé et modèle acceptés. La recherche web sera testée lors de la prochaine analyse.'}
    except (provider.ProviderError,config.LimitError) as exc:raise HTTPException(400,str(exc))

app.mount('/static',StaticFiles(directory=BASE/'static'),name='static')
