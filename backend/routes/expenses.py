from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import logging

from ..models import get_db, User, OrganizationMember, Expense, Creator, Contract, Placement
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


def verify_org_membership(db: Session, user_id: int, org_id: int):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return membership


class ExpenseCreate(BaseModel):
    category: str = "OTHER"
    description: str
    amount_cents: int = 0
    currency: str = "USD"
    payee_name: Optional[str] = None
    creator_id: Optional[int] = None
    contract_id: Optional[int] = None
    placement_id: Optional[int] = None
    song_id: Optional[int] = None
    expense_date: Optional[str] = None
    status: str = "PENDING"
    payment_method: Optional[str] = None
    invoice_reference: Optional[str] = None
    notes: Optional[str] = None
    budget_source: Optional[str] = None


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    amount_cents: Optional[int] = None
    currency: Optional[str] = None
    payee_name: Optional[str] = None
    creator_id: Optional[int] = None
    contract_id: Optional[int] = None
    placement_id: Optional[int] = None
    song_id: Optional[int] = None
    expense_date: Optional[str] = None
    status: Optional[str] = None
    payment_method: Optional[str] = None
    invoice_reference: Optional[str] = None
    notes: Optional[str] = None
    budget_source: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


@router.get("/org/{org_id}")
def list_expenses(
    org_id: int,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    creator_id: Optional[int] = Query(None),
    contract_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_membership(db, current_user.id, org_id)
    query = db.query(Expense).filter(Expense.organization_id == org_id)
    if category:
        query = query.filter(Expense.category == category)
    if status:
        query = query.filter(Expense.status == status)
    if creator_id:
        query = query.filter(Expense.creator_id == creator_id)
    if contract_id:
        query = query.filter(Expense.contract_id == contract_id)
    expenses = query.order_by(Expense.created_at.desc()).all()
    results = []
    for e in expenses:
        results.append({
            "id": e.id,
            "organization_id": e.organization_id,
            "category": e.category,
            "description": e.description,
            "amount_cents": e.amount_cents,
            "currency": e.currency,
            "payee_name": e.payee_name,
            "creator_id": e.creator_id,
            "creator_name": e.creator.display_name if e.creator else None,
            "contract_id": e.contract_id,
            "contract_title": e.contract.title if e.contract else None,
            "placement_id": e.placement_id,
            "song_id": e.song_id,
            "expense_date": str(e.expense_date) if e.expense_date else None,
            "status": e.status,
            "payment_method": e.payment_method,
            "invoice_reference": e.invoice_reference,
            "notes": e.notes,
            "budget_source": e.budget_source,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        })
    return results


@router.post("/org/{org_id}")
def create_expense(
    org_id: int,
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_membership(db, current_user.id, org_id)
    expense = Expense(
        organization_id=org_id,
        category=data.category,
        description=data.description,
        amount_cents=data.amount_cents,
        currency=data.currency,
        payee_name=data.payee_name,
        creator_id=data.creator_id,
        contract_id=data.contract_id,
        placement_id=data.placement_id,
        song_id=data.song_id,
        expense_date=date.fromisoformat(data.expense_date) if data.expense_date else None,
        status=data.status,
        payment_method=data.payment_method,
        invoice_reference=data.invoice_reference,
        notes=data.notes,
        budget_source=data.budget_source,
        created_by_user_id=current_user.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {"id": expense.id, "message": "Expense created successfully"}


@router.put("/{expense_id}")
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    verify_org_membership(db, current_user.id, expense.organization_id)
    update_data = data.dict(exclude_unset=True, exclude_none=True)
    if "expense_date" in update_data and update_data["expense_date"]:
        update_data["expense_date"] = date.fromisoformat(update_data["expense_date"])
    for key, value in update_data.items():
        setattr(expense, key, value)
    db.commit()
    return {"message": "Expense updated successfully"}


@router.patch("/{expense_id}/status")
def update_expense_status(
    expense_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    verify_org_membership(db, current_user.id, expense.organization_id)
    if data.status not in ["PENDING", "APPROVED", "PAID", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    expense.status = data.status
    db.commit()
    return {"message": f"Expense status updated to {data.status}"}


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    verify_org_membership(db, current_user.id, expense.organization_id)
    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}


@router.get("/org/{org_id}/summary")
def get_expense_summary(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_membership(db, current_user.id, org_id)
    expenses = db.query(Expense).filter(Expense.organization_id == org_id).all()
    total_amount = sum(e.amount_cents for e in expenses)
    by_category = {}
    by_status = {}
    for e in expenses:
        cat = e.category or "OTHER"
        by_category[cat] = by_category.get(cat, 0) + e.amount_cents
        st = e.status or "PENDING"
        by_status[st] = by_status.get(st, 0) + e.amount_cents
    return {
        "total_amount_cents": total_amount,
        "total_count": len(expenses),
        "by_category": by_category,
        "by_status": by_status,
    }
