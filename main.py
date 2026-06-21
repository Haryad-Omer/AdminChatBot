from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, json, os, secrets

# --- CONFIG: All credentials from Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikmuklqzxxpsggxgklph.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_G4Ad6UbE5foWG0n2CTl6EA_vsiBHHpR")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "Admin626")
RECOVERY_TOKEN = os.environ.get("RECOVERY_TOKEN", "")
# ئەم کلیلە زۆر گرنگە لە سێرڤەری ئەدمینیشدا هەبێت بۆ هێنانەوەی باڵانسی ڕاستەقینە
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXPERTS = {"brain", "trans", "calc", "content", "report", "finder"}

def is_admin(key: str) -> bool:
    try:
        valid_main = secrets.compare_digest(key.encode("utf-8"), ADMIN_SECRET.encode("utf-8"))
        if valid_main: return True
        if RECOVERY_TOKEN:
            return secrets.compare_digest(key.encode("utf-8"), RECOVERY_TOKEN.encode("utf-8"))
        return False
    except Exception:
        return False

# --- ASYNC Supabase Request ---
async def supabase_request(table, method="GET", data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=params, timeout=15.0)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=data, timeout=15.0)
            elif method == "PATCH":
                resp = await client.patch(url, headers=headers, json=data, params=params, timeout=15.0)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers, params=params, timeout=15.0)
            else:
                return []
            return resp.json()
    except Exception as e:
        return {"message": str(e)}

class AdminAction(BaseModel): admin_key: str; id: int = None
class AddUserRequest(BaseModel): admin_key: str; username: str; password: str; plan: str = "standard"
class PlanRequest(BaseModel): admin_key: str; username: str; new_plan: str
class KnowledgeRequest(BaseModel): admin_key: str; topic: str; content: str; category: str = "brain"
class BalanceRequest(BaseModel): admin_key: str; username: str; new_balance: int
class PersonaRequest(BaseModel): admin_key: str; expert: str; role_text: str

@app.get("/")
async def home(): return {"status": "Zirak Admin Server Online"}

@app.post("/check_auth")
async def check_auth(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    return {"status": "success"}

# --- فەنکشنی تایبەت بە هێنانەوەی باڵانسی ڕاستەقینە لە OpenRouter ---
@app.post("/get_system_stats")
async def get_system_stats(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=10.0)
            data = res.json()
            
            if "data" in data:
                usage_cost = data["data"].get("usage", 0.0) # تێچوو بە دۆلار
                limit = data["data"].get("limit", 0.0)
                
                # خەمڵاندنی ژمارەی تۆکنەکان لەسەر بنەمای ئەوەی کە فلاش ٠.٤٠ دۆلارە بۆ هەر ملیۆنێک
                estimated_total_tokens = int((usage_cost / 0.40) * 1000000) if usage_cost > 0 else 0
                
                return {
                    "status": "success", 
                    "cost": usage_cost, 
                    "limit": limit, 
                    "estimated_tokens": estimated_total_tokens
                }
            return {"status": "error", "message": "Could not parse OpenRouter response"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/get_users")
async def get_users(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    res = await supabase_request("users", "GET", params={"order": "created_at.desc"})
    return res if isinstance(res, list) else []

@app.post("/add_user")
async def add_user(req: AddUserRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    if req.plan not in {"course", "standard", "pro"}: raise HTTPException(400, "Invalid plan")
    check = await supabase_request("users", "GET", params={"username": f"eq.{req.username}"})
    if isinstance(check, list) and check: return {"status": "error", "message": "ئەم ناوە هەیە"}
    await supabase_request("users", "POST", data={"username": req.username, "password": req.password, "used_tokens": 0, "plan": req.plan})
    return {"status": "success"}

@app.post("/update_balance")
async def update_balance(req: BalanceRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    await supabase_request("users", "PATCH", data={"used_tokens": req.new_balance}, params={"username": f"eq.{req.username}"})
    return {"status": "success"}

@app.post("/update_plan")
async def update_plan(req: PlanRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    if req.new_plan not in {"course", "standard", "pro", "locked"}: raise HTTPException(400, "Invalid plan")
    await supabase_request("users", "PATCH", data={"plan": req.new_plan}, params={"username": f"eq.{req.username}"})
    return {"status": "success"}

@app.post("/lock_user")
async def lock_user(req: PlanRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    await supabase_request("users", "PATCH", data={"plan": "locked"}, params={"username": f"eq.{req.username}"})
    return {"status": "success", "message": f"User {req.username} locked"}

@app.post("/delete_user")
async def delete_user(req: BalanceRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    await supabase_request("users", "DELETE", params={"username": f"eq.{req.username}"})
    return {"status": "success"}

@app.post("/get_logs")
async def get_logs(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    res = await supabase_request("chat_logs", "GET", params={"order": "created_at.desc", "limit": "100"}) 
    return res if isinstance(res, list) else []

@app.post("/add_knowledge")
async def add_knowledge(req: KnowledgeRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    await supabase_request("knowledge_base", "POST", data={"topic": req.topic, "content": req.content, "category": req.category})
    return {"status": "success"}

@app.post("/get_knowledge")
async def get_knowledge(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    res = await supabase_request("knowledge_base", "GET", params={"order": "created_at.desc"})
    return res if isinstance(res, list) else []

@app.post("/delete_knowledge")
async def delete_knowledge(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    await supabase_request("knowledge_base", "DELETE", params={"id": f"eq.{req.id}"})
    return {"status": "success"}

@app.post("/get_personas")
async def get_personas(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    db_personas = await supabase_request("personas", "GET")
    db_dict = {}
    if isinstance(db_personas, list):
        for p in db_personas:
            if "expert" in p and "role_text" in p: db_dict[p["expert"]] = p["role_text"]
    result = []
    
    # Defaults in case DB is empty
    defaults = {"brain": "", "trans": "", "calc": "", "content": "", "report": "", "finder": ""}
    for key in ALLOWED_EXPERTS:
        result.append({"expert": key, "role_text": db_dict.get(key, defaults.get(key, ""))})
    return result

@app.post("/update_persona")
async def update_persona(req: PersonaRequest):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    if req.expert not in ALLOWED_EXPERTS: raise HTTPException(400, "Invalid expert key")
    check = await supabase_request("personas", "GET", params={"expert": f"eq.{req.expert}"})
    if isinstance(check, list) and check:
        res = await supabase_request("personas", "PATCH", data={"role_text": req.role_text}, params={"expert": f"eq.{req.expert}"})
    else:
        res = await supabase_request("personas", "POST", data={"expert": req.expert, "role_text": req.role_text})
    return {"status": "success"}
