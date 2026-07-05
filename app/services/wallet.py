import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet


async def lock_wallets_in_order(
    db: AsyncSession,
    wallet_id_a: uuid.UUID,
    wallet_id_b: uuid.UUID,
) -> tuple[Wallet, Wallet]:
    # Always lock the lower UUID wallet first so concurrent transfers
    # (A→B and B→A at the same time) cannot deadlock waiting on each other.
    first_id, second_id = sorted([wallet_id_a, wallet_id_b])

    first_result = await db.execute(
        select(Wallet).where(Wallet.id == first_id).with_for_update()
    )
    second_result = await db.execute(
        select(Wallet).where(Wallet.id == second_id).with_for_update()
    )

    first_wallet = first_result.scalar_one()
    second_wallet = second_result.scalar_one()

    if wallet_id_a == first_id:
        return first_wallet, second_wallet
    return second_wallet, first_wallet