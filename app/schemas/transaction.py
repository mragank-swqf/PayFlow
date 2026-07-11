import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class DepositRequest(BaseModel):
    amount: float = Field(
        gt=0,
        le=100000,
        description="Deposit amount in INR. Must be > 0 and <= 100000.",
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_valid(cls, value: float) -> float:
        if value <= 0 or value > 100000:
            raise ValueError("Amount must be greater than 0 and at most 100000")
        return value


class WithdrawRequest(BaseModel):
    amount: float = Field(
        gt=0,
        le=100000,
        description="Withdrawal amount in INR. Must be > 0 and <= 100000.",
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_valid(cls, value: float) -> float:
        if value <= 0 or value > 100000:
            raise ValueError("Amount must be greater than 0 and at most 100000")
        return value


class TransferRequest(BaseModel):
    amount: float = Field(
        gt=0,
        le=100000,
        description="Transfer amount in INR. Must be > 0 and <= 100000.",
    )
    to_user_email: EmailStr = Field(
        description="Recipient email. Must not be the sender's email (checked in route).",
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_valid(cls, value: float) -> float:
        if value <= 0 or value > 100000:
            raise ValueError("Amount must be greater than 0 and at most 100000")
        return value


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_wallet_id: uuid.UUID | None
    receiver_wallet_id: uuid.UUID | None
    amount: float
    currency: str
    type: str
    status: str
    failure_reason: str | None
    created_at: datetime


class TransactionListResponse(BaseModel):
    data: list[TransactionOut]
    total: int
    page: int
    page_size: int