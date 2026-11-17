"""Password protection for a small, single-workspace evaluation deployment.
Not a multi-user SSO / roles system. HTTPS is mandatory on the hosting platform.
"""
from __future__ import annotations
import os,time,hmac,hashlib,secrets,base64
from collections import defaultdict
from fastapi import Request
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse
from engine import config

TTL=12*3600
ATTEMPTS=defaultdict(list)

def password():return os.getenv('APP_PASSWORD','')
def secret():return os.getenv('SESSION_SECRET','')
def protected():return bool(password())
def validate_deployment():
    if config.production():
        if len(password())<16 or len(secret())<32:
            raise RuntimeError('Hébergement refusé : APP_PASSWORD (16 caractères minimum) et SESSION_SECRET (32 minimum) requis.')
        if not os.getenv('ALLOWED_HOSTS') and not os.getenv('RENDER_EXTERNAL_HOSTNAME'):
            raise RuntimeError('Hébergement refusé : configurez ALLOWED_HOSTS avec le domaine du service.')
    elif protected() and len(secret())<32:
        raise RuntimeError('SESSION_SECRET de 32 caractères minimum requis avec APP_PASSWORD.')

def signature(body):
    key=(secret()+hashlib.sha256(password().encode()).hexdigest()).encode()
    return hmac.new(key,body.encode(),hashlib.sha256).hexdigest()
def token():
    body=str(int(time.time())+TTL)+'.'+secrets.token_hex(16)
    return body+'.'+signature(body)
def valid(value):
    try:
        exp,nonce,sig=value.split('.')
        body=exp+'.'+nonce
        return int(time.time())<int(exp)<=int(time.time())+TTL and hmac.compare_digest(sig,signature(body))
    except (ValueError,AttributeError):return False

def login_page():
    return HTMLResponse('''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Accès privé · WellPack Intelligence</title><style>body{font:16px system-ui;background:#fafaf6;color:#111;margin:0;display:grid;place-items:center;min-height:100vh}.box{width:min(390px,85vw);padding:38px;border:1px solid #e5e5da;background:white;border-radius:20px}b{background:#f6ff00;padding:7px 10px}h1{font-size:30px;letter-spacing:-1px;margin:30px 0 12px}p{line-height:1.6;color:#56564f}label{display:block;margin:24px 0 7px}input{font:inherit;width:100%;box-sizing:border-box;padding:14px;border:1px solid #ccc;border-radius:8px}button{font:inherit;font-weight:700;background:#f6ff00;border:0;border-radius:8px;width:100%;padding:15px;margin-top:14px;cursor:pointer}#error{color:#a22;min-height:24px;font-size:14px}</style><form class="box" id="login"><b>WELLPACK / INTELLIGENCE</b><h1>Vos prochaines campagnes commencent ici.</h1><p>Espace privé de démonstration. Saisissez le mot de passe partagé par l’administrateur.</p><label for="password">Mot de passe d’accès</label><input id="password" type="password" autocomplete="current-password" required autofocus maxlength="300"><button id="submit">Entrer dans l’application →</button><p id="error" role="alert"></p></form><script>document.getElementById('login').onsubmit=async e=>{e.preventDefault();const b=document.getElementById('submit');b.disabled=true;try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json','X-Wellpack-Request':'local-app'},body:JSON.stringify({password:document.getElementById('password').value})});if(!r.ok)throw Error((await r.json()).detail||'Connexion refusée.');location.href='/';}catch(e){document.getElementById('error').textContent=e.message;}finally{b.disabled=false;}};</script></html>''')

async def login(request:Request):
    ip=request.client.host if request.client else 'unknown';now=time.monotonic()
    ATTEMPTS[ip]=[t for t in ATTEMPTS[ip] if now-t<600]
    if len(ATTEMPTS[ip])>=8:return JSONResponse({'detail':'Trop de tentatives. Réessayez dans dix minutes.'},status_code=429)
    try:value=(await request.json()).get('password','')
    except (ValueError,AttributeError):value=''
    if not protected() or not isinstance(value,str) or not hmac.compare_digest(value.encode(),password().encode()):
        ATTEMPTS[ip].append(now)
        return JSONResponse({'detail':'Mot de passe incorrect.'},status_code=401)
    ATTEMPTS.pop(ip,None)
    r=JSONResponse({'ok':True})
    r.set_cookie('wi_session',token(),max_age=TTL,httponly=True,secure=config.production(),samesite='strict',path='/')
    r.headers['Cache-Control']='no-store'
    return r
