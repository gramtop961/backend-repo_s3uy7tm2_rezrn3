import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document
from schemas import Lead, Event, Transcript, ChatMessage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Velodent Backend Running"}


@app.get("/test")
def test_database():
    info = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            info["database"] = "✅ Available"
            info["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            info["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                info["collections"] = db.list_collection_names()[:10]
                info["database"] = "✅ Connected & Working"
                info["connection_status"] = "Connected"
            except Exception as e:
                info["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            info["database"] = "⚠️ Database module not initialized"
    except Exception as e:
        info["database"] = f"❌ Error: {str(e)[:80]}"
    return info


# ------------------------- CRM Webhooks -------------------------

@app.post("/api/crm/lead")
def create_lead(lead: Lead):
    lead_id = create_document("lead", lead)
    # emit an event as well
    ev = Event(
        event_type="lead_captured",
        source=lead.source,
        page=lead.page,
        session_id=lead.session_id,
        payload={"lead_id": lead_id, "intent": lead.intent},
    )
    create_document("event", ev)
    return {"ok": True, "lead_id": lead_id}


class EventIn(BaseModel):
    event_type: str
    source: str = "website"
    page: Optional[str] = None
    session_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


@app.post("/api/crm/event")
def log_event(event: EventIn):
    ev = Event(**event.model_dump())
    event_id = create_document("event", ev)
    return {"ok": True, "event_id": event_id}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    page: Optional[str] = None
    consent: bool = False
    user: Optional[Dict[str, Any]] = None  # {name, email, phone}


@app.post("/api/chat")
def chat(req: ChatRequest):
    """Simple rules-based assistant for common dental flows.
    In production, swap the logic to call a private LLM via middleware.
    """
    text = (req.message or "").strip().lower()

    def reply(msg: str, intent: str = "general", quick=None):
        return {
            "reply": msg,
            "intent": intent,
            "quickReplies": quick or [
                {"label": "Book Now", "action": "book", "url": "https://cal.com/velodent-ogbkfv/20min"},
                {"label": "Check Insurance", "action": "insurance"},
                {"label": "Request Callback", "action": "callback"},
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # keyword intents
    intents = {
        "book": ["book", "appointment", "schedule", "demo"],
        "reschedule": ["reschedule", "missed", "change"],
        "cancel": ["cancel"],
        "braces": ["braces", "tightening", "adjustment"],
        "insurance": ["insurance", "covered", "verify"],
        "payment": ["pay", "payment", "billing"],
        "receptionist": ["receptionist", "ai", "assistant"],
        "callback": ["call", "phone", "contact"],
    }

    intent_detected = "general"
    for intent, kws in intents.items():
        if any(k in text for k in kws):
            intent_detected = intent
            break

    # responses
    if intent_detected == "book":
        create_document("event", Event(event_type="booking_requested", source="website", page=req.page, session_id=req.session_id))
        return reply(
            "I can help you book a visit. Use Book Now to choose a time, or share your name, email, phone, and preferred times and I’ll arrange it.",
            intent="booking",
        )
    if intent_detected == "reschedule":
        return reply(
            "No problem. Please share your name and the original appointment date, plus new preferred times. I can also send a rescheduling link.",
            intent="reschedule",
        )
    if intent_detected == "cancel":
        return reply(
            "I can assist with cancellations. Please confirm your name and appointment date so I can notify the team.",
            intent="cancel",
        )
    if intent_detected == "braces":
        return reply(
            "For braces, we typically schedule tightening every 4–8 weeks depending on your plan. If you’re due, I can help you book a slot.",
            intent="braces_guidance",
        )
    if intent_detected == "insurance":
        create_document("event", Event(event_type="insurance_check_requested", source="website", page=req.page, session_id=req.session_id))
        return reply(
            "We verify insurance by collecting your provider and member ID, then confirming coverage. I can start that if you consent to share details.",
            intent="insurance_info",
        )
    if intent_detected == "payment":
        return reply(
            "You can pay at the clinic via card or contactless. For invoices or estimates, our team can assist—would you like a callback?",
            intent="payment_info",
        )
    if intent_detected == "receptionist":
        return reply(
            "Velodent’s AI receptionist answers FAQs, helps with bookings, and can log your details privately. You control what you share.",
            intent="about_bot",
        )
    if intent_detected == "callback":
        create_document("event", Event(event_type="handoff_requested", source="website", page=req.page, session_id=req.session_id))
        return reply(
            "Sure—share your phone number and a good time to reach you, and we’ll arrange a call.",
            intent="callback",
        )

    return reply("How can I help today? I can assist with bookings, insurance, braces schedules, or payments.")


# ------------------------- Transcripts -------------------------

class TranscriptIn(BaseModel):
    session_id: str
    page: Optional[str] = None
    lead_name: Optional[str] = None
    lead_email: Optional[str] = None
    lead_phone: Optional[str] = None
    messages: list[ChatMessage]


@app.post("/api/chat/transcript")
def save_transcript(t: TranscriptIn):
    tr = Transcript(**t.model_dump())
    transcript_id = create_document("transcript", tr)
    return {"ok": True, "transcript_id": transcript_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
