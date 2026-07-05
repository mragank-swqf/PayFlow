VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"SUCCESS", "FAILED"},
}


class InvalidTransactionTransitionError(Exception):
    def __init__(self, current: str, next_status: str) -> None:
        self.current = current
        self.next_status = next_status
        super().__init__(f"Invalid transaction transition: {current} → {next_status}")


class TransactionStateMachine:
    @staticmethod
    def transition(current: str, next_status: str) -> str:
        allowed = VALID_TRANSITIONS.get(current, set())
        if next_status not in allowed:
            raise InvalidTransactionTransitionError(current, next_status)
        return next_status