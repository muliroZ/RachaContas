from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass


class ErroImportacao(Exception):
    """Erro de validação com falhas acumuladas por linha durante a importação."""

    def __init__(self, erros: Sequence[str]) -> None:
        self.erros = list(erros)
        super().__init__("; ".join(self.erros))


@dataclass(frozen=True)
class GastoImportado:
    descricao: str
    valor: int
    linha: int
    pagador: str | None = None


class FonteGastos(ABC):
    @abstractmethod
    def ler(self, arquivo: bytes) -> list[GastoImportado]:
        """Lê os gastos do arquivo, com os valores em centavos."""
