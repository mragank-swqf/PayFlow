from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_idempotency_key
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletOut
from app.models.transaction import Transaction
from app.schemas.transaction import DepositRequest, TransactionOut, TransferRequest, WithdrawRequest
from app.services.idempotency import IdempotencyContext, store_idempotency_key
from app.services.state_machine import TransactionStateMachine
from app.services.wallet import lock_wallets_in_order


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

@router.post("/withdraw", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def withdraw(
    payload: WithdrawRequest,
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

    if wallet.is_locked:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Wallet is locked")

    transaction = Transaction(
        sender_wallet_id=wallet.id,
        amount=payload.amount,
        currency=wallet.currency,
        type="WITHDRAWAL",
        status="PENDING",
        idempotency_key=idem.key,
    )
    db.add(transaction)
    await db.flush()

    if wallet.balance < payload.amount:
        transaction.status = "FAILED"
        transaction.failure_reason = "Insufficient funds"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Insufficient funds")

    wallet.balance -= payload.amount
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

@router.post("/transfer", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def transfer(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sender_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    sender_wallet = sender_result.scalar_one_or_none()
    if not sender_wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    if payload.to_user_email == current_user.email:
        transaction = Transaction(
            sender_wallet_id=sender_wallet.id,
            amount=payload.amount,
            currency=sender_wallet.currency,
            type="TRANSFER",
            status="PENDING",
        )
        db.add(transaction)
        await db.flush()
        transaction.status = TransactionStateMachine.transition(transaction.status, "FAILED")
        transaction.failure_reason = "Cannot transfer to yourself"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot transfer to yourself",
        )

    receiver_result = await db.execute(
        select(User).where(User.email == payload.to_user_email)
    )
    receiver_user = receiver_result.scalar_one_or_none()
    if not receiver_user:
        transaction = Transaction(
            sender_wallet_id=sender_wallet.id,
            amount=payload.amount,
            currency=sender_wallet.currency,
            type="TRANSFER",
            status="PENDING",
        )
        db.add(transaction)
        await db.flush()
        transaction.status = TransactionStateMachine.transition(transaction.status, "FAILED")
        transaction.failure_reason = "Receiver not found"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver not found")

    receiver_wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == receiver_user.id)
    )
    receiver_wallet = receiver_wallet_result.scalar_one_or_none()
    if not receiver_wallet:
        transaction = Transaction(
            sender_wallet_id=sender_wallet.id,
            amount=payload.amount,
            currency=sender_wallet.currency,
            type="TRANSFER",
            status="PENDING",
        )
        db.add(transaction)
        await db.flush()
        transaction.status = TransactionStateMachine.transition(transaction.status, "FAILED")
        transaction.failure_reason = "Receiver wallet not found"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver wallet not found",
        )

    sender_wallet, receiver_wallet = await lock_wallets_in_order(
        db, sender_wallet.id, receiver_wallet.id
    )

    transaction = Transaction(
        sender_wallet_id=sender_wallet.id,
        receiver_wallet_id=receiver_wallet.id,
        amount=payload.amount,
        currency=sender_wallet.currency,
        type="TRANSFER",
        status="PENDING",
    )
    db.add(transaction)
    await db.flush()

    if sender_wallet.balance < payload.amount:
        transaction.status = TransactionStateMachine.transition(transaction.status, "FAILED")
        transaction.failure_reason = "Insufficient funds"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient funds",
        )

    sender_wallet.balance -= payload.amount
    receiver_wallet.balance += payload.amount
    transaction.status = TransactionStateMachine.transition(transaction.status, "SUCCESS")

    await db.commit()
    await db.refresh(transaction)
    return transaction