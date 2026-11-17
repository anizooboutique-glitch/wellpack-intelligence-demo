"""Restore the original V3 frontend and integrate the exact reviewed 12-case release.
The compressed delta contains UTF-8 HTML data only, never evaluated as Python.
No paid API is enabled, no credentials are changed, and no customer data is seeded.
"""
from pathlib import Path
import base64, hashlib, json, lzma, os, re, secrets, tempfile

ROOT = Path(__file__).resolve().parent
parts = sorted((ROOT / 'frontend-release').glob('*.b64'))
assert [p.name for p in parts] == [f'{i:02}.b64' for i in range(12)], 'Incomplete original frontend archive'
encoded = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
raw = lzma.decompress(base64.b64decode(encoded, validate=True), memlimit=256*1024*1024)
assert hashlib.sha256(raw).hexdigest() == '2791fa1ba7175939b0c552900d5db118a18ccaed55bda57dffa72ed89d156879', 'Original frontend integrity check failed'
assets = json.loads(raw)
assert set(assets) == {'index.html', 'live.js', 'setup.js'}
assert hashlib.sha256(assets['index.html'].encode('utf-8')).hexdigest() == '939099f0ccab6d862f69152a859c81166c6ef139b5b5fb80e27a6236522663a0', 'Unexpected base HTML'

# Apply the exact, hash-verified editorial release without retransferring unchanged assets.
case_parts = sorted((ROOT / 'frontend-release' / 'cases-20261117').glob('*.b64'))
assert [p.name for p in case_parts] == [f'{i:02}.b64' for i in range(4)], 'Incomplete 12-case release'
delta_raw = lzma.decompress(base64.b64decode(''.join(p.read_text(encoding='ascii').strip() for p in case_parts), validate=True), memlimit=256*1024*1024)
assert hashlib.sha256(delta_raw).hexdigest() == '37a1f9fc7f2fcc9ee5a4b6cbb8a88a6137209b84d44667fe6b67d23356b6954d', '12-case delta integrity check failed'
changes = json.loads(delta_raw)
lines = assets['index.html'].splitlines(keepends=True)
last = len(lines)
for start, end, replacement in reversed(changes):
    assert isinstance(start, int) and isinstance(end, int) and isinstance(replacement, str)
    assert 0 <= start <= end <= last, 'Invalid delta positions'
    lines[start:end] = [replacement]
    last = start
assets['index.html'] = ''.join(lines)
index_sha = hashlib.sha256(assets['index.html'].encode('utf-8')).hexdigest()
assert index_sha == '317963d7321b043551ab31a435091a8529acb71bc2143e2a54990af0da297f2d', 'Final HTML integrity check failed'
state_match = re.search(r'window\.WITestState=(.*?);window\.WITestCases=', assets['index.html'], flags=re.S)
assert state_match, 'Missing editorial collection'
case_state = json.loads(state_match.group(1))
assert len(case_state['ops']) == 12 and len(case_state['clients']) == 12
assert len({o['id'] for o in case_state['ops']}) == 12
assert all(o.get('proposal') and o.get('brief') and o['id'].startswith('test-20261117-') for o in case_state['ops'])
assert all(not c.get('website') for c in case_state['clients']), 'Editorial cases must not trigger scans'
assert 'for(const o of initialCases.ops)if(!state.ops.some(x=>x.id===o.id))state.ops.push(o);' in assets['index.html'], 'Non-destructive migration missing'
assert 'proposalExportBtn' in assets['index.html'] and 'window.WIProposal.print()' in assets['index.html'], 'PDF export missing'
(ROOT / 'static').mkdir(exist_ok=True)
for name, content in assets.items():
    assert isinstance(content, str)
    (ROOT / 'static' / name).write_text(content, encoding='utf-8')
release = {'release': '20261117-12cases', 'cases': 12, 'presentations': 12, 'frontendSha256': index_sha}
(ROOT / 'static' / 'release.json').write_text(json.dumps(release), encoding='utf-8')
# Expose non-sensitive release metadata on the existing public readiness endpoint.
app_path = ROOT / 'app.py'
app_text = app_path.read_text(encoding='utf-8')
old_health = "async def healthz():return {'ok':True}"
assert old_health in app_text, 'Readiness endpoint changed; inspect before deployment'
app_text = app_text.replace(old_health, 'async def healthz():return ' + repr({'ok': True, **release}), 1)
app_path.write_text(app_text, encoding='utf-8')
print('Frontend ready: 12 sourced editorial TEST cases, 12 presentations, PDF export, non-destructive migration; no paid API.', flush=True)

# Isolated HTTP smoke test with throw-away credentials and data. No external API calls.
with tempfile.TemporaryDirectory(prefix='wellpack-build-') as data:
    test_password = secrets.token_urlsafe(24)
    os.environ.update(APP_ENV='production', FREE_DEMO='true',
        APP_PASSWORD=test_password, SESSION_SECRET=secrets.token_hex(32),
        ALLOWED_HOSTS='testserver', WELLPACK_DATA_DIR=data,
        WELLPACK_DB=str(Path(data) / 'test.sqlite3'),
        WEB_SEARCH_ENABLED='false', AUTO_SCAN='false',
        MAX_PAID_REQUESTS_PER_DAY='0', OPENAI_API_KEY='')
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app, base_url='https://testserver', follow_redirects=False) as client:
        health = client.get('/healthz')
        assert health.status_code == 200 and health.json()['release'] == release['release']
        assert client.get('/').status_code == 303
        assert client.get('/api/state').status_code == 401
        assert client.get('/login').status_code == 200
        headers = {'X-Wellpack-Request': 'local-app', 'Origin': 'https://testserver'}
        assert client.post('/api/login', json={'password':'incorrect'}, headers=headers).status_code == 401
        assert client.post('/api/login', json={'password':test_password}, headers=headers).status_code == 200
        page = client.get('/')
        assert page.status_code == 200 and page.text == assets['index.html']
        for name in ('live.js', 'setup.js'):
            result = client.get('/static/' + name)
            assert result.status_code == 200 and result.text == assets[name]
        assert client.get('/static/release.json').json() == release
        health = client.get('/api/health')
        assert health.status_code == 200 and health.json()['mode'] == 'rules'
        assert client.get('/api/state').status_code == 200
        assert client.post('/api/settings/test', json={}, headers=headers).status_code == 400
        assert client.post('/api/logout', json={}, headers=headers).status_code == 200
        assert client.get('/').status_code == 303
print('HTTP smoke tests passed: complete 12-case interface, presentations, login, release metadata, paid API blocked, logout.', flush=True)
