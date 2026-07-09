import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.celery_log import CeleryTaskLog
from app.models.transaction import Transaction
from app.workers.celery_app import celery_app

sync_engine = create_engine(settings.DATABASE_URL)
SyncSession = sessionmaker(bind=sync_engine)

SUSPICIOUS_AMOUNT_THRESHOLD = Decimal("10000")
VELOCITY_WINDOW_MINUTES = 10
VELOCITY_TRANSACTION_LIMIT = 5


def _wallet_id_for_check(transaction: Transaction) -> uuid.UUID | None:
    if transaction.type == "DEPOSIT":
        return transaction.receiver_wallet_id
    return transaction.sender_wallet_id


@celery_app.task(bind=True, name="flag_suspicious_transaction")
def flag_suspicious_transaction(self, transaction_id: str) -> None:
    with SyncSession() as session:
        transaction = session.get(Transaction, uuid.UUID(transaction_id))
        if not transaction:
            return

        wallet_id = _wallet_id_for_check(transaction)
        flagged_reasons: list[str] = []

        if Decimal(str(transaction.amount)) > SUSPICIOUS_AMOUNT_THRESHOLD:
            flagged_reasons.append("Amount exceeds ₹10,000 threshold")

        if wallet_id is not None:
            window_start = datetime.now(timezone.utc) - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
            recent_count = session.execute(
                select(func.count())
                .select_from(Transaction)
                .where(
                    Transaction.status == "SUCCESS",
                    Transaction.created_at >= window_start,
                    or_(
                        Transaction.sender_wallet_id == wallet_id,
                        Transaction.receiver_wallet_id == wallet_id,
                    ),
                )
            ).scalar_one()

            if recent_count >= VELOCITY_TRANSACTION_LIMIT:
                flagged_reasons.append("5+ transactions in 10 minutes")

        status = "FLAGGED" if flagged_reasons else "OK"
        result = "; ".join(flagged_reasons) if flagged_reasons else "No suspicious activity detected"

        log = CeleryTaskLog(
            transaction_id=transaction.id,
            task_name="flag_suspicious_transaction",
            celery_task_id=self.request.id,
            status=status,
            result=result,
        )
        session.add(log)
        session.commit()