from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_idempotency_key
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletOut
from app.models.transaction import Transaction
from app.schemas.transaction import DepositRequest, TransactionOut
from app.services.idempotency import IdempotencyContext, store_idempotency_key

router = APIRouter(prefix="/wallet", tags=["wallet"])

@router.get("/balance", response_model=WalletOut)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    return wallet

@router.post("/deposit", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def deposit(
    payload: DepositRequest,
    idem: IdempotencyContext = Depends(require_idempotency_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if idem.is_duplicate:
        return idem.cached_response

    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    transaction = Transaction(
        receiver_wallet_id=wallet.id,
        amount=payload.amount,
        currency=wallet.currency,
        type="DEPOSIT",
        status="PENDING",
        idempotency_key=idem.key,
    )
    db.add(transaction)
    await db.flush()

    wallet.balance += payload.amount
    transaction.status = "SUCCESS"

    response = TransactionOut.model_validate(transaction)
    await store_idempotency_key(
        idem.key,
        response.model_dump(mode="json"),
        db,
        transaction_id=transaction.id,
    )

    await db.commit()
    await db.refresh(transaction)
    return transaction