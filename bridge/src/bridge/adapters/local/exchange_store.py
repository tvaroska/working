"""Local exchange store adapter (skeleton — M1.2 fills in behavior).

In-memory exchange store for the local development environment. Satisfies the
ExchangeStoreSeam protocol. Real behavior lands in M1.2.
"""

__all__ = ["LocalExchangeStore"]


class LocalExchangeStore:
    """Local (in-memory) exchange store adapter.

    Skeleton conforming to ExchangeStoreSeam. Methods raise NotImplementedError
    until M1.2 implements the real in-memory store logic.
    """

    async def get(self, context_id: str) -> object | None:
        """Retrieve an exchange by context_id, or None if unmaterialized."""
        raise NotImplementedError("M1.2: in-memory exchange store")

    async def save(self, record: object) -> None:
        """Save or update an exchange record."""
        raise NotImplementedError("M1.2: in-memory exchange store")

    async def materialize(self, context_id: str, **kwargs) -> object:
        """Materialize an exchange (one-way transition)."""
        raise NotImplementedError("M1.2: in-memory exchange store")
