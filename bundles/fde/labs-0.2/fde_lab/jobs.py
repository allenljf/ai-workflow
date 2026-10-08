"""Bounded SQLite jobs. Local effects are atomic; unknown remote outcomes stop."""
from pathlib import Path
from decimal import Decimal,InvalidOperation
import hashlib,json,math,uuid
from .rag import database

def money(value):
    try:
        if not isinstance(value,str):raise ValueError()
        amount=Decimal(value)
        if not amount.is_finite() or amount<0 or amount>Decimal('100000'):raise ValueError()
    except (InvalidOperation,ValueError):raise ValueError('Invalid non-negative cost') from None
    return amount

def timestamp(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid timestamp')
    return value

def encoded(payload):
    try:text=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)
    except (ValueError,TypeError):raise ValueError('Invalid JSON payload') from None
    if len(text.encode())>50000:raise ValueError('Payload too large')
    return text

class JobStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with database(self.path) as db:
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1):raise ValueError('Unsupported jobs schema version')
            db.execute('''CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,tenant TEXT,key TEXT,payload TEXT,status TEXT,owner TEXT,lease_until REAL,lease_version INTEGER,attempts INTEGER,max_attempts INTEGER,deadline REAL,next_run REAL,cancel_requested INTEGER,cost TEXT,max_cost TEXT,step TEXT, UNIQUE(tenant,key))''')
            db.execute('CREATE TABLE IF NOT EXISTS receipts(job_id TEXT,step TEXT,payload TEXT,PRIMARY KEY(job_id,step))')
            db.execute('CREATE TABLE IF NOT EXISTS local_effects(job_id TEXT,step TEXT,payload TEXT,PRIMARY KEY(job_id,step))')
            db.execute('CREATE TABLE IF NOT EXISTS external_calls(job_id TEXT,step TEXT,status TEXT,PRIMARY KEY(job_id,step))')
            db.execute('PRAGMA user_version=1')
    def submit(self,tenant,key,payload,now,deadline,max_attempts=3,max_cost_usd='0'):
        timestamp(now);timestamp(deadline);money(max_cost_usd)
        if not isinstance(tenant,str) or not tenant or not isinstance(key,str) or not key or len(key)>200 or not isinstance(payload,dict) or type(max_attempts) is not int or not 1<=max_attempts<=10 or deadline<=now:raise ValueError('Invalid job contract')
        text=encoded(payload)
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM jobs WHERE tenant=? AND key=?',(tenant,key)).fetchone()
            if old:
                if old['payload']!=text:raise ValueError('Idempotency payload conflict')
                return self._row(old)
            id=str(uuid.uuid4())
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(id,tenant,key,text,'queued',None,0,0,0,max_attempts,deadline,now,0,'0',max_cost_usd,None))
            return self._row(db.execute('SELECT * FROM jobs WHERE id=?',(id,)).fetchone())
    @staticmethod
    def _row(row):
        d=dict(row);d['payload']=json.loads(d['payload']);return d
    def get(self,tenant,job_id):
        with database(self.path) as db:row=db.execute('SELECT * FROM jobs WHERE tenant=? AND id=?',(tenant,job_id)).fetchone()
        if not row:raise KeyError('Job not found')
        return self._row(row)
    def claim(self,owner,now,lease_seconds=30):
        timestamp(now)
        if not isinstance(owner,str) or not owner or type(lease_seconds) is not int or not 1<=lease_seconds<=300:raise ValueError('Invalid lease')
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE jobs SET status='ambiguous',owner=NULL WHERE status='running' AND (lease_until<=? OR deadline<=?) AND EXISTS (SELECT 1 FROM external_calls e WHERE e.job_id=jobs.id AND e.status='started')",(now,now))
            db.execute("UPDATE jobs SET status='cancelled',owner=NULL WHERE status='running' AND cancel_requested=1 AND (lease_until<=? OR deadline<=?)",(now,now))
            db.execute("UPDATE jobs SET status='failed',owner=NULL WHERE status IN ('queued','retry_wait','running') AND (deadline<=? OR (attempts>=max_attempts AND (status!='running' OR lease_until<=?)))",(now,now))
            row=db.execute("SELECT * FROM jobs WHERE cancel_requested=0 AND deadline>? AND attempts<max_attempts AND ((status IN ('queued','retry_wait') AND next_run<=?) OR (status='running' AND lease_until<=?)) ORDER BY next_run,id LIMIT 1",(now,now,now)).fetchone()
            if not row:return None
            db.execute("UPDATE jobs SET status='running',owner=?,lease_until=?,lease_version=lease_version+1,attempts=attempts+1 WHERE id=?",(owner,min(now+lease_seconds,row['deadline']),row['id']))
            return self._row(db.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone())
    def _owned(self,db,job_id,owner,version,now):
        timestamp(now)
        row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not row or row['status']!='running' or row['owner']!=owner or row['lease_version']!=version or row['lease_until']<=now or row['deadline']<=now:raise ValueError('Lease no longer owns this job')
        return row
    def _receipt(self,db,row,step,receipt,now,cost_usd,local):
        if not isinstance(step,str) or not step or len(step)>100:raise ValueError('Invalid checkpoint step')
        text=encoded(receipt);cost=money(cost_usd)
        old=db.execute('SELECT payload FROM receipts WHERE job_id=? AND step=?',(row['id'],step)).fetchone()
        if old:
            if old['payload']!=text:raise ValueError('Receipt conflict')
            return json.loads(old['payload'])
        if row['cancel_requested']:raise ValueError('Cancellation requested; do not start a new effect')
        total=money(row['cost'])+cost
        if total>money(row['max_cost']):raise ValueError('Job cost budget exhausted')
        if local:db.execute('INSERT INTO local_effects VALUES (?,?,?)',(row['id'],step,text))
        db.execute('INSERT INTO receipts VALUES (?,?,?)',(row['id'],step,text))
        db.execute('UPDATE jobs SET step=?,cost=? WHERE id=?',(step,str(total),row['id']))
        return receipt
    def apply_local_step(self,job_id,owner,lease_version,step,receipt,now,cost_usd='0'):
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=self._owned(db,job_id,owner,lease_version,now)
            return self._receipt(db,row,step,receipt,now,cost_usd,True)
    def checkpoint(self,job_id,owner,lease_version,step,receipt,now):
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=self._owned(db,job_id,owner,lease_version,now)
            # A completed remote receipt must be retained even if cancellation arrived during the call.
            data=dict(row);data['cancel_requested']=0
            self._receipt(db,data,step,receipt,now,'0',False)
            db.execute("UPDATE external_calls SET status='confirmed' WHERE job_id=? AND step=?",(job_id,step))
            if row['cancel_requested']:db.execute("UPDATE jobs SET status='cancelled',owner=NULL WHERE id=?",(job_id,))
    def finish(self,job_id,owner,lease_version,now):
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=self._owned(db,job_id,owner,lease_version,now)
            if db.execute("SELECT 1 FROM external_calls WHERE job_id=? AND status='started'",(job_id,)).fetchone():raise ValueError('Unresolved external call')
            db.execute('UPDATE jobs SET status=?,owner=NULL WHERE id=?',('cancelled' if row['cancel_requested'] else 'succeeded',job_id))
    def fail(self,job_id,owner,lease_version,now,kind):
        if kind not in {'transient','permanent','ambiguous'}:raise ValueError('Invalid failure class')
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=self._owned(db,job_id,owner,lease_version,now)
            status='ambiguous' if kind=='ambiguous' else 'retry_wait' if kind=='transient' and row['attempts']<row['max_attempts'] else 'failed'
            if db.execute("SELECT 1 FROM external_calls WHERE job_id=? AND status='started'",(job_id,)).fetchone():status='ambiguous'
            if row['cancel_requested'] and status!='ambiguous':status='cancelled'
            db.execute('UPDATE jobs SET status=?,owner=NULL,next_run=? WHERE id=?',(status,now+min(60,2**row['attempts']),job_id))
    def begin_external_step(self,job_id,owner,lease_version,step,now,cost_usd='0'):
        if not isinstance(step,str) or not step or len(step)>100:raise ValueError('Invalid external step')
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=self._owned(db,job_id,owner,lease_version,now)
            if row['cancel_requested']:raise ValueError('Cancellation requested')
            if db.execute('SELECT 1 FROM receipts WHERE job_id=? AND step=?',(job_id,step)).fetchone() or db.execute("SELECT 1 FROM external_calls WHERE job_id=? AND status='started'",(job_id,)).fetchone():raise ValueError('External step already completed or unresolved')
            total=money(row['cost'])+money(cost_usd)
            if total>money(row['max_cost']):raise ValueError('Job cost budget exhausted')
            db.execute("INSERT INTO external_calls VALUES (?,?,'started')",(job_id,step))
            db.execute('UPDATE jobs SET cost=? WHERE id=?',(str(total),job_id))
    def heartbeat(self,job_id,owner,lease_version,now,lease_seconds=30):
        if type(lease_seconds) is not int or not 1<=lease_seconds<=300:raise ValueError('Invalid lease')
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=self._owned(db,job_id,owner,lease_version,now)
            db.execute('UPDATE jobs SET lease_until=? WHERE id=?',(min(now+lease_seconds,row['deadline']),job_id))
    def cancel(self,tenant,job_id):
        with database(self.path) as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM jobs WHERE tenant=? AND id=?',(tenant,job_id)).fetchone()
            if not row:raise KeyError('Job not found')
            if row['status'] in {'queued','retry_wait'}:db.execute("UPDATE jobs SET status='cancelled',cancel_requested=1 WHERE id=?",(job_id,))
            elif row['status']=='running':db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(job_id,))
        return self.get(tenant,job_id)
    def receipts(self,tenant,job_id):
        self.get(tenant,job_id)
        with database(self.path) as db:return {r['step']:json.loads(r['payload']) for r in db.execute('SELECT * FROM receipts WHERE job_id=?',(job_id,))}
    def effect_count(self,job_id):
        with database(self.path) as db:return db.execute('SELECT COUNT(*) FROM local_effects WHERE job_id=?',(job_id,)).fetchone()[0]
