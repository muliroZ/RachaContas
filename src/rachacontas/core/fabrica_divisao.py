from abc import ABC, abstractmethod

from rachacontas.core.divisao import (
    DivisaoComExclusao,
    DivisaoIgual,
    DivisaoPercentual,
    DivisaoPorConsumo,
    EstrategiaDivisao,
)
from rachacontas.enums import TipoDivisao


class CriadorDivisao(ABC):
    @abstractmethod
    def criar(self) -> EstrategiaDivisao: ...


class CriadorDivisaoIgual(CriadorDivisao):
    def criar(self) -> EstrategiaDivisao:
        return DivisaoIgual()


class CriadorDivisaoPercentual(CriadorDivisao):
    def criar(self) -> EstrategiaDivisao:
        return DivisaoPercentual()


class CriadorDivisaoComExclusao(CriadorDivisao):
    def criar(self) -> EstrategiaDivisao:
        return DivisaoComExclusao()


class CriadorDivisaoPorConsumo(CriadorDivisao):
    def criar(self) -> EstrategiaDivisao:
        return DivisaoPorConsumo()


_CRIADORES = {
    TipoDivisao.IGUAL: CriadorDivisaoIgual(),
    TipoDivisao.PERCENTUAL: CriadorDivisaoPercentual(),
    TipoDivisao.COM_EXCLUSAO: CriadorDivisaoComExclusao(),
    TipoDivisao.POR_CONSUMO: CriadorDivisaoPorConsumo(),
}


def criar_estrategia(tipo: TipoDivisao | str) -> EstrategiaDivisao:
    return _CRIADORES[TipoDivisao(tipo)].criar()