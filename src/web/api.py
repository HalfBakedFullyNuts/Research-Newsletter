#!/usr/bin/env python3
"""
ResearchPulse — FastAPI Backend
User signup, newsletter config, delivery schedule, feedback.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

# Load topics
TOPICS_PATH = Path(__file__).parent / "topics.json"
with open(TOPICS_PATH) as f:
    TOPICS = json.load(f)

# SQLite for subscribers (reuse existing schema)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.db import init_db, get_subscriber, add_subscriber, update_subscriber, remove_subscriber

app = FastAPI(title="ResearchPulse Backend", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# Init DB on startup
@app.on_event("startup")
def startup():
    init_db()


# ── Pydantic Models ──
class SignupRequest(BaseModel):
    email: str
    profession: str  # sales, marketing, product, design, hr, etc.
    topics: List[str]  # topic keys within the profession
    day: str  # monday, wednesday, friday
    time: str  # morning, midday


class FeedbackRequest(BaseModel):
    email: str
    message: str
    rating: Optional[int] = None  # 1-5


class SettingsUpdate(BaseModel):
    email: str
    topics: Optional[List[str]] = None
    day: Optional[str] = None
    time: Optional[str] = None
    unsubscribe: Optional[bool] = False


# ── Pages ──
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page — profession selection."""
    return templates.TemplateResponse("home.html", {
        "request": request,
        "professions": TOPICS
    })


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page — topic selection."""
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "professions": TOPICS
    })


@app.get("/dashboard/{email}", response_class=HTMLResponse)
async def dashboard(request: Request, email: str):
    """User dashboard — settings, billing, feedback."""
    sub = get_subscriber(email)
    if not sub:
        raise HTTPException(404, "Subscriber not found")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "subscriber": sub,
        "professions": TOPICS
    })


@app.get("/unsubscribe/{email}", response_class=HTMLResponse)
async def unsubscribe_page(request: Request, email: str):
    """Unsubscribe confirmation."""
    sub = get_subscriber(email)
    if not sub:
        raise HTTPException(404, "Subscriber not found")
    return templates.TemplateResponse("unsubscribe.html", {
        "request": request,
        "subscriber": sub
    })


# ── API Endpoints ──
@app.post("/api/signup")
async def signup(req: SignupRequest):
    """Create a new subscriber."""
    existing = get_subscriber(req.email)
    if existing:
        raise HTTPException(400, "Already subscribed")
    
    add_subscriber(req.email, req.topics, req.profession, req.day, req.time)
    return {"ok": True, "message": "Signed up! Check your email for confirmation."}


@app.post("/api/settings")
async def update_settings(req: SettingsUpdate):
    """Update subscriber settings."""
    sub = get_subscriber(req.email)
    if not sub:
        raise HTTPException(404, "Subscriber not found")
    
    if req.unsubscribe:
        remove_subscriber(req.email)
        return {"ok": True, "message": "Unsubscribed."}
    
    updates = {}
    if req.topics is not None:
        updates["topics"] = req.topics
    if req.day is not None:
        updates["day"] = req.day
    if req.time is not None:
        updates["time"] = req.time
    
    if updates:
        update_subscriber(req.email, updates)
    
    return {"ok": True, "message": "Settings updated."}


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit feedback from a subscriber."""
    sub = get_subscriber(req.email)
    if not sub:
        raise HTTPException(404, "Subscriber not found")
    
    # Save to SQLite (extend schema later)
    # For now: log to JSONL
    log_path = Path(__file__).parent.parent.parent / "cache" / "feedback.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "email": req.email,
            "message": req.message,
            "rating": req.rating,
            "timestamp": datetime.utcnow().isoformat()
        }) + "\n")
    
    return {"ok": True, "message": "Feedback received!"}


@app.get("/api/topics/{profession}")
async def get_topics(profession: str):
    """Get academic topics for a profession."""
    if profession not in TOPICS:
        raise HTTPException(404, "Profession not found")
    return TOPICS[profession]


@app.get("/api/subscriber/{email}")
async def get_subscriber_info(email: str):
    """Get subscriber info."""
    sub = get_subscriber(email)
    if not sub:
        raise HTTPException(404, "Not found")
    return sub


# ── Stripe (placeholder) ──
@app.post("/api/stripe/create-checkout-session")
async def create_checkout_session():
    """Stripe checkout session placeholder."""
    return {"ok": True, "message": "Stripe integration coming soon"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
