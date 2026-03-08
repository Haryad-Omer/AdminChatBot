from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests, json

app = FastAPI()

# --- 🌐 CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🔑 CONFIG ---
SUPABASE_URL = "https://ikmuklqzxxpsggxgklph.supabase.co" 
SUPABASE_KEY = "sb_publishable_G4Ad6UbE5foWG0n2CTl6EA_vsiBHHpR" 
ADMIN_SECRET = "Admin626"
OPENROUTER_API_KEY = "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" 
GEMINI_MODEL = "google/gemini-2.0-flash-001" 

# --- 🎭 PERSONAS (هەر ٦ کەسایەتییەکە بە بنچینەیی) ---
PROMPTS = {
    "brain": "تۆ ناوت (مێشکی بازرگانی)یە. تۆ ڕاوێژکاری سەرەکی بزنس و ستراتیژییەتیت.\nئەرکەکانت:\n١. وەڵامدانەوەی پرسیارە گشتییەکانی بازرگانی و ئیدارە.\n٢. ڕوونکردنەوەی پلانی بازرگانی و گەشەپێدان.\n٣. هەمیشە بە کوردی و بە شێوازێکی پرۆفیشناڵ و هاندەر وەڵام بدەرەوە.",
    "trans": "تۆ ناوت (وەرگێڕی بازرگانی)یە. ئەرکی تۆ تەنها وەرگێڕانە بۆ زمانی کوردی.\nئەرکەکانت:\n١. هەر دەقێک (ئینگلیزی یان چینی)ت بۆ هات، بیکە بە کوردییەکی پاراو و بازرگانی.\n٢. زاراوە بازرگانییەکان (وەک FOB, CIF, MOQ) بە کوردی ڕوون بکەرەوە.\n٣. هیچ قسەی زیادە مەکە، تەنها وەرگێڕانەکە ئەنجام بدە.",
    "calc": "تۆ ناوت (حاسیبەی لۆجستی)یە. تۆ پسپۆڕی ژمارە و قازانج و تێچوویت.\nئەرکەکانت:\n١. هەژمارکردنی قازانجی صاف (Net Profit).\n٢. هەژمارکردنی تێچووی گومرگ و گواستنەوە (Shipping & Customs).\n٣. یارمەتی بەکارهێنەر بدە بزانێت ئایا بەرهەمێک قازانجی تێدایە یان نا.\n٤. وەڵامەکانت بە ژمارە و خاڵبەندی ڕێکبخە.",
    "content": "تۆ ناوت (ستراتیژیستی ناوەڕۆک)ە. تۆ پسپۆڕی مارکێتینگ و سۆشیاڵ میدیایت.\nئەرکەکانت:\n١. نووسینی ڕیکلامی سەرنجڕاکێش (Ad Copy) بۆ فەیسبووک و ئینستاگرام.\n٢. دانانی پلانی بڵاوکردنەوە (Content Calendar).\n٣. نووسینی سکریپتی ڤیدیۆ بۆ ڕیکلامی بەرهەمەکان.\n٤. بەکارهێنانی زمانی بازاڕ و کاریگەر.",
    "report": "تۆ ناوت (ڕاپۆرتی نهێنی)یە. تۆ شیکەرەوەی داتا و ئەدای کاریت.\nئەرکەکانت:\n١. شیکردنەوەی کێشەکانی بزنسەکە.\n٢. پێدانی ئامۆژگاری ڕەخنەگرانە بۆ باشترکردنی فرۆش.\n٣. کورتکردنەوەی زانیارییە ئاڵۆزەکان بۆ ڕاپۆرتێکی پوخت.",
    "finder": "تۆ ناوت (دۆزەرەوەی بەرهەم)ە. تۆ پسپۆڕی دۆزینەوەی بەرهەمی براوەیت (Winning Products).\nئەرکەکانت:\n١. پێدانی بیرۆکەی بەرهەمی نوێ بۆ فرۆشتن.\n٢. شیکردنەوەی ئەوەی بۆچی بەرهەمێک باشە یان خراپە.\n٣. یارمەتیدان لە دۆزینەوەی بەرهەم لە عەلی بابا بەپێی خواستی بازاڕی عێراق و کوردستان."
}

# --- HELPER FUNCTIONS ---
def supabase_request(table, method="GET", data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        if method == "GET": resp = requests.get(url, headers=headers, params=params)
        elif method == "POST": resp = requests.post(url, headers=headers, json=data)
        elif method == "PATCH": resp = requests.patch(url, headers=headers, json=data, params=params)
        elif method == "DELETE": resp = requests.delete(url, headers=headers, params=params)
        return resp.json()
    except Exception as e:
        return {"message": str(e)}

# --- MODELS ---
class AdminAction(BaseModel):
    admin_key: str
    id: int = None 

class AddUserRequest(BaseModel):
    admin_key: str
    username: str
    password: str
    plan: str = "standard"

class PlanRequest(BaseModel):
    admin_key: str
    username: str
    new_plan: str

class KnowledgeRequest(BaseModel):
    admin_key: str
    topic: str
    content: str
    category: str = "brain"

class BalanceRequest(BaseModel):
    admin_key: str
    username: str
    new_balance: int

class LoginRequest(BaseModel):
    username: str
    password: str

class PersonaRequest(BaseModel):
    admin_key: str
    expert: str
    role_text: str

# --- ENDPOINTS ---
@app.get("/")
def home():
    return {"status": "Zirak AI Server Online 🟢"}

@app.post("/check_auth")
def check_auth(req: AdminAction):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    return {"status": "success"}

# --- USERS MANAGEMENT ---
@app.post("/get_users")
def get_users(req: AdminAction):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    res = supabase_request("users", "GET", params={"order": "created_at.desc"})
    if not isinstance(res, list): return []
    return res

@app.post("/add_user")
def add_user(req: AddUserRequest):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    check = supabase_request("users", "GET", params={"username": f"eq.{req.username}"})
    if isinstance(check, list) and len(check) > 0: return {"status": "error", "message": "ئەم ناوە هەیە"}
    data = {"username": req.username, "password": req.password, "used_tokens": 0, "plan": req.plan}
    supabase_request("users", "POST", data=data)
    return {"status": "success"}

@app.post("/update_balance")
def update_balance(req: BalanceRequest):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    supabase_request("users", "PATCH", data={"used_tokens": req.new_balance}, params={"username": f"eq.{req.username}"})
    return {"status": "success"}

@app.post("/update_plan")
def update_plan(req: PlanRequest):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    supabase_request("users", "PATCH", data={"plan": req.new_plan}, params={"username": f"eq.{req.username}"})
    return {"status": "success"}

@app.post("/delete_user")
def delete_user(req: BalanceRequest):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    supabase_request("users", "DELETE", params={"username": f"eq.{req.username}"})
    return {"status": "success"}

@app.post("/login")
def login(req: LoginRequest):
    users = supabase_request("users", method="GET", params={"username": f"eq.{req.username.strip()}", "password": f"eq.{req.password.strip()}"})
    if isinstance(users, list) and len(users) > 0: return {"status": "success", "user": users[0]}
    raise HTTPException(status_code=401, detail="هەڵە لە چوونەژوورەوە")

# --- CHAT & LOGS ---
@app.post("/get_logs")
def get_logs(req: AdminAction):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    res = supabase_request("chat_logs", "GET", params={"order": "created_at.desc", "limit": "50"})
    if not isinstance(res, list): return []
    return res

@app.get("/get_history")
def get_history(username: str):
    res = supabase_request("chat_logs", method="GET", params={"username": f"eq.{username}", "order": "created_at.asc"})
    if not isinstance(res, list): return []
    return res

# --- KNOWLEDGE BASE ---
@app.post("/add_knowledge")
def add_knowledge(req: KnowledgeRequest):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    data = {"topic": req.topic, "content": req.content, "category": req.category}
    supabase_request("knowledge_base", "POST", data=data)
    return {"status": "success"}

@app.post("/get_knowledge")
def get_knowledge(req: AdminAction):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    res = supabase_request("knowledge_base", "GET", params={"order": "created_at.desc"})
    if not isinstance(res, list): return []
    return res

@app.post("/delete_knowledge")
def delete_knowledge(req: AdminAction):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    supabase_request("knowledge_base", "DELETE", params={"id": f"eq.{req.id}"})
    return {"status": "success"}

# --- PERSONAS ---
@app.post("/get_personas")
def get_personas(req: AdminAction):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    
    # هەوڵدەدات لە داتابەیسەوە بیهێنێت
    db_personas = supabase_request("personas", "GET")
    
    # دروستکردنی فەرهەنگێک لەو کەسایەتییانەی کە لە داتابەیسەکەدا هەن
    db_dict = {}
    if isinstance(db_personas, list):
        for p in db_personas:
            if 'expert' in p and 'role_text' in p:
                db_dict[p['expert']] = p['role_text']
    
    # دروستکردنی لیستەکە بە دڵنیاییەوە (هەردەم ٦ کەسایەتییەکە نیشان دەدات)
    result = []
    for key, text in PROMPTS.items():
        # ئەگەر لە داتابەیس هەبوو ئەوەیان بهێنە، ئەگەرنا ئەوەی ناو کۆدەکە
        role_text = db_dict.get(key, text)
        result.append({"expert": key, "role_text": role_text})
        
    return result

@app.post("/update_persona")
def update_persona(req: PersonaRequest):
    if req.admin_key != ADMIN_SECRET: raise HTTPException(401, "Unauthorized")
    
    # سەرەتا بزانە ئەم کەسایەتییە لە داتابەیس هەیە یان نا
    check = supabase_request("personas", "GET", params={"expert": f"eq.{req.expert}"})
    
    if isinstance(check, list) and len(check) > 0:
        # ئەگەر هەبوو، تەنها ئەپدەیت (PATCH)ی بکە
        res = supabase_request("personas", "PATCH", data={"role_text": req.role_text}, params={"expert": f"eq.{req.expert}"})
    else:
        # ئەگەر نەبوو، زیادی بکە (POST)
        res = supabase_request("personas", "POST", data={"expert": req.expert, "role_text": req.role_text})
    
    # پێداچوونەوە بۆ هەڵەی داتابەیس (وەک ئەوەی خشتەکە دروست نەکرابێت)
    if isinstance(res, dict) and (res.get("code") or res.get("message")):
        raise HTTPException(status_code=500, detail=f"کێشەی داتابەیس: پێویستە خشتەی personas دروست بکەیت لە Supabase. کێشە: {res.get('message', '')}")
        
    return {"status": "success"}

# --- CHAT LOGIC ---
@app.post("/chat")
def chat_endpoint(
    prompt: str = Form(...), expert: str = Form(...), username: str = Form(...),
    history: str = Form("[]"), image_url: str = Form(None)
):
    current_balance = 0
    u = supabase_request("users", "GET", params={"username": f"eq.{username}"})
    if isinstance(u, list) and u: current_balance = u[0].get('used_tokens', 0)

    # Get Persona
    system_instruction = PROMPTS.get(expert, PROMPTS["brain"])
    try:
        # Check DB for custom persona
        p_db = supabase_request("personas", "GET", params={"expert": f"eq.{expert}"})
        if isinstance(p_db, list) and len(p_db) > 0 and p_db[0].get('role_text'):
            system_instruction = p_db[0]['role_text']
    except: pass

    # RAG Logic (Simple)
    knowledge = ""
    if expert == "brain":
        kb = supabase_request("knowledge_base", "GET")
        if isinstance(kb, list):
            for k in kb: knowledge += f"\n- {k['topic']}: {k['content']}"
    
    if knowledge:
        system_instruction += f"\n\n[OFFICIAL KNOWLEDGE BASE]:\n{knowledge}\nUse this info to answer if relevant."

    messages = [{"role": "system", "content": system_instruction}]
    try:
        hist_list = json.loads(history)
        for msg in hist_list: messages.append({"role": "user" if msg['role'] == 'user' else "assistant", "content": msg['text']})
    except: pass
    
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://zirak-pro.netlify.app", 
        "X-Title": "Zirak Pro"
    }
    data = {"model": GEMINI_MODEL, "messages": messages}
    
    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        ai_text = res.json()['choices'][0]['message']['content']
        
        new_tokens = len(prompt) + len(ai_text)
        total_used = current_balance + new_tokens
        
        supabase_request("chat_logs", "POST", data={"username": username, "expert": expert, "user_message": prompt, "ai_response": ai_text})
        supabase_request("users", "PATCH", data={"used_tokens": total_used}, params={"username": f"eq.{username}"})
        
        return {"response": ai_text, "new_balance": total_used}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "new_balance": current_balance}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    return {"url": "disabled_for_now"}