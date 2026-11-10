"""
Admin Router for AGRI-TECH.
Provides administrative oversight: review flagged chatbot answers,
verify buyers, view analytics, and edit knowledge base documents.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Listing, ChatSession, ChatMessage, Offer
from app.dependencies import get_current_user
from app.services.rag_service import KNOWLEDGE_DIR, load_knowledge_base

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


class VerifyBuyerRequest(BaseModel):
    is_verified: bool


class KnowledgeEditRequest(BaseModel):
    content: str


@router.get("/analytics")
def get_system_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Overview analytics for administration dashboard.
    """
    total_users = db.query(User).count()
    farmers_count = db.query(User).filter(User.role == "farmer").count()
    buyers_count = db.query(User).filter(User.role == "buyer").count()
    active_listings = db.query(Listing).filter(Listing.status == "active").count()
    total_chats = db.query(ChatSession).count()
    flagged_messages = db.query(ChatMessage).filter(ChatMessage.is_flagged == True).count()  # noqa: E712
    total_offers = db.query(Offer).count()

    return {
        "users": {
            "total": total_users,
            "farmers": farmers_count,
            "buyers": buyers_count
        },
        "marketplace": {
            "active_listings": active_listings,
            "total_offers": total_offers
        },
        "chatbot": {
            "total_sessions": total_chats,
            "flagged_answers": flagged_messages
        }
    }


@router.put("/verify-buyer/{user_id}")
def toggle_buyer_verification(
    user_id: int,
    req: VerifyBuyerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Admin toggle to verify buyers with the 'Verified Buyer' trust badge.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_verified = req.is_verified
    db.commit()

    return {
        "user_id": target_user.id,
        "name": target_user.name,
        "role": target_user.role,
        "is_verified": target_user.is_verified,
        "message": "Buyer verification status updated."
    }


@router.get("/knowledge")
def list_knowledge_documents(
    current_user: User = Depends(get_current_user),
):
    """List all knowledge base documents available for RAG."""
    docs = []
    if os.path.exists(KNOWLEDGE_DIR):
        for f in sorted(os.listdir(KNOWLEDGE_DIR)):
            if f.endswith(".md"):
                fpath = os.path.join(KNOWLEDGE_DIR, f)
                with open(fpath, "r", encoding="utf-8") as file:
                    content = file.read()
                docs.append({
                    "filename": f,
                    "title": f.replace("_", " ").replace(".md", "").title(),
                    "size_bytes": os.path.getsize(fpath),
                    "content": content
                })
    return docs


@router.put("/knowledge/{filename}")
def update_knowledge_document(
    filename: str,
    req: KnowledgeEditRequest,
    current_user: User = Depends(get_current_user),
):
    """Update content of a verified knowledge base document."""
    # Prevent path traversal
    safe_filename = os.path.basename(filename)
    if not safe_filename.endswith(".md"):
        safe_filename += ".md"

    fpath = os.path.join(KNOWLEDGE_DIR, safe_filename)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(req.content)

    # Reload in-memory RAG index
    load_knowledge_base()

    return {
        "filename": safe_filename,
        "status": "updated",
        "message": "Knowledge document updated and RAG index reloaded."
    }

