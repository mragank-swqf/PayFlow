import uuid
from pydantic import BaseModel

class WalletOut(BaseModel):
    id: uuid.UUID
    balance: float
    currency: str

    class Config:
        from_attributes = True