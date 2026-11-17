"""Fixed external endpoints only. No redirects, private notes, client credentials or tool actions."""
import httpx
from . import config
class ProviderError(RuntimeError):pass
async def response(payload):
    key=config.get('OPENAI_API_KEY')
    if not key:raise ProviderError('Clé API absente.')
    config.reserve('openai')
    async with httpx.AsyncClient(timeout=90,trust_env=False,follow_redirects=False) as client:
        try:r=await client.post('https://api.openai.com/v1/responses',headers={'Authorization':'Bearer '+key},json=payload)
        except httpx.HTTPError as exc:raise ProviderError('Connexion au fournisseur impossible.') from exc
    if r.status_code!=200:
        label={401:'Clé API non acceptée.',403:'Accès API ou modèle non autorisé.',429:'Quota ou limite de débit API atteint.',400:'Modèle ou paramètres API non compatibles.'}.get(r.status_code,'Service IA indisponible.')
        raise ProviderError(label+f' (HTTP {r.status_code})')
    data=r.json()
    if data.get('status') not in (None,'completed'):raise ProviderError('Réponse IA incomplète : aucune proposition retenue.')
    return data

def output_text(data):
    return ''.join(c.get('text','') for item in data.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')
