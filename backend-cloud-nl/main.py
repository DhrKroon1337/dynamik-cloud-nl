import os, json, re
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","")
if not OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY ontbreekt")
SHARED_SECRET = os.getenv("SHARED_SECRET","")
CORS_ORIGINS = os.getenv("CORS_ORIGINS","*")

app = FastAPI()
allow = ["*"] if CORS_ORIGINS=="*" else [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=allow, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
client = OpenAI(api_key=OPENAI_API_KEY)

def require_auth(authorization: Optional[str]):
    if not SHARED_SECRET: return
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(status_code=401, detail="Unauthorized")
    if authorization.split(" ",1)[1] != SHARED_SECRET: raise HTTPException(status_code=403, detail="Forbidden")

@app.get("/health")
def health(): return {"ok": True}

@app.post("/agent")
async def agent(authorization: Optional[str] = Header(None), body: dict = Body(...)):
    require_auth(authorization)
    text = (body.get("input_text") or "").strip()
    if not text: return {"response":"Geen tekst ontvangen."}
    r = client.chat.completions.create(model="gpt-4o-mini", messages=[
        {"role":"system","content":"Je bent AeonCore, een vriendelijke en praktische assistent. Antwoord kort, helder en in het Nederlands."},
        {"role":"user","content":text}
    ])
    return {"response": r.choices[0].message.content}

@app.post("/agent_stream")
async def agent_stream(authorization: Optional[str] = Header(None), body: dict = Body(...)):
    require_auth(authorization)
    text = (body.get("input_text") or "").strip()
    if not text: return JSONResponse({"error":"empty"}, status_code=400)
    def gen():
        stream = client.chat.completions.create(model="gpt-4o-mini", messages=[
            {"role":"system","content":"Je bent AeonCore, een vriendelijke en praktische assistent. Antwoord kort, helder en in het Nederlands."},
            {"role":"user","content":text}
        ], stream=True)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.get("content"):
                yield f"data: {chunk.choices[0].delta['content']}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.post("/intent")
async def intent(authorization: Optional[str] = Header(None), body: dict = Body(...)):
    require_auth(authorization)
    kind = (body.get("kind") or "").strip()
    idea = (body.get("idea") or "").strip()
    if not kind or not idea: return JSONResponse({"error":"missing kind/idea"}, status_code=400)
    sys = "Je bent AeonCore (NL). Lever JSON: {type, content}. type in ['spec','code','html','text']."
    if kind=='spec':
        usr = f"Zet dit idee om naar een beknopte specificatie met 3-7 user stories. IDEA: {idea}\nJSON: {{\"type\":\"spec\",\"content\":\"...\"}}"
    elif kind=='code':
        usr = f"Genereer startercode in JS of Python met korte comments. IDEA: {idea}\nJSON: {{\"type\":\"code\",\"content\":\"<code>\"}}"
    elif kind=='visualize':
        usr = f"Maak HTML-fragment met Mermaid diagram (```mermaid of <div class='mermaid'>). IDEA: {idea}\nJSON: {{\"type\":\"html\",\"content\":\"<html_fragment>\"}}"
    else:
        usr = f"Beantwoord kort. IDEA: {idea}\nJSON: {{\"type\":\"text\",\"content\":\"...\"}}"
    r = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":sys},{"role":"user","content":usr}])
    txt = r.choices[0].message.content
    try:
        import re, json as J
        m = re.search(r'\{[\s\S]*\}', txt)
        data = J.loads(m.group(0) if m else txt)
        if not isinstance(data, dict) or "type" not in data or "content" not in data: raise ValueError
        return data
    except Exception:
        return {"type":"text","content":txt}
