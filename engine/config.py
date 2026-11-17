"""Server-only configuration. Secrets never enter the UI state, PDF or exports."""
from __future__ import annotations
import json, os, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.getenv('WELLPACK_DATA_DIR',str(ROOT/'data')))
CONFIG_FILE=DATA/'private-config.json'

def local_config():
    try:return json.loads(CONFIG_FILE.read_text('utf-8'))
    except (OSError,ValueError):return {}

def free_demo():
    return os.getenv('FREE_DEMO','false').lower()=='true'

def get(key,default=''):
    if free_demo():
        if key in ('OPENAI_API_KEY','FIRECRAWL_API_KEY'):return ''
        if key=='MAX_PAID_REQUESTS_PER_DAY':return '0'
        if key=='WEB_SEARCH_ENABLED':return 'false'
    return os.environ.get(key) or str(local_config().get(key,default))

def enabled(key,default='false'):return get(key,default).lower()=='true'
def ai_ready():return bool(get('OPENAI_API_KEY') and get('OPENAI_MODEL','gpt-4.1-mini'))
def search_ready():return ai_ready() and enabled('WEB_SEARCH_ENABLED','true')
def production():return os.getenv('APP_ENV','local')=='production'

def public_config():
    return {'freeDemo':free_demo(),'aiConfigured':ai_ready(),'webSearch':search_ready(),
            'model':get('OPENAI_MODEL','gpt-4.1-mini'),
            'firecrawl':bool(get('FIRECRAWL_API_KEY')),
            'editable':not free_demo() and not production() and not bool(os.getenv('OPENAI_API_KEY')),
            'dailyLimit':int(get('MAX_PAID_REQUESTS_PER_DAY','40')),
            'paidRequestsToday':usage(),
            'automatic':os.getenv('AUTO_SCAN','false').lower()=='true'}

def save_local(key:str,model:str,web_search:bool,remove:bool=False):
    if free_demo():raise ValueError('Démo gratuite : les connexions aux API payantes sont désactivées.')
    if production() or os.getenv('OPENAI_API_KEY'):raise ValueError('Configuration gérée par les variables sécurisées de l’hébergement.')
    if not re.fullmatch(r'[a-zA-Z0-9._:-]{2,100}',model):raise ValueError('Identifiant du modèle invalide.')
    conf=local_config()
    if remove:conf.pop('OPENAI_API_KEY',None)
    elif key:
        if not key.startswith('sk-') or not 20<=len(key)<=500 or any(c.isspace() for c in key):raise ValueError('Format de clé invalide. Utilisez une clé API OpenAI, pas un mot de passe.')
        conf['OPENAI_API_KEY']=key
    conf.update(OPENAI_MODEL=model,WEB_SEARCH_ENABLED=str(web_search).lower())
    CONFIG_FILE.parent.mkdir(parents=True,exist_ok=True)
    temp=CONFIG_FILE.with_suffix('.tmp')
    fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(conf,f,ensure_ascii=False)
    os.replace(temp,CONFIG_FILE)
    try:os.chmod(CONFIG_FILE,0o600)
    except OSError:pass

class LimitError(RuntimeError):pass

def _db():
    DATA.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DATA/'usage.sqlite3',timeout=15)
    c.execute('CREATE TABLE IF NOT EXISTS usage(day TEXT NOT NULL, provider TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(day,provider))')
    return c

def usage():
    with _db() as c:return c.execute('SELECT COALESCE(SUM(count),0) FROM usage WHERE day=?',(datetime.now(timezone.utc).date().isoformat(),)).fetchone()[0]

def reserve(provider):
    if free_demo():raise LimitError('Démo gratuite : aucun appel fournisseur payant autorisé.')
    day=datetime.now(timezone.utc).date().isoformat()
    limit=max(0,min(1000,int(get('MAX_PAID_REQUESTS_PER_DAY','40'))))
    with _db() as c:
        c.execute('BEGIN IMMEDIATE')
        n=c.execute('SELECT COALESCE(SUM(count),0) FROM usage WHERE day=?',(day,)).fetchone()[0]
        if n>=limit:raise LimitError('Limite quotidienne d’appels externes atteinte. Collecte gratuite conservée ; réessayez demain.')
        c.execute('INSERT INTO usage VALUES(?,?,1) ON CONFLICT(day,provider) DO UPDATE SET count=count+1',(day,provider))
