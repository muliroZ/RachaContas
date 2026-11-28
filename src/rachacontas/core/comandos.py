from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

from rachacontas.enums import TipoEvento

type EstadoDespesa = dict[str, object]


# Interfaces para implementações dos padrões Command e Observer
@dataclass(frozen=True)
class Evento:
    tipo: TipoEvento
    grupo_id: int
    despesa_id: int


@dataclass(frozen=True)
class AlteracaoDespesa:
    tipo: TipoEvento
    despesa_id: int


class Comando(ABC):
    @abstractmethod
    def executar(self) -> AlteracaoDespesa | None: ...

    @abstractmethod
    def desfazer(self) -> AlteracaoDespesa | None: ...

    def refazer(self) -> AlteracaoDespesa | None:
        return self.executar()


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
        self._exclusao: ExcluirDespesa | None = None

    def executar(self) -> AlteracaoDespesa:
        self.despesa_id = self.repo.criar(self.estado)
        self._exclusao = None
        return AlteracaoDespesa(TipoEvento.DESPESA_CRIADA, self.despesa_id)

    def desfazer(self) -> AlteracaoDespesa | None:
        if self.despesa_id is None:
            return None

        exclusao = ExcluirDespesa(self.repo, self.despesa_id)
        alteracao = exclusao.executar()
        if alteracao is not None:
            self._exclusao = exclusao
            self.despesa_id = None
        return alteracao

    def refazer(self) -> AlteracaoDespesa | None:
        if self._exclusao is None:
            return None

        alteracao = self._exclusao.desfazer()
        if alteracao is not None:
            self.despesa_id = alteracao.despesa_id
            self._exclusao = None
        return alteracao


class EditarDespesa(Comando):
    def __init__(self, repo: RepositorioDespesas, id_despesa: int, estado: EstadoDespesa) -> None:
        self.repo = repo
        self.id_despesa = id_despesa
        self.estado_novo = estado
        self.backup: EstadoDespesa | None = None

    def executar(self) -> AlteracaoDespesa | None:
        estado_anterior = self.repo.buscar(self.id_despesa)
        if estado_anterior is None or estado_anterior.get("excluida", False):
            return None

        self.repo.salvar(self.id_despesa, self.estado_novo)
        self.backup = estado_anterior
        return AlteracaoDespesa(TipoEvento.DESPESA_EDITADA, self.id_despesa)

    def desfazer(self) -> AlteracaoDespesa | None:
        if self.backup is None:
            return None

        self.repo.salvar(self.id_despesa, self.backup)
        self.backup = None
        return AlteracaoDespesa(TipoEvento.DESPESA_EDITADA, self.id_despesa)


class ExcluirDespesa(Comando):
    def __init__(self, repo: RepositorioDespesas, id_despesa: int) -> None:
        self.repo = repo
        self.id_despesa = id_despesa
        self.backup: EstadoDespesa | None = None

    def executar(self) -> AlteracaoDespesa | None:
        estado_anterior = self.repo.buscar(self.id_despesa)
        if estado_anterior is None or estado_anterior.get("excluida", False):
            return None

        self.repo.salvar(self.id_despesa, {**estado_anterior, "excluida": True})
        self.backup = estado_anterior
        return AlteracaoDespesa(TipoEvento.DESPESA_EXCLUIDA, self.id_despesa)

    def desfazer(self) -> AlteracaoDespesa | None:
        if self.backup is None:
            return None

        self.repo.salvar(self.id_despesa, self.backup)
        self.backup = None
        return AlteracaoDespesa(TipoEvento.DESPESA_RESTAURADA, self.id_despesa)


class GerenciadorComandos:
    def __init__(self) -> None:
        self.observadores: list[Observador] = []
        self._executados: defaultdict[int, list[Comando]] = defaultdict(list)
        self._desfeitos: defaultdict[int, list[Comando]] = defaultdict(list)

    def executar(self, grupo_id: int, comando: Comando) -> Evento | None:
        alteracao = comando.executar()
        if alteracao is None:
            return None

        self._executados[grupo_id].append(comando)
        self._desfeitos.pop(grupo_id, None)
        return self._publicar(grupo_id, alteracao)

    def desfazer(self, grupo_id: int) -> Evento | None:
        executados = self._executados.get(grupo_id)
        if not executados:
            return None

        comando = executados[-1]
        alteracao = comando.desfazer()
        if alteracao is None:
            return None

        executados.pop()
        self._desfeitos[grupo_id].append(comando)
        return self._publicar(grupo_id, alteracao)

    def refazer(self, grupo_id: int) -> Evento | None:
        desfeitos = self._desfeitos.get(grupo_id)
        if not desfeitos:
            return None

        comando = desfeitos[-1]
        alteracao = comando.refazer()
        if alteracao is None:
            return None

        desfeitos.pop()
        self._executados[grupo_id].append(comando)
        return self._publicar(grupo_id, alteracao)

    def _publicar(self, grupo_id: int, alteracao: AlteracaoDespesa) -> Evento:
        evento = Evento(alteracao.tipo, grupo_id, alteracao.despesa_id)
        self.notificar(evento)
        return evento

    def notificar(self, evento: Evento) -> None:
        for observador in tuple(self.observadores):
            observador.atualizar(evento)

    def inscrever(self, observador: Observador) -> None:
        if observador not in self.observadores:
            self.observadores.append(observador)

    def desinscrever(self, observador: Observador) -> None:
        if observador in self.observadores:
            self.observadores.remove(observador)
