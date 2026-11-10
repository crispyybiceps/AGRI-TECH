"""
Chatbot Router for AGRI-TECH.
Handles conversation sessions, messages, RAG queries, and expert review flagging.
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, ChatSession, ChatMessage
from app.dependencies import get_current_user
from app.services.chatbot_service import process_chat_query

router = APIRouter(prefix="/chat", tags=["AI Agricultural Chatbot"])


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    farm_id: Optional[int] = None
    language: Optional[str] = "mr"


class FlagRequest(BaseModel):
    reason: Optional[str] = "Incorrect dosage or advice"


@router.post("")
def send_chat_message(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send message to the AI Chatbot.
    Runs RAG retrieval, tool calling (weather, soil), and safety guardrails.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    lang = req.language or current_user.language_preference or "mr"

    res = process_chat_query(
        db=db,
        user_id=current_user.id,
        session_id=req.session_id,
        message=req.message.strip(),
        farm_id=req.farm_id,
        language=lang
    )
    return res


@router.get("/sessions")
def get_user_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent conversation sessions for authenticated farmer."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
def get_session_history(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full message history for a chat session."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "session_id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "sources": json.loads(m.sources_json) if m.sources_json else [],
                "is_flagged": m.is_flagged,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/messages/{message_id}/flag")
def flag_message(
    message_id: int,
    req: FlagRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    'Flag this answer' feature — farmer flags an inaccurate or unsafe answer
    for expert review by KVK specialists.
    """
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.is_flagged = True
    msg.flag_reason = req.reason
    db.commit()

    return {
        "status": "flagged",
        "message_id": msg.id,
        "notice": "Thank you. This response has been flagged and queued for agricultural expert review."
    }


@router.get("/flagged")
def list_flagged_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to view all flagged chatbot answers for quality assurance.
    """
    flagged = (
        db.query(ChatMessage)
        .filter(ChatMessage.is_flagged == True)  # noqa: E712
        .order_by(ChatMessage.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": m.id,
            "session_id": m.session_id,
            "sender": m.sender,
            "content": m.content,
            "flag_reason": m.flag_reason,
            "sources": json.loads(m.sources_json) if m.sources_json else [],
            "created_at": m.created_at.isoformat(),
        }
        for m in flagged
    ]

