import uuid
from fastapi import FastAPI, HTTPException
from app import db
from app.schemas import ProjectCreate, Approval, FollowUp, SimulatedSend
from app.agents import generate_package, compare_requirements

app=FastAPI(title="Task 3 — Meeting-to-Scope",version="1.0.0",
 description="Meeting transcript to scope, estimates and proposal; follow-up change detection against approved baseline.")

@app.on_event("startup")
def startup(): db.init_db()

@app.get("/")
def root(): 
    return {"service":"task3-meeting-to-scope","status":"ready","proposal_delivery":"simulated_only"}
@app.get("/health")
def health(): 
    return {"status":"ok","service":"task3-meeting-to-scope"}

def build_or_fail(client,project,transcript):
    try: return generate_package(client,project,transcript)
    except Exception as e: raise HTTPException(status_code=502,detail=f"Generation failed: {type(e).__name__}: {e}")

@app.post("/projects",status_code=201)
def create(payload: ProjectCreate):
    package=build_or_fail(payload.client_name,payload.project_name,payload.transcript)
    pid=str(uuid.uuid4()); db.create_project(pid,payload.client_name,payload.project_name)
    db.save_version(pid,1,payload.meeting_id,payload.transcript,package)
    db.audit(pid,"project_created","system",{"version":1,"meeting_id":payload.meeting_id})
    return {"project_id":pid,"version":1,"status":"draft","requires_human_approval":True,"package":package}

@app.get("/projects/{pid}")
def get_project(pid:str):
    p=db.project(pid)
    if not p: raise HTTPException(404,"Project not found")
    return {"project":p,"versions":db.versions(pid)}

@app.post("/projects/{pid}/approve")
def approve(pid:str,payload:Approval):
    if not db.project(pid): raise HTTPException(404,"Project not found")
    v=db.version(pid,payload.version)
    if not v: raise HTTPException(404,"Version not found")
    if not v["package"].get("requirements"): raise HTTPException(400,"Cannot approve scope without extracted requirements")
    db.approve(pid,payload.version,payload.reviewer,payload.notes)
    return {"project_id":pid,"approved_version":payload.version,"approved_by":payload.reviewer,"status":"approved","baseline_updated":True}

@app.post("/projects/{pid}/meetings/follow-up")
def followup(pid:str,payload:FollowUp):
    p=db.project(pid)
    if not p: raise HTTPException(404,"Project not found")
    baseline,base_v=db.baseline(pid)
    if not baseline: raise HTTPException(409,"Approve an initial scope before comparing a follow-up meeting")
    package=build_or_fail(p["client_name"],p["project_name"],payload.transcript)
    changes=compare_requirements(baseline.get("requirements",[]),package.get("requirements",[]))
    package["change_report"]={"compared_against_approved_version":base_v,**changes,"requires_human_review":True,
        "note":"This draft does not change the approved baseline until a reviewer approves it."}
    new_v=max((x["version"] for x in db.versions(pid)),default=0)+1
    db.save_version(pid,new_v,payload.meeting_id,payload.transcript,package)
    db.audit(pid,"follow_up_compared","system",{"version":new_v,"baseline_version":base_v,"changes":changes})
    return {"project_id":pid,"version":new_v,"status":"draft","requires_human_approval":True,
        "compared_against_approved_version":base_v,"change_report":package["change_report"],"package":package}

@app.post("/projects/{pid}/proposal/send")
def send(pid:str,payload:SimulatedSend):
    if not db.project(pid): raise HTTPException(404,"Project not found")
    result=db.send(pid,payload.version,payload.reviewer)
    if not result["ok"]: raise HTTPException(409,result["error"])
    return result

@app.get("/projects/{pid}/audit")
def audit(pid:str):
    if not db.project(pid): raise HTTPException(404,"Project not found")
    return {"project_id":pid,"events":db.audit_list(pid)}
