"""Dynamik • AeonCore backend: een kleine FastAPI-server die met Claude praat.

De app op je telefoon praat met deze server, en alleen deze server kent de
Claude-sleutel. Zo staat de sleutel nooit in de app.
"""

import hmac
import json
import os
from typing import Literal, Optional

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY ontbreekt (zet hem in Render of in .env)")

SHARED_SECRET = os.getenv("SHARED_SECRET", "")
if not SHARED_SECRET:
    # Zonder geheim kan iedereen met je URL op jouw kosten chatten.
    raise RuntimeError("SHARED_SECRET ontbreekt: kies een lang willekeurig wachtwoord")

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
MAX_HISTORY = 20  # aantal eerdere berichten dat meegaat als geheugen

SYSTEM_PROMPT = (
    "Je bent AeonCore, een vriendelijke en praktische assistent. "
    "Antwoord kort, helder en in het Nederlands."
)

# Bij een weigering door de veiligheidscontrole probeert de API het zelf
# opnieuw met een geschikt ander model (server-side fallback).
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

app = FastAPI(title="Dynamik AeonCore")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ORIGINS == "*" else [o.strip() for o in CORS_ORIGINS.split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
client = anthropic.Anthropic()  # leest ANTHROPIC_API_KEY uit de omgeving


# ── Verzoeken ────────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20000)


class AgentRequest(BaseModel):
    input_text: str = Field(max_length=20000)
    history: list[HistoryItem] = []


class IntentRequest(BaseModel):
    kind: str
    idea: str = Field(max_length=20000)


# ── Hulpfuncties ─────────────────────────────────────────────────────────────

def require_auth(authorization: Optional[str]) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Niet ingelogd")
    token = authorization.split(" ", 1)[1]
    if not hmac.compare_digest(token.encode(), SHARED_SECRET.encode()):
        raise HTTPException(status_code=403, detail="Verkeerd geheim")


def build_messages(history: list[HistoryItem], text: str) -> list[dict]:
    items = [h for h in history[-MAX_HISTORY:] if h.content.strip()]
    # Het eerste bericht naar Claude moet van de gebruiker zijn
    # (de begroeting van de app valt dus weg).
    while items and items[0].role != "user":
        items.pop(0)
    messages = [{"role": h.role, "content": h.content} for h in items]
    messages.append({"role": "user", "content": text})
    return messages


def ask_claude(**kwargs) -> str:
    """Roept Claude aan en vertaalt fouten naar nette meldingen voor de app."""
    try:
        response = client.beta.messages.create(model=MODEL, **FALLBACK, **kwargs)
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="De Claude-sleutel op de server klopt niet.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Even te druk, probeer het zo opnieuw.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Claude gaf een fout ({e.status_code}).")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Kan Claude niet bereiken.")

    if response.stop_reason == "refusal":
        raise HTTPException(status_code=422, detail="Claude kan hier niet bij helpen.")
    return "".join(b.text for b in response.content if b.type == "text")


# ── Endpoints ────────────────────────────────────────────────────────────────
# Gewone `def` (geen async): FastAPI draait ze in een aparte thread, zodat een
# Claude-aanroep de server niet blokkeert.

@app.get("/health")
def health():
    return {"ok": True}


@app.post("/agent")
def agent(body: AgentRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    text = body.input_text.strip()
    if not text:
        return {"response": "Geen tekst ontvangen."}
    reply = ask_claude(
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        messages=build_messages(body.history, text),
    )
    return {"response": reply}


INTENT_PROMPTS = {
    "spec": "Zet dit idee om naar een beknopte specificatie met 3-7 user stories.",
    "code": "Genereer startercode in JavaScript of Python met korte comments.",
    "visualize": (
        "Maak een HTML-fragment met een Mermaid-diagram "
        "(gebruik <div class='mermaid'>...</div>)."
    ),
}
INTENT_TYPE = {"spec": "spec", "code": "code", "visualize": "html"}

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["spec", "code", "html", "text"]},
        "content": {"type": "string"},
    },
    "required": ["type", "content"],
    "additionalProperties": False,
}


@app.post("/intent")
def intent(body: IntentRequest, authorization: Optional[str] = Header(None)):
    require_auth(authorization)
    idea = body.idea.strip()
    if not body.kind or not idea:
        raise HTTPException(status_code=400, detail="kind en idea zijn verplicht")

    task = INTENT_PROMPTS.get(body.kind, "Beantwoord kort.")
    wanted = INTENT_TYPE.get(body.kind, "text")
    raw = ask_claude(
        max_tokens=8000,
        system=SYSTEM_PROMPT + f" Geef je antwoord als JSON met type '{wanted}'.",
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": INTENT_SCHEMA},
        },
        messages=[{"role": "user", "content": f"{task}\n\nIDEE: {idea}"}],
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "text", "content": raw}
