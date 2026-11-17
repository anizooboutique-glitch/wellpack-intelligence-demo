from __future__ import annotations
import sqlite3,json
from pathlib import Path
from .crawl import now

class Store:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('CREATE TABLE IF NOT EXISTS brands(id TEXT PRIMARY KEY,data TEXT NOT NULL,last_scan TEXT)')
            con.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,brand_id TEXT NOT NULL,state TEXT NOT NULL,data TEXT NOT NULL,created TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS reports(brand_id TEXT PRIMARY KEY,data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS ops(id TEXT PRIMARY KEY,brand_id TEXT NOT NULL,data TEXT NOT NULL)')
            con.execute("UPDATE jobs SET state='interrupted' WHERE state IN ('queued','running')")
    def db(self):
        con=sqlite3.connect(self.path,timeout=15);con.row_factory=sqlite3.Row;return con
    def brands(self):
        with self.db() as c:return [dict(json.loads(r['data']),lastScan=r['last_scan']) for r in c.execute('SELECT * FROM brands')]
    def brand(self,id):return next((x for x in self.brands() if x['id']==id),None)
    def upsert_brand(self,b):
        old=self.brand(b['id']);changed=not old or any(old.get(k)!=b.get(k) for k in ('name','website','catalogue'))
        with self.db() as c:c.execute('INSERT INTO brands(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(b['id'],json.dumps(b,ensure_ascii=False)))
        return changed
    def job(self,id):
        with self.db() as c:r=c.execute('SELECT * FROM jobs WHERE id=?',(id,)).fetchone()
        return dict(json.loads(r['data']),id=r['id'],brandId=r['brand_id'],state=r['state'],created=r['created']) if r else None
    def jobs(self):
        with self.db() as c:ids=[r[0] for r in c.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT 100')]
        return [self.job(i) for i in ids]
    def set_job(self,id,brand,state,**data):
        old=self.job(id);payload={**(old or {}),**data};created=(old or {}).get('created',now())
        with self.db() as c:c.execute('INSERT INTO jobs VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,data=excluded.data',(id,brand,state,json.dumps(payload,ensure_ascii=False),created))
    def report(self,brand):
        with self.db() as c:r=c.execute('SELECT data FROM reports WHERE brand_id=?',(brand,)).fetchone()
        return json.loads(r[0]) if r else None
    def save_report(self,brand,report,ops):
        old=self.report(brand) or {};oldhash={p['url']:p['hash'] for p in old.get('pages',[])}
        report['changes']={'newPages':sum(p['url'] not in oldhash for p in report['pages']),'changedPages':sum(p['url'] in oldhash and oldhash[p['url']]!=p['hash'] for p in report['pages'])}
        active={o['id'] for o in ops}
        with self.db() as c:
            for row in c.execute('SELECT id,data FROM ops WHERE brand_id=?',(brand,)).fetchall():
                if row['id'] not in active:
                    data=json.loads(row['data']);data['live']['stale']=True;data['live']['warning']='Non reconfirmée par la dernière collecte : à vérifier avant utilisation.'
                    c.execute('UPDATE ops SET data=? WHERE id=?',(json.dumps(data,ensure_ascii=False),row['id']))
            for op in ops:
                op['live']['stale']=False
                c.execute('INSERT INTO ops VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(op['id'],brand,json.dumps(op,ensure_ascii=False)))
            c.execute('INSERT INTO reports VALUES(?,?) ON CONFLICT(brand_id) DO UPDATE SET data=excluded.data',(brand,json.dumps(report,ensure_ascii=False)))
            c.execute('UPDATE brands SET last_scan=? WHERE id=?',(now(),brand))
    def opportunities(self):
        with self.db() as c:return [json.loads(r[0]) for r in c.execute('SELECT data FROM ops LIMIT 500')]
