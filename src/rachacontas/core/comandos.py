from abc import ABC, abstractmethod
from dataclasses import dataclass

from rachacontas.enums import TipoEvento

type EstadoDespesa = dict[str, object]


# Interfaces para implementações dos padrões Command e Observer
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


# Comandos concretos
class CriarDespesa(Comando):
    def __init__(self, repo: RepositorioDespesas, estado_inicial: EstadoDespesa) -> None:
        self.repo = repo
        self.estado = estado_inicial
        self.despesa_id: int | None = None

    def executar(self) -> None:
        self.despesa_id = self.repo.criar(self.estado)

    def desfazer(self) -> None:
        if self.despesa_id is not None:
            ExcluirDespesa(self.repo, self.despesa_id).executar()
            self.despesa_id = None


class EditarDespesa(Comando):
    def __init__(self, repo: RepositorioDespesas, id_despesa: int, estado: EstadoDespesa) -> None:
        self.repo = repo
        self.id_despesa = id_despesa
        self.estado_novo = estado
        self.backup: EstadoDespesa | None = None

    def executar(self) -> None:
        estado_anterior = self.repo.buscar(self.id_despesa)
        if estado_anterior is not None and not estado_anterior.get("excluida", False):
            self.repo.salvar(self.id_despesa, self.estado_novo)
            self.backup = estado_anterior

    def desfazer(self) -> None:
        if self.backup is not None:
            self.repo.salvar(self.id_despesa, self.backup)
            self.backup = None


class ExcluirDespesa(Comando):
    def __init__(self, repo: RepositorioDespesas, id_despesa: int) -> None:
        self.repo = repo
        self.id_despesa = id_despesa
        self.backup: EstadoDespesa | None = None

    def executar(self) -> None:
        estado_anterior = self.repo.buscar(self.id_despesa)
        if estado_anterior is not None:
            self.repo.salvar(self.id_despesa, {**estado_anterior, "excluida": True})
            self.backup = estado_anterior

    def desfazer(self) -> None:
        if self.backup is not None:
            self.repo.salvar(self.id_despesa, self.backup)
            self.backup = None
