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


def _ids_unicos(participantes: list[int]) -> list[int]:
    ids = list(dict.fromkeys(participantes))
    if not ids:
        raise ValueError("Informe ao menos um participante.")
    return ids


def _ratear(total: int, pesos: dict[int, int]) -> dict[int, int]:
    if total < 0:
        raise ValueError("O total da despesa não pode ser negativo.")

    soma_pesos = sum(pesos.values())
    if soma_pesos == 0:
        if total:
            raise ValueError("O total positivo precisa de pelo menos um peso positivo.")
        return dict.fromkeys(pesos, 0)

    parcelas = {}
    restos = {}
    for participante_id, peso in pesos.items():
        parcelas[participante_id], restos[participante_id] = divmod(total * peso, soma_pesos)

    faltam = total - sum(parcelas.values())
    ordem = sorted(restos, key=restos.__getitem__, reverse=True)
    for participante_id in ordem[:faltam]:
        parcelas[participante_id] += 1

    return parcelas


class DivisaoIgual(EstrategiaDivisao):
    def dividir(
        self,
        total: int,
        participantes: list[int],
        itens: Sequence[ItemDivisao],
        params: dict[str, object],
    ) -> dict[int, int]:
        ids = _ids_unicos(participantes)
        return _ratear(total, dict.fromkeys(ids, 1))


class DivisaoPercentual(EstrategiaDivisao):
    def dividir(
        self,
        total: int,
        participantes: list[int],
        itens: Sequence[ItemDivisao],
        params: dict[str, object],
    ) -> dict[int, int]:
        ids = _ids_unicos(participantes)
        percentuais = params.get("percentuais_bps")
        if not isinstance(percentuais, dict) or percentuais.keys() != {str(pid) for pid in ids}:
            raise ValueError("Informe um percentual por ID de participante no JSON.")

        pesos = {}
        for participante_id in ids:
            peso = percentuais[str(participante_id)]
            if type(peso) is not int or peso < 0:
                raise ValueError("Use percentuais inteiros e não negativos em pontos-base.")
            pesos[participante_id] = peso

        if sum(pesos.values()) != 10_000:
            raise ValueError("Os percentuais devem somar 100% (10.000 pontos-base).")

        return _ratear(total, pesos)


class DivisaoComExclusao(EstrategiaDivisao):
    def dividir(
        self,
        total: int,
        participantes: list[int],
        itens: Sequence[ItemDivisao],
        params: dict[str, object],
    ) -> dict[int, int]:
        ids = _ids_unicos(participantes)
        excluidos = params.get("excluidos", [])
        if not isinstance(excluidos, list) or any(type(pid) is not int for pid in excluidos):
            raise ValueError("Informe os excluídos como uma lista de IDs inteiros.")

        ids_excluidos = set(excluidos)
        if not ids_excluidos.issubset(ids):
            raise ValueError("Os excluídos devem fazer parte da despesa.")
        if len(ids_excluidos) == len(ids):
            raise ValueError("A despesa precisa de pelo menos um participante não excluído.")

        return _ratear(total, {pid: int(pid not in ids_excluidos) for pid in ids})


class DivisaoPorConsumo(EstrategiaDivisao):
    def dividir(
        self,
        total: int,
        participantes: list[int],
        itens: Sequence[ItemDivisao],
        params: dict[str, object],
    ) -> dict[int, int]:
        ids = _ids_unicos(participantes)
        consumos = dict.fromkeys(ids, 0)
        ids_pais = {item.parent_id for item in itens if item.parent_id is not None}

        for item in itens:
            valor = item.valor
            if item.id in ids_pais or valor is None or valor == 0:
                continue

            ids_consumidores = {pessoa.id for pessoa in item.consumidores}
            if not ids_consumidores or not ids_consumidores.issubset(consumos):
                raise ValueError(f"Item {item.id} precisa de consumidores válidos da despesa.")

            pesos_item = {pid: 1 for pid in ids if pid in ids_consumidores}
            for participante_id, parcela in _ratear(valor, pesos_item).items():
                consumos[participante_id] += parcela

        return _ratear(total, consumos)