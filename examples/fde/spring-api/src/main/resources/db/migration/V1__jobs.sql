CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,tenant TEXT,key TEXT,payload TEXT,status TEXT,owner TEXT,lease_until REAL,lease_version INTEGER,attempts INTEGER,max_attempts INTEGER,deadline REAL,next_run REAL,cancel_requested INTEGER,cost TEXT,max_cost TEXT,step TEXT, UNIQUE(tenant,key));
CREATE TABLE IF NOT EXISTS receipts(job_id TEXT,step TEXT,payload TEXT,PRIMARY KEY(job_id,step));
CREATE TABLE IF NOT EXISTS local_effects(job_id TEXT,step TEXT,payload TEXT,PRIMARY KEY(job_id,step));
CREATE TABLE IF NOT EXISTS external_calls(job_id TEXT,step TEXT,status TEXT,PRIMARY KEY(job_id,step));
PRAGMA user_version=1;
