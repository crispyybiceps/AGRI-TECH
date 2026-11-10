"""
Admin Router for AGRI-TECH.
Security Item 1: All endpoints require require_admin check.
Admin role is granted solely via the ADMIN_PHONES environment configuration.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Listing, ChatSession, ChatMessage, Offer
from app.dependencies import require_admin
from app.services.rag_service import KNOWLEDGE_DIR, load_knowledge_base

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


class VerifyBuyerRequest(BaseModel):
    is_verified: bool


class KnowledgeEditRequest(BaseModel):
    content: str


@router.get("/analytics")
def get_system_analytics(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()
    farmers_count = db.query(User).filter(User.role == "farmer").count()
    buyers_count = db.query(User).filter(User.role == "buyer").count()
    active_listings = db.query(Listing).filter(Listing.status == "active").count()
    total_chats = db.query(ChatSession).count()
    flagged_messages = db.query(ChatMessage).filter(ChatMessage.is_flagged == True).count()
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


@router.post("/verify-buyer/{user_id}")
def verify_buyer_status(
    user_id: int,
    req: VerifyBuyerRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = req.is_verified
    db.commit()

    return {
        "user_id": user.id,
        "name": user.name,
        "is_verified": user.is_verified,
        "message": f"Buyer verification set to {user.is_verified}"
    }


@router.get("/knowledge/docs")
def list_knowledge_documents(
    current_admin: User = Depends(require_admin),
):
    import os
    if not os.path.exists(KNOWLEDGE_DIR):
        return []
    files = [f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".md")]
    return sorted(files)


@router.get("/knowledge/doc/{filename}")
def get_knowledge_document(
    filename: str,
    current_admin: User = Depends(require_admin),
):
    import os
    safe_name = os.path.basename(filename)
    path = os.path.join(KNOWLEDGE_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Knowledge doc not found")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"filename": safe_name, "content": content}


@router.put("/knowledge/doc/{filename}")
def update_knowledge_document(
    filename: str,
    req: KnowledgeEditRequest,
    current_admin: User = Depends(require_admin),
):
    import os
    safe_name = os.path.basename(filename)
    path = os.path.join(KNOWLEDGE_DIR, safe_name)

    with open(path, "w", encoding="utf-8") as f:
        f.write(req.content)

    load_knowledge_base()

    return {
        "status": "success",
        "filename": safe_name,
        "message": "Knowledge document updated and RAG re-indexed."
    }
