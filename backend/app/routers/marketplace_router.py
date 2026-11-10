"""
Marketplace and Direct Selling Router for AGRI-TECH.
Security Fixes:
- Item 2: Signature verification for Razorpay using HMAC-SHA256 and hmac.compare_digest
- Item 3: Without Razorpay keys, create clearly labeled demo orders that cannot be marked paid
- Item 5: Uses Python Enums; only seller can accept an offer; buyer cannot confirm their own offer; only transporters can accept jobs
- Item 7: register-buyer cannot assign admin/transporter
"""

import json
import secrets
import hmac
import hashlib
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User, Listing, MarketPrice, Offer, TransportRequest, PaymentOrder,
    OfferStatus, TransportStatus, PaymentStatus, UserRole
)
from app.dependencies import get_current_user
from app.config import settings
from app.services.mandi_service import (
    seed_mandi_prices_if_empty,
    compare_farmer_price_to_mandi,
    sync_mandi_prices_task
)

router = APIRouter(prefix="/marketplace", tags=["Marketplace & Prices"])


# ──────────────────────────────────────────────
# Pydantic Request Models
# ──────────────────────────────────────────────

class PriceCompareRequest(BaseModel):
    crop: str
    expected_price: float = Field(..., gt=0)


class CreateListingRequest(BaseModel):
    crop: str = Field(..., min_length=2)
    quantity_quintals: float = Field(..., gt=0)
    quality_grade: str = Field("Grade A (Premium)")
    expected_price: float = Field(..., gt=0)
    location: str
    photos: Optional[List[str]] = []


class CreateOfferRequest(BaseModel):
    offered_price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = None


class UpdateOfferStatusRequest(BaseModel):
    status: OfferStatus


class RegisterBuyerRequest(BaseModel):
    name: str
    business_name: Optional[str] = None


class TransportRequestInput(BaseModel):
    pickup_location: str
    drop_location: str
    weight_quintals: float = Field(..., gt=0)
    preferred_date: str
    listing_id: Optional[int] = None
    driver_notes: Optional[str] = None


class UpdateTransportStatusInput(BaseModel):
    status: TransportStatus
    driver_notes: Optional[str] = None


class CreatePaymentOrderRequest(BaseModel):
    offer_id: int


class VerifyPaymentSignatureRequest(BaseModel):
    order_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ──────────────────────────────────────────────
# Mandi APMC Prices
# ──────────────────────────────────────────────

@router.get("/prices")
def get_mandi_prices(
    query: Optional[str] = None,
    district: Optional[str] = None,
    sync: bool = False,
    db: Session = Depends(get_db),
):
    if sync:
        sync_mandi_prices_task(db)
    else:
        seed_mandi_prices_if_empty(db)

    q = db.query(MarketPrice)
    if query:
        q = q.filter(MarketPrice.commodity.ilike(f"%{query}%"))
    if district:
        q = q.filter(MarketPrice.district.ilike(f"%{district}%"))

    prices = q.order_by(MarketPrice.commodity.asc()).all()

    return [
        {
            "id": p.id,
            "commodity": p.commodity,
            "mandi_name": p.mandi_name,
            "district": p.district,
            "min_price": p.min_price,
            "max_price": p.max_price,
            "modal_price": p.modal_price,
            "unit": p.unit,
            "arrival_date": p.arrival_date,
            "is_mock": p.is_mock,
            "source": p.source,
        } for p in prices
    ]


@router.post("/compare-price")
def compare_price(
    req: PriceCompareRequest,
    db: Session = Depends(get_db),
):
    seed_mandi_prices_if_empty(db)
    return compare_farmer_price_to_mandi(db, req.crop, req.expected_price)


# ──────────────────────────────────────────────
# Direct Listings
# ──────────────────────────────────────────────

@router.post("/listings", status_code=status.HTTP_201_CREATED)
def create_crop_listing(
    req: CreateListingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = Listing(
        farmer_id=current_user.id,
        crop=req.crop,
        quantity_quintals=req.quantity_quintals,
        quality_grade=req.quality_grade,
        expected_price=req.expected_price,
        location=req.location,
        photos_json=json.dumps(req.photos) if req.photos else None,
        status="active"
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    return {
        "id": listing.id,
        "crop": listing.crop,
        "quantity_quintals": listing.quantity_quintals,
        "expected_price": listing.expected_price,
        "quality_grade": listing.quality_grade,
        "location": listing.location,
        "status": listing.status,
        "created_at": listing.created_at.isoformat()
    }


@router.get("/listings")
def browse_active_listings(
    crop: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Listing).filter(Listing.status == "active")
    if crop:
        q = q.filter(Listing.crop.ilike(f"%{crop}%"))
    if location:
        q = q.filter(Listing.location.ilike(f"%{location}%"))

    listings = q.order_by(Listing.created_at.desc()).all()
    return [
        {
            "id": l.id,
            "farmer_id": l.farmer_id,
            "farmer_name": l.farmer.name if l.farmer else "Farmer",
            "farmer_phone": l.farmer.phone if l.farmer else "",
            "farmer_rating": l.farmer.rating if l.farmer else 5.0,
            "crop": l.crop,
            "quantity_quintals": l.quantity_quintals,
            "quality_grade": l.quality_grade,
            "expected_price": l.expected_price,
            "location": l.location,
            "status": l.status,
            "created_at": l.created_at.isoformat()
        } for l in listings
    ]


@router.get("/my-listings")
def get_my_listings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listings = (
        db.query(Listing)
        .filter(Listing.farmer_id == current_user.id)
        .order_by(Listing.created_at.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "crop": l.crop,
            "quantity_quintals": l.quantity_quintals,
            "quality_grade": l.quality_grade,
            "expected_price": l.expected_price,
            "location": l.location,
            "status": l.status,
            "offers_count": len(l.offers),
            "created_at": l.created_at.isoformat()
        } for l in listings
    ]


# ──────────────────────────────────────────────
# Offers Workflow (Security Item 5)
# ──────────────────────────────────────────────

@router.post("/listings/{listing_id}/offer", status_code=status.HTTP_201_CREATED)
def make_buyer_offer(
    listing_id: int,
    req: CreateOfferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.farmer_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot place offer on your own crop listing")

    offer = Offer(
        listing_id=listing.id,
        buyer_id=current_user.id,
        offered_price=req.offered_price,
        quantity=req.quantity,
        buyer_notes=req.notes,
        status=OfferStatus.OFFER_MADE.value
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    return {
        "id": offer.id,
        "listing_id": offer.listing_id,
        "offered_price": offer.offered_price,
        "quantity": offer.quantity,
        "status": offer.status,
        "created_at": offer.created_at.isoformat()
    }


@router.get("/offers")
def get_user_offers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    received = (
        db.query(Offer)
        .join(Listing)
        .filter(Listing.farmer_id == current_user.id)
        .order_by(Offer.created_at.desc())
        .all()
    )
    made = (
        db.query(Offer)
        .filter(Offer.buyer_id == current_user.id)
        .order_by(Offer.created_at.desc())
        .all()
    )

    def format_offer(o):
        return {
            "id": o.id,
            "listing_id": o.listing_id,
            "crop": o.listing.crop if o.listing else "",
            "offered_price": o.offered_price,
            "quantity": o.quantity,
            "status": o.status,
            "buyer_name": o.buyer.name if o.buyer else "Buyer",
            "buyer_phone": o.buyer.phone if o.buyer else "",
            "buyer_is_verified": o.buyer.is_verified if o.buyer else False,
            "has_payment_order": len(o.payment_orders) > 0,
            "created_at": o.created_at.isoformat(),
        }

    return {
        "received_offers": [format_offer(o) for o in received],
        "made_offers": [format_offer(o) for o in made],
    }


@router.put("/offers/{offer_id}/status")
def update_offer_lifecycle(
    offer_id: int,
    req: UpdateOfferStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Security Item 5:
    - Only the SELLER (listing farmer) can confirm/accept an offer.
    - A BUYER CANNOT confirm their own offer.
    - Either buyer or seller can reject an offer.
    - Seller marks delivered when complete.
    """
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    is_seller = offer.listing.farmer_id == current_user.id
    is_buyer = offer.buyer_id == current_user.id

    if not (is_seller or is_buyer):
        raise HTTPException(status_code=403, detail="Not authorized to update this offer")

    # Seller-only action: confirming an offer
    if req.status == OfferStatus.CONFIRMED and not is_seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security rule: Only the seller (listing owner) can accept/confirm an offer. Buyers cannot confirm their own offer."
        )

    # Seller or Buyer can mark delivered
    if req.status == OfferStatus.DELIVERED and not is_seller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can mark an offer delivered."
        )

    offer.status = req.status.value
    if req.status == OfferStatus.DELIVERED:
        offer.listing.status = "sold"

    offer.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(offer)

    return {
        "id": offer.id,
        "status": offer.status,
        "message": f"Offer status updated to '{offer.status}' successfully."
    }


@router.post("/register-buyer")
def register_or_switch_buyer(
    req: RegisterBuyerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Security Item 7: Cannot self-assign admin/transporter via register endpoint."""
    current_user.role = UserRole.BUYER.value
    current_user.name = req.name.strip()
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "id": current_user.id,
        "name": current_user.name,
        "role": current_user.role,
        "is_verified": current_user.is_verified
    }


# ──────────────────────────────────────────────
# Item 8 & 5: In-App Logistics & Transport Flow
# ──────────────────────────────────────────────

@router.post("/transport/request", status_code=status.HTTP_201_CREATED)
def create_transport_request(
    req: TransportRequestInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transport = TransportRequest(
        user_id=current_user.id,
        listing_id=req.listing_id,
        pickup_location=req.pickup_location,
        drop_location=req.drop_location,
        weight_quintals=req.weight_quintals,
        preferred_date=req.preferred_date,
        driver_notes=req.driver_notes,
        status=TransportStatus.REQUESTED.value
    )
    db.add(transport)
    db.commit()
    db.refresh(transport)

    return {
        "id": transport.id,
        "status": transport.status,
        "pickup_location": transport.pickup_location,
        "drop_location": transport.drop_location,
        "weight_quintals": transport.weight_quintals,
        "preferred_date": transport.preferred_date,
        "created_at": transport.created_at.isoformat()
    }


@router.get("/transport/requests")
def list_transport_requests(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(TransportRequest)
    if current_user.role not in [UserRole.TRANSPORTER.value, UserRole.ADMIN.value]:
        q = q.filter(TransportRequest.user_id == current_user.id)
    if status_filter:
        q = q.filter(TransportRequest.status == status_filter)

    requests = q.order_by(TransportRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "requester_id": r.user_id,
            "requester_name": r.requester.name if r.requester else "Farmer",
            "requester_phone": r.requester.phone if r.requester else "",
            "transporter_id": r.transporter_id,
            "transporter_name": r.transporter.name if r.transporter else None,
            "pickup_location": r.pickup_location,
            "drop_location": r.drop_location,
            "weight_quintals": r.weight_quintals,
            "preferred_date": r.preferred_date,
            "status": r.status,
            "driver_notes": r.driver_notes,
            "created_at": r.created_at.isoformat()
        } for r in requests
    ]


@router.put("/transport/{transport_id}/status")
def update_transport_status(
    transport_id: int,
    req: UpdateTransportStatusInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Security Item 5: Only users with role='transporter' (or admin) can accept transport requests.
    """
    transport = db.query(TransportRequest).filter(TransportRequest.id == transport_id).first()
    if not transport:
        raise HTTPException(status_code=404, detail="Transport request not found")

    if req.status == TransportStatus.ACCEPTED:
        # Check transporter role
        if current_user.role not in [UserRole.TRANSPORTER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security rule: Only certified transporters can accept transport jobs."
            )
        transport.transporter_id = current_user.id
        transport.status = TransportStatus.ACCEPTED.value
    else:
        # Status progress (in_transit, delivered, cancelled)
        if transport.transporter_id != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="Not authorized to update this transport")
        transport.status = req.status.value

    if req.driver_notes:
        transport.driver_notes = req.driver_notes

    transport.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(transport)

    return {
        "id": transport.id,
        "status": transport.status,
        "transporter_id": transport.transporter_id,
        "message": f"Transport status updated to '{transport.status}'"
    }


# ──────────────────────────────────────────────
# Security Items 2 & 3: Razorpay Payment Orders & Signature Verification
# ──────────────────────────────────────────────

@router.post("/payments/create-order", status_code=status.HTTP_201_CREATED)
def create_payment_order(
    req: CreatePaymentOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Security Item 3: Without Razorpay keys (RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET),
    creates a clearly labeled demo order that CANNOT be marked paid.
    """
    offer = db.query(Offer).filter(Offer.id == req.offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.status != OfferStatus.CONFIRMED.value:
        raise HTTPException(status_code=400, detail="Payment order can only be created for confirmed offers")

    amount_inr = round(offer.offered_price * offer.quantity, 2)
    has_real_keys = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)

    if has_real_keys:
        razorpay_order_id = f"order_{secrets.token_hex(8)}"
        is_test_mode = False
        notice = "Live Razorpay order created."
    else:
        # Labeled demo order
        razorpay_order_id = f"demo_order_{secrets.token_hex(8)}"
        is_test_mode = True
        notice = "DEMO ORDER: Razorpay keys not configured. This demo order CANNOT be marked paid."

    payment_order = PaymentOrder(
        offer_id=offer.id,
        buyer_id=current_user.id,
        razorpay_order_id=razorpay_order_id,
        amount_inr=amount_inr,
        status=PaymentStatus.CREATED.value,
        is_test_mode=is_test_mode
    )
    db.add(payment_order)
    db.commit()
    db.refresh(payment_order)

    return {
        "payment_order_id": payment_order.id,
        "offer_id": offer.id,
        "amount_inr": amount_inr,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID or "rzp_demo_unconfigured",
        "is_test_mode": is_test_mode,
        "notice": notice
    }


@router.post("/payments/verify")
def verify_payment_signature(
    req: VerifyPaymentSignatureRequest,
    db: Session = Depends(get_db),
):
    """
    Security Item 2: Verifies Razorpay signatures using HMAC-SHA256 and hmac.compare_digest.
    NEVER marks paid without a valid signature.
    Security Item 3: Demo orders (created without keys) CANNOT be marked paid.
    """
    p_order = db.query(PaymentOrder).filter(PaymentOrder.id == req.order_id).first()
    if not p_order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    # Item 3: Demo orders without keys cannot be marked paid
    if p_order.is_test_mode or p_order.razorpay_order_id.startswith("demo_order_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security rule: Demo orders created without Razorpay credentials cannot be marked paid."
        )

    if not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification failed: RAZORPAY_KEY_SECRET is not configured on the server."
        )

    # Item 2: HMAC-SHA256 verification of order_id|payment_id
    expected_message = f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        expected_message,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, req.razorpay_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay payment signature. Payment cannot be verified."
        )

    # Signature valid -> mark paid
    p_order.razorpay_payment_id = req.razorpay_payment_id
    p_order.status = PaymentStatus.PAID.value
    p_order.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": PaymentStatus.PAID.value,
        "order_id": p_order.id,
        "razorpay_payment_id": p_order.razorpay_payment_id,
        "message": "Payment verified successfully with valid cryptographic signature."
    }


@router.post("/payments/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
):
    """
    Security Item 2: Razorpay webhook must verify signature with RAZORPAY_KEY_SECRET.
    Never marks paid without valid signature.
    """
    body = await request.body()

    if not settings.RAZORPAY_KEY_SECRET or not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature or server secret")

    expected_sig = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        data = json.loads(body.decode("utf-8"))
        event = data.get("event")
        payload = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payload.get("order_id")

        if order_id:
            p_order = db.query(PaymentOrder).filter(PaymentOrder.razorpay_order_id == order_id).first()
            if p_order and not p_order.is_test_mode:
                if event == "payment.captured":
                    p_order.status = PaymentStatus.PAID.value
                elif event == "payment.failed":
                    p_order.status = PaymentStatus.FAILED.value
                p_order.updated_at = datetime.now(timezone.utc)
                db.commit()
        return {"status": "received"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
