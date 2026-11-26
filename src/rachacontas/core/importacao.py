from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GastoImportado:
    descricao: str
    valor: int
    linha: int


class FonteGastos(ABC):
    @abstractmethod
    def ler(self, arquivo: bytes) -> list[GastoImportado]:
        """Lê os gastos do arquivo, com os valores em centavos."""
