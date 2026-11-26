from abc import ABC, abstractmethod
from dataclasses import dataclass

from rachacontas.enums import TipoEvento

type EstadoDespesa = dict[str, object]


@dataclass(frozen=True)
class Evento:
    tipo: TipoEvento
    grupo_id: int
    despesa_id: int


class Comando(ABC):
    @abstractmethod
    def executar(self) -> None: ...

    @abstractmethod
    def desfazer(self) -> None: ...


class Observador(ABC):
    @abstractmethod
    def atualizar(self, evento: Evento) -> None: ...


class RepositorioDespesas(ABC):
    @abstractmethod
    def criar(self, estado: EstadoDespesa) -> int:
        """Persiste uma despesa e retorna o ID gerado."""

    @abstractmethod
    def buscar(self, despesa_id: int) -> EstadoDespesa | None:
        """Retorna uma cópia do estado, inclusive para despesas excluídas."""

    @abstractmethod
    def salvar(self, despesa_id: int, estado: EstadoDespesa) -> None:
        """Substitui o estado de uma despesa existente; ID ausente gera KeyError."""
