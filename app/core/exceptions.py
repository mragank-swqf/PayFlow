class PayFlowError(Exception):
    """Base exception for all PayFlow domain errors."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InsufficientFundsError(PayFlowError):
    def __init__(self, message: str = "Insufficient funds") -> None:
        super().__init__(
            code="INSUFFICIENT_FUNDS",
            message=message,
            status_code=422,
        )


class WalletLockedError(PayFlowError):
    def __init__(self, message: str = "Wallet is locked") -> None:
        super().__init__(
            code="WALLET_LOCKED",
            message=message,
            status_code=423,
        )


class DuplicateTransactionError(PayFlowError):
    def __init__(self, message: str = "Duplicate transaction") -> None:
        super().__init__(
            code="DUPLICATE_TRANSACTION",
            message=message,
            status_code=409,
        )


class WalletNotFoundError(PayFlowError):
    def __init__(self, message: str = "Wallet not found") -> None:
        super().__init__(
            code="WALLET_NOT_FOUND",
            message=message,
            status_code=404,
        )


class ReceiverNotFoundError(PayFlowError):
    def __init__(self, message: str = "Receiver not found") -> None:
        super().__init__(
            code="RECEIVER_NOT_FOUND",
            message=message,
            status_code=404,
        )


class SelfTransferError(PayFlowError):
    def __init__(self, message: str = "Cannot transfer to yourself") -> None:
        super().__init__(
            code="SELF_TRANSFER",
            message=message,
            status_code=422,
        )


class TransactionNotFoundError(PayFlowError):
    def __init__(self, message: str = "Transaction not found") -> None:
        super().__init__(
            code="TRANSACTION_NOT_FOUND",
            message=message,
            status_code=404,
        )


class EmailAlreadyRegisteredError(PayFlowError):
    def __init__(self, message: str = "Email already registered") -> None:
        super().__init__(
            code="EMAIL_ALREADY_REGISTERED",
            message=message,
            status_code=409,
        )