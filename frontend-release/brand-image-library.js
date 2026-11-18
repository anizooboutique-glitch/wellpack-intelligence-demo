/* Brand imagery from public pages, selected by the user before entering any RCS PDF. */
(()=>{'use strict';
const base=window.WIRCS;if(!base||!base.mountEditor)return;
const previous=base.mountEditor;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=u=>{try{let p=new URL(u);return p.protocol==='https:'||p.protocol==='http:'?p.href:''}catch{return''}};
function pickSources(o){
 const b=(window.WIApp?.clients?.()||[]).find(c=>c.id===o.clientId||c.name===o.brand)||{};
 const links=(o.evidence||[]).filter(e=>e.url).map(e=>e.url);
 const site=safeURL(b.website)||safeURL(b.catalogue)||safeURL(links[0])||safeURL(o.proposal?.destination);
 const pages=[safeURL(b.catalogue),...links].filter(Boolean);
 const extra=pages.find(u=>{try{return new URL(u).hostname===new URL(site).hostname&&u!==site}catch{return false}})||'';
 return {site,extra,brand:b.name||o.brand};
}
function message(node,s,error=false){node.textContent=s;node.style.color=error?'#a12626':'#566474'}
async function shrink(data){
 const img=new Image();img.src=data;await img.decode();
 const scale=Math.min(1,650/Math.max(img.width,img.height));
 const canvas=document.createElement('canvas');
 canvas.width=Math.max(1,Math.round(img.width*scale));canvas.height=Math.max(1,Math.round(img.height*scale));
 const ctx=canvas.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
 let quality=.77,output=canvas.toDataURL('image/jpeg',quality);
 while(output.length>220000&&quality>.35){quality-=.12;output=canvas.toDataURL('image/jpeg',quality)}
 if(output.length>220000)throw Error('Visuel trop complexe pour un PDF local. Choisissez une autre photo.');
 return output;
}
function applyImage(o,m,onChange,index,imageData,sourceURL){
 const all=base.cards(o,m).map(c=>({...c}));
 if(!all[index])throw Error('Carte RCS introuvable.');
 all[index].imageData=imageData;
 all[index].sourceURL=sourceURL;
 m.rcsCardsJSON=JSON.stringify(all);
 if(index===0)m.imageData=imageData;
 m.approval.editorial=false;
 onChange();
}
function mount(host,o,m,onChange){
 previous(host,o,m,onChange);
 if(!host?.querySelector('#p_channel')||host.querySelector('.wi-image-discovery'))return;
 const {site,extra}=pickSources(o);
 const details=document.createElement('details');details.className='pdetails wi-image-discovery';
 const cards=base.cards(o,m);
 const choices=cards.map((c,i)=>'<option value="'+i+'">Carte '+(i+1)+' — '+esc(c.title||'Visuel')+'</option>').join('');
 details.innerHTML='<summary>Photos du site prospect · rechercher et choisir</summary>'+
 '<p class="wi-image-tip">Recherche dans les pages publiques indiquées pour cette marque. Les visuels restent à faire valider avant tout envoi au prospect.</p>'+
 '<div class="wi-image-controls"><label>Site officiel ou page produit <input class="wi-image-site" type="url" placeholder="https://www.marque.fr" value="'+esc(site)+'"></label>'+
 '<label>Page catalogue ou collection (facultatif) <input class="wi-image-extra" type="url" value="'+esc(extra)+'" placeholder="https://www.marque.fr/collection"></label>'+
 '<label>Placer dans <select class="wi-image-card">'+choices+'</select></label></div>'+
 '<button type="button" class="btn light wi-image-find">Rechercher des photos</button>'+
 '<p class="wi-image-status" aria-live="polite"></p><div class="wi-image-gallery" aria-label="Images trouvées sur le site prospect"></div>'+
 '<p class="wi-image-tip">Source affichée pour chaque visuel. Une image publique n’est pas libre de droits. Seule votre sélection est intégrée au PDF ; aucune image n’est envoyée à une IA.</p>';
 const ed=host.querySelector('.rx-editor');
 if(ed)ed.before(details);else host.querySelector('.step-controls')?.before(details);
 const btn=details.querySelector('.wi-image-find'),status=details.querySelector('.wi-image-status'),gallery=details.querySelector('.wi-image-gallery'),card=details.querySelector('.wi-image-card');
 btn.onclick=async()=>{
   const website=details.querySelector('.wi-image-site').value.trim();
   const catalogue=details.querySelector('.wi-image-extra').value.trim();
   if(!safeURL(website)){message(status,'Ajoutez une URL publique http(s) de la marque.',true);return}
   btn.disabled=true;gallery.innerHTML='';message(status,'Recherche des visuels et vérification des pages publiques…');
   try{
     const res=await fetch('/api/brand-images/search',{method:'POST',headers:{'Content-Type':'application/json','X-Wellpack-Request':'local-app'},body:JSON.stringify({website,catalogue,query:[o.brand,o.focus?.product,o.focus?.moment].filter(Boolean).join(' ')})});
     const data=await res.json();
     if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Recherche indisponible.');
     const images=data.images||[];
     message(status,images.length?images.length+' visuel(s) proposés. Choisissez une image pour l’ajouter à la carte sélectionnée.':(data.warnings?.[0]||'Aucune photo exploitable sur ces pages. Essayez une page produit ou galerie.'));
     for(const item of images){
       const tile=document.createElement('article');tile.className='wi-image-tile';
       const src=safeURL(item.url);if(!src)continue;
       const preview=document.createElement('img');preview.src=src;preview.alt=item.label||'Visuel du site';preview.loading='lazy';preview.referrerPolicy='no-referrer';preview.onerror=()=>{preview.style.display='none';tile.classList.add('wi-image-no-preview')};
       const caption=document.createElement('div');caption.className='wi-image-tile-caption';
       const title=document.createElement('strong');title.textContent=(item.label||'Photo du site').slice(0,85);
       const source=document.createElement('a');source.href=item.sourcePage;source.target='_blank';source.rel='noopener noreferrer';source.textContent='Voir la page source ↗';
       const use=document.createElement('button');use.type='button';use.className='btn sm';use.textContent='Utiliser cette photo';
       use.onclick=async()=>{
         use.disabled=true;message(status,'Import et adaptation de la photo pour le PDF…');
         try{
           const response=await fetch('/api/brand-images/import',{method:'POST',headers:{'Content-Type':'application/json','X-Wellpack-Request':'local-app'},body:JSON.stringify({token:item.token})});
           const answer=await response.json();
           if(!response.ok)throw Error(typeof answer.detail==='string'?answer.detail:'Import impossible');
           const imageData=await shrink(answer.imageData);
           applyImage(o,m,onChange,Number(card.value),imageData,answer.url);
           message(status,'Photo ajoutée à la carte '+(Number(card.value)+1)+'. Elle sera reprise dans la maquette et le PDF. Droits à valider.');
           use.textContent='Photo ajoutée ✓';
         }catch(e){message(status,e.message||'Erreur d’import',true);use.disabled=false}
       };
       caption.append(title,source,use);tile.append(preview,caption);gallery.append(tile);
     }
     if(data.warnings?.length){const p=document.createElement('p');p.className='wi-image-warnings';p.textContent='Pages non lues : '+data.warnings.join(' · ').slice(0,390);gallery.after(p)}
   }catch(e){message(status,e.message||'Recherche impossible',true)}
   finally{btn.disabled=false}
 };
}
base.mountEditor=mount;
window.WIBrandImages={pickSources};
})();