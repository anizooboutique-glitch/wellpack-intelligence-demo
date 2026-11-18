/* Premium, print-first RCS sales-page renderer. Keeps editable cards and image uploads. */
(()=>{'use strict';
const original=window.WIRCS;if(!original)return;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clean=v=>String(v??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const short=(v,n=100)=>{let s=String(v??'').replace(/\s+/g,' ').trim();return s.length>n?s.slice(0,n-1).replace(/\s+\S*$/,'')+'…':s};
function theme(o,m){const raw=original.palette(o,m);return {accent:/^#[0-9a-f]{6}$/i.test(m.brandColor||'')?m.brandColor:raw.accent,ink:raw.ink}}
function kind(o,m){let t=clean([o.brand,o.creative?.title,m.concept,o.focus?.product].join(' '));return /black friday|soldes|promotion|remise|-[0-9]+%|offres en cours/.test(t)?'promo':String(o.id).includes('-local-')||/atelier|march[eé] de no[eë]l|fleuriste|boutique/.test(t)?'local':'service'}
function art(o,m,c,i,k,mini){
 const p=theme(o,m),img=typeof c.imageData==='string'&&/^data:image\/(png|jpeg|webp);base64,[a-zA-Z0-9+/=]+$/.test(c.imageData)?c.imageData:'';
 const match=String(c.title||'').match(/-\s?\d{1,2}\s?%/);
 const big=k==='promo'?(match?match[0]:'LES OFFRES'):k==='local'?'À DÉCOUVRIR':'VOTRE SERVICE';
 const legend=k==='promo'?'DÉCOUVREZ NOS OFFRES':k==='local'?'UNE ADRESSE À DÉCOUVRIR':'UN SERVICE UTILE';
 return '<div class="prem-art prem-'+k+(mini?' prem-mini':'')+'" style="--prem-accent:'+esc(p.accent)+';--prem-ink:'+esc(p.ink)+'">'+
  (img?'<img src="'+esc(img)+'" alt="Visuel de carte '+(i+1)+'">':
  '<div class="prem-art-pattern" aria-hidden="true"><i></i><i></i><i></i></div><div class="prem-art-brand">'+esc(short(o.brand,26))+'<b>0'+(i+1)+'</b></div>'+
  '<div class="prem-art-title"><small>'+legend+'</small><strong>'+esc(big)+'</strong><span>'+esc(short(c.title,mini?36:64))+'</span></div>'+
  '<div class="prem-art-bottom">'+esc(k==='local'?short(o.geo||m.region||'Point de vente',36):'CONCEPT CRÉATIF · DÉMONSTRATION')+'</div>')+'</div>';
}
function render(o,m){
 const cards=original.cards(o,m).slice(0,4);
 const p=theme(o,m),k=kind(o,m),a=cards[0]||{title:m.product||'L’offre',body:m.benefit||'',cta:m.cta||'Découvrir'};
 const story=(cards.length>1?cards.slice(1):cards).map((c,j)=>{
   const idx=cards.length>1?j+1:j;
   return '<div class="prem-row"><span class="prem-index">0'+(idx+1)+'</span><div class="prem-thumb">'+art(o,m,c,idx,k,true)+'</div>'+
    '<div class="prem-row-copy"><small>CARTE 0'+(idx+1)+'</small><h4>'+esc(short(c.title,70))+'</h4><p>'+esc(short(c.body,145))+'</p><b>'+esc(short(c.cta,27))+' ↗</b></div></div>';
 }).join('');
 const sms=short(String(m.sms||o.creative?.sms||'SMS de repli à préparer').replace(/\{LIEN\}/g,'[lien]').replace(/\{STOP\}/g,'STOP'),170);
 const hasLP=String(m.channel||'').includes('LP');
 return '<div class="prem-pitch" style="--prem-accent:'+esc(p.accent)+';--prem-ink:'+esc(p.ink)+'">'+
 '<div class="prem-topline"><span>03 / 04 — EXPÉRIENCE CLIENT</span><span>'+esc(k==='promo'?'OFFRE COMMERCIALE':k==='local'?'ACTIVATION LOCALE':'SERVICE & RENDEZ-VOUS')+'</span></div>'+
 '<div class="prem-head"><div><span>PROPOSITION RCS · '+cards.length+' CARTE'+(cards.length>1?'S':'')+'</span><h2>'+esc(short(o.brand,36))+' <em>dans la conversation.</em></h2></div><b>RCS ↗</b></div>'+
 '<div class="prem-main"><div class="prem-col-phone"><div class="prem-phone"><div class="prem-phone-top">9:41 <span>▮▮ ▰</span></div><div class="prem-agent"><b>‹</b><span class="prem-avatar">'+esc(String(o.brand||'').replace(/[^a-zA-ZÀ-ÿ]/g,'').slice(0,2).toUpperCase())+'</span><div><strong>'+esc(short(o.brand,22))+'</strong><small>Aperçu de conversation · RCS</small></div><b>⋮</b></div><div class="prem-thread"><div class="prem-date">Aujourd’hui · maquette</div><div class="prem-message">'+art(o,m,a,0,k,false)+'<div class="prem-copy"><h3>'+esc(short(a.title,68))+'</h3><p>'+esc(short(a.body,165))+'</p></div><div class="prem-cta">'+esc(short(a.cta,26))+' <b>↗</b></div></div><div class="prem-pips">'+cards.map((_,i)=>'<i'+(i===0?' class="on"':'')+'></i>').join('')+'</div></div><div class="prem-compose">＋ <span>Message</span> ›</div></div><div class="prem-caption">● Concept graphique à valider par la marque</div></div>'+
 '<div class="prem-col-story"><div class="prem-story-label"><strong>LE CARROUSEL</strong><span>'+cards.length+' séquences</span></div><div class="prem-story">'+story+'</div><div class="prem-destination"><small>APRÈS LE CLIC</small><h3>'+esc(short(m.cta||a.cta||'Découvrir',34))+' ↗</h3><p>'+esc(short(hasLP?(m.lpBody||m.benefit||'Landing page dédiée'):'Destination officielle de la marque et conditions de l’offre',165))+'</p><b>'+esc(hasLP?'RCS → LP → Action':'RCS → Destination → Action')+'</b></div></div></div>'+
 '<div class="prem-fallback"><b>SMS DE REPLI</b><span>'+esc(sms)+'</span></div>'+
 '<div class="prem-disclaimer">Piste graphique illustrative, non commandée. Agent, visuels, offre, droits, prix et conditions à valider avant toute utilisation commerciale.</div>'+
 '</div>';
}
original.render=render;
window.WIPremiumRCS={render,kind};
})();