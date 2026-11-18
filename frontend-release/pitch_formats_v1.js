/* Three client-ready / internal deliverable modes; no external dependencies or paid AI. */
(()=>{'use strict';
const api=window.WIProposal;if(!api||!api.mount)return;
const originalMount=api.mount,originalPrint=api.print,originalSetPage=api.setPage;
let active=null,mode='creative',rendering=false,observer=null,printBusy=false;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const short=(v,n=550)=>{const text=String(v??'').trim();return text.length>n?text.slice(0,n-1)+'…':text};
const safe=v=>esc(short(v));
function bar(root){return root?.querySelector('.doc-bar')?.outerHTML||'<div class="doc-bar">WELLPACK · RECOMMANDATION</div>'}
function foot(n,total,brand){return '<footer class="doc-foot"><span>DOCUMENT DE TRAVAIL · '+safe(brand)+'</span><b>'+String(n).padStart(2,'0')+' / '+String(total).padStart(2,'0')+'</b></footer>'}
function values(){const m=api.read();const o=active;return {m,o}}
function listed(v){return '<div class="wf-value">'+safe(v||'À renseigner')+'</div>'}
function field(label,value){return '<div class="wf-field"><span>'+esc(label)+'</span>'+listed(value)+'</div>'}
function sheet(no,total,body,className,reference){
 const {m,o}=values();const draft=o.fixture||api.status().length>0;
 return '<article class="pdfpage wf-format-page '+className+(draft?' draft':'')+'" data-pdf-page="'+no+'" aria-label="Page '+no+'" style="--client:'+esc(m.brandColor||'#f6d536')+'">'+
 bar(reference)+(draft?'<div class="doc-status">'+(o.fixture?'DÉMONSTRATION FICTIVE — NON TRANSMISSIBLE':'BROUILLON — POINTS À VALIDER')+'</div>':'')+body+foot(no,total,o.brand)+'</article>';
}
function briefPages(reference){
 const {m,o}=values();const cards=window.WIRCS?.cards?.(o,m)||o.creative?.rcs||[];
 const dates=(m.start||'À préciser')+' → '+(m.end||'À préciser');
 const sourced=(o.evidence||[]).filter(e=>e.url).slice(0,5);
 const summary='<div class="wf-kicker">DOCUMENT INTERNE / 01</div><h2>Le brief opérationnel.</h2><p class="wf-intro">Préparation, vérification et exécution de la recommandation. Ne pas envoyer tel quel au prospect.</p>'+
 '<div class="wf-sectionlabel">01 / CONTEXTE</div><div class="wf-brief-grid">'+
 field('ANNONCEUR',o.brand)+field('CANAL',m.channel)+field('PÉRIODE',dates)+field('ZONE',m.region)+
 field('OPÉRATION',m.concept)+field('PRODUIT / SERVICE',m.product)+'</div>'+
 '<div class="wf-sectionlabel">02 / INTENTION MARKETING</div>'+
 '<div class="wf-block">'+field('POURQUOI MAINTENANT',m.moment)+field('BÉNÉFICE CLIENT',m.benefit)+field('CIBLE',m.target)+field('OBJECTIF',m.goal)+'</div>'+
 '<div class="wf-sectionlabel">03 / PARCOURS ET MESURE</div>'+
 '<div class="wf-brief-grid">'+field('ACTION PRINCIPALE',m.cta)+field('DESTINATION',m.destination)+field('KPI',m.kpis)+field('INTERLOCUTEUR',m.sender)+'</div>';
 const scripts='<div class="wf-kicker">DOCUMENT INTERNE / 02</div><h2>Les créations à produire.</h2>'+
 '<p class="wf-intro">Textes, visuels et mentions à faire valider avant toute activation.</p>'+
 '<div class="wf-sectionlabel">MESSAGES</div>'+
 '<div class="wf-message"><b>SMS / FALLBACK</b><p>'+safe(m.sms||o.creative?.sms||'À rédiger')+'</p></div>'+
 (m.channel?.startsWith('RCS')?'<div class="wf-sectionlabel">CARROUSEL RCS</div><div class="wf-cards">'+cards.slice(0,4).map((c,i)=>
 '<div class="wf-card"><strong>CARTE '+String(i+1).padStart(2,'0')+'</strong><div><b>'+safe(c.title)+'</b><p>'+safe(c.body)+'</p><small>CTA : '+safe(c.cta)+'</small><small>'+safe(c.imageData?'Visuel présent — vérifier droits et approbation':'Visuel à sélectionner ou à produire')+'</small></div></div>').join('')+'</div>':'')+
 (m.channel?.includes('LP')?'<div class="wf-sectionlabel">LANDING PAGE</div><div class="wf-message"><b>'+safe(m.lpTitle)+'</b><p>'+safe(m.lpBody)+'</p></div>':'')+
 '<div class="wf-sectionlabel">POINTS DE VALIDATION</div>'+
 '<div class="wf-checklist">'+['Offre, prix, mentions et disponibilité vérifiés','Droits des photographies et identité de marque validés','Ciblage, consentement et désinscription conformes','CTA, liens, tracking et parcours testés','BAT et contrôle créatif approuvés'].map(t=>'<div>☐ '+esc(t)+'</div>').join('')+'</div>'+
 '<div class="wf-source-list"><b>SOURCES À RECONTRÔLER</b>'+sourced.map(e=>'<span>'+safe(e.claim||e.url,100)+'</span>').join('')+'</div>';
 return [sheet(1,2,summary,'wf-brief',reference),sheet(2,2,scripts,'wf-brief',reference)];
}
function transform(){
 if(rendering||!active||mode==='creative')return;
 const zone=document.getElementById('proposalPages');if(!zone)return;
 if(zone.dataset.wfMode===mode&&zone.children.length===(mode==='express'?2:2))return;
 const originals=[...zone.querySelectorAll(':scope > .pdfpage')];
 if(originals.length!==4)return;
 rendering=true;
 try{
   let pages=[];
   if(mode==='express'){
     pages=[originals[0].cloneNode(true),originals[2].cloneNode(true)];
     pages.forEach((p,i)=>{p.classList.remove('is-current');p.classList.add('wf-format-page','wf-express');p.dataset.pdfPage=String(i+1);p.setAttribute('aria-label','Page '+(i+1));const footer=p.querySelector('.doc-foot b');if(footer)footer.textContent=String(i+1).padStart(2,'0')+' / 02'});
   }else{
     const html=briefPages(originals[0]);const container=document.createElement('template');container.innerHTML=html.join('');pages=[...container.content.children];
   }
   zone.replaceChildren(...pages);
   zone.dataset.wfMode=mode;
   updatePageControls();
 }finally{rendering=false}
}
function selectPage(index){
 const pages=[...document.querySelectorAll('#proposalPages > .pdfpage')];
 pages.forEach((p,i)=>p.classList.toggle('is-current',i===index));
 document.querySelectorAll('#pdfPageNav [data-wf-page]').forEach((b,i)=>{b.classList.toggle('active',i===index);b.setAttribute('aria-selected',String(i===index))});
 const label=document.getElementById('pdfPageLabel');if(label)label.textContent='Page '+(index+1)+' / '+pages.length+(mode==='brief'?' · brief interne':' · pitch express');
}
function updatePageControls(){
 const nav=document.getElementById('pdfPageNav'),label=document.getElementById('pdfPageLabel'),heading=document.querySelector('.preview-heading h3');
 if(nav&&mode!=='creative'){
   nav.hidden=false;
   nav.innerHTML=(mode==='express'?['Couverture','Expérience client']:['Cadrage','Production & contrôles']).map((name,i)=>'<button type="button" data-wf-page="'+i+'" class="'+(i===0?'active':'')+'">'+String(i+1).padStart(2,'0')+' <span>'+name+'</span></button>').join('');
   nav.querySelectorAll('[data-wf-page]').forEach(b=>b.onclick=()=>selectPage(Number(b.dataset.wfPage)));
 }else if(nav)nav.hidden=false;
 if(label)label.textContent=mode==='express'?'Page 1 / 2 · pitch express':mode==='brief'?'Page 1 / 2 · document interne':'Page 1 / 4 · présentation créative';
 if(heading)heading.textContent=mode==='express'?'Pitch commercial express':mode==='brief'?'Brief opérationnel interne':'Le document prospect';
 if(mode!=='creative')selectPage(0);
 const b=document.getElementById('proposalExportBtn');
 if(b){b.textContent=mode==='brief'?'Exporter le brief interne en PDF':mode==='express'?'Exporter le pitch express en PDF':'Exporter la présentation créative en PDF'}
}
function renderMode(){if(mode==='creative'){const {o}=values();originalMount.call(api,o,active.settings,active.save,active.back);return}transform()}
function sync(){
 if(rendering||!active)return;
 const root=document.getElementById('proposalPages');
 if(!root)return;
 if(root.querySelectorAll(':scope > .pdfpage').length===4){delete root.dataset.wfMode;transform()}
}
function setupToolbar(){
 const anchor=document.querySelector('.proposal-preview-zone');if(!anchor)return;
 let bar=document.getElementById('wiDeckFormats');
 if(!bar){bar=document.createElement('div');bar.id='wiDeckFormats';bar.className='wf-mode-switch';anchor.prepend(bar)}
 bar.innerHTML='<div><span class="wf-mode-eyebrow">NOUVEAU · PRÉSENTATIONS COMMERCIALES</span><strong>Choisir le format à transmettre</strong><p>Une recommandation, trois documents adaptés à leur destinataire.</p></div>'+
 '<div class="wf-buttons">'+[
 ['creative','Présentation créative','4 pages · prospect'],
 ['express','Pitch express','2 pages · premier contact'],
 ['brief','Brief opérationnel','2 pages · équipes internes']
 ].map(([id,title,subtitle])=>'<button type="button" data-wf-mode="'+id+'" aria-pressed="'+String(mode===id)+'"><b>'+title+'</b><span>'+subtitle+'</span></button>').join('')+'</div>'+
 '<p class="wf-mode-note">Les offres et les visuels restent à valider. Les formats partagent les mêmes données : aucune nouvelle campagne créée.</p>';
 bar.querySelectorAll('[data-wf-mode]').forEach(b=>b.onclick=()=>{
   const next=b.dataset.wfMode;if(next===mode)return;
   mode=next;
   bar.querySelectorAll('[data-wf-mode]').forEach(a=>a.setAttribute('aria-pressed',String(a.dataset.wfMode===mode)));
   const root=document.getElementById('proposalPages');if(root)delete root.dataset.wfMode;
   if(mode==='creative'){renderMode()}else if(root){
     if(root.querySelectorAll(':scope > .pdfpage').length!==4){
       originalMount.call(api,active.o,active.settings,active.save,active.back);
     }
     transform();
   }
   if(mode==='brief'||mode==='express')updatePageControls();
 });
}
api.mount=function(o,settings,save,back){
 if(observer)observer.disconnect();active={o,settings,save,back};mode='creative';
 originalMount.call(api,o,settings,save,back);
 setupToolbar();updatePageControls();
 const zone=document.getElementById('proposalPages');
 if(zone){observer=new MutationObserver(sync);observer.observe(zone,{childList:true})}
};
api.print=function(){
 if(mode==='creative')return originalPrint.call(api);
 const zone=document.getElementById('proposalPages');if(!zone||printBusy)return;
 transform();
 const pages=[...zone.querySelectorAll(':scope > .pdfpage')];if(pages.length!==2){alert('Les pages ne sont pas prêtes à être exportées.');return}
 const clone=document.createElement('div');
 clone.style.cssText='position:fixed;left:-11000px;width:794px;visibility:hidden;pointer-events:none';
 clone.innerHTML=pages.map(p=>p.outerHTML).join('');document.body.append(clone);
 let overflow=[];clone.querySelectorAll('.pdfpage').forEach((p,i)=>{p.style.display='flex';p.style.width='794px';p.style.height='1123px';p.style.zoom='1';if(p.scrollHeight>p.clientHeight+3)overflow.push(i+1)});
 clone.remove();
 if(overflow.length){alert('Le format déborde sur la page '+overflow.join(', ')+'. Raccourcissez les textes avant d’exporter.');return}
 printBusy=true;document.body.classList.add('print-proposal');
 const title=document.title;document.title=(mode==='brief'?'Brief opérationnel':'Pitch express')+' — '+active.o.brand;
 window.setTimeout(()=>{try{window.print()}finally{document.title=title;document.body.classList.remove('print-proposal');printBusy=false}},90);
};
})();