"""Deletion controls applied to the verified frontend during the build."""
from pathlib import Path
JS = r'''
const manageKey='wellpack-management-v1';
let managed={brands:[],pending:[],sources:{},migrated:false};
try{const x=JSON.parse(localStorage.getItem(manageKey)||'null');if(x&&Array.isArray(x.brands)&&Array.isArray(x.pending)&&x.sources&&typeof x.sources==='object')managed=x;}catch{}
const sourceKey=e=>e.url?'url:'+e.url:'id:'+e.id+'|'+e.claim;
function saveManaged(){try{localStorage.setItem(manageKey,JSON.stringify(managed));return true;}catch{toast('Suppression non enregistrée : stockage du navigateur indisponible.');return false;}}
function pruneManaged(){
 const ids=new Set(managed.brands),before=state.clients.length+state.ops.length;
 state.clients=state.clients.filter(c=>!ids.has(c.id));
 state.ops=state.ops.filter(o=>!ids.has(o.clientId));
 for(const o of state.ops){const removed=new Set(managed.sources[o.id]||[]);if(removed.size)o.evidence=(o.evidence||[]).filter(e=>!removed.has(sourceKey(e)));}
 return before!==state.clients.length+state.ops.length;
}
function markRemoved(id){if(!managed.brands.includes(id))managed.brands.push(id);if(!managed.pending.includes(id))managed.pending.push(id);}
function isOldIntersport(c){
 if(/^intersport(?:$|[\s-])/i.test((c.name||c.brand||'').trim()))return true;
 try{const h=new URL(c.website||'').hostname;return h==='intersport.fr'||h.endsWith('.intersport.fr');}catch{return false;}
}
if(!managed.migrated){
 const ids=new Set(state.clients.filter(isOldIntersport).map(c=>c.id));
 for(const o of state.ops.filter(isOldIntersport))if(o.clientId)ids.add(o.clientId);
 for(const id of ids)markRemoved(id);
 state.ops=state.ops.filter(o=>!isOldIntersport(o));managed.migrated=true;saveManaged();
}
pruneManaged();
let flushingDeletes=false;
async function flushDeletes(){
 if(flushingDeletes||!engineConnected||location.protocol==='file:')return;flushingDeletes=true;
 try{for(const id of [...managed.pending]){try{
  const r=await fetch('/api/brands/'+encodeURIComponent(id),{method:'DELETE',headers:{'X-Wellpack-Request':'local-app'},signal:AbortSignal.timeout(15000)});
  if(r.status===401)break;if(!r.ok)throw Error('HTTP '+r.status);
  managed.pending=managed.pending.filter(x=>x!==id);saveManaged();
 }catch{toast('Suppression locale conservée. Synchronisation à réessayer à la reconnexion.');break;}}}finally{flushingDeletes=false;}
}
async function removeBrand(id){
 const c=state.clients.find(x=>x.id===id);if(!c)return;
 const linked=state.ops.filter(o=>o.clientId===id||(!o.clientId&&E.norm(o.brand)===E.norm(c.name)));
 if(!confirm('Supprimer '+c.name+' et ses liens du portefeuille ? '+linked.length+' idée(s) et leurs présentations associées seront également retirées. Les autres marques sont conservées.'))return;
 markRemoved(id);if(!saveManaged())return;
 state.ops=state.ops.filter(o=>!linked.some(x=>x.id===o.id));pruneManaged();persist();
 closeModal();navigate('clients');toast(c.name+' supprimée.');await flushDeletes();
}
function removeSource(id,index){
 const o=state.ops.find(x=>x.id===id),e=o?.evidence?.[index];if(!o||!e)return;
 if(!confirm('Supprimer ce lien / cette source de la recommandation ? Les validations seront à refaire.'))return;
 const key=sourceKey(e);managed.sources[id]=[...new Set([...(managed.sources[id]||[]),key])];if(!saveManaged())return;
 o.evidence.splice(index,1);o.checks={};
 if(o.proposal){o.proposal.approval={};if(o.proposal.proofURL===e.url){o.proposal.proofURL='';o.proposal.proofNote='';o.proposal.proofDate='';}}
 persist();renderDetail();toast('Source supprimée. La recommandation est à revalider.');
}
document.addEventListener('click',ev=>{
 const b=ev.target.closest('[data-remove-brand],[data-remove-source],[data-clear-link]');if(!b)return;ev.preventDefault();
 if(b.hasAttribute('data-remove-brand')){void removeBrand(b.dataset.removeBrand);return;}
 if(b.hasAttribute('data-remove-source')){removeSource(b.dataset.op,Number(b.dataset.removeSource));return;}
 const field=$(b.dataset.clearLink);if(field){field.value='';field.focus();$('watchError').textContent='Lien retiré du formulaire. Cliquez sur Enregistrer pour confirmer.';}
});
'''
BACKEND = r'''
@app.delete('/api/brands/{id}')
async def delete_brand(id:str):
    if not id or len(id)>100 or not all(ch.isalnum() or ch in '_-' for ch in id):
        raise HTTPException(400,'Identifiant invalide.')
    task=RUNNING.get(id)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):await task
    store.delete_brand(id)
    return {'ok':True,'id':id}

with store.db() as _con:
    _con.execute('CREATE TABLE IF NOT EXISTS migrations(key TEXT PRIMARY KEY)')
    _done=_con.execute("SELECT 1 FROM migrations WHERE key='remove-intersport-v1'").fetchone()
if not _done:
    for _brand in store.brands():
        _name=_brand.get('name','').strip().lower()
        _host=urlsplit(_brand.get('website','')).hostname or ''
        if _name=='intersport' or _name.startswith(('intersport ','intersport-')) or _host=='intersport.fr' or _host.endswith('.intersport.fr'):
            store.delete_brand(_brand['id'])
    with store.db() as _con:_con.execute("INSERT OR IGNORE INTO migrations VALUES('remove-intersport-v1')")
'''
STORE_METHODS = r'''
    def deleted_ids(self):
        with self.db() as c:return [r[0] for r in c.execute('SELECT id FROM deleted_brands')]
    def delete_brand(self,id):
        with self.db() as c:
            c.execute('INSERT OR IGNORE INTO deleted_brands(id) VALUES(?)',(id,))
            c.execute('DELETE FROM ops WHERE brand_id=?',(id,))
            c.execute('DELETE FROM reports WHERE brand_id=?',(id,))
            c.execute('DELETE FROM jobs WHERE brand_id=?',(id,))
            c.execute('DELETE FROM brands WHERE id=?',(id,))
'''
def once(s,old,new,label):
    if s.count(old)!=1:raise RuntimeError('Unexpected source for '+label+': '+str(s.count(old)))
    return s.replace(old,new,1)
def apply(root,assets):
    root=Path(root);s=assets['index.html']
    s=once(s,'window.WIApp={',JS+'\nwindow.WIApp={','management actions')
    s=once(s,'applyBackend(data){backendJobs=data.jobs||[];let changed=false;',"applyBackend(data){for(const id of data.deletedIds||[])if(!managed.brands.includes(id))managed.brands.push(id);saveManaged();pruneManaged();const removed=new Set(managed.brands);data={...data,brands:(data.brands||[]).filter(c=>!removed.has(c.id)),ops:(data.ops||[]).filter(o=>!removed.has(o.clientId)),jobs:(data.jobs||[]).filter(j=>!removed.has(j.brandId))};backendJobs=data.jobs||[];let changed=false;",'poll deletion filter')
    s=once(s,'if(changed)persist();this.refresh();','pruneManaged();if(changed)persist();this.refresh();void flushDeletes();','persist backend merge')
    s=once(s,'clients:()=>state.clients, state:()=>state,toast,navigate,openWatch,','clients:()=>state.clients, state:()=>state,toast,navigate,openWatch,removeBrand,removeSource,','management API')
    s=once(s,"wire();$('radarCoverageBtn').onclick=openCoverage;","persist();wire();$('radarCoverageBtn').onclick=openCoverage;",'persist initial cleanup')
    s=once(s,'>Configurer</button>${c.website?','>Configurer</button><button class="btn light sm" style="margin-top:6px;color:#9b2626" data-remove-brand="${esc(c.id)}" aria-label="Supprimer ${esc(c.name)}">Supprimer</button>${c.website?','brand button')
    s=once(s,"(o.evidence||[]).map(e=>{const v=E.evidenceStatus(e,state.settings.date);return `<div class=\"sourceitem\">","(o.evidence||[]).map((e,index)=>{const v=E.evidenceStatus(e,state.settings.date);return `<div class=\"sourceitem\"><button class=\"btn light sm\" style=\"float:right;color:#9b2626\" data-op=\"${esc(o.id)}\" data-remove-source=\"${index}\" aria-label=\"Supprimer cette source\">Supprimer</button>",'source button')
    s=once(s,'o.evidence.push(e);persist();','managed.sources[o.id]=(managed.sources[o.id]||[]).filter(k=>k!==sourceKey(e));saveManaged();o.evidence.push(e);persist();','explicit source re-add')
    s=once(s,"$('modalWrap').classList.add('open');$('wName').focus();","for(const id of ['wSite','wCatalogue'])$(id).insertAdjacentHTML('afterend','<button type=\"button\" class=\"text-button\" data-clear-link=\"'+id+'\">Retirer le lien</button>');$('modalWrap').classList.add('open');$('wName').focus();",'link clear buttons')
    s=once(s,"if(name.length<2||!website){$('watchError')","if(name.length<2||(!website&&(!watchId||$('wSite').value.trim()))){$('watchError')",'save empty site')
    s=s.replace('Site officiel *</label>','Site officiel (nécessaire pour analyser)</label>')
    s=once(s,"toast(engineConnected?'Marque enregistrée. L’analyse va démarrer.':'Marque enregistrée. Ouvrez le lanceur pour activer l’analyse.');","toast(!website?'Liens enregistrés. Sans site, les prochaines analyses sont désactivées.':engineConnected?'Marque enregistrée. L’analyse va démarrer.':'Marque enregistrée. Ouvrez le lanceur pour activer l’analyse.');",'paused brand message')
    for key in ('index.html','live.js'):
        text=s if key=='index.html' else assets[key]
        assets[key]=once(text,'for(const c of A.clients().filter(c=>c.website)){','for(const c of A.clients().filter(c=>c.website||synced.has(c.id)||data.brands.some(b=>b.id===c.id))){','empty-site sync '+key)
    app_path=root/'app.py';app=app_path.read_text()
    app=once(app,"if not v and info.field_name=='catalogue':return ''","if not v:return ''",'server empty URL')
    app=once(app,'return dict(brands=store.brands(),jobs=store.jobs(),ops=store.opportunities())','return dict(brands=store.brands(),jobs=store.jobs(),ops=store.opportunities(),deletedIds=store.deleted_ids())','deleted state')
    app=once(app,'changed=store.upsert_brand(b.model_dump())',"if b.id in store.deleted_ids():raise HTTPException(410,'Marque supprimée : ajoutez une nouvelle fiche pour la rétablir.')\n    changed=store.upsert_brand(b.model_dump())",'reject stale saves')
    app=once(app,'job=enqueue(b.id) if changed else None','job=enqueue(b.id) if changed and b.website else None','skip paused scan')
    app=once(app,'for b in store.brands():\n                last=',"for b in store.brands():\n                if not b.get('website'):continue\n                last=",'skip scheduler')
    app=once(app,"if not store.brand(id):raise HTTPException(404,'Marque inconnue.')","if not store.brand(id):raise HTTPException(404,'Marque inconnue.')\n    if not store.brand(id).get('website'):raise HTTPException(400,'Ajoutez un site avant de lancer une analyse.')",'manual scan guard')
    app+='\n'+BACKEND;app_path.write_text(app)
    sp=root/'engine'/'store.py';store=sp.read_text()
    store=once(store,"con.execute('PRAGMA journal_mode=WAL')","con.execute('PRAGMA journal_mode=WAL')\n            con.execute('CREATE TABLE IF NOT EXISTS deleted_brands(id TEXT PRIMARY KEY)')",'tombstone table')
    sp.write_text(store+'\n'+STORE_METHODS)
    compile(app,str(app_path),'exec');compile(sp.read_text(),str(sp),'exec')
    print('Deletion controls, Intersport cleanup and persistent tombstones installed.',flush=True)
