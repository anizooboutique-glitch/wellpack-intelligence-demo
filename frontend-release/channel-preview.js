/* Presentation previews adapt to the selected channel; no campaign is sent. */
(()=>{'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const line=v=>esc(v).replace(/\n/g,'<br>');
const params=v=>String(v??'').replace(/\{LIEN\}/g,'lien-campagne.fr').replace(/\{STOP\}/g,'STOP');
function render(o,m){
 const ch=String(m.channel||'SMS'),hasLP=ch.includes('LP'),isRCS=ch.startsWith('RCS');
 if(isRCS)return window.WIRCS.render(o,m);
 const accent=/^#[\da-f]{6}$/i.test(m.brandColor||'')?m.brandColor:'#f3e442';
 const sms=params(m.sms||o.creative?.sms||'Message de campagne à rédiger.');
 const title=m.lpTitle||m.product||'Votre offre';
 const why=m.benefit||'Bénéfice consommateur à préciser.';
 const dest=m.cta||'Découvrir la sélection';
 const url=m.destination||m.proofURL||'Destination à valider';
 const pieces=[
 '<div class="wi-channel-experience" style="--wi-channel-accent:'+esc(accent)+'">',
 '<div class="wi-channel-header"><span>02 / PARCOURS CLIENT</span><b>'+esc(ch)+'</b></div>',
 '<h2>'+ (hasLP?'Du message à la page de conversion.':'Un message court. Une action directe.')+'</h2>',
 '<p class="wi-channel-intro">Maquette spécifique à '+esc(o.brand)+' · '+esc(m.region||'périmètre à confirmer')+'</p>',
 '<div class="wi-channel-flow">',
 '<div class="wi-channel-handset"><div class="wi-channel-status">9:41 <span>▰ ▰ ▰</span></div>',
 '<div class="wi-channel-agent"><span>‹</span><strong>'+esc(o.brand)+'</strong><span>•••</span></div>',
 '<div class="wi-channel-day">Message commercial · exemple</div>',
 '<div class="wi-channel-bubble">'+line(sms)+'</div>',
 '<div class="wi-channel-smsnote">Le lien, l’émetteur et le STOP doivent être validés avant l’envoi.</div>',
 '<div class="wi-channel-composer">Message texte <span>›</span></div></div>',
 '<div class="wi-channel-arrow">→</div>',
 '<div class="wi-channel-landing">',
 '<div class="wi-channel-browser"><span>● ● ●</span> '+esc(o.brand)+' · page mobile</div>',
 '<div class="wi-channel-hero"><span>'+esc(o.brand)+'</span><strong>'+esc(title)+'</strong><small>Création de démonstration, visuels à valider</small></div>',
 '<div class="wi-channel-copy"><span>'+(hasLP?'LANDING PAGE DÉDIÉE':'PAGE DE DESTINATION EXISTANTE')+'</span>',
 '<h3>'+esc(title)+'</h3><p>'+esc(hasLP?(m.lpBody||why):why)+'</p>',
 '<div class="wi-channel-cta">'+esc(dest)+' <b>↗</b></div>',
 '<small>'+esc(m.region||'Magasins et zones à confirmer')+'</small></div></div></div>',
 '<div class="wi-channel-takeaway"><div><b>POURQUOI CE DISPOSITIF</b><p>'+esc(hasLP?'Le SMS présente le bénéfice en quelques mots. La LP précise l’offre, les modalités et le passage à l’action.':'Un SMS direct limite les étapes lorsque la page officielle couvre déjà les informations utiles.')+'</p></div><div><b>LE CLIC RENVOIE VERS</b><p>'+esc(url)+'</p></div></div>',
 '<div class="wi-channel-warning">Proposition non diffusée. Offre, cible, autorisations, tracking et disponibilité du point de vente à confirmer.</div></div>'
 ];
 return pieces.join('');
}
window.WIChannels={render};
})();