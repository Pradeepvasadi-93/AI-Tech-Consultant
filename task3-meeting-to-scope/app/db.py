import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from app.config import DATABASE_PATH

def now(): return datetime.now(timezone.utc).isoformat()
def connect():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(DATABASE_PATH); db.row_factory=sqlite3.Row; return db

def init_db():
    with connect() as d:
        d.executescript('''
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, client_name TEXT, project_name TEXT, created_at TEXT, baseline_json TEXT, baseline_version INTEGER);
        CREATE TABLE IF NOT EXISTS versions(project_id TEXT, version INTEGER, meeting_id TEXT, transcript TEXT, package_json TEXT, status TEXT, created_at TEXT, approved_by TEXT, approved_at TEXT, PRIMARY KEY(project_id,version));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, event_type TEXT, actor TEXT, details_json TEXT, created_at TEXT);
        CREATE TABLE IF NOT EXISTS sends(id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, version INTEGER, reviewer TEXT, created_at TEXT, UNIQUE(project_id,version));
        ''')

def audit(pid, event, actor, details):
    with connect() as d: d.execute("INSERT INTO audit(project_id,event_type,actor,details_json,created_at) VALUES(?,?,?,?,?)",(pid,event,actor,json.dumps(details),now()))
def create_project(pid,client,name):
    with connect() as d: d.execute("INSERT INTO projects VALUES(?,?,?,?,NULL,NULL)",(pid,client,name,now()))
def save_version(pid,v,meeting,transcript,package):
    with connect() as d: d.execute("INSERT INTO versions(project_id,version,meeting_id,transcript,package_json,status,created_at) VALUES(?,?,?,?,?,'draft',?)",(pid,v,meeting,transcript,json.dumps(package,ensure_ascii=False),now()))
def project(pid):
    with connect() as d:
        r=d.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone()
        return dict(r) if r else None
def version(pid,v):
    with connect() as d:
        r=d.execute("SELECT * FROM versions WHERE project_id=? AND version=?",(pid,v)).fetchone()
        if not r: return None
        x=dict(r); x["package"]=json.loads(x.pop("package_json")); return x
def versions(pid):
    with connect() as d: return [dict(r) for r in d.execute("SELECT version,meeting_id,status,created_at,approved_by,approved_at FROM versions WHERE project_id=? ORDER BY version",(pid,)).fetchall()]
def baseline(pid):
    p=project(pid)
    return (json.loads(p["baseline_json"]) if p and p["baseline_json"] else None, p["baseline_version"] if p else None)
def approve(pid,v,reviewer,notes):
    item=version(pid,v)
    if not item: return False
    with connect() as d:
        d.execute("UPDATE versions SET status='approved',approved_by=?,approved_at=? WHERE project_id=? AND version=?",(reviewer,now(),pid,v))
        d.execute("UPDATE projects SET baseline_json=?,baseline_version=? WHERE id=?",(json.dumps(item["package"],ensure_ascii=False),v,pid))
    audit(pid,"version_approved",reviewer,{"version":v,"notes":notes}); return True
def send(pid,v,reviewer):
    item=version(pid,v)
    if not item or item["status"]!="approved": return {"ok":False,"error":"Only an approved version can be sent."}
    try:
        with connect() as d: d.execute("INSERT INTO sends(project_id,version,reviewer,created_at) VALUES(?,?,?,?)",(pid,v,reviewer,now()))
    except sqlite3.IntegrityError: return {"ok":False,"error":"This version was already simulated as sent."}
    audit(pid,"proposal_simulated_send",reviewer,{"version":v})
    return {"ok":True,"delivery":"simulated_only","project_id":pid,"version":v}
def audit_list(pid):
    with connect() as d:
        rows=d.execute("SELECT * FROM audit WHERE project_id=? ORDER BY id",(pid,)).fetchall()
        return [{**dict(r),"details":json.loads(r["details_json"])} for r in rows]
