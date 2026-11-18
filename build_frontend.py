"""Restore verified assets, then apply reviewed editorial and presentation changes."""
from pathlib import Path
import base64, hashlib, json, lzma, os, re, runpy, secrets, tempfile
ROOT = Path(__file__).resolve().parent
parts = sorted((ROOT / 'frontend-release').glob('*.b64'))
assert [p.name for p in parts] == [f'{i:02}.b64' for i in range(12)], 'Incomplete original frontend archive'
raw = lzma.decompress(base64.b64decode(''.join(p.read_text(encoding='ascii').strip() for p in parts), validate=True), memlimit=256*1024*1024)
assert hashlib.sha256(raw).hexdigest() == '2791fa1ba7175939b0c552900d5db118a18ccaed55bda57dffa72ed89d156879', 'Original integrity failure'
assets = json.loads(raw)
assert set(assets) == {'index.html', 'live.js', 'setup.js'}
assert hashlib.sha256(assets['index.html'].encode()).hexdigest() == '939099f0ccab6d862f69152a859c81166c6ef139b5b5fb80e27a6236522663a0'
case_parts = sorted((ROOT / 'frontend-release' / 'cases-20261117').glob('*.b64'))
assert [p.name for p in case_parts] == [f'{i:02}.b64' for i in range(4)]
delta_raw = lzma.decompress(base64.b64decode(''.join(p.read_text(encoding='ascii').strip() for p in case_parts), validate=True), memlimit=256*1024*1024)
assert hashlib.sha256(delta_raw).hexdigest() == '37a1f9fc7f2fcc9ee5a4b6cbb8a88a6137209b84d44667fe6b67d23356b6954d'
lines = assets['index.html'].splitlines(keepends=True);last = len(lines)
for start,end,replacement in reversed(json.loads(delta_raw)):
    assert isinstance(start,int) and isinstance(end,int) and isinstance(replacement,str)
    assert 0 <= start <= end <= last
    lines[start:end]=[replacement];last=start
assets['index.html']=''.join(lines)
assert hashlib.sha256(assets['index.html'].encode()).hexdigest() == '317963d7321b043551ab31a435091a8529acb71bc2143e2a54990af0da297f2d'

# Source-controlled Python patches, not executable content from the data archives.
runpy.run_path(str(ROOT/'frontend-release'/'manage_v1.py'))['apply'](ROOT,assets)
counts=runpy.run_path(str(ROOT/'frontend-release'/'editorial_v2.py'))['apply'](ROOT,assets)
rcs=runpy.run_path(str(ROOT/'frontend-release'/'rcs_v1.py'))['apply'](ROOT,assets)
local=runpy.run_path(str(ROOT/'frontend-release'/'regional_drive_v1.py'))['apply'](ROOT,assets)
phase1=runpy.run_path(str(ROOT/'frontend-release'/'phase1_dashboard.py'))['apply'](ROOT,assets)
channels=runpy.run_path(str(ROOT/'frontend-release'/'channel_preview_v2.py'))['apply'](ROOT,assets)
visible=runpy.run_path(str(ROOT/'frontend-release'/'visible_radar_v2.py'))['apply'](ROOT,assets)
repair=runpy.run_path(str(ROOT/'frontend-release'/'home_repair_v3.py'))['apply'](ROOT,assets)
searchfix=runpy.run_path(str(ROOT/'frontend-release'/'search_reset_v4.py'))['apply'](ROOT,assets)
case_state=json.loads(re.search(r'window\.WITestState=(.*?);window\.WITestCases=',assets['index.html'],re.S).group(1))
assert len(case_state['ops'])==23 and len(case_state['clients'])==23
assert len({o['id'] for o in case_state['ops']})==23
assert all(o.get('proposal') and o.get('brief') for o in case_state['ops'])
assert all(not c.get('website') for c in case_state['clients'])
assert all(1 <= len(o['creative']['rcs']) <= 4 for o in case_state['ops'])
assert len([o for o in case_state['ops'] if o['id'].startswith('test-20261118-local-')])==8
assert all('drive-to-store' in o['notes'] for o in case_state['ops'] if o['id'].startswith('test-20261118-local-'))
assert 'proposalExportBtn' in assets['index.html'] and 'window.WIProposal.print()' in assets['index.html']
assert 'data-remove-brand' in assets['index.html'] and 'data-remove-source' in assets['index.html']
assert 'Darty — Faire réparer son four avant les fêtes' in assets['index.html']
assert 'window.WIChannels.render(op,m)' in assets['index.html']
assert 'Personnaliser les cartes RCS' in assets['index.html']
assert all(k in assets['index.html'] for k in ['id="wiChannel"','id="wiStage"','id="wiPriority"','data-propose-fast','opportunityRank'])
assert 'reader.readAsDataURL(f)' in assets['index.html']
assert 'window.WIChannels.render(op,m)' in assets['index.html']
assert 'wi-channel-smsnote' in assets['index.html']
assert 'id="wiResetEverything"' in assets['index.html']
assert 'function wiClearAllFilters()' in assets['index.html']
assert 'wiRepairStaleSearch()' in assets['index.html']
assert '<section class="wi-v2-radar"' not in assets['index.html']
assert 'id="wiResetEverything"' in assets['index.html']
assert 'date de vérification' in assets['index.html']
(ROOT/'static').mkdir(exist_ok=True)
for name,content in assets.items():
    assert isinstance(content,str)
    (ROOT/'static'/name).write_text(content,encoding='utf-8')
release={'release':'20261118-intersport-search-reset','cases':23,'presentations':23,'deletionControls':True,'plainTitles':True,**rcs,**local,**phase1,**channels,**visible,**repair,**searchfix,'frontendSha256':hashlib.sha256(assets['index.html'].encode()).hexdigest()}
(ROOT/'static'/'release.json').write_text(json.dumps(release),encoding='utf-8')
app_path=ROOT/'app.py';app_text=app_path.read_text(encoding='utf-8')
old_health="async def healthz():return {'ok':True}"
assert old_health in app_text
app_text=app_text.replace(old_health,'async def healthz():return '+repr({'ok':True,**release}),1)
app_path.write_text(app_text,encoding='utf-8')
print('Frontend ready: full campaign grid, working filters and scrolling, permanent Intersport removal, 23 cases and PDF; no paid API.',flush=True)

with tempfile.TemporaryDirectory(prefix='wellpack-build-') as data:
    test_password=secrets.token_urlsafe(24)
    os.environ.update(APP_ENV='production',FREE_DEMO='true',APP_PASSWORD=test_password,SESSION_SECRET=secrets.token_hex(32),ALLOWED_HOSTS='testserver',WELLPACK_DATA_DIR=data,WELLPACK_DB=str(Path(data)/'test.sqlite3'),WEB_SEARCH_ENABLED='false',AUTO_SCAN='false',MAX_PAID_REQUESTS_PER_DAY='0',OPENAI_API_KEY='')
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app,base_url='https://testserver',follow_redirects=False) as client:
        assert client.get('/healthz').json()['release']==release['release']
        assert client.get('/').status_code==303
        assert client.get('/api/state').status_code==401
        assert client.delete('/api/brands/example').status_code==401
        headers={'X-Wellpack-Request':'local-app','Origin':'https://testserver'}
        assert client.post('/api/login',json={'password':'incorrect'},headers=headers).status_code==401
        assert client.post('/api/login',json={'password':test_password},headers=headers).status_code==200
        page=client.get('/')
        assert page.status_code==200 and page.text==assets['index.html']
        for name in ('live.js','setup.js'):
            result=client.get('/static/'+name)
            assert result.status_code==200 and result.text==assets[name]
        assert client.get('/static/release.json').json()==release
        assert client.get('/api/health').json()['mode']=='rules'
        assert client.post('/api/settings/test',json={},headers=headers).status_code==400
        brand={'id':'delete-smoke','name':'Test suppression','website':''}
        assert client.post('/api/brands',json=brand,headers=headers).status_code==200
        assert client.delete('/api/brands/delete-smoke').status_code==403
        assert client.delete('/api/brands/delete-smoke',headers=headers).status_code==200
        result=client.get('/api/state').json()
        assert 'delete-smoke' in result['deletedIds'] and not result['brands']
        assert client.post('/api/brands',json=brand,headers=headers).status_code==410
        assert client.delete('/api/brands/delete-smoke',headers=headers).status_code==200
        assert client.post('/api/logout',json={},headers=headers).status_code==200
        assert client.get('/').status_code==303
print('HTTP smoke tests passed: authentication, 23 presentations with 8 local DTS scenarios, deletion, stale-save rejection, paid API blocked.',flush=True)
