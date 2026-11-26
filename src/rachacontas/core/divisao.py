from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol


class ParticipanteDivisao(Protocol):
    @property
    def id(self) -> int: ...


class ItemDivisao(Protocol):
    @property
    def valor(self) -> int | None: ...

    @property
    def parent_id(self) -> int | None: ...

    @property
    def id(self) -> int: ...

    @property
    def consumidores(self) -> Sequence[ParticipanteDivisao]: ...


class EstrategiaDivisao(ABC):
    @abstractmethod
    def dividir(
        self,
        total: int,
        participantes: list[int],
        itens: Sequence[ItemDivisao],
        params: dict[str, object],
    ) -> dict[int, int]:
        """Retorna a parcela em centavos por ID de participante."""
