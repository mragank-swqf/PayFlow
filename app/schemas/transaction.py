import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)


class WithdrawRequest(BaseModel):
    amount: float = Field(gt=0, le=100000)


class TransactionOut(BaseModel):
    id: uuid.UUID
    sender_wallet_id: uuid.UUID | None
    receiver_wallet_id: uuid.UUID | None
    amount: float
    currency: str
    type: str
    status: str
    failure_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True