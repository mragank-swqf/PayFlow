from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.transaction import TransactionListResponse, TransactionOut
import uuid

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    offset = (page - 1) * page_size

    wallet_filter = or_(
        Transaction.sender_wallet_id == wallet.id,
        Transaction.receiver_wallet_id == wallet.id,
    )

    count_result = await db.execute(
        select(func.count()).select_from(Transaction).where(wallet_filter)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Transaction)
        .where(wallet_filter)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    transactions = result.scalars().all()

    return TransactionListResponse(
        data=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            or_(
                Transaction.sender_wallet_id == wallet.id,
                Transaction.receiver_wallet_id == wallet.id,
            ),
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    return transaction