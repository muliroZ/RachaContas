from collections.abc import Iterable, Sequence
from copy import deepcopy

from .comandos import Comando, EstadoDespesa, Evento, Observador, RepositorioDespesas
from .divisao import EstrategiaDivisao, ItemDivisao
from .importacao import FonteGastos, GastoImportado
from .valor import ComponenteDespesa


class IgualFalsa(EstrategiaDivisao):
    def dividir(
        self,
        total: int,
        participantes: list[int],
        itens: Sequence[ItemDivisao],
        params: dict[str, object],
    ) -> dict[int, int]:
        ids = list(dict.fromkeys(participantes))
        if not ids:
            raise ValueError("Informe ao menos um participante.")

        parcela, sobra = divmod(total, len(ids))
        return {
            participante_id: parcela + int(indice < sobra)
            for indice, participante_id in enumerate(ids)
        }


class ValorFixo(ComponenteDespesa):
    def __init__(self, valor: int) -> None:
        self.valor = valor

    def total(self) -> int:
        return self.valor


class FonteGastosFalsa(FonteGastos):
    def __init__(self, gastos: Iterable[GastoImportado] = ()) -> None:
        self._gastos = tuple(gastos)

    def ler(self, arquivo: bytes) -> list[GastoImportado]:
        return list(self._gastos)


class ComandoFalso(Comando):
    def __init__(self) -> None:
        self.chamadas: list[str] = []

    def executar(self) -> None:
        self.chamadas.append("executar")

    def desfazer(self) -> None:
        self.chamadas.append("desfazer")


class ObservadorFalso(Observador):
    def __init__(self) -> None:
        self.eventos: list[Evento] = []

    def atualizar(self, evento: Evento) -> None:
        self.eventos.append(evento)


class RepositorioDespesasEmMemoria(RepositorioDespesas):
    def __init__(self) -> None:
        self._despesas: dict[int, EstadoDespesa] = {}
        self._proximo_id = 1

    def criar(self, estado: EstadoDespesa) -> int:
        despesa_id = self._proximo_id
        self._despesas[despesa_id] = deepcopy(estado)
        self._proximo_id += 1
        return despesa_id

    def buscar(self, despesa_id: int) -> EstadoDespesa | None:
        return deepcopy(self._despesas.get(despesa_id))

    def salvar(self, despesa_id: int, estado: EstadoDespesa) -> None:
        if despesa_id not in self._despesas:
            raise KeyError(despesa_id)
        self._despesas[despesa_id] = deepcopy(estado)
