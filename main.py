from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, json, os, secrets

# --- Graceful slowapi import (rate limiting) ---
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMIT_ENABLED = True
except ImportError:
    RATE_LIMIT_ENABLED = False

# --- CONFIG: All credentials from Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikmuklqzxxpsggxgklph.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_G4Ad6UbE5foWG0n2CTl6EA_vsiBHHpR")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "Admin626")
RECOVERY_TOKEN = os.environ.get("RECOVERY_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")

# هێشتنەوەی هەموو شتێک لەسەر Gemini وەک داواکاریت
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "google/gemini-3.1-flash-lite")

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    class _DummyLimiter:
        def limit(self, *a, **kw):
            def decorator(f): return f
            return decorator
    limiter = _DummyLimiter()

ALLOWED_EXPERTS = {"brain", "trans", "calc", "content", "report", "finder"}

PROMPTS = {
    "brain": "تۆ ناوت (مێشکی بازرگانی)یە. تۆ ڕاوێژکاری سەرەکی بزنس و ستراتیژییەتیت.\nئەرکەکانت:\n١. وەڵامدانەوەی پرسیارە گشتییەکانی بازرگانی و ئیدارە.\n٢. ڕوونکردنەوەی پلانی بازرگانی و گەشەپێدان.\n٣. هەمیشە بە کوردی و بە شێوازێکی پرۆفیشناڵ و هاندەر وەڵام بدەرەوە.",
    "trans": "تۆ ناوت (وەرگێڕی بازرگانی)یە. ئەرکی تۆ تەنها وەرگێڕانە بۆ زمانی کوردی.\nئەرکەکانت:\n١. هەر دەقێک (ئینگلیزی یان چینی)ت بۆ هات، بیکە بە کوردییەکی پاراو و بازرگانی.\n٢. زاراوە بازرگانییەکان (وەک FOB, CIF, MOQ) بە کوردی ڕوون بکەرەوە.\n٣. هیچ قسەی زیادە مەکە، تەنها وەرگێڕانەکە ئەنجام بدە.",
    "calc": "تۆ ناوت (حاسیبەی لۆجستی)یە. تۆ پسپۆڕی ژمارە و قازانج و تێچوویت.\nئەرکەکانت:\n١. هەژمارکردنی قازانجی صاف (Net Profit).\n٢. هەژمارکردنی تێچووی گومرگ و گواستنەوە (Shipping & Customs).\n٣. یارمەتی بەکارهێنەر بدە بزانێت ئایا بەرهەمێک قازانجی تێدایە یان نا.\n٤. وەڵامەکانت بە ژمارە و خاڵبەندی ڕێکبخە.",
    "content": "تۆ ناوت (ستراتیژیستی ناوەڕۆک)ە. تۆ پسپۆڕی مارکێتینگ و سۆشیاڵ میدیایت.\nئەرکەکانت:\n١. نووسینی ڕیکلامی سەرنجڕاکێش (Ad Copy) بۆ فەیسبووک و ئینستاگرام.\n٢. دانانی پلانی بڵاوکردنەوە (Content Calendar).\n٣. نووسینی سکریپتی ڤیدیۆ بۆ ڕیکلامی بەرهەمەکان.\n٤. بەکارهێنانی زمانی بازاڕ و کاریگەر.",
    "report": "تۆ ناوت (ڕاپۆرتی نهێنی)یە. تۆ شیکەرەوەی داتا و ئەدای کاریت.\nئەرکەکانت:\n١. شیکردنەوەی کێشەکانی بزنسەکە.\n٢. پێدانی ئامۆژگاری ڕەخنەگرانە بۆ باشترکردنی فرۆش.\n٣. کورتکردنەوەی زانیارییە ئاڵۆزەکان بۆ ڕاپۆرتێکی پوخت.",
    "finder": "تۆ ناوت (دۆزەرەوەی بەرهەم)ە. تۆ پسپۆڕی دۆزینەوەی بەرهەمی براوەیت (Winning Products).\nئەرکەکانت:\n١. پێدانی بیرۆکەی بەرهەمی نوێ بۆ فرۆشتن.\n٢. شیکردنەوەی ئەوەی بۆچی بەرهەمێک باشە یان خراپە.\n٣. یارمەتیدان لە دۆزینەوەی بەرهەم لە عەلی بابا بەپێی خواستی بازاڕی عێراق و کوردستان."
}

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
class LoginRequest(BaseModel): username: str; password: str
class PersonaRequest(BaseModel): admin_key: str; expert: str; role_text: str

@app.get("/")
async def home(): return {"status": "Zirak AI Server Online - Admin & User Backend"}

@app.post("/check_auth")
async def check_auth(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    return {"status": "success"}

# --- NEW: Get Real API Stats from OpenRouter ---
@app.post("/get_system_stats")
async def get_system_stats(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }
    try:
        async with httpx.AsyncClient() as client:
            # پەیوەندی کردن بە OpenRouter بۆ هێنانەوەی باڵانسی ڕاستەقینەی کلیلەکە
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

@app.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest):
    users = await supabase_request("users", "GET", params={"username": f"eq.{req.username.strip()}", "password": f"eq.{req.password.strip()}"})
    if isinstance(users, list) and users:
        user = users[0]
        if user.get("plan") == "locked": raise HTTPException(status_code=403, detail="ئەم ئەکاونتە قفڵکراوە.")
        return {"status": "success", "user": user}
    raise HTTPException(status_code=401, detail="هەڵە لە چوونەژوورەوە")

@app.post("/get_logs")
async def get_logs(req: AdminAction):
    if not is_admin(req.admin_key): raise HTTPException(401, "Unauthorized")
    res = await supabase_request("chat_logs", "GET", params={"order": "created_at.desc", "limit": "100"}) # زیادکرا بۆ ١٠٠
    return res if isinstance(res, list) else []

@app.get("/get_history")
async def get_history(username: str):
    res = await supabase_request("chat_logs", "GET", params={"username": f"eq.{username}", "order": "created_at.asc"})
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
    for key, text in PROMPTS.items():
        result.append({"expert": key, "role_text": db_dict.get(key, text)})
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

@app.post("/chat")
@limiter.limit("15/minute")
async def chat_endpoint(
    request: Request, prompt: str = Form(...), expert: str = Form(...), username: str = Form(...), history: str = Form("[]"), image_url: str = Form(None)
):
    if expert not in ALLOWED_EXPERTS: raise HTTPException(400, "Invalid expert")
    current_balance = 0
    u = await supabase_request("users", "GET", params={"username": f"eq.{username}"})
    if isinstance(u, list) and u:
        if u[0].get("plan") == "locked": raise HTTPException(403, "Account locked")
        current_balance = u[0].get("used_tokens", 0)

    system_instruction = PROMPTS.get(expert, PROMPTS["brain"])
    try:
        p_db = await supabase_request("personas", "GET", params={"expert": f"eq.{expert}"})
        if isinstance(p_db, list) and p_db and p_db[0].get("role_text"): system_instruction = p_db[0]["role_text"]
    except Exception: pass

    if expert == "brain":
        kb = await supabase_request("knowledge_base", "GET")
        if isinstance(kb, list) and kb:
            knowledge_lines = "\n".join(f"- {k.get('topic','')}: {k.get('content','')}" for k in kb)
            system_instruction += f"\n\n[OFFICIAL KNOWLEDGE BASE — MUST FOLLOW]:\n{knowledge_lines}\nYou MUST use this information."

    system_instruction += "\n\n[OUTPUT RULES]: Format professionally using Markdown. Respond in user's language."

    messages = [{"role": "system", "content": system_instruction}]
    try:
        db_history = await supabase_request("chat_logs", "GET", params={"username": f"eq.{username}", "expert": f"eq.{expert}", "order": "created_at.asc", "limit": "20"})
        if isinstance(db_history, list) and db_history:
            for log in db_history:
                if log.get("user_message"): messages.append({"role": "user", "content": log["user_message"]})
                if log.get("ai_response"): messages.append({"role": "assistant", "content": log["ai_response"]})
        else:
            for msg in json.loads(history):
                messages.append({"role": "user" if msg.get("role") == "user" else "assistant", "content": msg.get("text", "")})
    except Exception: pass
    messages.append({"role": "user", "content": prompt})

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://zirak-pro.netlify.app", "X-Title": "Zirak Pro"}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json={"model": GEMINI_MODEL, "messages": messages}, timeout=60.0)
        res_json = res.json()
        ai_text = res_json["choices"][0]["message"]["content"]

        total_used = current_balance + len(prompt) + len(ai_text)
        await supabase_request("chat_logs", "POST", data={"username": username, "expert": expert, "user_message": prompt, "ai_response": ai_text})
        await supabase_request("users", "PATCH", data={"used_tokens": total_used}, params={"username": f"eq.{username}"})
        return {"response": ai_text, "new_balance": total_used}
    except Exception as e:
        return {"response": "کێشەی سێرڤەر. تکایە دووبارە هەوڵ بدە.", "new_balance": current_balance}
