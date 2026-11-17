"""Assemble the original V3 frontend, verify its digest and test HTTP integration.
The base64 parts are an archive of UTF-8 assets, not executable Python.
No secret or paid API is needed during this build.
"""
from pathlib import Path
import base64, hashlib, json, lzma, os, secrets, tempfile

ROOT = Path(__file__).resolve().parent
parts = sorted((ROOT / 'frontend-release').glob('*.b64'))
assert [p.name for p in parts] == [f'{i:02}.b64' for i in range(12)], 'Incomplete frontend transfer'
encoded = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
raw = lzma.decompress(base64.b64decode(encoded, validate=True), memlimit=256*1024*1024)
assert hashlib.sha256(raw).hexdigest() == '2791fa1ba7175939b0c552900d5db118a18ccaed55bda57dffa72ed89d156879', 'Frontend integrity check failed'
assets = json.loads(raw)
assert set(assets) == {'index.html', 'live.js', 'setup.js'}
for name, content in assets.items():
    assert isinstance(content, str)
    (ROOT / 'static' / name).write_text(content, encoding='utf-8')
print('Frontend restored: original V3 assets, SHA-256 verified.', flush=True)

# Isolated smoke test: generated test credentials, no actual provider calls.
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
    from engine import config
    with TestClient(app, base_url='https://testserver', follow_redirects=False) as client:
        assert client.get('/healthz').status_code == 200
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
        health = client.get('/api/health')
        assert health.status_code == 200 and health.json()['mode'] == 'rules'
        assert client.get('/api/state').status_code == 200
        assert client.post('/api/settings/test', json={}, headers=headers).status_code == 400
        assert client.post('/api/logout', json={}, headers=headers).status_code == 200
        assert client.get('/').status_code == 303
print('HTTP smoke test passed: login, complete interface, scripts, API, paid API blocked, logout.', flush=True)
