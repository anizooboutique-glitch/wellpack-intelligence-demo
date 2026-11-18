"""Authenticated prospect photo discovery and controlled import API."""
from pathlib import Path

ROUTES = """
from engine import image_discovery as _brand_pictures

class BrandPhotoSearch(BaseModel):
    website:str=Field(min_length=9,max_length=2000)
    catalogue:str=Field(default='',max_length=2000)
    query:str=Field(default='',max_length=300)
    @field_validator('website','catalogue')
    @classmethod
    def validate_url(cls,v,info):
        if not v and info.field_name=='catalogue':return ''
        try:return canonical(v)
        except FetchError as exc:raise ValueError(str(exc))

class BrandPhotoImport(BaseModel):
    token:str=Field(min_length=12,max_length=120,pattern=r'^[A-Za-z0-9_\\-]+$')

_PHOTO_GATE=asyncio.Semaphore(2)
_PHOTO_SEARCHES:dict[str,float]={}

@app.post('/api/brand-images/search')
async def find_brand_images(body:BrandPhotoSearch,request:Request):
    # Limit accidental repeated scans (one user/hosting instance prototype).
    key=request.client.host if request.client else 'unknown'
    current=asyncio.get_running_loop().time()
    if current-_PHOTO_SEARCHES.get(key,0)<3:
        raise HTTPException(429,'Requête récente : réessayez dans quelques secondes.')
    _PHOTO_SEARCHES[key]=current
    async with _PHOTO_GATE:
        try:
            return await asyncio.wait_for(
                _brand_pictures.discover(body.website,body.catalogue,body.query),timeout=52)
        except (FetchError,ValueError) as exc:raise HTTPException(400,str(exc))
        except asyncio.TimeoutError:raise HTTPException(504,'Recherche trop longue : essayez une page produit plus précise.')

@app.post('/api/brand-images/import')
async def load_brand_image(body:BrandPhotoImport):
    async with _PHOTO_GATE:
        try:
            return await asyncio.wait_for(_brand_pictures.import_image(body.token),timeout=32)
        except (FetchError,ValueError) as exc:raise HTTPException(400,str(exc))
        except asyncio.TimeoutError:raise HTTPException(504,'La photo ne répond pas : choisissez une autre image.')
"""

def apply(root,assets):
    root=Path(root)
    app_file=root/'app.py'
    app=app_file.read_text(encoding='utf-8')
    assert '/api/brand-images/search' not in app
    assert 'app.mount' in app
    app=app+'\n'+ROUTES
    compile(app,str(app_file),'exec')
    app_file.write_text(app,encoding='utf-8')
    css=(root/'frontend-release'/'brand-image-library.css').read_text(encoding='utf-8')
    js=(root/'frontend-release'/'brand-image-library.js').read_text(encoding='utf-8')
    h=assets['index.html']
    assert 'window.WIRCS=' in h
    assert 'window.WIPremiumRCS' in h
    assert '</head>' in h
    h=h.replace('</head>','<style id="brand-image-library-style">'+css+'</style><script id="brand-image-library-script">'+js+'</script></head>',1)
    assert 'WIBrandImages' in h
    assert 'brand-images/import' in h
    assets['index.html']=h
    return {'prospectImageDiscovery':True,'imageCardsEditable':True,'publicPagesOnly':True,'rightsWarnings':True}
